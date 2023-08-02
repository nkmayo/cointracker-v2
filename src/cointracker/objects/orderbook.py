# %%
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset, AssetRegistry

dataclass_kw = {"frozen": False, "order": True}
if sys.version_info[:2] >= (3, 10):
    dataclass_kw["slots"] = True  # speed improvement if >= Python 3.10


@dataclass(**dataclass_kw)
class Order:
    date: datetime
    market_1: Asset
    market_2: Asset
    kind: str
    price: float
    amount: float  # convert to int with market1 units
    fee: float
    fee_coin: Asset
    spot_1: float
    spot_2: float
    fee_spot: float

    @property
    def amount_base_units(self):
        return int(self.amount / self.market_1.smallest_unit)

    @property
    def rounded_amount(self):
        return self.amount_base_units * self.market_1.smallest_unit

    @property
    def total(self):
        total = self.rounded_amount * self.price
        # convert the total to the market2 units
        total = int(total / self.market_2.smallest_unit) * self.market_2.smallest_unit

    @property
    def m1_tick(self):
        return self.market_1.ticker

    @property
    def m2_tick(self):
        return self.market_2.ticker

    @property
    def market(self):
        return f"{self.m1_tick}-{self.m2_tick}"

    def __repr__(self) -> str:
        d = self.date.strftime("%Y/%m/%d")
        return f"{d} {self.market_1.ticker}-{self.market_2.ticker} {self.kind} {self.price} {self.amount} {self.total}"

    def to_series(self):
        """Returns the object as a pandas series"""
        series = {
            "Date(UTC)": self.date,
            "Market": self.market,
            "Type": self.kind,
            "Price": self.price,
            "Amount": self.amount,
            "Total": self.total,
            "Fee": self.fee,
            "Fee Coin": self.fee_coin,
            "Market 1 USD Spot Price": self.spot_1,
            "Market 2 USD Spot Price": self.spot_2,
            "Fee Coin USD Spot Price": self.fee_spot,
        }
        return pd.Series(series)


@dataclass
class OrderBook:
    orders: list[Order] = field(default_factory=list, repr=False)
    _iter_idx: int = field(init=False, repr=False)

    def __len__(self) -> int:
        return len(self.orders)

    def __repr__(self) -> str:
        ordered = self.sort(ascending=True, inplace=False)
        start = ordered.orders[0].date.strftime("%Y/%m/%d")
        end = ordered.orders[-1].date.strftime("%Y/%m/%d")

        return f"OrderBook(size: {len(self)}, dates: {start}-{end})"

    def __add__(self, item):
        if isinstance(item, OrderBook):
            combined_orders = [*self.orders, *item.orders]
            return OrderBook(combined_orders)
        if isinstance(item, list):
            assert [
                isinstance(i, Order) for i in item
            ].all(), f"Orders appending to `OrderBook` must be all be of `Order` type"

            combined_orders = [*self.orders, *item]
            return OrderBook(combined_orders)
        elif isinstance(item, Order):
            combined_orders = [*self.orders, item]
            return OrderBook(combined_orders)
        else:
            raise TypeError(f"")

    def __iter__(self):
        self._iter_idx = 0
        return self

    def __next__(self):
        if self._iter_idx < len(self):
            i = self._iter_idx
            self._iter_idx += 1
            return self.orders[i]
        else:
            raise StopIteration

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return self.orders[start:stop:step]
        elif isinstance(key, int):
            return self.orders[key]
        elif isinstance(key, str):
            asset = None
            for asset_in_registry in self:
                if asset_in_registry.name == key or asset_in_registry.ticker == key:
                    asset = asset_in_registry
            if asset is None:
                raise ValueError(f"{key} not found in `AssetRegistry`")
            else:
                return asset
        else:
            raise TypeError(f"Invalid argument type: {type(key)}")

    def sort(self, ascending=True, inplace=False):
        """Sorts the orderbook by date. `acending=True` sorts oldest to newest. `inplace` can be specified to
        apply the sorted result to the underlying instance."""
        if ascending:
            orders = sorted(self.orders)
        else:
            orders = sorted(self.orders, reverse=True)

        if inplace:
            self.orders = orders
            sorted_ob = self
        else:
            sorted_ob = OrderBook(orders=orders)

        return sorted_ob

    def to_df(self, ascending=True):
        """Converts the `OrderBook` object into a pandas DataFrame. Sorts orders by ascending date if `ascending=True`,
        descending date if `ascending=False` or does not change the ordering indicies if `ascending=None`.
        """
        df = pd.DataFrame([order.to_series() for order in self])
        if ascending is not None:
            df.sort_values(
                by="Date(UTC)", ascending=ascending, ignore_index=True, inplace=True
            )
        return df
