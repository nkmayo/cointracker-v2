import pytest
from cointracker.objects.asset import Asset, AssetRegistry, import_registry
from cointracker.objects.orderbook import Order, OrderBook
from cointracker.util.parsing import orderbook_from_df, parse_orderbook
from cointracker.process.transact import split_order

# from cointracker.objects.pool import Sale, Pool
from cointracker.settings.config import read_config

sheet = "Sheet1"
cfg = read_config()
registry_file = cfg.paths.data / "token_registry.yaml"
token_registry = import_registry(filename=registry_file)
registry_file = cfg.paths.data / "fiat_registry.yaml"
fiat_registry = import_registry(filename=registry_file)
registry = token_registry + fiat_registry


def load_excel_orderbook(file: str, sheetname: str = "Sheet1"):
    filename = cfg.paths.tests / file
    order_df = parse_orderbook(filename, sheetname)
    orderbook = orderbook_from_df(order_df, registry=registry)

    return orderbook


@pytest.fixture(scope="session")
def simple_orderbook():
    return load_excel_orderbook(file="simple_orders.xlsx", sheetname="Sheet1")


@pytest.fixture(scope="session")
def mixed_orderbook():
    return load_excel_orderbook(file="mixed_orders.xlsx", sheetname="Sheet1")


if __name__ == "__main__":
    ob = load_excel_orderbook(file="simple_orders.xlsx", sheetname="Sheet1")
    for order in ob:
        buy_pool, sell_txn = split_order(order)
        print(f"buy_pool: {buy_pool}\nsell_txn: {sell_txn}")

# Create Balance Object?
