import pytest
from cointracker.objects.asset import Asset, AssetRegistry, import_registry
from cointracker.objects.orderbook import Order, OrderBook
from cointracker.util.parsing import orderbook_from_df, parse_orderbook
from cointracker.process.transact import split_order

# from cointracker.objects.pool import Sale, Pool
from cointracker.settings.config import read_config

sheet = "Sheet1"
cfg = read_config()


def load_simple_order():
    filename = cfg.paths.tests / "simple_orders.xlsx"
    sheetname = "Sheet1"
    # order_df = pd.read_csv(filename, parse_dates=["Date(UTC)"])
    # print(f"{order_df}\n{order_df.dtypes}")
    registry_file = cfg.paths.data / "token_registry.yaml"
    token_registry = import_registry(filename=registry_file)
    registry_file = cfg.paths.data / "fiat_registry.yaml"
    fiat_registry = import_registry(filename=registry_file)
    registry = token_registry + fiat_registry
    order_df = parse_orderbook(filename, sheetname)
    orderbook = orderbook_from_df(order_df, registry=registry)

    return orderbook


@pytest.fixture(scope="session")
def simple_orderbook():
    return load_simple_order()


if __name__ == "__main__":
    ob = load_simple_order()
    for order in ob:
        buy_pool, sell_txn = split_order(order)
        print(f"buy_pool: {buy_pool}\nsell_txn: {sell_txn}")

# Create Balance Object?
