from cointracker.objects.orderbook import Order, OrderBook
import pandas as pd


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
