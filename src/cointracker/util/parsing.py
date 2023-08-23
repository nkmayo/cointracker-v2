import pandas as pd
import numpy as np
import datetime
from dateutil import parser
from cointracker.objects.orderbook import Order, OrderBook
from cointracker.objects.asset import AssetRegistry, import_registry
from cointracker.objects.enumerated_values import TransactionType
from cointracker.pricing.getAssetPrice import getAssetPrice
from cointracker.settings.config import read_config


def load_excel_orderbook(file: str, sheetname: str = "Sheet1"):
    cfg = read_config()
    registry_file = cfg.paths.data / "token_registry.yaml"
    token_registry = import_registry(filename=registry_file)
    registry_file = cfg.paths.data / "fiat_registry.yaml"
    fiat_registry = import_registry(filename=registry_file)
    registry = token_registry + fiat_registry

    filename = cfg.paths.tests / file
    order_df = parse_orderbook(filename, sheetname)
    orderbook = orderbook_from_df(order_df, registry=registry)

    return orderbook


def parse_orderbook(filename, sheet):
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
    if not isinstance(string, datetime.datetime):
        date = parser.parse(string)  # parse the date to datetime
    else:
        date = string

    return date.replace(tzinfo=datetime.timezone.utc)  # convert to non-naive UTC


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


def split_markets_str(markets: str):
    if "-" not in markets:
        asset1 = markets
        asset2 = "Fiat"
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
