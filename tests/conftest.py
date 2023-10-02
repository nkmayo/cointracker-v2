import pytest
from cointracker.util.file_io import load_excel_orderbook
from cointracker.process.transact import split_order


@pytest.fixture(scope="session")
def simple_orderbook():
    return load_excel_orderbook(file="simple_orders.xlsx", sheetname="Sheet1")


@pytest.fixture(scope="session")
def mixed_orderbook():
    return load_excel_orderbook(file="mixed_orders.xlsx", sheetname="Sheet1")


@pytest.fixture(scope="session")
def simple_wash_orderbook():
    return load_excel_orderbook(file="simple_wash.xlsx", sheetname="Sheet1")


@pytest.fixture(scope="session")
def chain_wash_orderbook():
    return load_excel_orderbook(file="chain_wash.xlsx", sheetname="Sheet1")


@pytest.fixture(scope="session")
def same_day_wash_orderbook():
    return load_excel_orderbook(file="same_day_wash.xlsx", sheetname="Sheet1")


if __name__ == "__main__":
    ob = load_excel_orderbook(file="simple_orders.xlsx", sheetname="Sheet1")
    for order in ob:
        buy_pool, sell_txn = split_order(order)
        print(f"buy_pool: {buy_pool}\nsell_txn: {sell_txn}")

# Create Balance Object?
