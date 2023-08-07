import logging

from cointracker.objects.orderbook import Order, OrderBook, Transaction
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.pool import Pool, Pools
from cointracker.objects.enumerated_values import TransactionType, OrderingStrategy
from cointracker.process.conversions import fiat_equivalent


def execute_order(order: Order, pools: Pools, strategy: OrderingStrategy):
    logging.debug(f"executing order with strategy {strategy}")
    buy_txn, sell_txn = split_order(order=order)

    # Add the buy pool to Pools after executing the sell side
    buy_pool = Pool(
        asset=buy_txn.asset,
        amount=buy_txn.amount,
        purchase_date=buy_txn.date,
        purchase_price_fiat=buy_txn.amount_fiat,
        purchase_fee_fiat=buy_txn.fee_fiat,
    )

    if pools is None:
        pools = Pools(pools=[buy_pool])
    else:
        pools = pools + buy_pool

    return pools


def split_order(order: Order):
    buy_txn = order.buy_transaction
    sell_txn = order.sell_transaction

    # Check that the fees aren't associated with the purchase/sale of fiat
    if buy_txn.asset.is_fiat:
        assert (
            buy_txn.fee == 0
        ), "Fees must be associated with token purchases/sales, not fiat purchases/sales"
    if sell_txn.asset.is_fiat:
        assert (
            sell_txn.fee == 0
        ), "Fees must be associated with token purchases/sales, not fiat purchases/sales"

    # buy_pool = Pool(
    #     asset=buy_txn.asset,
    #     amount=buy_txn.amount,
    #     purchase_date=buy_txn.date,
    #     purchase_price_fiat=buy_txn.amount_fiat,
    #     purchase_fee_fiat=buy_txn.fee_fiat,
    # )

    return buy_txn, sell_txn
