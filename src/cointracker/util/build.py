# %%
from tkinter import filedialog
from pathlib import Path
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.util.parsing import (
    load_asset_registry,
    parse_orderbook,
    split_markets_str,
)

registry = load_asset_registry()


def build_dummy_assets_from_orderbook_file(
    filepath: Path = None, sheet="Sheet1"
) -> AssetRegistry:
    if filepath is None:
        filepath = filedialog.askopenfilename(
            title="Select pool registry file",
            filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
        )

    orderbook_df = parse_orderbook(filename=filepath, sheet=sheet)
    semi_unique_assets = orderbook_df["Market"].drop_duplicates()
    asset_reg = []
    unique_assets = []
    dummy_decimals = 14
    for assets in semi_unique_assets.values:
        asset1, asset2 = split_markets_str(assets)
        if asset1 not in unique_assets:
            unique_assets.append(asset1)
        if asset2 not in unique_assets:
            unique_assets.append(asset2)

    for asset_str in unique_assets:
        fungible = True
        known_nft_names = [
            "ape",
            "cabin",
            "acronym",
            "reality",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "alpha",
            "beta",
            "delta",
            "gamma",
            "sigma",
            "omega",
        ]
        for name in known_nft_names:
            if name in asset_str.lower():
                fungible = False
        asset_reg.append(
            Asset(
                name=asset_str,
                ticker=asset_str.upper(),
                fungible=fungible,
                decimals=dummy_decimals,
            )
        )

    return AssetRegistry(asset_reg)


# %%
