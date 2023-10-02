import pandas as pd
import numpy as np
import datetime
from dateutil import parser
import uuid
from cointracker.objects.orderbook import Order, OrderBook
from cointracker.objects.pool import Pool, PoolRegistry, Wash
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.enumerated_values import TransactionType
from cointracker.objects.exceptions import AssetNotFoundError
from cointracker.pricing.getAssetPrice import getAssetPrice
from cointracker.settings.config import cfg
from cointracker.util.dialogue import register_asset_dialogue


def parse_orderbook(filename, sheet) -> pd.DataFrame:
    """Loads an orderbook from the input file and parses it, combining common orders within the same day."""
    # if isinstance(filename, Path):
    #     filename = str(filename)
    xl_file = pd.ExcelFile(filename)

    df = xl_file.parse(sheet)

    # change all dates into timezone-aware datetime objects to be able to compare
    # NOTE: As (regular) Coinbase doesn't provide accurate timestamps, we have to
    # hope that things work assuming it's 12AM
    for index, _ in df.iterrows():
        dateObject = df.loc[index, "Date(UTC)"]
        if not isinstance(dateObject, datetime.datetime):
            dateObject = parser.parse(dateObject)  # parse the date to datetime

        df.loc[index, "Date(UTC)"] = dateObject.replace(
            tzinfo=datetime.timezone.utc
        )  # convert to non-naive UTC

        orderType = df.loc[index, "Type"]
        orderType = orderType.upper()

    print("Order book loaded...dates converted to UTC")

    # Lets clean up the order book by combining small orders that occurred at
    # the same time and averaging their cost
    partialOrderNum = 1
    avg_1_spot_fiat = np.nan
    avg_2_spot_fiat = np.nan
    fee_spot_fiat = np.nan

    for index, _ in df.iterrows():
        # possible matches are orders occurring on the same day
        potMergersMask = (
            (
                df["Date(UTC)"].apply(lambda x: x.strftime("%Y/%m/%d"))
                == df.loc[index, "Date(UTC)"].strftime("%Y/%m/%d")
            )
            & (df["Market"] == df.loc[index, "Market"])
            & (df["Type"] == df.loc[index, "Type"])
            & (df["Fee Asset"] == df.loc[index, "Fee Asset"])
        )
        tempMergers = df[potMergersMask]
        numPartialOrders = len(tempMergers)
        if numPartialOrders > 1:  # nothing to merge if there's only one in the list
            indicies = tempMergers.index  # get the indicies of all being merged
            if (
                not (tempMergers == tempMergers.loc[indicies[0], :]).all().all()
            ):  # only need ot examine if not already averaged
                # total = price*amount - fee*fee spot price?
                netAmount = tempMergers["Amount"].sum()
                # total = tempMergers['Total'].sum()
                total = (
                    tempMergers["Price"] * tempMergers["Amount"]
                ).sum()  # may have been empty
                netFee = tempMergers["Fee"].sum()
                avgPrice = total / netAmount
                # weight the avg price by the amounts
                weights = tempMergers["Amount"] / tempMergers["Amount"].sum(min_count=1)
                avg_1_spot_fiat = (
                    tempMergers["Market 1 Fiat Spot Price"] * weights
                ).sum(min_count=1)
                avg_2_spot_fiat = (
                    tempMergers["Market 2 Fiat Spot Price"] * weights
                ).sum(min_count=1)
                fee_spot_fiat = (
                    tempMergers["Fee Asset Fiat Spot Price"] * weights
                ).sum(min_count=1)

                # set average values
                df.loc[indicies, "Price"] = avgPrice
                df.loc[indicies, "Amount"] = netAmount
                # later becomes redundant... df.loc[index, 'Total'] = total
                df.loc[indicies, "Fee"] = netFee
                df.loc[indicies, "Market 1 Fiat Spot Price"] = avg_1_spot_fiat
                df.loc[indicies, "Market 2 Fiat Spot Price"] = avg_2_spot_fiat
                df.loc[indicies, "Fee Asset Fiat Spot Price"] = fee_spot_fiat

                # duplicate to the other rows in tempMergers
                df[potMergersMask] = df.loc[index, :]

    # all partial orders are now duplicates, so drop them
    df = df.drop_duplicates()
    df = df.sort_values(by=["Date(UTC)"])
    df = df.reset_index(drop=True)

    # total, defined per Binance (not CB) doesn't include fees
    df["Total"] = df["Price"] * df["Amount"]  # may have been empty

    # reset dataframe indices after sorting by date
    df = df.sort_values(by=["Date(UTC)"]).reset_index(drop=True)

    print("Orders consolidated")

    # Get missing spot prices
    dfmissing = df[
        df.isnull().values
    ].drop_duplicates()  # duplicates if multiple missing per row

    # print(dfmissing)

    for index, _ in dfmissing.iterrows():
        asset1, asset2 = split_markets_str(dfmissing.loc[index, "Market"])
        date = dfmissing.loc[index, "Date(UTC)"]
        # replace each missing value in the row
        if np.isnan(dfmissing.loc[index, "Market 1 Fiat Spot Price"]):
            df.loc[index, "Market 1 Fiat Spot Price"] = getAssetPrice(
                asset1, date
            )  # df has same indicies
        if np.isnan(dfmissing.loc[index, "Market 2 Fiat Spot Price"]):
            df.loc[index, "Market 2 Fiat Spot Price"] = getAssetPrice(asset2, date)
        if np.isnan(dfmissing.loc[index, "Fee Asset Fiat Spot Price"]):
            df.loc[index, "Fee Asset Fiat Spot Price"] = getAssetPrice(
                dfmissing.loc[index, "Fee Asset"], date
            )
    print("Prices updated")

    df["Type"] = df["Type"].apply(lambda x: x.upper())  # enforce Type capitalization

    return df


def str_to_datetime_utc(string: str) -> datetime.datetime:
    """Converts a string to timezone aware utc time"""

    if string == "NaT":
        date = np.datetime64("NaT")
    else:
        if not isinstance(string, datetime.datetime):
            date = parser.parse(string)  # parse the date to datetime
        else:
            date = string

        date = date.replace(tzinfo=datetime.timezone.utc)  # convert to non-naive UTC

    return date


def orderbook_from_df(dataframe: pd.DataFrame, registry: AssetRegistry):
    orderbook = []
    for _, row in dataframe.iterrows():
        asset1, asset2 = split_markets(row["Market"], registry=registry)
        date = str_to_datetime_utc(row["Date(UTC)"])
        orderbook.append(
            Order(
                date=date,
                market_1=asset1,
                market_2=asset2,
                kind=TransactionType.from_str(row["Type"]),
                price=row["Price"],
                amount=row["Amount"],
                # total is a property, not taken from the dataframe
                fee=row["Fee"],
                fee_asset=row["Fee Asset"],
                spot_1_fiat=row["Market 1 Fiat Spot Price"],
                spot_2_fiat=row["Market 2 Fiat Spot Price"],
                fee_spot_fiat=row["Fee Asset Fiat Spot Price"],
            )
        )

    return OrderBook(orders=orderbook)


def set_pool_reg_df_dtypes(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Handles conversion of values within the dataframe to their correct data type."""
    dataframe.purchase_date = pd.to_datetime(dataframe.purchase_date)
    dataframe.sale_date = pd.to_datetime(dataframe.sale_date)
    dataframe = dataframe.replace({pd.NaT: None, pd.NA: None, float("nan"): None})
    dataframe.id = dataframe.id.apply(clean_uuid)
    dataframe.triggered_by_id = dataframe.triggered_by_id.apply(
        lambda x: uuid.UUID(x) if x is not None else None
    )
    dataframe.triggers_id = dataframe.triggers_id.apply(
        lambda x: uuid.UUID(x) if x is not None else None
    )

    return dataframe.astype(
        {
            "id": "object",
            "asset": "str",
            "amount": "float",
            "purchase_cost_fiat": "float",
            "purchase_fee_fiat": "float",
            "sale_value_fiat": "float",
            "sale_fee_fiat": "float",
            "triggered_by_id": "object",
            "triggers_id": "object",
            "addition_to_cost_fiat": "float",
            "disallowed_loss_fiat": "float",
            "holding_period_modifier": "timedelta64[ns]",
        }
    )


def pool_reg_from_df(dataframe: pd.DataFrame, asset_reg: AssetRegistry):
    """Creates a `PoolRegistry` from the input `dataframe`."""
    pool_reg = []
    dataframe = set_pool_reg_df_dtypes(dataframe=dataframe)
    for _, row in dataframe.iterrows():
        pool_dict = row.to_dict()
        try:
            pool_dict["asset"] = asset_reg[
                pool_dict["asset"]
            ]  # use ticker to get Asset
        except AssetNotFoundError(
            f"Asset {pool_dict['asset']} not found. Please enter asset details"
        ):
            asset_reg.assets.append(Asset(**register_asset_dialogue()))
        wash_dict = {}
        wash_dict["triggered_by_id"] = pool_dict.pop("triggered_by_id")
        wash_dict["triggers_id"] = pool_dict.pop("triggers_id")
        wash_dict["addition_to_cost_fiat"] = pool_dict.pop("addition_to_cost_fiat")
        wash_dict["disallowed_loss_fiat"] = pool_dict.pop("disallowed_loss_fiat")
        wash_dict["holding_period_modifier"] = pool_dict.pop("holding_period_modifier")

        pool_reg.append(
            Pool(
                **pool_dict,
                wash=Wash(**wash_dict),
            )
        )

    return PoolRegistry(pools=pool_reg)


def pool_reg_from_v1_df(dataframe: pd.DataFrame, asset_reg: AssetRegistry):
    """Creates a `PoolRegistry` from the input `dataframe`."""
    pool_reg = []
    old_ids = dataframe.id.copy()
    dataframe = set_pool_reg_df_dtypes(dataframe=dataframe)
    new_ids = dataframe.id.copy()
    id_dict = {old_id: new_ids[i] for i, old_id in enumerate(old_ids)}
    for _, row in dataframe.iterrows():
        pool_dict = row.to_dict()
        try:
            pool_dict["asset"] = asset_reg[
                pool_dict["asset"]
            ]  # use ticker to get Asset
        except AssetNotFoundError(
            f"Asset {pool_dict['asset']} not found. Please enter asset details"
        ):
            asset_reg.assets.append(Asset(**register_asset_dialogue()))
        wash_dict = {}
        wash_dict["triggered_by_id"] = pool_dict.pop("triggered_by_id")
        wash_dict["triggers_id"] = pool_dict.pop("triggers_id")
        wash_dict["addition_to_cost_fiat"] = pool_dict.pop("addition_to_cost_fiat")
        wash_dict["disallowed_loss_fiat"] = pool_dict.pop("disallowed_loss_fiat")
        wash_dict["holding_period_modifier"] = pool_dict.pop("holding_period_modifier")

        pool = Pool(
            **pool_dict,
            wash=Wash(**wash_dict),
        )
        pool = convert_v1_ids(pool_df=pool, id_dict=id_dict)
        pool_reg.append(pool)

    return PoolRegistry(pools=pool_reg)


def clean_uuid(id) -> uuid:
    try:
        new_id = uuid.UUID(id)
    except Exception:
        new_id = uuid.uuid4()
    return new_id


def convert_purchase_v1_ids(
    purchase_pool_df: pd.DataFrame, purchase_id_dict: dict, sale_id_dict: dict
) -> pd.DataFrame:
    """Converts v1 Purchase Pool IDs into a UUID equivalent with mappings (old id->new id) provided by
    `purchase_id_dict` and `sale_id_dict`
    """
    purchase_pool_df.id = purchase_pool_df.id.apply(lambda x: purchase_id_dict[x])
    purchase_pool_df.triggers_id = purchase_pool_df.triggers_id.apply(
        lambda x: sale_id_dict[x] if x in sale_id_dict.keys() else None
    )

    return purchase_pool_df


def convert_sale_v1_ids(
    sale_pool_df: pd.DataFrame, purchase_id_dict: dict, sale_id_dict: dict
) -> pd.DataFrame:
    """Converts v1 Sale Pool IDs into a UUID equivalent with mappings (old id->new id) provided by
    `purchase_id_dict` and `sale_id_dict`
    """
    sale_pool_df.id = sale_pool_df.id.apply(lambda x: sale_id_dict[x])
    sale_pool_df.triggered_by_id = sale_pool_df.triggered_by_id.apply(
        lambda x: purchase_id_dict[x] if x in purchase_id_dict.keys() else None
    )
    sale_pool_df.triggers_id = sale_pool_df.triggers_id.apply(
        lambda x: sale_id_dict[x] if x in sale_id_dict.keys() else None
    )

    return sale_pool_df


def convert_v1_ids(
    purchase_pool_df: pd.DataFrame,
    sale_pool_df: pd.DataFrame,
    purchase_id_dict: dict,
    sale_id_dict: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Converts v1 Purchase and Sale Pool IDs into a UUID equivalent with mappings (old id->new id) provided by
    `purchase_id_dict` and `sale_id_dict`"""

    purchase_pool_df = convert_purchase_v1_ids(
        purchase_pool_df=purchase_pool_df,
        purchase_id_dict=purchase_id_dict,
        sale_id_dict=sale_id_dict,
    )
    sale_pool_df = convert_sale_v1_ids(
        sale_pool_df=sale_pool_df,
        purchase_id_dict=purchase_id_dict,
        sale_id_dict=sale_id_dict,
    )

    return purchase_pool_df, sale_pool_df


def split_markets_str(markets: str):
    if "-" not in markets:
        asset1 = markets
        asset2 = cfg.processing.default_fiat.upper()
    else:
        asset1, asset2 = markets.split("-")

    return asset1, asset2


def split_markets(markets: str, registry: AssetRegistry):
    asset1, asset2 = split_markets_str(markets=markets)

    return registry[asset1], registry[asset2]


def orderbook_header():
    return [
        "Date(UTC)",
        "Market",
        "Type",
        "Price",
        "Amount",
        "Total",
        "Fee",
        "Fee Asset",
        "Market 1 Fiat Spot Price",
        "Market 2 Fiat Spot Price",
        "Fee Asset Fiat Spot Price",
    ]
