from cointracker.objects.asset import Asset


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
