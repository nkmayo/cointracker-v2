import logging

from cointracker.objects.pool import Pool, PoolRegistry
from cointracker.process.conversions import split_pool


def unmatched_washes(pool_reg: PoolRegistry) -> bool:
    """Looks through pool_reg and returns `True` if an unmatched wash is found, otherwise returns `False`."""
    for pool in pool_reg:
        if pool.potential_wash:
            match = find_wash_match(pool, pool_reg=pool_reg)
            if match is not None:
                return True
    return False


def execute_washes(pool_reg: PoolRegistry) -> PoolRegistry:
    """
    Executes orders within `orderbook` according to the strategy in the configuration settings.
    Optionally, an existing set of `pools` can be specified to pull in previous data.

    """
    while unmatched_washes(pool_reg=pool_reg):
        pool_reg.sort(by="sale", ascending=True)
        for pool in pool_reg:
            if pool.potential_wash:
                matched_pool = find_wash_match(pool_with_loss=pool, pool_reg=pool_reg)
                if matched_pool is not None:
                    pool_reg = execute_wash(pool, matched_pool, pool_reg=pool_reg)
                    break  # break from the for loop and restart the while loop
    return pool_reg


def execute_wash(
    wash_pool: Pool, pool_that_triggered: Pool, pool_reg: PoolRegistry
) -> PoolRegistry:
    loss_amount = wash_pool.amount
    remaining_loss_amount = pool_that_triggered.amount - loss_amount

    frac_remaining = abs(remaining_loss_amount / loss_amount)

    if (frac_remaining < 0.01) & (
        loss_amount * frac_remaining * wash_pool.sale_value_fiat < 1
    ):
        # wash is considered completely matched if the remaining value is less than $1
        pass  # No split needed
    elif remaining_loss_amount > 0:
        # the pool_that_triggered has a greater amount than wash_pool. Split the pool_that_triggered into the wash_pool
        # amount and the extra (pool_that_triggered could simply retain the entire cost basis adjustment, but the remainder amount
        # may trigger other loss sales that it becomes hard to keep track of)
        remaining_fraction = remaining_loss_amount / pool_that_triggered.amount
        triggered_fraction = 1 - remaining_fraction

        pool_that_triggered, pool_remainder = split_pool(
            pool=pool_that_triggered, retained_fraction=triggered_fraction
        )

        pool_reg = pool_reg + pool_remainder

    elif remaining_loss_amount < 0:
        # the wash_pool has a greater_amount than the pool_that_triggered. Split wash_pool and apply the proportional
        # disallowed loss to pool_that_triggered. The remaining split will have to also seek out another pool that might potentially
        # trigger a wash sale for it as well.
        wash_fraction = -remaining_loss_amount / wash_pool.amount

        wash_pool, pool_remainder = split_pool(
            pool=wash_pool, retained_fraction=wash_fraction
        )

        pool_reg = pool_reg + pool_remainder

    # Update the wash_pool and pool_that_triggered
    wash_pool.wash_pool_id = pool_that_triggered.id
    wash_pool.disallowed_loss = wash_pool.sale_value_fiat

    pool_that_triggered.triggers_wash_id = wash_pool.id
    pool_that_triggered.wash_sale_addition_to_cost_fiat = wash_pool.sale_value_fiat
    pool_that_triggered.holding_period_modifier = wash_pool.holding_period

    # Update both pools within pool_reg
    wash_idx = pool_reg.idx_for_id(wash_pool.id)
    triggered_idx = pool_reg.idx_for_id(pool_that_triggered.id)
    pool_reg[wash_idx] = wash_pool
    pool_reg[triggered_idx] = pool_that_triggered

    return pool_reg


def find_wash_match(pool_with_loss: Pool, pool_reg: PoolRegistry) -> Pool:
    """For the given `pool_with_loss` that has a negative `net_gain`"""
    # NOTE: OrderingStrategy shouldn't matter at this point as the orders have already been executed
    assert (
        pool_with_loss.potential_wash
    ), "Only pools with negative net gain can be triggered as a wash sale"
    loss_sale_date = pool_with_loss.sale_date
    pool_reg.sort(by="purchase", ascending=True)
    matched_pool = None
    for pool in pool_reg:
        within_wash_window = pool.within_wash_window(
            date=loss_sale_date, kind="purchase"
        )
        after_loss_sale = pool.purchase_date > loss_sale_date
        matched_assets = pool.asset == pool_with_loss.asset
        not_already_paired = pool.triggers_wash_id is None

        if all(
            (within_wash_window, after_loss_sale, matched_assets, not_already_paired)
        ):
            logging.debug(
                f"Purchase {pool} triggers the wash rule in pool {pool_with_loss}"
            )
            matched_pool = pool
            break

    return matched_pool
