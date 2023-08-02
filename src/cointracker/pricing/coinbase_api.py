# %% https://algotrading101.com/learn/coinbase-pro-api-guide/
import cbpro  # requires Python < 3.10 for `requests` to work properly
import pandas as pd

c = cbpro.PublicClient()

data = pd.DataFrame(c.get_products())
data.tail().T

ticker = c.get_product_ticker(product_id="ADA-USD")
ticker
# %%
# You can also use the Coinbase Pro REST API endpoints to obtain data in the following way:
import requests

ticker = requests.get("https://api.pro.coinbase.com/products/ADA-USD/ticker").json()
ticker

# %%
historical = pd.DataFrame(
    c.get_product_historic_rates(
        product_id="ADA-USD",
        start="2022-04-06T18:06:44+00:00",
        end="2022-04-07T20:07:44+00:00",
        granularity=21600,
    )
)
historical.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
historical["Date"] = pd.to_datetime(historical["Date"], unit="s")
historical.set_index("Date", inplace=True)
historical.sort_values(by="Date", ascending=True, inplace=True)
historical
# %%
candle = requests.get(
    "https://api.pro.coinbase.com/products/BTC-USD/candles?start=2018-07-10T12:00:00&end=2018-07-15T12:00:00&granularity=3600"
).json()
candle
# %%
