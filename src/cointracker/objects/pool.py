# %%
import numpy as np
import pandas as pd
import datetime
from itertools import count
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset

WASH_WINDOW = datetime.timedelta(days=31)


@dataclass
class Wash:
    triggered_by_id: int = None
    triggers_id: int = None
    addition_to_cost_fiat: float = 0.0
    disallowed_loss_fiat: float = 0.0
    holding_period_modifier: datetime.timedelta = datetime.timedelta(days=0)

    def copy(self):
        return Wash(
            triggered_by_id=self.triggered_by_id,
            triggers_id=self.triggers_id,
            addition_to_cost_fiat=self.addition_to_cost_fiat,
            disallowed_loss_fiat=self.disallowed_loss_fiat,
            holding_period_modifier=self.holding_period_modifier,
        )


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
    wash: Wash = Wash()

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
            return (
                self.sale_date - self.purchase_date + self.wash.holding_period_modifier
            )

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
        return (
            self.purchase_cost_fiat
            + self.wash.addition_to_cost_fiat
            + self.purchase_fee_fiat
        )

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
            # (proceeds - cost_basis) is negative if there is disallowed loss
            return self.proceeds - self.cost_basis + self.wash.disallowed_loss_fiat

    @property
    def potential_wash(self):
        if self.open:
            return False
        elif (self.asset.fungible) & (self.net_gain < 0) & (not self.is_wash):
            return True
        else:
            return False

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
        if self.wash.triggered_by_id is None:
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
            wash=self.wash.copy(),
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
            self.wash.disallowed_loss_fiat = np.round(
                self.wash.disallowed_loss_fiat, decimals=2
            )
            self.wash.addition_to_cost_fiat = np.round(
                self.wash.addition_to_cost_fiat, decimals=2
            )

    def to_series(self):
        raise NotImplementedError

    def to_sales_report(self):
        """Returns a sales report row for IRS form 8949 if the object is closed."""
        if self.closed:
            series = {
                "Asset Sold": self.asset.ticker,
                "Purchase Date": self.purchase_date.strftime("%Y-%m-%d"),
                "Sale Date": self.sale_date.strftime("%Y-%m-%d"),
                "Amount": self.amount,
                "Spot Price (USD)": np.round(
                    self.sale_value_fiat / self.amount, decimals=2
                ),
                "Fee": self.sale_fee_fiat,
                "Holding Period": self.holding_period.days,
                "Short/Long": self.holdings_type_str,
                "Proceeds": self.proceeds,
                "Cost Basis": self.cost_basis,
                "Wash Sale": "W" if self.is_wash else "",
                "Disallowed Loss": self.wash.disallowed_loss_fiat,
                "Net Gain": self.net_gain,
            }
            return pd.Series(series)
        else:
            return None

    def to_irs8949(self):
        """Returns a sales report row for IRS form 8949 if the object is closed."""
        if self.closed:
            series = {
                "Description of Property": f"{self.amount} of {self.asset.ticker}",
                "Date Acquired (Mo., day, yr.)": self.purchase_date.strftime(
                    "%m/%d/%Y"
                ),
                "Date Acquired (Mo., day, yr.)": self.sale_date.strftime("%m/%d/%Y"),
                "Proceeds": self.proceeds,
                "Cost Basis": self.cost_basis,
                "Adjustment Code": "W" if self.is_wash else "",
                "Amount of Adjustment": self.wash.disallowed_loss_fiat,
                "Gain": self.net_gain,
            }
            return pd.Series(series)
        else:
            return None

    def within_wash_window(self, date: datetime, kind="purchase"):
        if kind == "sale":
            return abs(self.sale_date - date) < WASH_WINDOW
        elif kind == "purchase":
            return abs(self.purchase_date - date) < WASH_WINDOW
        else:
            raise ValueError(
                "Unrecognized `kind` argument when calling `within_wash_window`."
            )


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
        elif isinstance(key, (int, np.integer)):
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

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            self.pools[start:stop:step] = value
        elif isinstance(key, (int, np.integer)):
            self.pools[key] = value
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
        return sum([pool.wash.disallowed_loss_fiat for pool in self if pool.closed])

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

    def to_df(self, ascending=True, kind="sales_report"):
        """Converts the `PoolRegistry` object into a pandas DataFrame. Sorts orders by ascending date if `ascending=True`,
        descending date if `ascending=False` or does not change the ordering indicies if `ascending=None`.
        """
        pool_reg = sort_pools(self, by="purchase", ascending=ascending)
        if kind == "sales_report":
            df = pd.DataFrame(
                [pool.to_sales_report() for pool in pool_reg.closed_pools]
            )
        elif kind in ["irs", "tax", "8949"]:
            df = pd.DataFrame([pool.to_irs8949() for pool in pool_reg.closed_pools])
        else:
            df = pd.DataFrame([pool.to_series() for pool in pool_reg])

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
