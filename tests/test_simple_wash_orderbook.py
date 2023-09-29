from cointracker.objects.enumerated_values import OrderingStrategy
from cointracker.process.execute import execute_order, execute_washes
import numpy as np


def test_simple_wash_orderbook_execution(simple_wash_orderbook) -> None:
    """This orderbook consists of 8 orders, 4 buys and 4 sells.

    BUY 5 ETH at 1000 USD each for 5000 USD (id 0)
    SELL 5 ETH at 900 USD each for 4500 USD
        - close id 0 with -500 USD net gain

    BUY 6 ETH at 1000 USD each for 6000 USD (id 1)
    SELL 6 ETH at 1100 USD each for 6600 USD
        - close id 1 with 600 USD net gain

    BUY 1000 ADA at 1 USD each for 1000 USD (id 2)
    SELL 500 ADA at 0.90 USD each for 450 USD
        - set id 2 (1000 ADA) to have 500 ADA at 1 USD each
        - close id 2 with -50 USD net gain
        - new id 3 has 500 ADA at 1 USD each (id 3)

    BUY 1000 ADA at 0.80 USD each for 800 USD (id 4)
    SELL 1500 ADA at 0.80 USD each for 1200 USD
        SELL 500 ADA at 0.80 USD each for 400 USD
            - close id 3 with -100 USD net gain
        SELL 1000 ADA at 0.80 USD each for 800 USD
            - close id 4 with 0 USD net gain

    Cumulative gain: -500 + 600 - 50 - 100 + 0 = -50 USD

    Wash Sales Are Computed
    Split id 1
        - set id 1 (6 ETH) to 5 ETH at 1000 USD EACH for 5000, modified cost basis +500 USD
            - id 1 is already closed, but now has 0 USD net gain
        - set id 0 to have 500 USD disallowed loss
            - id 0 is already closed, but now has 0 USD net gain
        - new id 5 has 1 ETH at 1000 USD each for 1000
            - close id 5 with 100 USD net gain
    Split id 4
        - set id 4 (1000 ADA) to 500 ADA at 1 USD EACH for 500, modified cost basis +50 USD
            - id 4 is already closed, but now has -50 USD net gain
        - set id 2 to have 50 USD disallowed loss
            - id 2 is already closed, but now has 0 USD net gain
        - new id 6 has 500 ADA at 1 USD each for 500
            - close id 6 with 0 USD net gain

    Cumulative gain: 0 + 0 + 0 - 100 - 50 + 100 + 0 = -50 USD

    """
    pool_reg = None
    for (
        order
    ) in simple_wash_orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(order, pools=pool_reg, strategy=OrderingStrategy.FIFO)
    pool_reg.sort(by="sale", ascending=True)  # most recent sales at the bottom
    print([pool for pool in pool_reg])

    assert (
        np.round(pool_reg[0].net_gain, decimals=2) == -500
    ), "First pool to be closed out has a net gain of -500.00"
    assert (
        np.round(pool_reg[1].net_gain, decimals=2) == 600.00
    ), "Second pool to be closed out has a net gain of 600.00"
    assert (
        np.round(pool_reg[2].net_gain, decimals=2) == -50.00
    ), "Third pool to be closed out has a net gain of -50.00"
    assert (
        np.round(pool_reg[3].net_gain, decimals=2) == -100.00
    ), "Fourth pool to be closed out has a net gain of -100.00"
    assert (
        np.round(pool_reg[4].net_gain, decimals=2) == 0.00
    ), "Fifth pool to be closed out has a net gain of 0.00"

    assert pool_reg.proceeds == 12750.0, "Net Proceeds before wash should be 12750 USD"
    assert (
        pool_reg.cost_basis == 12800.0
    ), "Net Cost Basis before wash should be 12800 USD"
    assert (
        pool_reg.disallowed_loss == 0.0
    ), "Net Disallowed Loss before wash should be 0 USD"
    assert pool_reg.net_gain == -50.0, "Total Net Gain before wash should be -50 USD"

    net_gain_before = pool_reg.net_gain

    # -----Executing Washes-----

    pool_reg = execute_washes(pool_reg=pool_reg)
    print([f"{i}->{pool.asset.ticker}" for i, pool in enumerate(pool_reg)])
    assert (
        np.round(pool_reg[0].net_gain, decimals=2) == 0.00
    ), "First pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[1].net_gain, decimals=2) == 0.00
    ), "Second pool to be closed out has a net gain of 0.00"

    print([pool for pool in pool_reg if pool.asset.ticker == "ETH"])
    print([pool for pool in pool_reg if pool.asset.ticker == "ADA"])

    assert (
        np.round(pool_reg[2].net_gain, decimals=2) == 0.00
    ), "Third pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[3].net_gain, decimals=2) == -100.00
    ), "Fourth pool to be closed out has a net gain of -100.00"
    assert (
        np.round(pool_reg[4].net_gain, decimals=2) == -50.00
    ), "Fifth pool to be closed out has a net gain of -50.00"
    assert (
        np.round(pool_reg[5].net_gain, decimals=2) == 100.00
    ), "Sixth pool to be closed out has a net gain of 100.00"
    assert (
        np.round(pool_reg[6].net_gain, decimals=2) == 0.00
    ), "Seventh pool to be closed out has a net gain of 0.00"

    assert pool_reg.proceeds == 12750.0, "Net Proceeds after wash should be 12750 USD"
    assert (
        pool_reg.cost_basis == 13350.0
    ), "Net Cost Basis after wash should be 13350 USD"
    assert (
        pool_reg.disallowed_loss == 550.0
    ), "Net Disallowed Loss after wash should be 550 USD"
    assert pool_reg.net_gain == -50.0, "Total Net Gain after wash should be -50 USD"

    net_gain_after = pool_reg.net_gain

    assert (
        net_gain_before == net_gain_after
    ), "Fully expended pools should have same net gain before and after wash sales are accounted for."
