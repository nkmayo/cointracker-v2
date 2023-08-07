from cointracker.objects.orderbook import Order, OrderBook, Transaction
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.pool import Pool, Pools
from cointracker.objects.enumerated_values import TransactionType, OrderingStrategy
from cointracker.process.conversions import fiat_equivalent
from cointracker.process.transact import execute_order
from cointracker.settings.config import read_config


def execute_orderbook(orderbook: OrderBook, pools: Pools = None):
    """
    Executes orders within `orderbook` according to the strategy in the configuration settings.
    Optionally, an existing set of `pools` can be specified to pull in previous data.

    """
    cfg = read_config()
    for order in orderbook:
        pools = execute_order(
            order, pools=pools, strategy=cfg.processing.ordering_strategy
        )

    return pools
