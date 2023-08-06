# %%
import sys
import numpy as np
import pandas as pd
from itertools import count
from datetime import datetime
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.enumerated_values import TransactionType

USD = Asset(name="US Dollar", ticker="USD", fungible=True, decimals=2)

dataclass_kw = {"frozen": False, "order": True}
if sys.version_info[:2] >= (3, 10):
    dataclass_kw["slots"] = True  # speed improvement if >= Python 3.10


@dataclass(**dataclass_kw)
class Order:
    date: datetime
    market_1: Asset
    market_2: Asset
    kind: TransactionType
    price: float
    amount: float  # convert to int with market1 units
    fee: float
    fee_asset: Asset
    spot_1_fiat: float
    spot_2_fiat: float
    fee_spot_fiat: float

    @property
    def amount_base_units(self):
        return int(self.amount / self.market_1.smallest_unit)

    @property
    def rounded_amount(self):
        return self.amount_base_units * self.market_1.smallest_unit

    @property
    def total(self):
        t = self.rounded_amount * self.price
        # convert the total to the market2 units
        t = int(t / self.market_2.smallest_unit) * self.market_2.smallest_unit
        return t

    @property
    def fee_fiat(self):
        return self.fee * self.fee_spot_fiat

    @property
    def m1_tick(self):
        return self.market_1.ticker

    @property
    def m2_tick(self):
        return self.market_2.ticker

    @property
    def market(self):
        return f"{self.m1_tick}-{self.m2_tick}"

    @property
    def asset_bought(self) -> TransactionType:
        if self.kind == TransactionType.BUY:
            return self.market_1
        elif self.kind == TransactionType.SELL:
            return self.market_2
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

    @property
    def asset_sold(self) -> TransactionType:
        if self.kind == TransactionType.BUY:
            return self.market_2
        elif self.kind == TransactionType.SELL:
            return self.market_1
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

    @property
    def amount_bought(self) -> TransactionType:
        if self.kind == TransactionType.BUY:
            return self.rounded_amount
        elif self.kind == TransactionType.SELL:
            return self.total
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

    @property
    def amount_sold(self) -> TransactionType:
        if self.kind == TransactionType.BUY:
            return self.total
        elif self.kind == TransactionType.SELL:
            return self.rounded_amount
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

    @property
    def buy_transaction(self) -> TransactionType:
        """When buying/selling a pair one asset is bought and the other is sold. This generates the transaction details for the asset that is bought."""
        if self.kind == TransactionType.BUY:
            return Transaction(
                self.date,
                asset=self.market_1,
                kind=TransactionType.BUY,
                amount=self.amount,
                asset_spot_fiat=self.spot_1_fiat,
                # If it is a BUY transaction, the fees are associated with the asset bought
                fee=self.fee,
                fee_asset=self.fee_asset,
                fee_spot_fiat=self.fee_spot_fiat,
            )
        elif self.kind == TransactionType.SELL:
            return Transaction(
                self.date,
                asset=self.market_2,
                kind=TransactionType.BUY,
                amount=self.total,
                asset_spot_fiat=self.spot_2_fiat,
                # If it is a SELL transaction, the fees are associated with the asset sold
            )
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

    @property
    def sell_transaction(self) -> TransactionType:
        """When buying/selling a pair one asset is bought and the other is sold. This generates the transaction details for the asset that is sold."""
        if self.kind == TransactionType.BUY:
            return Transaction(
                self.date,
                asset=self.market_2,
                kind=TransactionType.SELL,
                amount=self.total,
                asset_spot_fiat=self.spot_2_fiat,
                # If it is a BUY transaction, the fees are associated with the asset bought
            )
        elif self.kind == TransactionType.SELL:
            return Transaction(
                self.date,
                asset=self.market_1,
                kind=TransactionType.SELL,
                amount=self.amount,
                asset_spot_fiat=self.spot_1_fiat,
                # If it is a SELL transaction, the fees are associated with the asset sold
                fee=self.fee,
                fee_asset=self.fee_asset,
                fee_spot_fiat=self.fee_spot_fiat,
            )
        else:
            raise ValueError(f"TransactionType {self.kind} must be BUY or SELL")

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
            "Fee Asset": self.fee_asset,
            "Market 1 Fiat Spot Price": self.spot_1_fiat,
            "Market 2 Fiat Spot Price": self.spot_2_fiat,
            "Fee Asset Fiat Spot Price": self.fee_spot_fiat,
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


"""Does this make sense?"""


@dataclass(**dataclass_kw)
class Transaction:
    id: int = field(init=False, default_factory=count().__next__)
    date: datetime
    asset: Asset
    kind: TransactionType
    amount: float
    asset_spot_fiat: float
    fee: float = 0
    fee_asset: Asset = USD
    fee_spot_fiat: float = 1.00

    @property
    def amount_base_units(self):
        return int(self.amount / self.asset.smallest_unit)

    @property
    def rounded_amount(self):
        return self.amount_base_units * self.asset.smallest_unit

    @property
    def amount_fiat(self):
        return self.amount * self.asset_spot_fiat

    @property
    def fee_fiat(self):
        return self.fee * self.fee_spot_fiat

    @property
    def market(self):
        return self.asset.ticker

    def __repr__(self) -> str:
        d = self.date.strftime("%Y/%m/%d")
        return f"{d} {self.market} {self.kind} {self.amount} {self.asset_spot_fiat} {self.amount_fiat}"

    def to_series(self):
        """Returns the object as a pandas series"""
        series = {
            "ID": self.id,
            "Date(UTC)": self.date,
            "Asset": self.asset,
            "Type": self.kind,
            "Amount": self.amount,
            "Asset Fiat Spot Price": self.asset_spot_fiat,
            "Fiat Equivalent": self.amount_fiat,
            "Fee": self.fee,
            "Fee Asset": self.fee_asset,
            "Fee Asset Fiat Spot Price": self.fee_spot_fiat,
        }
        return pd.Series(series)
