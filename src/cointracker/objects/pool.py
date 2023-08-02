# %%
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from cointracker.objects.asset import Asset
from itertools import count


@dataclass
class Sale:
    poolID: int = field(init=False, default_factory=count().__next__)
    asset_sold: Asset
    asset_received: Asset
    purchase_date: datetime
    sale_date: datetime
    amount: float  # convert to int with market1 units
    sale_price: float
    asset_sold_spot: float
    asset_recieved_spot: float
    fee: float
    fee_coin: Asset
    fee_spot: float
    fee_usd: float
    purchase_pool_id: int
    holding_period: timedelta
    long: bool
    proceeds: float
    cost_basis: float
    wash_pool_id: int
    disallowed_loss: float
    net_gain: float

    @property
    def amount_base_units(self):
        return int(self.amount / self.market1.smallest_unit)

    @property
    def rounded_amount(self):
        return self.amount_base_units * self.market1.smallest_unit

    @property
    def total(self):
        total = self.rounded_amount * self.price
        # convert the total to the market2 units
        total = int(total / self.market2.smallest_unit) * self.market2.smallest_unit


@dataclass
class Pool:
    poolID: int = field(init=False, default_factory=count().__next__)
    asset_sold: Asset
    asset_received: Asset
    purchase_date: datetime
    sale_date: datetime
    amount: float  # convert to int with market1 units
    sale_price: float
    asset_sold_spot: float
    asset_recieved_spot: float
    fee: float
    fee_coin: Asset
    fee_spot: float
    fee_usd: float
    purchase_pool_id: int
    holding_period: timedelta
    long: bool
    proceeds: float
    cost_basis: float
    wash_pool_id: int
    disallowed_loss: float
    net_gain: float


# %%
def getEmptySalePool():
    sCols = [
        "Pool ID",
        "Asset Sold",
        "Asset Received",
        "Purchase Date",
        "Sale Date",
        "Amount",
        "Sale Price",
        "Asset Sold Spot Price",
        "Asset Received Spot Price",
        "Fee",
        "Fee Coin",
        "Fee Coin Spot Price",
        "Fee USD",
        "Purchase Pool ID",
        "Holding Period",
        "Long",
        "Proceeds",
        "Cost Basis",
        "Wash Pool ID",
        "Disallowed Loss",
        "Net Gain",
    ]
    typeDict = {
        "Pool ID": "int64",
        "Asset Sold": "object",
        "Asset Received": "object",
        "Purchase Date": "datetime64[ns, UTC]",
        "Sale Date": "datetime64[ns, UTC]",
        "Amount": "float64",
        "Sale Price": "float64",
        "Asset Sold Spot Price": "float64",
        "Asset Received Spot Price": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Fee Coin Spot Price": "float64",
        "Fee USD": "float64",
        "Purchase Pool ID": "int64",
        "Holding Period": "timedelta64[ns]",
        "Long": "bool",
        "Proceeds": "float64",
        "Cost Basis": "float64",
        "Wash Pool ID": "int64",
        "Disallowed Loss": "float64",
        "Net Gain": "float64",
    }

    salePool = pd.DataFrame(columns=sCols)
    salePool = salePool.astype(typeDict)

    return salePool


def getEmptyPurchasePool():
    pCols = [
        "Pool ID",
        "Active",
        "Purchase Date",
        "Asset",
        "Asset Spot Price",
        "Amount",
        "Fee",
        "Fee Coin",
        "Fee Coin Spot Price",
        "Fee USD",
        "Initiates Wash",
        "Holding Period Modifier",
        "Cost Basis",
        "Modified Cost Basis",
    ]
    typeDict = {
        "Pool ID": "int64",
        "Active": "bool",
        "Purchase Date": "datetime64[ns, UTC]",
        "Asset": "object",
        "Asset Spot Price": "float64",
        "Amount": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Fee Coin Spot Price": "float64",
        "Fee USD": "float64",
        "Initiates Wash": "bool",
        "Holding Period Modifier": "timedelta64[ns]",
        "Cost Basis": "float64",
        "Modified Cost Basis": "float64",
    }
    purchasePool = pd.DataFrame(columns=pCols)
    purchasePool = purchasePool.astype(typeDict)

    return purchasePool


def getEmptyOrder():
    pCols = [
        "Date(UTC)",
        "Market",
        "Type",
        "Price",
        "Amount",
        "Total",
        "Fee",
        "Fee Coin",
        "Market 1 USD Spot Price",
        "Market 2 USD Spot Price",
        "Fee Coin USD Spot Price",
    ]
    typeDict = {
        "Date(UTC)": "datetime64[ns, UTC]",
        "Market": "object",
        "Type": "object",
        "Price": "float64",
        "Amount": "float64",
        "Total": "float64",
        "Fee": "float64",
        "Fee Coin": "object",
        "Market 1 USD Spot Price": "float64",
        "Market 2 USD Spot Price": "float64",
        "Fee Coin USD Spot Price": "float64",
    }
    purchasePool = pd.DataFrame(columns=pCols)
    purchasePool = purchasePool.astype(typeDict)

    return purchasePool
