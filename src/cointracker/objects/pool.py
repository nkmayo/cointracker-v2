# %%
import numpy as np
import pandas as pd
import datetime
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset
from itertools import count


@dataclass
class Sale:
    id: int = field(init=False, default_factory=count().__next__)
    asset_sold: Asset
    asset_received: Asset
    purchase_date: datetime.datetime
    sale_date: datetime.datetime
    amount: float  # convert to int with market1 units
    sale_price: float
    asset_sold_spot: float
    asset_recieved_spot: float
    fee: float
    fee_coin: Asset
    fee_spot: float
    fee_fiat: float
    purchase_pool_id: int
    holding_period: datetime.timedelta
    long: bool
    proceeds: float
    cost_basis: float
    wash_pool_id: int
    disallowed_loss: float
    net_gain: float

    @property
    def amount_base_units(self):
        return int(self.amount / self.market1.smallest_unit)

    @property
    def rounded_amount(self):
        return self.amount_base_units * self.market1.smallest_unit

    @property
    def total(self):
        total = self.rounded_amount * self.price
        # convert the total to the market2 units
        total = int(total / self.market2.smallest_unit) * self.market2.smallest_unit


@dataclass
class Pool:
    id: int = field(init=False, default_factory=count().__next__)
    asset: Asset
    amount: float  # convert to int with market1 units?
    purchase_date: datetime.datetime
    purchase_cost_fiat: float
    purchase_fee_fiat: float
    sale_date: datetime.datetime = None
    sale_value_fiat: float = None
    sale_fee_fiat: float = None
    wash_pool_id: int = None
    disallowed_loss: float = 0.0

    def __repr__(self) -> str:
        if self.sale_date is None:
            sale_date = "None"
        else:
            sale_date = self.sale_date.strftime("%Y/%m/%d")

        return f"Pool(\nid: {self.id}, \npurchase date: {self.purchase_date.strftime('%Y/%m/%d')}, \nsale date: {sale_date}, \
                \nasset: {self.asset.ticker}, \namount: {self.amount}, \ncost_fiat: {self.purchase_cost_fiat}, \
                \nsale_fiat: {self.sale_value_fiat}\n)\n\n"

    @property
    def holding_period(self) -> datetime.timedelta:
        if self.open:
            return None
        else:
            assert (
                self.sale_date >= self.purchase_date
            ), "Sale must occur after purchase"
            return self.sale_date - self.purchase_date

    @property
    def holdings_type(self) -> bool:
        if self.open:
            return None
        else:
            return self.holding_period >= datetime.timedelta(days=366)

    @property
    def holdings_type_str(self):
        if self.open:
            return None
        elif self.holdings_type:
            return "LONG-TERM"
        else:
            return "SHORT-TERM"

    @property
    def cost_basis(self):
        return self.purchase_cost_fiat - self.purchase_fee_fiat

    @property
    def proceeds(self):
        if self.open:
            return None
        else:
            return self.sale_value_fiat - self.sale_fee_fiat

    @property
    def net_gain(self):
        if self.open:
            return None
        else:
            return self.proceeds - self.cost_basis - self.disallowed_loss

    @property
    def closed(self) -> bool:
        if self.sale_date is None:
            return False
        else:
            return True

    @property
    def open(self) -> bool:
        return not self.closed

    @property
    def is_wash(self) -> bool:
        if self.wash_pool_id is None:
            return False
        else:
            return True

    def copy(self):
        return Pool(
            asset=self.asset,
            amount=self.amount,
            purchase_date=self.purchase_date,
            purchase_cost_fiat=self.purchase_cost_fiat,
            purchase_fee_fiat=self.purchase_fee_fiat,
            sale_date=self.sale_date,
            sale_value_fiat=self.sale_value_fiat,
            sale_fee_fiat=self.sale_fee_fiat,
            wash_pool_id=self.wash_pool_id,
            disallowed_loss=self.disallowed_loss,
        )

    def set_dtypes(self):
        self.amount = float(self.amount)
        self.purchase_date = self.purchase_date.replace(tzinfo=datetime.timezone.utc)
        self.purchase_cost_fiat = np.round(self.purchase_cost_fiat, decimals=2)
        self.purchase_fee_fiat = np.round(self.purchase_fee_fiat, decimals=2)
        if self.sale_date is not None:
            self.sale_date = self.sale_date.replace(tzinfo=datetime.timezone.utc)
            self.sale_value_fiat = np.round(self.sale_value_fiat, decimals=2)
            self.sale_fee_fiat = np.round(self.sale_fee_fiat, decimals=2)
            self.disallowed_loss = float(self.disallowed_loss)


@dataclass
class PoolRegistry:
    pools: list[Pool] = field(default_factory=list, repr=False)
    _iter_idx: int = field(init=False, repr=False)

    def __len__(self) -> int:
        return len(self.pools)

    def __repr__(self) -> str:
        start = datetime.datetime(
            year=9999, month=12, day=31, tzinfo=datetime.timezone.utc
        )
        end = datetime.datetime(year=1900, month=1, day=1, tzinfo=datetime.timezone.utc)
        for pool in self.pools:
            if pool.purchase_date < start:
                start = pool.purchase_date
            if pool.purchase_date > end:
                end = pool.purchase_date
            if pool.sale_date is not None:
                if pool.sale_date < start:
                    start = pool.sale_date
                if pool.sale_date > end:
                    end = pool.sale_date

        start = start.strftime("%Y/%m/%d")
        end = end.strftime("%Y/%m/%d")
        return f"PoolRegistry(size: {len(self)}, open: {len(self.open_pools)}, closed: {len(self.closed_pools)}, dates: {start}-{end})"

    def __add__(self, item):
        if isinstance(item, PoolRegistry):
            combined_pools = [*self.pools, *item.pools]
            return PoolRegistry(combined_pools)
        if isinstance(item, list):
            assert [
                isinstance(i, Pool) for i in item
            ].all(), f"Pools appending to `PoolRegistry` must be all be of `Pool` type"

            combined_pools = [*self.pools, *item]
            return PoolRegistry(combined_pools)
        elif isinstance(item, Pool):
            combined_pools = [*self.pools, item]
            return PoolRegistry(combined_pools)
        else:
            raise TypeError(f"")

    def __iter__(self):
        self._iter_idx = 0
        return self

    def __next__(self):
        if self._iter_idx < len(self):
            i = self._iter_idx
            self._iter_idx += 1
            return self.pools[i]
        else:
            raise StopIteration

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return self.pools[start:stop:step]
        elif isinstance(key, int):
            return self.pools[key]
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

    @property
    def closed_pools(self):
        return PoolRegistry([pool for pool in self if pool.closed])

    @property
    def open_pools(self):
        return PoolRegistry([pool for pool in self if pool.open])

    @property
    def proceeds(self):
        return sum([pool.proceeds for pool in self if pool.closed])

    @property
    def cost_basis(self):
        return sum([pool.cost_basis for pool in self if pool.closed])

    @property
    def disallowed_loss(self):
        return sum([pool.disallowed_loss for pool in self if pool.closed])

    @property
    def net_gain(self):
        return sum([pool.net_gain for pool in self if pool.closed])

    def idx_for_id(self, id: int):
        """Returns the index (as currently sorted) within the `pools` list of the pool with id `id`."""
        return np.argmin([abs(pool.id - id) for pool in self])

    def pools_with(self, asset: Asset, open: bool = None):
        """Returns the subset of pools with asset matching `asset`. If `open=None` all matching pools are returned. If
        `open=True` then only open pools are returned. If `open=False` then only closed pools are returned.
        """
        subset = PoolRegistry([pool for pool in self if pool.asset == asset])
        if open is None:
            pass
        elif open:
            subset = subset.open_pools
        else:
            subset = subset.closed_pools

        return subset

    def sort(self, by: str = "purchase", ascending: bool = True) -> None:
        """Sorts the pools in the `PoolRegistry` in place by date. `acending=True` sorts oldest to newest."""
        pool_reg = sort_pools(self, by=by, ascending=ascending)
        self.pools = pool_reg.pools

    def to_df(self, ascending=True):
        """Converts the `PoolRegistry` object into a pandas DataFrame. Sorts orders by ascending date if `ascending=True`,
        descending date if `ascending=False` or does not change the ordering indicies if `ascending=None`.
        """
        df = pd.DataFrame([pool.to_series() for pool in self])
        if ascending is not None:
            df.sort_values(
                by="Date(UTC)", ascending=ascending, ignore_index=True, inplace=True
            )
        return df


def sort_pools(
    pool_reg: PoolRegistry, by: str = "purchase", ascending: bool = True
) -> PoolRegistry:
    """Sorts the pools in the `PoolRegistry` by date. `acending=True` sorts oldest to newest. `inplace` can be specified to
    apply the sorted result to the underlying instance."""
    pools = pool_reg.pools
    if by == "purchase":
        if ascending:
            pools = sorted(pools, key=lambda x: x.purchase_date)
        else:
            pools = sorted(pools, key=lambda x: x.purchase_date, reverse=True)
    elif by == "sale":
        # Can't sort `None` type so first separate open pools with no `sale_date`
        open_pools = [pool for pool in pools if pool.open]
        closed_pools = [pool for pool in pools if pool.closed]
        if ascending:
            closed_pools = sorted(closed_pools, key=lambda x: x.sale_date)
            open_pools = sorted(open_pools, key=lambda x: x.purchase_date)
        else:
            closed_pools = sorted(closed_pools, key=lambda x: x.sale_date, reverse=True)
            open_pools = sorted(open_pools, key=lambda x: x.purchase_date, reverse=True)

        pools = [*closed_pools, *open_pools]  # append open pools to   the end
    elif by == "asset":
        if ascending:
            pools = sorted(pools, key=lambda x: x.asset.ticker)
        else:
            pools = sorted(pools, key=lambda x: x.asset.ticker, reverse=True)
    else:
        raise ValueError(f"Unrecognized sort argument `by={by}`.")

    return PoolRegistry(pools=pools)


# %%
def getEmptySalePool():
    sCols = [
        "Pool ID",
        "Asset Sold",
        "Asset Received",
        "Purchase Date",
        "Sale Date",
        "Amount",
        "Sale Price",
        "Asset Sold Spot Price",
        "Asset Received Spot Price",
        "Fee",
        "Fee Coin",
        "Fee Coin Spot Price",
        "Fee Fiat",
        "Purchase Pool ID",
        "Holding Period",
        "Long",
        "Proceeds",
        "Cost Basis",
        "Wash Pool ID",
        "Disallowed Loss",
        "Net Gain",
    ]
    typeDict = {
        "Pool ID": "int64",
        "Asset Sold": "object",
        "Asset Received": "object",
        "Purchase Date": "datetime64[ns, UTC]",
        "Sale Date": "datetime64[ns, UTC]",
        "Amount": "float64",
        "Sale Price": "float64",
        "Asset Sold Spot Price": "float64",
        "Asset Received Spot Price": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Fee Coin Spot Price": "float64",
        "Fee Fiat": "float64",
        "Purchase Pool ID": "int64",
        "Holding Period": "timedelta64[ns]",
        "Long": "bool",
        "Proceeds": "float64",
        "Cost Basis": "float64",
        "Wash Pool ID": "int64",
        "Disallowed Loss": "float64",
        "Net Gain": "float64",
    }

    salePool = pd.DataFrame(columns=sCols)
    salePool = salePool.astype(typeDict)

    return salePool


def getEmptyPurchasePool():
    pCols = [
        "Pool ID",
        "Active",
        "Purchase Date",
        "Asset",
        "Asset Spot Price",
        "Amount",
        "Fee",
        "Fee Coin",
        "Fee Coin Spot Price",
        "Fee Fiat",
        "Initiates Wash",
        "Holding Period Modifier",
        "Cost Basis",
        "Modified Cost Basis",
    ]
    typeDict = {
        "Pool ID": "int64",
        "Active": "bool",
        "Purchase Date": "datetime64[ns, UTC]",
        "Asset": "object",
        "Asset Spot Price": "float64",
        "Amount": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Fee Coin Spot Price": "float64",
        "Fee Fiat": "float64",
        "Initiates Wash": "bool",
        "Holding Period Modifier": "timedelta64[ns]",
        "Cost Basis": "float64",
        "Modified Cost Basis": "float64",
    }
    purchasePool = pd.DataFrame(columns=pCols)
    purchasePool = purchasePool.astype(typeDict)

    return purchasePool


def getEmptyOrder():
    pCols = [
        "Date(UTC)",
        "Market",
        "Type",
        "Price",
        "Amount",
        "Total",
        "Fee",
        "Fee Coin",
        "Market 1 Fiat Spot Price",
        "Market 2 Fiat Spot Price",
        "Fee Coin Fiat Spot Price",
    ]
    typeDict = {
        "Date(UTC)": "datetime64[ns, UTC]",
        "Market": "object",
        "Type": "object",
        "Price": "float64",
        "Amount": "float64",
        "Total": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Market 1 Fiat Spot Price": "float64",
        "Market 2 Fiat Spot Price": "float64",
        "Fee Coin Fiat Spot Price": "float64",
    }
    purchasePool = pd.DataFrame(columns=pCols)
    purchasePool = purchasePool.astype(typeDict)

    return purchasePool


# %%
