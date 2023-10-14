# %%
import numpy as np
import pandas as pd
import datetime
import uuid
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset

WASH_WINDOW = datetime.timedelta(days=31)
VARIOUS_DATES_MICROSECOND = 123456


@dataclass
class Wash:
    triggered_by_id: uuid = None
    triggers_id: uuid = None
    addition_to_cost_fiat: float = 0.0
    disallowed_loss_fiat: float = 0.0
    holding_period_modifier: datetime.timedelta = datetime.timedelta(days=0)

    def copy(self):
        return Wash(**self.__dict__)


@dataclass
class Pool:
    # TODO: need to generate a unique id that is aware of what other id's have been loaded (from file perhaps). Or perhaps
    # change all loaded assets (and references to them) to negative numbers. This however would create a conflict when new
    # pools are created (id 1, 2, 3, etc) and then saved again, having the same id (-1, -2, -3) as previously saved pools.
    asset: Asset
    amount: float  # convert to int with market1 units?
    purchase_date: datetime.datetime
    purchase_cost_fiat: float
    purchase_fee_fiat: float
    sale_date: datetime.datetime = None
    sale_value_fiat: float = None
    sale_fee_fiat: float = None
    wash: Wash = field(default_factory=Wash)  # don't share the same instance
    id: uuid = field(default_factory=uuid.uuid4)  # don't share the same instance

    def __repr__(self) -> str:
        return f"Pool(\nid: {self.id}, \npurchase date: {self.purchase_date_str}, \nsale date: {self.sale_date_str}, \
                \nasset: {self.asset.ticker}, \namount: {self.amount}, \ncost_fiat: {self.purchase_cost_fiat}, \
                \nsale_fiat: {self.sale_value_fiat}\n)\n\n"

    @property
    def purchase_date_str(self) -> str:
        return date_to_str(self.purchase_date, kind="sales report")

    @property
    def sale_date_str(self) -> str:
        return date_to_str(self.sale_date, kind="sales report")

    @property
    def holding_period(self) -> datetime.timedelta:
        """Returns the total adjusted holding period of the sale or `None` if the pool is still open."""
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
        """Returns `True` if holdings are long-term, `False` if holdings are short-term, and `None` if the pool is open."""
        if self.open:
            return None
        else:
            return self.holding_period >= datetime.timedelta(days=366)

    @property
    def holdings_type_str(self) -> str:
        """Converts the `holdings_type` boolean and returns a descriptive string."""
        if self.open:
            return None
        elif self.holdings_type:
            return "LONG-TERM"
        else:
            return "SHORT-TERM"

    @property
    def cost_basis(self):
        """Returns the pool's total cost basis with adjustments and purchasing fees in fiat."""
        return (
            self.purchase_cost_fiat
            + self.wash.addition_to_cost_fiat
            + self.purchase_fee_fiat
        )

    @property
    def proceeds(self):
        """Returns the pool's total proceeds in fiat, i.e. the sale value minus sale fees. Returns `None` if the pool is open."""
        if self.open:
            return None
        else:
            return self.sale_value_fiat - self.sale_fee_fiat

    @property
    def net_gain(self):
        """Returns the pool's net gain from proceeds in fiat, including any disallowed loss. Returns `None` if the pool is open."""
        if self.open:
            return None
        else:
            # (proceeds - cost_basis) is negative if there is disallowed loss
            return self.proceeds - self.cost_basis + self.wash.disallowed_loss_fiat

    @property
    def potential_wash(self):
        """Returns `True` if the pool could potentially become a wash sale and `False` otherwise."""
        if self.open:
            return False
        elif (self.asset.fungible) & (self.net_gain < 0) & (not self.is_wash):
            return True
        else:
            return False

    @property
    def closed(self) -> bool:
        """Returns `True` if the pool is closed and the asset has been sold. Returns `False` otherwise."""
        if self.sale_date is None:
            return False
        else:
            return True

    @property
    def open(self) -> bool:
        """Returns `True` if the pool is open and the asset has NOT been sold. Returns `False` otherwise."""
        return not self.closed

    @property
    def is_wash(self) -> bool:
        """Returns `True` if the pool's cost basis is modified by a wash sale."""
        if self.wash.triggered_by_id is None:
            return False
        else:
            return True

    def copy(self):
        attrs = self.__dict__.copy()  # don't pop this __dict__
        attrs.pop("id")
        attrs["wash"] = self.wash.copy()
        return Pool(**attrs)

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
        return pd.Series(self.to_dict())

    def to_dict(self) -> dict:
        attr_dict = self.__dict__.copy()
        attr_dict.pop("wash")
        wash_dict = self.wash.__dict__.copy()
        return {**attr_dict, **wash_dict}

    def to_sales_report(self):
        """Returns a sales report row for IRS form 8949 if the object is closed."""
        if self.closed:
            return {
                "Asset Sold": self.asset.ticker,
                "Purchase Date": date_to_str(self.purchase_date, kind="sales report"),
                "Sale Date": date_to_str(self.sale_date, kind="sales report"),
                "Amount": self.amount,
                "Spot Price (USD)": self.sale_value_fiat / self.amount,
                "Fee": self.sale_fee_fiat,
                "Holding Period": self.holding_period.days,
                "Short/Long": self.holdings_type_str,
                "Proceeds": self.proceeds,
                "Cost Basis": self.cost_basis,
                "Wash Sale": "W" if self.is_wash else "",
                "Disallowed Loss": self.wash.disallowed_loss_fiat,
                "Net Gain": self.net_gain,
            }
        else:
            return None

    def to_irs8949(self):
        """Returns a sales report row for IRS form 8949 if the object is closed."""
        if self.closed:
            return {
                "Asset Sold": self.asset.ticker,
                "Amount": self.amount,
                "Description of Property": f"{self.amount} of {self.asset.ticker}",
                "Date Acquired (Mo., day, yr.)": date_to_str(
                    self.purchase_date, kind="irs"
                ),
                "Date Sold (Mo., day, yr.)": date_to_str(self.sale_date, kind="irs"),
                "Proceeds": self.proceeds,
                "Cost Basis": self.cost_basis,
                "Adjustment Code": "W" if self.is_wash else "",
                "Amount of Adjustment": self.wash.disallowed_loss_fiat,
                "Gain": self.net_gain,
            }
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
        return self.pools.__iter__()

    def __next__(self):
        return self.pools.__next__()

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return self.pools[start:stop:step]
        elif isinstance(key, (int, np.integer)):
            return self.pools[key]
        elif isinstance(key, str):
            pools = [
                pool
                for pool in self
                if (
                    pool.asset.name.upper() == key.upper()
                    or pool.asset.ticker.upper() == key.upper()
                )
            ]
            return PoolRegistry(pools=pools)
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
        """Pools where the asset has been sold."""
        return PoolRegistry([pool for pool in self if pool.closed])

    @property
    def open_pools(self):
        """Pools where the asset has not been sold."""
        return PoolRegistry([pool for pool in self if pool.open])

    @property
    def shorts(self):
        """Short-term holding pools."""
        return PoolRegistry(
            [
                pool
                for pool in self.closed_pools
                if pool.holdings_type and pool.asset.fungible
            ]
        )

    @property
    def longs(self):
        """Long-term holding pools."""
        return PoolRegistry(
            [
                pool
                for pool in self.closed_pools
                if (not pool.holdings_type) and pool.asset.fungible
            ]
        )

    @property
    def nfts(self):
        """Pools with collectibles/non-fungible tokens."""
        return PoolRegistry([pool for pool in self if not pool.asset.fungible])

    @property
    def tokens(self):
        """Pools with fungible tokens."""
        return PoolRegistry([pool for pool in self if pool.asset.fungible])

    @property
    def proceeds(self) -> float:
        """Net proceeds from all pools."""
        return np.around(
            sum([pool.proceeds for pool in self if pool.closed]), decimals=2
        )

    @property
    def cost_basis(self) -> float:
        """Net cost basis from all pools"""
        return np.around(
            sum([pool.cost_basis for pool in self if pool.closed]), decimals=2
        )

    @property
    def disallowed_loss(self) -> float:
        """Net disallowed loss from all pools."""
        return np.around(
            sum([pool.wash.disallowed_loss_fiat for pool in self if pool.closed]),
            decimals=2,
        )

    @property
    def net_gain(self) -> float:
        """Net gain from all pools."""
        return np.around(
            sum([pool.net_gain for pool in self if pool.closed]), decimals=2
        )

    @property
    def is_empty(self) -> bool:
        """Returns `True` if the `PoolRegistry` has no elements, `False` otherwise."""
        return len(self.pools) == 0

    @property
    def tickers(self) -> set:
        """Returns the set of tickers for all assets contained within the `PoolRegistry`."""
        return {pool.asset.ticker for pool in self}

    @property
    def assets(self):
        """Returns the set of unique `Asset`s contained within the `PoolRegistry`."""
        return {pool.asset for pool in self}

    @property
    def washes(self):
        """All `Pool`s that contain a disallowed loss.
        NOTE: The technical definition is that the pool contains a `wash.triggered_by_id`, but these pools subsequently have
        a disallowed wash added.
        """
        return PoolRegistry([pool for pool in self if pool.is_wash])

    @property
    def not_washes(self):
        """All `Pool`s that do not contain a disallowed loss.
        NOTE: The technical definition is that the pool's `wash.triggered_by_id is None`.
        """
        return PoolRegistry([pool for pool in self if not pool.is_wash])

    def idx_for_id(self, id: uuid):
        """Returns the index (as currently sorted) within the `pools` list of the pool with id `id`."""
        return ([pool.id for pool in self]).index(id)

    def by_year(self, year: int, by: str = "sale"):
        """Returns pools whose purchase or sale date was in the `year` specified.`"""
        if by.lower() == "sale":
            pool_reg = PoolRegistry(
                pools=[pool for pool in self if pool.sale_date.year == year]
            )
        if by.lower() == "purchase":
            pool_reg = PoolRegistry(
                pools=[pool for pool in self if pool.purchase_date.year == year]
            )
        return pool_reg

    def pools_with(
        self,
        asset: Asset = None,
        open: bool = None,
        long_term: bool = None,
        wash: bool = None,
        purchase_date: datetime = None,
        sale_date: datetime = None,
        explicit_date: bool = False,
    ):
        """Returns the subset of pools with with the matching conditions. Any of the parameters that are `None` have no effect on the
        filtering process. If `explicit_date` is `False` then all pools that match to the day are returned.
        """
        if asset is None:
            subset = self
        else:
            subset = self[asset.ticker]

        if open is None:
            pass
        elif open:
            subset = subset.open_pools
        else:
            subset = subset.closed_pools

        if long_term is None:
            pass
        elif long_term:
            subset = subset.longs
        else:
            subset = subset.shorts

        if wash is None:
            pass
        elif wash:
            subset = subset.washes
        else:
            subset.not_washes

        if purchase_date is None:
            pass
        else:
            if explicit_date:
                subset = PoolRegistry(
                    [pool for pool in subset if pool.purchase_date == purchase_date]
                )
            else:
                subset = PoolRegistry(
                    [
                        pool
                        for pool in subset
                        if pool.purchase_date.date() == purchase_date.date()
                    ]
                )

        if sale_date is None:
            pass
        else:
            if explicit_date:
                subset = PoolRegistry(
                    [pool for pool in subset if pool.sale_date == sale_date]
                )
            else:
                subset = PoolRegistry(
                    [
                        pool
                        for pool in subset
                        if pool.sale_date.date() == sale_date.date()
                    ]
                )

        return subset

    def sort(self, by: str = "purchase", ascending: bool = True) -> None:
        """Sorts the pools in the `PoolRegistry` in place by date. `acending=True` sorts oldest to newest."""
        pool_reg = sort_pools(self, by=by, ascending=ascending)
        self.pools = pool_reg.pools

    def to_df(self, ascending=True, kind="sales_report"):
        """Converts the `PoolRegistry` object into a pandas DataFrame. Sorts orders by ascending date if `ascending=True`,
        descending date if `ascending=False` or does not change the ordering indicies if `ascending=None`.
        """
        pool_reg = sort_pools(self, by="sale", ascending=ascending)
        if kind == "sales_report":
            df = pd.DataFrame(
                [pool.to_sales_report() for pool in pool_reg.closed_pools]
            )
        elif kind in ["irs", "tax", "8949"]:
            df = pd.DataFrame([pool.to_irs8949() for pool in pool_reg.closed_pools])
        else:
            df = pd.DataFrame([pool.to_dict() for pool in pool_reg])

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


def date_to_str(date: datetime.datetime, kind: str = "default"):
    if date is None:
        date_str = "None"
    elif date.microsecond == VARIOUS_DATES_MICROSECOND:
        date_str = "Various Dates"
    elif kind.lower() == "sales report":
        date_str = date.strftime("%Y/%m/%d")
    elif kind.lower() in ["irs", "tax", "8949"]:
        date_str = date.strftime("%m/%d/%Y")
    else:
        date_str = date.strftime("%Y/%m/%d %H:%M:%S")

    return date_str


# %%
