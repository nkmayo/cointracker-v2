import pandas as pd
from tkinter import filedialog
from pathlib import Path

from cointracker.objects.asset import AssetRegistry, import_registry
from cointracker.objects.pool import PoolRegistry
from cointracker.settings.config import cfg
from cointracker.util.parsing import (
    parse_orderbook,
    orderbook_from_df,
    pool_reg_from_df,
)


# -----Import Functions-----


def load_asset_registry():
    """Loads the `AssetRegistry` from the default configuration location."""
    registry_file = cfg.paths.data / "token_registry.yaml"
    token_registry = import_registry(filename=registry_file)
    registry_file = cfg.paths.data / "fiat_registry.yaml"
    fiat_registry = import_registry(filename=registry_file)
    registry = token_registry + fiat_registry
    return registry


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
    pool_reg = pool_reg_from_df(df)

    return pool_reg


# -----Export Functions-----


def export_pool_reg(pool_reg: PoolRegistry, filename: str, iso=True) -> None:
    if ".xlsx" not in filename:
        filename = filename + ".xlsx"
    filepath = cfg.paths.data / filename
    df = pool_reg.to_df(ascending=True, kind="default")

    if iso:
        df.purchase_date = df.purchase_date.apply(lambda x: x.isoformat())
        df.sale_date = df.sale_date.apply(lambda x: x.isoformat())

    # excel cannot handle timezone aware datetimes, convert to string
    df = df.astype({"purchase_date": "str", "sale_date": "str"})
    df.to_excel(filepath, "All Pools", index=False)
