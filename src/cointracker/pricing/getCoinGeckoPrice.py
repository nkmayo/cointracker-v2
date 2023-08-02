# %%
import requests
import json
import os
import time
from pathlib import Path

WAITSHORT = 2  # free api is limited to 10-30 calls per minute or one every 2-6 seconds.
WAITLONG = 6.01
TIMEOUT = 91
ID_PATH = Path(__file__).resolve().parent / "data/CoinGeckoIDs.json"


def getCoinGeckoPrice(asset, date):
    # takes the asset ticker (ex:BTC) and date (datetime) and returns the open price
    """
    filepath = 'unknown'
    rootDir = '.'
    for dirName, subdirList, fileList in os.walk(rootDir, topdown=False):
        # print('Found directory: %s' % dirName)
        for fname in fileList:
            # print('\t%s' % fname)
            if fname == 'CoinGeckoIDs.json':
                filepath = dirName + '\\' + fname
    """
    date_string = date.strftime("%d-%m-%Y")  # format date

    try:
        # with open(filepath, 'r') as fr:  # import saved ID dictionary
        with open(ID_PATH, "r") as fr:  # import saved ID dictionary
            idDict = json.load(fr)

        ID = idDict[asset.lower()]
    except Exception:
        print("Error, couldn't find CoinGeckoIDs.json in")
        SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))
        print(SCRIPTDIR, "\\data")
        price = 0

    url = (
        "https://api.coingecko.com/api/v3/coins/" + ID + "/history?date=" + date_string
    )
    try:
        gecko = requests.get(url)

        if gecko.status_code == 429:  # if too many requests error sent
            print(f"Too many CoinGecko requests...waiting {TIMEOUT}s for timeout")
            time.sleep(TIMEOUT)
            gecko = requests.get(url)
        time.sleep(WAITLONG)
        price = gecko.json()["market_data"]["current_price"]["usd"]
        print(f"Received price data for {asset} on {date}: {price} USD")
    except Exception:
        print("Bad CoinGecko request URL")
        print(url)
        print(gecko.status_code)
        price = 0

    return price


def updateCoinGeckoIDs():
    # query's the CoinGecko API to generate a ticker:ID dictionary
    coinList = requests.get("https://api.coingecko.com/api/v3/coins/list").json()
    """
    filepath = 'unknown'
    rootDir = '.'
    for dirName, subdirList, fileList in os.walk(rootDir, topdown=False):
        # print('Found directory: %s' % dirName)
        for fname in fileList:
            # print('\t%s' % fname)
            if fname == 'CoinGeckoIDs.json':
                filepath = dirName + '\\' + fname
    """
    idDict = {}
    for coin in coinList:
        idDict[coin["symbol"].lower()] = coin["id"]

    # save dictionary locally
    # with open(filepath, 'w+') as fw:
    print(f"ID_PATH: {ID_PATH}")
    with open(ID_PATH, "w+") as fw:
        json.dump(idDict, fw, indent=4)
    return


if __name__ == "__main__":
    updateCoinGeckoIDs()

"""
from datetime import datetime
start_d = datetime(2019, 8, 7)
amount = getCoinGeckoPrice('ADA', start_d)
print(amount)
"""

# %%
