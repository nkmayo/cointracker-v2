# %%
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, asdict, field

from cointracker.settings.config import fiat_currencies
import yaml


dataclass_kw = {"frozen": True, "order": True}
if sys.version_info[:2] >= (3, 10):
    dataclass_kw["slots"] = True  # speed improvement if >= Python 3.10


@dataclass(**dataclass_kw)
class Asset:
    name: str  # asset name
    ticker: str  # typically 3-4 characters
    fungible: bool  # fungible/non-fungible
    decimals: int = None  # smallest decimal permitted. Ex: USD = 2 for $0.01 or 1 cent

    def __post_init__(self):
        if not self.fungible:  # non-fungible tokens have no sub-units
            object.__setattr__(self, "decimals", 0)
            # self.decimals = 0

    def __str__(self) -> str:
        return self.ticker

    @property
    def smallest_unit(self):
        return 10 ** (-self.decimals)

    @property
    def is_fiat(self) -> bool:
        return is_asset_fiat(
            self.ticker
        )  # TODO: creates circular reference if fiat currencies are imported from an AssetRegistry?

    def is_asset(self, string: str) -> bool:
        """Returns true if the input string matches the `Asset` name or ticker."""
        is_name = self.name.lower() == string.lower()
        is_ticker = self.ticker.lower() == string.lower()
        return is_name | is_ticker

    def to_dict(self):
        return asdict(self)


@dataclass
class AssetRegistry:
    assets: list[Asset] = field(
        default_factory=list, repr=False
    )  # TODO: consider refactoring using sets instead of lists

    def to_yaml(self, filename):
        registry = {}
        for asset in self.assets:
            registry[asset.ticker] = asset.to_dict()

        with open(filename, "wb") as file:
            yaml.dump(registry, file, encoding="utf-8")

    def __len__(self) -> int:
        return len(self.assets)

    def __repr__(self) -> int:
        combined = f"Registry Items ({len(self)}): ["
        for idx, asset in enumerate(self):
            if asset is not None:
                if idx == 0:
                    combined += str(asset)
                else:
                    combined = combined + ", " + str(asset)
        combined += "]"
        return combined

    def __add__(self, item):
        if isinstance(item, AssetRegistry):
            combined_assets = [*self.assets, *item.assets]
            return AssetRegistry(combined_assets)
        if isinstance(item, list):
            all_asset = [isinstance(i, Asset) for i in item].all()
            all_str = [isinstance(i, str) for i in item].all()
            assert (
                all_asset or all_str
            ), f"Assets appending to `AssetRegistry` must be all be of `Asset` or `str` type"
            if all_str:
                item = [
                    self[i] for i in item
                ]  # convert from list of `str` to list of `Asset`

            combined_assets = [*self.assets, *item]
            return AssetRegistry(combined_assets)
        elif isinstance(item, Asset):
            combined_assets = [*self.assets, item]
            return AssetRegistry(combined_assets)
        else:
            raise TypeError(f"")

    def __iter__(self):
        return self.assets.__iter__()

    def __next__(self):
        return self.assets.__next__()

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return self.assets[start:stop:step]
        elif isinstance(key, (int, np.integer)):
            return self.assets[key]
        elif isinstance(key, str):
            asset = None
            for asset_in_registry in self:
                if (
                    asset_in_registry.name.upper() == key.upper()
                    or asset_in_registry.ticker.upper() == key.upper()
                ):
                    asset = asset_in_registry
            if asset is None:
                raise ValueError(f"{key} not found in `AssetRegistry`")
            else:
                return asset
        else:
            raise TypeError(f"Invalid argument type: {type(key)}")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            self.assets[start:stop:step] = value
        elif isinstance(key, (int, np.integer)):
            self.assets[key] = value
        else:
            raise TypeError(f"Invalid argument type: {type(key)}")

    @property
    def nft(self):
        return AssetRegistry(
            [asset for asset in self.assets if asset.fungible == False]
        )

    @property
    def fungible(self):
        return AssetRegistry([asset for asset in self.assets if asset.fungible == True])

    @property
    def fiat(self):
        return AssetRegistry([asset for asset in self.assets if asset.is_fiat])


def asset_from_dict(dictionary):
    if "fungible" not in dictionary:
        dictionary["fungible"] = True  # fiat may not specify fungibility
    return Asset(
        name=dictionary["name"],
        ticker=dictionary["ticker"],
        fungible=dictionary["fungible"],
        decimals=dictionary["decimals"],
    )


def import_registry(filename):
    with open(filename, "r") as file:
        registry = yaml.safe_load(file)

    assets = [asset_from_dict(asset) for _, asset in registry.items()]

    return AssetRegistry(assets)


def is_asset_fiat(asset_ticker: str) -> bool:
    """Returns `True` if the asset ticker is in the list of known fiat currencies."""
    return asset_ticker.upper() in fiat_currencies()


# %%
