from datetime import datetime, timedelta
import time, requests, pandas, lxml
from lxml import html


def getYahooPrice(symbol, start, end):
    start = format_date(start)
    end = format_date(end)

    sub = subdomain(symbol, start, end)
    # We do not need to include the filter argument because arguments with default values are optional.base_url = 'https://finance.yahoo.com'
    base_url = "https://finance.yahoo.com"
    url = base_url + sub
    header = header_function(sub)
    scraped = scrape_page(url, header)
    return scraped


def format_date(date_datetime):
    # Example
    # datetime_start = datetime.today() - timedelta(days=1000)
    # datetime_end = datetime.today() #Define end date as today's datestart = format_date(dt_start)
    # end = format_date(dt_end)
    date_timetuple = date_datetime.timetuple()
    date_mktime = time.mktime(date_timetuple)
    date_int = int(date_mktime)
    date_str = str(date_int)

    return date_str


def subdomain(symbol, start, end, filter="history"):
    subdoma = (
        "/quote/{0}/history?period1={1}&period2={2}&interval=1d&filter={3}&frequency=1d"
    )
    subdomain = subdoma.format(symbol, start, end, filter)
    return subdomain


def header_function(subdomain):
    hdrs = {
        "authority": "finance.yahoo.com",
        "method": "GET",
        "path": subdomain,  # path key assigned as subdomain
        "scheme": "https",
        "accept": "text/html",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "cookie": "Cookie:identifier",
        "dnt": "1",
        "pragma": "no-cache",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64)",
    }
    return hdrs


def scrape_page(url, header):
    page = requests.get(url, params=header)
    element_html = html.fromstring(page.content)
    table = element_html.xpath("//table")
    table_tree = lxml.etree.tostring(table[0], method="xml")
    panda = pandas.read_html(table_tree)
    # panda is a list of dataframes rather than the dataframe itself
    panda = panda[0]
    # Yahoo gives headers 'Date', 'Open', 'High', Low', 'Close*', 'Adj Close**', 'Volume'
    return panda


if __name__ == "__main__":
    enddate = datetime.today()
    startdate = enddate - timedelta(days=0)
    output = getYahooPrice("BTC-USD", startdate, enddate)
    print(output.loc[0, "Open"])
    print(output)
