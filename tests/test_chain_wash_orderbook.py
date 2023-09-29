from cointracker.objects.enumerated_values import OrderingStrategy
from cointracker.process.execute import execute_order, execute_washes
import numpy as np


def test_chain_wash_orderbook_execution(chain_wash_orderbook) -> None:
    """This orderbook consists of 6 orders, 3 buys and 3 sells.

    BUY 5 ETH at 1000 USD each for 5000 USD (id 0)
    SELL 5 ETH at 900 USD each for 4500 USD
        - close id 0 with -500 USD net gain

    BUY 5 ETH at 1000 USD each for 5000 USD (id 1)
    SELL 5 ETH at 1000 USD each for 5000 USD
        - close id 1 with 0 USD net gain

    BUY 5 ETH at 1000 USD each for 5000 USD (id 2)
    SELL 5 ETH at 1000 USD each for 5000 USD
        - close id 2 with 0 USD net gain

    Cumulative gain: -500 + 0 + 0 = -500 USD

    Wash Sales Are Computed
    - set id 0 to have 500 USD disallowed loss
        - id 0 is already closed, but now has 0 USD net gain
    - set id 1 to have modified cost basis +500 USD
        - id 1 is already closed, but now has -500 USD net gain
    - set id 1 to have 500 USD disallowed loss
        - id 1 is already closed, but now has 0 USD net gain
    - set id 2 to have modified cost basis +500 USD
        - id 2is already closed but now has a -500 USD net gain

    Cumulative gain: 0 + 0 - 500 = -500 USD

    """
    pool_reg = None
    for (
        order
    ) in chain_wash_orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(order, pools=pool_reg, strategy=OrderingStrategy.FIFO)
    pool_reg.sort(by="sale", ascending=True)  # most recent sales at the bottom
    print([pool for pool in pool_reg])

    assert (
        np.round(pool_reg[0].net_gain, decimals=2) == -500
    ), "First pool to be closed out has a net gain of -500.00"
    assert (
        np.round(pool_reg[1].net_gain, decimals=2) == 0.00
    ), "Second pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[2].net_gain, decimals=2) == 0.00
    ), "Third pool to be closed out has a net gain of 0.00"

    assert pool_reg.proceeds == 14500.0, "Net Proceeds before wash should be 14500 USD"
    assert (
        pool_reg.cost_basis == 15000.0
    ), "Net Cost Basis before wash should be 15000 USD"
    assert (
        pool_reg.disallowed_loss == 0.0
    ), "Net Disallowed Loss before wash should be 0 USD"
    assert pool_reg.net_gain == -500.0, "Total Net Gain before wash should be -50 USD"

    net_gain_before = pool_reg.net_gain

    # -----Executing Washes-----
    pool_reg = execute_washes(pool_reg=pool_reg)
    print([pool for pool in pool_reg])

    assert (
        np.round(pool_reg[0].net_gain, decimals=2) == 0.00
    ), "First pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[1].net_gain, decimals=2) == 0.00
    ), "Second pool to be closed out has a net gain of 0.00"
    assert (
        np.round(pool_reg[2].net_gain, decimals=2) == -500.00
    ), "Third pool to be closed out has a net gain of -500.00"

    assert pool_reg.proceeds == 14500.0, "Net Proceeds after wash should be 14500 USD"
    assert (
        pool_reg.cost_basis == 16000.0
    ), "Net Cost Basis after wash should be 15000 USD"
    assert (
        pool_reg.disallowed_loss == 1000.0
    ), "Net Disallowed Loss after wash should be 0 USD"
    assert pool_reg.net_gain == -500.0, "Total Net Gain after wash should be -50 USD"

    net_gain_after = pool_reg.net_gain

    assert (
        net_gain_before == net_gain_after
    ), "Fully expended pools should have same net gain before and after wash sales are accounted for."
