import logging
import numpy as np
from cointracker.objects.orderbook import Order, OrderBook, Transaction
from cointracker.objects.asset import Asset, AssetRegistry
from cointracker.objects.pool import Pool, PoolRegistry
from cointracker.objects.enumerated_values import TransactionType, OrderingStrategy
from cointracker.objects.exceptions import NoMatchingPoolError
from cointracker.process.conversions import fiat_equivalent


def execute_order(
    order: Order, pools: PoolRegistry, strategy: OrderingStrategy
) -> PoolRegistry:
    print(f"\n\n")
    logging.debug(f"executing order {order} with strategy {strategy}")
    logging.debug(f"---Initial pools list: {pools}")
    buy_txn, sell_txn = split_order(order=order)

    if (not sell_txn.asset.is_fiat) and (sell_txn.amount != 0.0):
        pools = execute_sell(sell_txn=sell_txn, pool_reg=pools, strategy=strategy)
    logging.debug(f"---Pools list after execute_sell: {pools}")
    # Add the buy pool to Pools after executing the sell side

    if (not buy_txn.asset.is_fiat) and (buy_txn.amount != 0.0):
        buy_pool = Pool(
            asset=buy_txn.asset,
            amount=buy_txn.amount,
            purchase_date=buy_txn.date,
            purchase_cost_fiat=buy_txn.amount_fiat,
            purchase_fee_fiat=buy_txn.fee_fiat,
        )

        if pools is None:
            pools = PoolRegistry(pools=[buy_pool])
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

    return buy_txn, sell_txn


def execute_sell(
    sell_txn: Transaction, pool_reg: PoolRegistry, strategy: OrderingStrategy
) -> PoolRegistry:
    print(
        f"entered execute_sell of asset {sell_txn.asset.ticker} and amount {sell_txn.amount}:\n{pool_reg}"
    )
    """Executes the sale side of an order using the specified `strategy`."""
    candidate_pools = pool_reg[sell_txn.asset.ticker].open_pools

    if strategy == OrderingStrategy.FIFO:
        candidate_pools.sort(by="sale", ascending=True)
    elif strategy == OrderingStrategy.LIFO:
        candidate_pools.sort(by="sale", ascending=False)

    if candidate_pools.is_empty:
        non_candidate_pools = pool_reg[sell_txn.asset.ticker].closed_pools
        print(f"sell_txn:\n{sell_txn}")
        print(
            f"All pools with {sell_txn.asset}:\n{non_candidate_pools.to_df(kind='dict')}"
        )
        raise NoMatchingPoolError(
            f"No matching pool found for {sell_txn.asset} on {sell_txn.date}"
        )

    matched_pool = candidate_pools[0]
    remaining_sell_amount = sell_txn.amount - matched_pool.amount
    logging.debug(f"beginning {remaining_sell_amount=}")

    frac_remaining = abs((remaining_sell_amount) / sell_txn.amount)
    # if selling > 99% and the percent remaining is less than $1 round it to selling the entire pool
    if (frac_remaining < 0.01) & (
        sell_txn.amount * frac_remaining * sell_txn.asset_spot_fiat < 1
    ):
        remaining_sell_amount = 0
        sell_txn.amount = matched_pool.amount

    if remaining_sell_amount == 0:
        # if the sale amount exactly matches that in the matched pool, update and close the matched pool
        logging.debug("sale amount matched exactly with pool")
        matched_pool.sale_date = sell_txn.date
        matched_pool.sale_value_fiat = sell_txn.amount_fiat
        matched_pool.sale_fee_fiat = sell_txn.fee_fiat
    elif remaining_sell_amount < 0:
        # else if the matched pool has more money than the sale_txn amount, update the matched pool
        # and generate a new pool with the remaining balance

        # logging.debug(
        #     f"Matched pool has more money ({matched_pool.amount}) than the sale_txn ({sell_txn.amount})"
        # )
        matched_pool_excess_amount = (
            -remaining_sell_amount
        )  # renaming the negative for clarity
        pool_excess_fraction = matched_pool_excess_amount / matched_pool.amount
        matched_fraction = 1 - pool_excess_fraction

        excess_pool = matched_pool.copy()
        print(
            f"excess pool asset {excess_pool.asset}\nmatched_pool asset: {matched_pool.asset}"
        )
        excess_pool.amount = matched_pool_excess_amount
        excess_pool.purchase_cost_fiat = (
            matched_pool.purchase_cost_fiat * pool_excess_fraction
        )
        excess_pool.purchase_fee_fiat = (
            matched_pool.purchase_fee_fiat * pool_excess_fraction
        )

        err = (
            sell_txn.amount - (matched_pool.amount - matched_pool_excess_amount)
        ) / sell_txn.amount
        assert (
            err < 0.001
        ), f"excess_amount ({sell_txn.amount}) should equal pool.amount - txn.amount ({matched_pool.amount - matched_pool_excess_amount}) (rounding?)"

        # assert (
        #     sell_txn.amount == matched_pool.amount * matched_fraction
        # ), f"sale amount ({sell_txn.amount}) should equal pool_amount * matched_fraction ({matched_pool.amount * matched_fraction})"

        excess_pool.set_dtypes()
        pool_reg = pool_reg + excess_pool

        matched_pool.amount = (
            sell_txn.amount
        )  # same as matched_amount * matched_fraction
        matched_pool.purchase_cost_fiat = (
            matched_pool.purchase_cost_fiat * matched_fraction
        )
        matched_pool.purchase_fee_fiat = (
            matched_pool.purchase_fee_fiat * matched_fraction
        )
        matched_pool.sale_date = sell_txn.date
        matched_pool.sale_value_fiat = sell_txn.amount_fiat
        matched_pool.sale_fee_fiat = sell_txn.fee_fiat
    else:  # remaining_sell_amount > 0
        # else if the matched_pool has less than the sale amount, close the matched_pool and generate a new transaction
        # with the remaining txn balance (TODO: or do you just update the existing txn?)

        # logging.debug(
        #     f"sale_txn ({sell_txn.amount}) greater than matched_pool ({matched_pool.amount}) requires an additional pool to complete. Closing matched_pool"
        # )
        matched_fraction = matched_pool.amount / sell_txn.amount
        txn_excess_fraction = 1 - matched_fraction

        remaining_txn = sell_txn.copy()
        remaining_txn.amount = remaining_sell_amount
        remaining_txn.fee = 0  # let the matched_pool contain the entirety of the fees...fewer adjustments

        assert_test = sell_txn.amount_fiat * matched_fraction
        sell_txn.amount = matched_pool.amount

        assert np.round(sell_txn.amount_fiat, decimals=2) == np.round(
            assert_test, decimals=2
        ), "sale_cost_fiat should be the previous amount * matched_fraction"

        matched_pool.sale_date = sell_txn.date
        matched_pool.sale_value_fiat = sell_txn.amount_fiat
        matched_pool.sale_fee_fiat = (
            sell_txn.fee_fiat
        )  # let the matched_pool contain the entirety of the fees...fewer adjustments
        # logging.debug(
        #     f"matched_pool closed, seeking additonal pool for the remaining ({remaining_txn.amount})"
        # )

    matched_pool.set_dtypes()
    # logging.debug(f"matched_pool:\n{matched_pool}")
    # Update the pool registry with the new pool after the sale
    idx = pool_reg.idx_for_id(matched_pool.id)
    # logging.debug(
    #     f"idx: {idx}\npool_reg.pools[idx] (id={pool_reg.pools[idx].id}):\n{pool_reg.pools[idx]}"
    # )
    pool_reg.pools[idx] = matched_pool

    # Recursively repeat the process if there is a remaining transaction
    if remaining_sell_amount > 0:
        print(f"about to execute_sell: {pool_reg}")
        print(f"{[pool for pool in pool_reg]}")
        pool_reg = execute_sell(
            sell_txn=remaining_txn, pool_reg=pool_reg, strategy=strategy
        )

    return pool_reg
