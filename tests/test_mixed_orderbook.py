from cointracker.objects.orderbook import Order, OrderBook
from cointracker.objects.enumerated_values import OrderingStrategy
from cointracker.process.execute import execute_order
import pandas as pd
import numpy as np


def test_mixed_orderbook_creation(mixed_orderbook) -> None:
    assert (
        type(mixed_orderbook) == OrderBook
    ), f"OrderBook ({type(mixed_orderbook)}) should be of type `OrderBook`"
    for order in mixed_orderbook:
        assert (
            type(order) == Order
        ), f"Order ({type(order)}) in `OrderBook` should be of type `Order`"


def test_mixed_orderbook_to_df_ascending(mixed_orderbook) -> None:
    order_df = mixed_orderbook.to_df(ascending=True)
    assert (
        type(order_df) == pd.DataFrame
    ), f"OrderBook ({type(order_df)}) should be of type `pd.DataFrame`"

    ordered_dates = order_df["Date(UTC)"].to_list()
    prev_date = None
    for i, date in enumerate(ordered_dates):
        if i == 0:
            prev_date = date
        else:
            assert (
                prev_date <= date
            ), f"Incorrect ascending ordering at index {i} and date {date}"


def test_mixed_orderbook_to_df_descending(mixed_orderbook) -> None:
    order_df = mixed_orderbook.to_df(ascending=False)
    assert (
        type(order_df) == pd.DataFrame
    ), f"OrderBook ({type(order_df)}) should be of type `pd.DataFrame`"

    ordered_dates = order_df["Date(UTC)"].to_list()
    prev_date = None
    for i, date in enumerate(ordered_dates):
        if i == 0:
            prev_date = date
        else:
            assert (
                prev_date >= date
            ), f"Incorrect descending ordering at index {i} and date {date}"


def test_mixed_orderbook_execution_fifo(mixed_orderbook) -> None:
    """This orderbook consists of 7 orders (after preprocessing combines 2 ADA orders from the same day), 4 buys and 3 sells.

    BUY 5 ETH at 1000 USD each for 5000 USD (id 0)
    BUY 5 ETH at 1100 USD each for 5500 USD (id 1)
    BUY 15000 ADA at 0.56667 USD each (avg) for 8500 USD (id 2)
    BUY 0.5 ETH for 1000 ADA
        SELL 1000 ADA at 1 USD each for 1000 USD
            -set id 2 (15000 ADA) to 1000 ADA at 0.56667 USD each for 566.67 USD (id 2)
            -close id 2 for with 433.33 USD net gain
            -new id 4 has 14000 ADA at 0.56667 USD each for 7933.38 USD (id 3)
        BUY 0.5 ETH at 2000 USD each for 1000 USD (id 4)
    SELL 0.5 ETH for 1100 ADA
        SELL 0.5 ETH at 2200 USD each for 1100 USD
            -set id 0 (5 ETH) to 0.5 ETH at 1000 USD each for 500 USD (id 0)
            -close id 0 with 600 USD net gain
            -new id 5 has 4.5 ETH at 1000 USD each for 4500 USD (id 5)
        BUY 1100 ADA at 1 USD each for 1100 USD (id 6)
    SELL 6 ETH at 1000 each for 6000 USD
        SELL 1.5 ETH at 1000 each for 1500 USD
            -set id 1 (5 ETH) to 1.5 ETH at 1100 USD each for 1650 USD (id 0)
            -close id 1 with -150 USD net gain
            -new id 7 has 3.5 ETH at 1100 USD each for 3850 USD (id 7)
        SELL 4.5 ETH at 1000 each for 4500 USD
            -close id 5 with 0 USD net gain
    SELL 12500 ADA at 0.75 USD each for 9375 USD
        -set id 3 to (14000 ADA) 12500 ADA at 0.56667 USD each for 7083.33 USD (id 3)
        -close id 3 with 2291.67 USD net gain
        -new id 8 has 1500 ADA at 0.56667 USD each for 850 USD (id 8)

    Cumulative gain: 433.33 + 600 - 150 + 0 + 2291.67 = 3175 USD

    """
    pool_reg = None
    for (
        order
    ) in mixed_orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(order, pools=pool_reg, strategy=OrderingStrategy.FIFO)
    pool_reg.sort(by="sale", ascending=True)  # most recent sales at the bottom
    print([pool for pool in pool_reg])

    assert (
        np.round(pool_reg[0].net_gain, decimals=2) == 433.33
    ), "First pool to be closed out has a net gain of 433.33"
    assert (
        np.round(pool_reg[1].net_gain, decimals=2) == 600.00
    ), "Second pool to be closed out has a net gain of 600.00"
    assert (
        np.round(pool_reg[2].net_gain, decimals=2) == -150.00
    ), "Third pool to be closed out has a net gain of -150.00"
    assert (
        np.round(pool_reg[3].net_gain, decimals=2) == 0.00
    ), "Fourth pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[4].net_gain, decimals=2) == 2291.67
    ), "Fifth pool to be closed out has a net gain of 2291.67"

    assert pool_reg.proceeds == 17475.0, "Net Proceeds should be 17475 USD"
    assert pool_reg.cost_basis == 14300.0, "Net Cost Basis should be 14300 USD"
    assert pool_reg.disallowed_loss == 0.0, "Net Disallowed Loss should be 0 USD"
    assert pool_reg.net_gain == 3175.0, "Total Net Gain should be 3175 USD"
