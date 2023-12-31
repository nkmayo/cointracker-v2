import pandas as pd
from tkinter import filedialog
from pathlib import Path
import warnings

from cointracker.objects.asset import AssetRegistry, import_registry
from cointracker.objects.pool import Pool, PoolRegistry, Wash
from cointracker.objects.exceptions import IncorrectPoolFormat
from cointracker.settings.config import cfg
from cointracker.util.parsing import (
    parse_orderbook,
    orderbook_from_df,
    pool_reg_from_df,
    clean_uuid,
    convert_v1_ids,
    consolidate_pool_reg,
)

# -----Import Functions-----


def load_asset_registry():
    """Loads the `AssetRegistry` from the default configuration location."""
    registry_file = cfg.paths.data / "token_registry.yaml"
    token_registry = import_registry(filename=registry_file)
    registry_file = cfg.paths.data / "nft_registry.yaml"
    nft_registry = import_registry(filename=registry_file)
    registry_file = cfg.paths.data / "fiat_registry.yaml"
    fiat_registry = import_registry(filename=registry_file)
    registry = token_registry + nft_registry + fiat_registry
    registry = [item for item in registry if item is not None]
    return AssetRegistry(registry)


def load_excel_orderbook(file: str, sheetname: str = "Sheet1"):
    """Loads an `Orderbook` from data saved in the .xlsx format from Excel."""
    registry = load_asset_registry()
    if file is None:
        filename = filedialog.askopenfilename(
            title="Select pool registry file",
            filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
        )
    else:
        filename = cfg.paths.tests / file
    order_df = parse_orderbook(filename, sheetname)
    orderbook = orderbook_from_df(order_df, registry=registry)

    return orderbook


def load_excel_pool_registry(filepath: Path = None, sheetname: str = "Sheet1"):
    """Loads a `PoolRegistry` from data saved in the .xlsx format from Excel."""
    if filepath is None:
        filepath = filedialog.askopenfilename(
            title="Select pool registry file",
            filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
        )

    df = pd.read_excel(filepath, sheet_name=sheetname)
    pool_reg = pool_reg_from_df(df, asset_reg=load_asset_registry())

    return pool_reg


def load_v1_purchase_pool(
    filepath: Path = None, sheetname: str = "Sheet1"
) -> pd.DataFrame:
    """Loads the EOY Purchase Pools into a `PoolRegistry` object."""
    if filepath is None:
        filepath = filedialog.askopenfilename(
            title="Select Purchase Pool file",
            filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
        )
    print(f"Filepath: {filepath}")
    v1_df = pd.read_excel(filepath, sheet_name=sheetname)
    v2_info = []
    for _, row in v1_df.iterrows():
        v2_info.append(
            {
                "id": row["Pool ID"],
                "asset": row["Asset"],
                "amount": row["Amount"],
                "purchase_date": row["Purchase Date"],
                "purchase_cost_fiat": row["Asset Spot Price"] * row["Amount"],
                "purchase_fee_fiat": row["Fee USD"],
                "sale_date": None,
                "sale_value_fiat": None,
                "sale_fee_fiat": None,
                "triggered_by_id": row["Initiates Wash"]
                if row["Initiates Wash"] != 0
                else None,
                "triggers_id": None,  # Can't tell which pool it may have triggered
                "disallowed_loss_fiat": row["Modified Cost Basis"] - row["Cost Basis"],
                "holding_period_modifier": row["Holding Period Modifier"],
            }
        )

    v2_df = pd.DataFrame(v2_info)

    return v2_df


def load_v1_sale_pool(filepath: Path = None, sheetname: str = "Sheet1"):
    """Loads the EOY Sale Pools into a `PoolRegistry` object.
    NOTE: V1 EOY Asset Pools only contain "Active" (open) orders. EOY Sale Pools contain both Active and Inactive orders
    which are needed to correctly account for potential wash sales from December of the previous year.
    TODO: Can you get sale information from the Asset Pools that aren't active?
    """
    if filepath is None:
        filepath = filedialog.askopenfilename(
            title="Select Sale Pool file",
            filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
        )

    v1_df = pd.read_excel(filepath, sheet_name=sheetname)

    v2_info = []
    for _, row in v1_df.iterrows():
        v2_info.append(
            {
                "id": row["Pool ID"],
                "asset": row["Asset Sold"],
                "amount": row["Amount"],
                "purchase_date": row["Purchase Date"],
                "purchase_cost_fiat": row["Cost Basis"],
                "purchase_fee_fiat": 0.0,
                "sale_date": row["Sale Date"],
                "sale_value_fiat": row["Proceeds"] + row["Fee USD"],
                "sale_fee_fiat": row["Fee USD"],
                "triggered_by_id": row["Wash Pool ID"]
                if row["Wash Pool ID"] != 0
                else None,
                "triggers_id": None,  # Can't tell which pool it may have triggered
                "disallowed_loss_fiat": row["Disallowed Loss"],
                "holding_period_modifier": row[
                    "Holding Period"
                ],  # to be corrected after changing to timedelta
            }
        )

    v2_df = pd.DataFrame(v2_info)

    return v2_df


def load_from_v1_pools(
    purchase_pools_filepath: Path = None,
    purchase_pools_sheetname: str = "Sheet1",
    sale_pools_filepath: Path = None,
    sale_pools_sheetname: str = "Sheet1",
):
    """Loads the EOY Purchase Pools into a `PoolRegistry` object.
    NOTE: V1 EOY Asset Pools only contain "Active" (open) orders. EOY Purchase Pools contain both Active and Inactive orders
    which are needed to correctly account for potential wash sales from December of the previous year.
    TODO: Can you get sale information from the Asset Pools that aren't active?
    """

    purchase_pools = load_v1_purchase_pool(
        filepath=purchase_pools_filepath, sheetname=purchase_pools_sheetname
    )
    print(purchase_pools)
    sale_pools = load_v1_sale_pool(
        filepath=sale_pools_filepath, sheetname=sale_pools_sheetname
    )
    print(sale_pools)

    # Resolve IDs
    purchase_ids = {i: clean_uuid(i) for i in purchase_pools.id}
    sale_ids = {i: clean_uuid(i) for i in sale_pools.id}

    purchase_pools, sale_pools = convert_v1_ids(
        purchase_pool_df=purchase_pools,
        sale_pool_df=sale_pools,
        purchase_id_dict=purchase_ids,
        sale_id_dict=sale_ids,
    )

    print(f"after:\n{sale_pools}")
    asset_reg = load_asset_registry()
    purchase_pool_reg = pool_reg_from_df(purchase_pools, asset_reg=asset_reg)
    sale_pool_reg = pool_reg_from_df(sale_pools, asset_reg=asset_reg)

    # Correct holding period modifier on sale pools (is currently entire holding period)
    for pool in sale_pool_reg:
        if pool.is_wash:
            pool.wash.holding_period_modifier = pool.wash.holding_period_modifier - (
                pool.sale_date - pool.purchase_date
            )

    return PoolRegistry([*purchase_pool_reg, *sale_pool_reg])


# -----Export Functions-----


def export_pool_reg(
    pool_reg: PoolRegistry,
    filename: str,
    iso: bool = True,
    kind: str = "default",
    consolidate: bool = False,
    by_date: str = "both",
) -> None:
    if ".xlsx" not in filename:
        filename = filename + ".xlsx"
    filepath = cfg.paths.data / filename

    if consolidate:
        if kind not in ["sales_report", "irs", "tax", "8949"]:
            warnings.warn(
                "Non-report style data being produced with consolidated pool registry"
            )
        if by_date == "both" or by_date == "double":
            pool_reg = consolidate_pool_reg(pool_reg=pool_reg, by_date="purchase")
            by_date = "sale"
        pool_reg = consolidate_pool_reg(pool_reg=pool_reg, by_date=by_date)

    df = pool_reg.to_df(ascending=True, kind=kind)

    if iso:
        if kind == "sales_report":
            df["Purchase Date"] = df["Purchase Date"].apply(lambda x: x.isoformat())
            df["Sale Date"] = df["Sale Date"].apply(lambda x: x.isoformat())
            # excel cannot handle timezone aware datetimes, convert to string
            df = df.astype({"Purchase Date": "str", "Sale Date": "str"})
        elif kind in ["irs", "tax", "8949"]:
            # Date format specified in header and cannot be changed
            # excel cannot handle timezone aware datetimes, convert to string
            df = df.astype(
                {
                    "Date Acquired (Mo., day, yr.)": "str",
                    "Date Sold (Mo., day, yr.)": "str",
                }
            )
        else:
            df.purchase_date = df.purchase_date.apply(lambda x: x.isoformat())
            df.sale_date = df.sale_date.apply(lambda x: x.isoformat())
            # excel cannot handle timezone aware datetimes, convert to string
            df = df.astype({"purchase_date": "str", "sale_date": "str"})

    df.to_excel(filepath, "All Pools", index=False)
