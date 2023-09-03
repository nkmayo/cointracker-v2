# %%
import datetime

from cointracker.objects.asset import import_registry
from cointracker.util.parsing import (
    orderbook_from_df,
    parse_orderbook,
)
from cointracker.process.execute import execute_orderbook
from cointracker.settings.config import cfg
from cointracker.util.file_io import (
    export_pool_reg,
    load_excel_orderbook,
    load_excel_pool_registry,
)


# %%
def run():
    # fromExcel = True
    # fromExisingPools = False
    # root = tk.Tk()
    # root.withdraw()

    # # outputPath = cfg.paths.data
    # # if fromExcel:
    # #     filename = filedialog.askopenfilename(
    # #         title="Select current year's order book",
    # #         filetypes=(("Excel files", "*.xlsx"), ("all files", "*.*")),
    # #     )
    # #     sheetname = "Combined"

    # #     oBook = ob.parse_orderbook(filename, sheetname)
    # #     outputFilename = outputPath + "OrderBookRefined.csv"
    # #     oBook.to_csv(outputFilename, index=False, encoding="utf-8")
    # # else:
    # #     filename = filedialog.askopenfilename(
    # #         title="Select current year's order book",
    # #         filetypes=(("CSV files", "*.csv"), ("all files", "*.*")),
    # #     )
    # #     oBook = pd.read_csv(filename, parse_dates=["Date(UTC)"])

    # # %% Loading From File
    # pool_reg = load_excel_pool_registry(sheetname="All Pools")
    # print(f"Pools:\n{[pool for pool in pool_reg]}")

    # %%
    ob = load_excel_orderbook(None, "Combined")
    pool_reg = execute_orderbook(orderbook=ob, pool_reg=None)

    print(f"Pools:\n{[pool for pool in pool_reg]}")
    print(f"Wash Pools:\n{[pool for pool in pool_reg if pool.is_wash]}")

    startDate = cfg.processing.start_date
    endDate = cfg.processing.end_date
    filingYear = (
        cfg.processing.filing_years
    )  # list of years to include in short/long/etc pools reports
    print(f"IRS summary:\n{pool_reg.to_df(ascending=True, kind='irs')}")
    print(f"Export:\n{pool_reg.to_df(ascending=True, kind='default')}")

    export_pool_reg(pool_reg=pool_reg, filename="test")
    print("Finished")

    # ----------------------PRINT OUTPUT TO FILES----------------------#

    # go back through and set dates to simple MM/DD/YY (as is wanted on taxes)
    # NOTE: #x is MM/DD/YY in local time
    # NOTE: organize by date first, otherwise it will sort by month not actual date

    # salePools = purchasePools[(purchasePools['Purchase Date']>cutoffDate)
    # & (purchasePools['Asset']==asset)]
    # assetPools = potentialPools.sort_values(by=['Purchase Date'], ascending = True)

    # yearSalePools = salePools[
    #     pd.DatetimeIndex(salePools["Sale Date"]).year.isin(filingYear)
    # ]
    # shortPools = yearSalePools[yearSalePools["Long"] == False]
    # longPools = yearSalePools[yearSalePools["Long"] == True]
    # assetPools = purchasePools[purchasePools["Active"] == True]

    # # output to files
    # outputFilename = outputPath + "Puchase Pools.csv"

    # purchasePools.to_csv(outputFilename, index=False, encoding="utf-8")

    # outputFilename = outputPath + "Sale Pools.csv"
    # salePools.to_csv(outputFilename, index=False, encoding="utf-8")

    # outputFilename = outputPath + "Asset Pools.csv"
    # assetPools.to_csv(outputFilename, index=False, encoding="utf-8")

    # outputFilename = outputPath + "Short Pools.csv"
    # prettyPrintPools(shortPools, outputFilename)

    # outputFilename = outputPath + "Long Pools.csv"
    # prettyPrintPools(longPools, outputFilename)


# %%
