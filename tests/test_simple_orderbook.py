from cointracker.objects.orderbook import Order, OrderBook
from cointracker.objects.enumerated_values import OrderingStrategy
from cointracker.process.execute import execute_order
import pandas as pd
import datetime


def test_simple_orderbook_creation(simple_orderbook) -> None:
    assert (
        type(simple_orderbook) == OrderBook
    ), f"OrderBook ({type(simple_orderbook)}) should be of type `OrderBook`"
    for order in simple_orderbook:
        assert (
            type(order) == Order
        ), f"Order ({type(order)}) in `OrderBook` should be of type `Order`"


def test_simple_orderbook_to_df_ascending(simple_orderbook) -> None:
    order_df = simple_orderbook.to_df(ascending=True)
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


def test_simple_orderbook_to_df_descending(simple_orderbook) -> None:
    order_df = simple_orderbook.to_df(ascending=False)
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


def test_simple_orderbook_execution_fifo(simple_orderbook) -> None:
    """This orderbook consists of 4 orders, 2 buys and 2 sells. The 2 sells close out all positions (sell all of the ETH bought).
    When executed in FIFO, the 2 sells split the 2 pools into 3 as the first sale for 6 ETH closes out the first pool and also a
    portion (1 ETH) from the second pool. The last sell then closes out the last remaining open pool with 4 ETH.

    BUY 5 ETH at 1000 USD each for 5000 USD (id 0)
    BUY 5 ETH at 1100 USD each for 5500 USD (id 1)
    SELL 6 ETH at 1000 USD each for 6000 USD
        - SELL 5 ETH at 1000 USD each for 5000 USD
            Close id 0 with $0 net gain
        - SELL 1 ETH at 1000 USD each for 1000 USD
            id 1 has 1 ETH at 1100 USD each for 1100 USD (id 1)
            Close id 1 with -100 USD net gain
            id 2 has 4 ETH at 1100 USD each for 4400 USD (id 2)
    SELL 4 ETH at 1200 USD each for 4800 USD
        Close id 2 with 400 USD net gain

    """
    pool_reg = None
    for (
        order
    ) in simple_orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(order, pools=pool_reg, strategy=OrderingStrategy.FIFO)
    pool_reg.sort(by="sale", ascending=True)  # most recent sales at the bottom
    print([pool for pool in pool_reg])

    PURCHASE_DATE_1 = datetime.datetime(2022, 1, 29, tzinfo=datetime.timezone.utc)
    PURCHASE_DATE_2 = datetime.datetime(2022, 1, 30, tzinfo=datetime.timezone.utc)
    PURCHASE_DATE_3 = datetime.datetime(2022, 1, 30, tzinfo=datetime.timezone.utc)
    SALE_DATE_1 = datetime.datetime(2022, 2, 8, tzinfo=datetime.timezone.utc)
    SALE_DATE_2 = datetime.datetime(2022, 2, 8, tzinfo=datetime.timezone.utc)
    SALE_DATE_3 = datetime.datetime(2022, 3, 1, tzinfo=datetime.timezone.utc)

    assert len(pool_reg.open_pools) == 0, "All pools in registry should be closed"
    assert pool_reg[0].amount == 5, "First pool to be closed out amount is 5"
    assert (
        pool_reg[0].purchase_date == PURCHASE_DATE_1
    ), f"First pool to be closed's purchase_date ({(pool_reg[0].purchase_date)}) is ({PURCHASE_DATE_1})"
    assert (
        pool_reg[0].purchase_cost_fiat == 5000
    ), "First pool to be closed cost 5000 USD"
    assert (
        pool_reg[0].sale_date == SALE_DATE_1
    ), f"First pool to be closed sale_date ({(pool_reg[0].sale_date)}) is ({SALE_DATE_1})"
    assert (
        pool_reg[0].sale_value_fiat == 5000
    ), "First pool to be closed sold for 5000 USD"

    assert pool_reg[1].amount == 1, "Second pool to be closed out amount is 5"
    assert (
        pool_reg[1].purchase_date == PURCHASE_DATE_2
    ), f"Second pool to be closed's purchase_date ({(pool_reg[1].purchase_date)}) is ({PURCHASE_DATE_2})"
    assert (
        pool_reg[1].purchase_cost_fiat == 1100
    ), "Second pool to be closed cost 1100 USD"
    assert (
        pool_reg[1].sale_date == SALE_DATE_2
    ), f"Second pool to be closed sale_date ({(pool_reg[1].sale_date)}) is ({SALE_DATE_2})"
    assert (
        pool_reg[1].sale_value_fiat == 1000
    ), "Second pool to be closed sold for 1000 USD"

    assert pool_reg[2].amount == 4, "Last pool to be closed out amount is 5"
    assert (
        pool_reg[2].purchase_date == PURCHASE_DATE_3
    ), f"Last pool to be closed purchase_date ({(pool_reg[2].purchase_date)}) is ({PURCHASE_DATE_3})"
    assert (
        pool_reg[2].purchase_cost_fiat == 4400
    ), "Last pool to be closed cost 4400 USD"
    assert (
        pool_reg[2].sale_date == SALE_DATE_3
    ), f"Last pool to be closed sale_date ({(pool_reg[2].sale_date)}) is ({SALE_DATE_3})"
    assert (
        pool_reg[2].sale_value_fiat == 4800
    ), "Last pool to be closed sold for 4800 USD"

    assert pool_reg.proceeds == 10800.0, "Net Proceeds should be 10800 USD"
    assert pool_reg.cost_basis == 10500.0, "Net Cost Basis should be 10500 USD"
    assert pool_reg.disallowed_loss == 0.0, "Net Disallowed Loss should be 0 USD"
    assert pool_reg.net_gain == 300.0, "Total Net Gain should be 300 USD"


def test_simple_orderbook_execution_lifo(simple_orderbook) -> None:
    """This orderbook consists of 4 orders, 2 buys and 2 sells. The 2 sells close out all positions (sell all of the ETH bought).
    When executed in LIFO, the 2 sells split the 2 pools into 3 as the first sale for 6 ETH closes out the second pool and also a
    portion (1 ETH) from the first pool. The last sell then closes out the last remaining open pool with 4 ETH.

    BUY 5 ETH at 1000 USD each for 5000 USD (id 3)
    BUY 5 ETH at 1100 USD each for 5500 USD (id 4)
    SELL 6 ETH at 1000 USD each for 6000 USD
        - SELL 5 ETH at 1000 USD each for 5000 USD
            Close id 4 with -$500 net gain
        - SELL 1 ETH at 1000 USD each for 1000 USD
            id 3 has 1 ETH at 1000 USD each for 1000 USD (id 3)
            Close id 3 with 0 USD net gain
            id 5 has 4 ETH at 1000 USD each for 4000 USD (id 5)
    SELL 4 ETH at 1200 USD each for 4800 USD
        Close id 5 with 800 USD net gain

    NOTE THAT ID 4 CLOSES BEFORE ID 3, though sorting still orders ID 3 first
    """
    pool_reg = None
    for (
        order
    ) in simple_orderbook:  # default orderbook is already sorted by ascending date
        pool_reg = execute_order(order, pools=pool_reg, strategy=OrderingStrategy.LIFO)

    pool_reg.sort(by="sale", ascending=True)  # most recent sales at the bottom
    print([pool for pool in pool_reg])

    PURCHASE_DATE_3 = datetime.datetime(2022, 1, 29, tzinfo=datetime.timezone.utc)
    PURCHASE_DATE_4 = datetime.datetime(2022, 1, 30, tzinfo=datetime.timezone.utc)
    PURCHASE_DATE_5 = datetime.datetime(2022, 1, 29, tzinfo=datetime.timezone.utc)
    SALE_DATE_3 = datetime.datetime(2022, 2, 8, tzinfo=datetime.timezone.utc)
    SALE_DATE_4 = datetime.datetime(2022, 2, 8, tzinfo=datetime.timezone.utc)
    SALE_DATE_5 = datetime.datetime(2022, 3, 1, tzinfo=datetime.timezone.utc)

    assert len(pool_reg.open_pools) == 0, "All pools in registry should be closed"
    assert pool_reg[1].amount == 5, "First pool to be closed out amount is 5"
    assert (
        pool_reg[1].purchase_date == PURCHASE_DATE_4
    ), f"First pool to be closed's purchase_date ({(pool_reg[1].purchase_date)}) is ({PURCHASE_DATE_4})"
    assert (
        pool_reg[1].purchase_cost_fiat == 5500
    ), "First pool to be closed cost 5500 USD"
    assert (
        pool_reg[1].sale_date == SALE_DATE_3
    ), f"First pool to be closed sale_date ({(pool_reg[1].sale_date)}) is ({SALE_DATE_4})"
    assert (
        pool_reg[1].sale_value_fiat == 5000
    ), "First pool to be closed sold for 5000 USD"

    assert pool_reg[0].amount == 1, "Second pool to be closed out amount is 5"
    assert (
        pool_reg[0].purchase_date == PURCHASE_DATE_3
    ), f"Second pool to be closed's purchase_date ({(pool_reg[0].purchase_date)}) is ({PURCHASE_DATE_3})"
    assert (
        pool_reg[0].purchase_cost_fiat == 1000
    ), "Second pool to be closed cost 1000 USD"
    assert (
        pool_reg[0].sale_date == SALE_DATE_3
    ), f"Second pool to be closed sale_date ({(pool_reg[0].sale_date)}) is ({SALE_DATE_3})"
    assert (
        pool_reg[0].sale_value_fiat == 1000
    ), "Second pool to be closed sold for 1000 USD"

    assert pool_reg[2].amount == 4, "Last pool to be closed out amount is 5"
    assert (
        pool_reg[2].purchase_date == PURCHASE_DATE_5
    ), f"Last pool to be closed purchase_date ({(pool_reg[2].purchase_date)}) is ({PURCHASE_DATE_5})"
    assert (
        pool_reg[2].purchase_cost_fiat == 4000
    ), "Last pool to be closed cost 4000 USD"
    assert (
        pool_reg[2].sale_date == SALE_DATE_5
    ), f"Last pool to be closed sale_date ({(pool_reg[2].sale_date)}) is ({SALE_DATE_5})"
    assert (
        pool_reg[2].sale_value_fiat == 4800
    ), "Last pool to be closed sold for 4800 USD"

    assert pool_reg.proceeds == 10800.0, "Net Proceeds should be 10800 USD"
    assert pool_reg.cost_basis == 10500.0, "Net Cost Basis should be 10500 USD"
    assert pool_reg.disallowed_loss == 0.0, "Net Disallowed Loss should be 0 USD"
    assert pool_reg.net_gain == 300.0, "Total Net Gain should be 300 USD"
