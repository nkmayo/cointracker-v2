from cointracker.objects.orderbook import Order, OrderBook, Transaction
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.pool import Pool, PoolRegistry
from cointracker.objects.enumerated_values import TransactionType, OrderingStrategy
from cointracker.process.conversions import fiat_equivalent
from cointracker.process.transact import execute_order
from cointracker.process.wash import execute_washes
from cointracker.settings.config import read_config


def execute_orderbook(
    orderbook: OrderBook, pool_reg: PoolRegistry = None
) -> PoolRegistry:
    """
    Executes orders within `orderbook` according to the strategy in the configuration settings.
    Optionally, an existing set of `pools` can be specified to pull in previous data.

    """
    cfg = read_config()
    for order in orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(
            order, pools=pool_reg, strategy=cfg.processing.ordering_strategy
        )

    if cfg.processing.wash_rule:
        pool_reg = execute_washes(pool_reg=pool_reg)

    return pool_reg
