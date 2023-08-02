import datetime
from dateutil import parser
from cointracker.pricing.getYahooPrice import getYahooPrice as gyp
from cointracker.pricing.getCoinGeckoPrice import getCoinGeckoPrice as gcgp

# maybe use relative imports instead?
# from .getYahooPrice import getYahooPrice as gyp
# from .getCoinGeckoPrice import getCoinGeckoPrice as gcgp


def getAssetPrice(asset, date):
    # change all dates into timezone-aware datetime objects to be able to compare
    # NOTE: As (regular) Coinbase doesn't provide accurate timestamps, we have to hope
    # that things work assuming it's 12AM

    # if type(date) != type(datetime.datetime.now()):
    if not isinstance(date, datetime.datetime):
        date = parser.parse(date)  # parse the date to datetime

    date = date.replace(tzinfo=datetime.timezone.utc)  # convert to non-naive UTC
    # print('converted date: ', date)

    # startdate = date - datetime.timedelta(days=1)

    price = 0

    if asset == "USD":
        price = 1
    else:
        try:
            price = gcgp(asset, date)
            # print('getCoinGecko price: ', price)
        except Exception:
            print("Could not get ", asset, "'s CoinGecko price...trying Yahoo")
            try:
                yahooPair = asset + "-USD"
                price = gyp(yahooPair, date, date)
                # print('getYahooPair price: ', price)
                price = price.loc[0, "Open"]
            except Exception:
                print("Cannot get ", asset, "'s price")

    if price == 0:
        print("0 priced Asset: ", asset)
    # print('price being returned: ', price)
    return price


if __name__ == "__main__":
    start_d = datetime.datetime(2019, 8, 7)
    amount = getAssetPrice("ADA", start_d)
    print(amount)
