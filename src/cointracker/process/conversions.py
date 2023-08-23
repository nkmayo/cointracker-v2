from cointracker.objects.asset import Asset
from cointracker.objects.pool import Pool


def fiat_equivalent(amount: float, spot_price: float, asset: Asset):
    total_float = amount * spot_price
    # TODO: base units conversion...
    total = total_float
    return total


def amount_from_price_total(spot: float, total: float, asset: Asset, market_num: int):
    amount_float = (
        total / spot
    )  # TODO: consider market_1/market_2 price vs market_2/market_1 price
    # TODO: base units conversion...
    return amount_float


def split_pool(pool: Pool, retained_fraction: float):
    assert not pool.is_wash, "Pools already in a wash sale cannot be additionally split"
    assert (
        pool.triggers_wash_id is None
    ), "Pools that have already triggered a wash sale cannot be additonally split"
    fragment_fraction = 1 - retained_fraction

    fragment = pool.copy()
    fragment.amount = fragment.amount * fragment_fraction
    fragment.purchase_cost_fiat = fragment.purchase_cost_fiat * fragment_fraction
    fragment.purchase_fee_fiat = fragment.purchase_fee_fiat * fragment_fraction
    if fragment.closed:
        fragment.sale_value_fiat = fragment.sale_value_fiat * fragment_fraction
        fragment.sale_fee_fiat = fragment.sale_fee_fiat * fragment_fraction

    pool.amount = pool.amount * retained_fraction
    pool.purchase_cost_fiat = pool.purchase_cost_fiat * retained_fraction
    pool.purchase_fee_fiat = pool.purchase_fee_fiat * retained_fraction
    if pool.closed:
        pool.sale_value_fiat = pool.sale_value_fiat * retained_fraction
        pool.sale_fee_fiat = pool.sale_fee_fiat * retained_fraction

    return pool, fragment
