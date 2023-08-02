import pandas as pd
import datetime
from dateutil import parser
import ctypes  # For popup windows


def findSaleMatch(order, poolList, invMethod):
    # findSaleMatch identifies an open purchase pool with the correct asset
    # it returns the index and poolID (as the index may change with subsequent calls)
    # along with a numerical value 'greaterLessEqual' which is 0 if the balance in the matched pool
    # is equal to that in the sale, 1 if the matched pool has a greater balance, and -1 if
    # the matched pool has a lower balance than the sale amount calls for

    temp = order.loc[0, "Market"]
    try:
        asset1, asset2 = temp.split("-")
    except:
        asset1 = temp
        asset2 = "USD"

    orderType = order.loc[0, "Type"]
    orderType = orderType.upper()

    # if the order is 'BUY' asset1 is assetReceived and asset 2 is sellAsset
    if orderType == "BUY":
        sellAsset = asset2
        sellAmount = order.loc[0, "Total"]
        sellUSDprice = order.loc[0, "Market 2 USD Spot Price"]
    # if the order is 'Sell' asset 2 is assetReceived and asset 1 is sellAsset
    elif orderType == "SELL":
        sellAsset = asset1
        sellAmount = order.loc[0, "Amount"]
        sellUSDprice = order.loc[0, "Market 1 USD Spot Price"]

    if invMethod == "LIFO":
        poolList = poolList.sort_values(by=["Purchase Date"], ascending=False)
        # no need to reset index because we will reference it later
        # poolList = poolList.reset_index(drop=True)
    elif invMethod == "FIFO":
        poolList = poolList.sort_values(by=["Purchase Date"], ascending=True)
    else:
        print("Error: unidentifiable investment method (FIFO,LIFO,etc).")

    purchasePoolIndex = []

    if sellAsset != "USD":
        # this runs through the poolList AS IT HAS BEEN SORTED
        # which may NOT be index=(0,1,2,3...)
        for index, _ in poolList.iterrows():
            # look for the last pool which has asset
            if poolList.loc[index, "Asset"] == sellAsset:
                # if the pool is not already closed, it will be the sale pool
                if poolList.loc[index, "Active"]:
                    purchasePoolIndex = index
                    pID = poolList.loc[index, "Pool ID"]

                    # does the matched purchase pool have an amount greater than, less than,
                    # or equal to the amount being sold?
                    # NOTE: If we want to be certain that the amount in the pool is greater,
                    # take away the Abs()
                    perc = abs(
                        (sellAmount - poolList.loc[index, "Amount"])
                        / poolList.loc[index, "Amount"]
                    )
                    # if selling > 99% and the percent remaining is less than $1
                    if (perc < 0.01) & (sellAmount * perc * sellUSDprice < 1):
                        greaterLessEqual = 0
                    elif sellAmount > poolList.loc[index, "Amount"]:
                        greaterLessEqual = -1
                    else:  # poolList.loc[index,'Amount'] > sellAmount
                        greaterLessEqual = 1
                    return purchasePoolIndex, pID, greaterLessEqual
                    break

    # def need to return some value. Check if it has found a pool
    try:
        if isinstance(purchasePoolIndex, int):
            print("Error: Not sure how you got here")
        else:
            errorString = (
                "Error: No valid purchase pool match for " + sellAsset + " found"
            )
            raise ValueError(errorString)
            ctypes.windll.user32.MessageBoxW(0, errorString, "Error", 0)
            print("purchasePoolIndex: ", purchasePoolIndex)
            return 0, 0, 0
    except Exception:
        errorString = "Error: No valid purchase pool match for " + sellAsset + " found"
        # raise ValueError(errorString)
        # ctypes.windll.user32.MessageBoxW(0, errorString, "Error", 0)
        print(
            "----------Error: No valid purchase pool match for",
            sellAsset,
            "found ----------",
        )
        print("Attempted Sell Amount: ", sellAmount)
        print(
            "Available ",
            sellAsset,
            " Supply: ",
            poolList[(poolList["Asset"] == sellAsset) & poolList["Active"]][
                "Amount"
            ].sum(),
        )
        print("----------------------------------------------------------------")
        return 0, 0, 0


def getIDIndex(pools, ID):
    poolSet = pools[(pools["Pool ID"] == ID)]

    if len(poolSet) == 0:
        print("Error: Cannot find ID index for ID ", ID)
        return 0
    elif len(poolSet) > 1:
        print(
            "Error: ",
            len(poolSet),
            " instances of ID found. Returning the first index found",
        )

    idIndex = poolSet.iloc[0].name

    return idIndex


def getIDIndexOld(pools, ID):
    idIndex = -1
    iterations = 0
    for index, _ in pools:  # needs pools.iterrows()?
        if pools.loc[index, "Pool ID"] == ID:
            idIndex = index
            iterations = iterations + 1
    if idIndex == -1:
        print("Error: Cannot find ID index for ID ", ID)
    if iterations > 1:
        print(
            "Error: ",
            iterations,
            " instances of ID found. Returning only the last index found",
        )

    return idIndex


def makeID(pools):
    if len(pools) == 0:
        newID = 1
    else:
        newID = pools["Pool ID"].max()
        newID += 1
        """
        try:
            temp = pools.sort_values(by=['Pool ID'], ascending=False)
            # temp = temp.iloc[0,'Pool ID'] doesn't work as iloc cannot reference 'Pool ID'
            # and loc references the index, not the sorted order
            temp = temp.iloc[0, 0]
            newID = temp+1
        except:
            print('Error: Cannot make new Pool ID. Existing Pool IDs not found.')
        """

    return int(newID)


def buyAsset(order, purchasePools, salePools, invMethod):
    poolMinUSD = 0.25  # minimum purchase value

    temp = order.loc[0, "Market"]
    try:
        asset1, asset2 = temp.split("-")
    except:
        asset1 = temp
        asset2 = "USD"

    orderType = order.loc[0, "Type"]
    orderType = orderType.upper()
    orderDate = order.loc[0, "Date(UTC)"]

    # if the order is 'BUY' asset1 is assetReceived and asset 2 is assetSold
    if orderType == "BUY":
        assetSold = asset2
        assetSoldSpot = order.loc[0, "Market 2 USD Spot Price"]
        assetReceived = asset1
        assetReceivedSpot = order.loc[0, "Market 1 USD Spot Price"]
        # a 'BUY' of asset 1 is a 'SELL' of asset 2
        buyAmount = order.loc[0, "Amount"]
        sellAmount = order.loc[0, "Total"]
        purchaseFee = order.loc[0, "Fee"]
        purchaseFeeCoin = order.loc[0, "Fee Coin"]
        purchaseFeeCoinSpot = order.loc[0, "Fee Coin USD Spot Price"]
        purchaseFeeUSD = purchaseFee * purchaseFeeCoinSpot

    # if the order is 'Sell' asset 2 is assetReceived and asset 1 is assetSold
    elif orderType == "SELL":
        saleDate = orderDate
        assetSold = asset1
        assetSoldSpot = order.loc[0, "Market 1 USD Spot Price"]
        assetReceived = asset2
        assetReceivedSpot = order.loc[0, "Market 2 USD Spot Price"]
        buyAmount = order.loc[0, "Total"]
        sellAmount = order.loc[0, "Amount"]
        salePrice = order.loc[0, "Price"]

        # can't double count the fee for both the sell and the new buy for 'virtual' sales
        purchaseFee = 0
        purchaseFeeCoin = "USD"
        purchaseFeeCoinSpot = 1
        purchaseFeeUSD = 0

    if order.loc[0, "Price"] == 0:
        purchaseCostBasis = 0
    else:
        purchaseCostBasis = (
            sellAmount * assetSoldSpot + purchaseFeeUSD
        )  # doesn't work for free items with cost=0

    purchaseModifiedCostBasis = purchaseCostBasis

    # check for Wash sales
    washPair = 0
    holdingPerMod = datetime.timedelta(days=0)

    # check for empty orders (orders costing less poolMinUSD and worth less than poolMinUSD)
    emptyOrder = False
    if (purchaseCostBasis < poolMinUSD) & (assetReceivedSpot * buyAmount < poolMinUSD):
        emptyOrder = True
        print("-------------------EMPTY ORDER -------------------")
        print("Order Market: ", order.loc[0, "Market"])
        print("Order Amount: ", order.loc[0, "Amount"])

    # ----------------assetReceived ADDRESSED HERE---------------------
    # ----------------PURCHASE POOLS EXECUTED HERE---------------------
    # pools are not created for 'USD', this eliminates the SELL asset for USD case.
    if (assetReceived != "USD") & (emptyOrder == False):
        # create purchase pool
        pPool = getEmptyPurchasePool()
        pID = makeID(purchasePools)
        # populate purchaseOrder items

        pPool_dict = {
            "Pool ID": pID,
            "Active": True,
            "Purchase Date": orderDate,
            "Asset": assetReceived,
            "Asset Spot Price": assetReceivedSpot,
            "Amount": buyAmount,
            "Fee": purchaseFee,
            "Fee Coin": purchaseFeeCoin,
            "Fee Coin Spot Price": purchaseFeeCoinSpot,
            "Fee USD": purchaseFeeUSD,
            "Initiates Wash": washPair,
            "Holding Period Modifier": holdingPerMod,
            "Cost Basis": purchaseCostBasis,
            "Modified Cost Basis": purchaseModifiedCostBasis,
        }
        pPool.loc[0, :] = pPool_dict

        """
        pPool.loc[0, 'Pool ID'] = pID
        pPool.loc[0, 'Active'] = True
        pPool.loc[0, 'Purchase Date'] = orderDate
        pPool.loc[0, 'Asset'] = assetReceived
        pPool.loc[0, 'Asset Spot Price'] = assetReceivedSpot
        pPool.loc[0, 'Amount'] = buyAmount
        pPool.loc[0, 'Fee'] = purchaseFee
        pPool.loc[0, 'Fee Coin'] = purchaseFeeCoin
        pPool.loc[0, 'Fee Coin Spot Price'] = purchaseFeeCoinSpot
        pPool.loc[0, 'Fee USD'] = purchaseFeeUSD
        pPool.loc[0, 'Initiates Wash'] = washPair  # check for this!!!
        pPool.loc[0, 'Holding Period Modifier'] = holdingPerMod
        pPool.loc[0, 'Cost Basis'] = purchaseCostBasis
        pPool.loc[0, 'Modified Cost Basis'] = purchaseModifiedCostBasis
        """
        # add the new purchase pool to the purchase pools list

        purchasePools = pd.concat([purchasePools, pPool], ignore_index=True)
        purchasePools2 = purchasePools.sort_values("Purchase Date")

        # check for wash sales
        # this could be done outside of buyAsset as it is not called recursively and would
        # elminate the need to take in and return salePools
        print(
            "orderType should be BUY: ", orderType
        )  # NOTE: is this necessarily true? appears not if the second asset in a SELL is crypto too

        purchasePools, salePools = washPoolMatches(
            pID, "BUY", invMethod, purchasePools, salePools
        )

    return purchasePools, salePools


def sellAsset(order, purchasePools, salePools, invMethod):
    # as sellAsset is called recursively, it needs to check for wash sales within itself
    USDdecimals = 3  # number of decimal places all USD values are rounded to
    poolLimitUSD = 1  # if a split would leave a pool with less than this value in USD, the split does not occur

    temp = order.loc[0, "Market"]
    try:
        asset1, asset2 = temp.split("-")
    except:
        asset1 = temp
        asset2 = "USD"

    orderType = order.loc[0, "Type"]
    orderType = orderType.upper()
    orderDate = order.loc[0, "Date(UTC)"]
    saleDate = orderDate

    # if the order is 'BUY' asset1 is assetReceived and asset 2 is assetSold
    if orderType == "BUY":
        assetSold = asset2
        assetSoldSpot = order.loc[0, "Market 2 USD Spot Price"]
        assetReceived = asset1
        assetReceivedSpot = order.loc[0, "Market 1 USD Spot Price"]
        # a 'BUY' of asset 1 is a 'SELL' of asset 2
        buyAmount = order.loc[0, "Amount"]
        sellAmount = order.loc[0, "Total"]
        if order.loc[0, "Price"] == 0:  # if it was free
            salePrice = 0  # this sale price shouldn't be used as it's a USD buy
        else:
            salePrice = 1 / order.loc[0, "Price"]  # sale price is inverse of buy price
        purchaseFee = order.loc[0, "Fee"]
        purchaseFeeCoin = order.loc[0, "Fee Coin"]
        purchaseFeeCoinSpot = order.loc[0, "Fee Coin USD Spot Price"]
        purchaseFeeUSD = purchaseFee * purchaseFeeCoinSpot

        # can't double count the fee for both the sell and the new buy for 'virtual' sales
        saleFee = 0
        saleFeeCoin = "USD"
        saleFeeCoinSpot = 1
        saleFeeUSD = 0

    # if the order is 'Sell' asset 2 is assetReceived and asset 1 is assetSold
    elif orderType == "SELL":
        assetSold = asset1
        assetSoldSpot = order.loc[0, "Market 1 USD Spot Price"]
        assetReceived = asset2
        assetReceivedSpot = order.loc[0, "Market 2 USD Spot Price"]
        buyAmount = order.loc[0, "Total"]
        sellAmount = order.loc[0, "Amount"]
        salePrice = order.loc[0, "Price"]
        saleFee = order.loc[0, "Fee"]
        saleFeeCoin = order.loc[0, "Fee Coin"]
        saleFeeCoinSpot = order.loc[0, "Fee Coin USD Spot Price"]
        saleFeeUSD = saleFee * saleFeeCoinSpot

        # can't double count the fee for both the sell and the new buy for 'virtual' sales
        purchaseFee = 0
        purchaseFeeCoin = "USD"
        purchaseFeeCoinSpot = 1
        purchaseFeeUSD = 0

    # ----------------assetSold ADDRESSED HERE---------------------
    # ----------------SALE POOLS EXECUTED HERE---------------------
    # no 'USD' purchase pools exist to be matched with a sale pool
    if assetSold != "USD":
        # findSaleMatch already takes into consideration if the order is 'BUY' or 'SELL'
        # print('order type: ', order)
        pIndex, pID, greaterLessEqual = findSaleMatch(order, purchasePools, invMethod)
        # print('identified purchase pool:', purchasePools.loc[pIndex])

        purchaseDate = purchasePools.loc[pIndex, "Purchase Date"]
        pPoolAmount = purchasePools.loc[pIndex, "Amount"]
        # costBasis = purchasePools.loc[pIndex,'Cost Basis']
        costBasis = purchasePools.loc[
            pIndex, "Modified Cost Basis"
        ]  # needs to used the modified cost basis

        remainingSellAmount = 0

        # if the sale amount exactly matches that in the purchase pool, close the purchase pool
        # and generate the sale pool
        if greaterLessEqual == 0:
            purchasePools.loc[pIndex, "Active"] = False

        # else if the purchase pool has more money than the sale amount, update the purchase pool
        # and generate the sale pool
        elif greaterLessEqual == 1:
            # In lieu of simply updating the old purchase pool,
            # I am splitting the purchase pool and updating both
            purchasePools.loc[pIndex, "Active"] = True  # the old pool stays active

            # do the calculations necessary
            remainingPoolAmount = (
                pPoolAmount - sellAmount
            )  # purchasePool amount - salePool amount
            percentUsed = (
                sellAmount / pPoolAmount
            )  # calculate before updating the original purchasePool

            # create new pool copying the existing purchase pool
            newPurchasePool = purchasePools.loc[pIndex:pIndex].copy()
            pID = makeID(
                purchasePools
            )  # update pID, which is used later for the pool that is being closed
            newPurchasePool.loc[
                pIndex, "Pool ID"
            ] = pID  # NOTE: pIndex has not changed yet

            # update the new pool
            newPurchasePool.loc[
                pIndex, "Amount"
            ] = sellAmount  # should equal newPurchasePool.loc[pIndex,'Amount']*percentUsed
            newPurchasePool.loc[pIndex, "Fee"] = (
                newPurchasePool.loc[pIndex, "Fee"] * percentUsed
            )
            newPurchasePool.loc[pIndex, "Fee USD"] = round(
                newPurchasePool.loc[pIndex, "Fee USD"] * percentUsed, USDdecimals
            )
            newPurchasePool.loc[pIndex, "Cost Basis"] = round(
                costBasis * percentUsed, USDdecimals
            )
            # modified cost basis too?
            newPurchasePool.loc[pIndex, "Modified Cost Basis"] = round(
                newPurchasePool.loc[pIndex, "Modified Cost Basis"] * percentUsed,
                USDdecimals,
            )
            newPurchasePool.loc[pIndex, "Active"] = False  # close the new pool

            # update old pool
            purchasePools.loc[pIndex, "Amount"] = purchasePools.loc[
                pIndex, "Amount"
            ] * (
                1 - percentUsed
            )  # should equal newPurchasePool.loc[pIndex,'Amount']*percentUsed
            purchasePools.loc[pIndex, "Fee"] = purchasePools.loc[pIndex, "Fee"] * (
                1 - percentUsed
            )
            purchasePools.loc[pIndex, "Fee USD"] = round(
                purchasePools.loc[pIndex, "Fee USD"] * (1 - percentUsed), USDdecimals
            )
            purchasePools.loc[pIndex, "Cost Basis"] = round(
                purchasePools.loc[pIndex, "Cost Basis"] * (1 - percentUsed), USDdecimals
            )
            # modified cost basis too?
            purchasePools.loc[pIndex, "Modified Cost Basis"] = round(
                purchasePools.loc[pIndex, "Modified Cost Basis"] * (1 - percentUsed),
                USDdecimals,
            )

            # only split the pool if both parts would have a significant value
            # NOTE: this could also be done as a percentage using percentUsed>0.995 or something of that sort
            if newPurchasePool.loc[pIndex, "Modified Cost Basis"] > poolLimitUSD:
                # add the new pool to the pools list and change its index
                purchasePools = pd.concat(
                    [purchasePools, newPurchasePool], ignore_index=True
                )
            else:
                purchasePools.loc[
                    pIndex, "Active"
                ] = True  # the old pool becomes inactive
                # as it is used in lieu of the new pool
                print("A pool split was avoided due to an insufficient pool size")
            # update the sale pool items needed
            costBasis = (
                costBasis * percentUsed
            )  # this doesn't use the modified cost basis
            # (assumes Wash Sales are looked for after the fact)

        # else if the purchase pool is less than the sale amount, close the purchase pool and
        # generate the partial sale pool
        # create a new sell order with the remaining amount
        elif greaterLessEqual == -1:
            purchasePools.loc[pIndex, "Active"] = False

            remainingSaleAmount = (
                sellAmount - pPoolAmount
            )  # salePool amount - purchasePool amount
            percentUsed = pPoolAmount / sellAmount

            sellAmount = purchasePools.loc[pIndex, "Amount"]
            # costBasis is already correctly calculated
            modifiedCostBasis = costBasis

            # split the order into the realized order and remaining order
            remainingOrder = order.copy()
            remainingOrder.loc[0, "Amount"] = remainingSaleAmount
            remainingOrder.loc[
                0, "Fee"
            ] = 0  # let the first salePool contain the entirety of the
            # fees...fewer adjustments
            remainingOrder.loc[0, "Total"] = remainingOrder.loc[0, "Total"] * (
                1 - percentUsed
            )

            # order needs to be updated to the realized order values for wash sale checking later
            # order.loc[0,'Amount'] = order.loc['Amount']-remainingSaleAmount
            # order.loc[0,'Total'] = order.loc[0,'Total']*percentUsed

        else:
            print("Unexpected Error: greaterLessEqual is not -1, 0, or 1")

        proceeds = sellAmount * assetSoldSpot - saleFeeUSD
        netGain = proceeds - costBasis

        # --------TEMPORARY---------------
        disallowedLoss = 0
        washID = 0
        purchaseDate = purchasePools.loc[pIndex, "Purchase Date"]
        holdingPerMod = purchasePools.loc[pIndex, "Holding Period Modifier"]

        # holdingPeriod = (saleDate.replace(tzinfo=datetime.timezone.utc) - purchaseDate.replace(tzinfo=datetime.timezone.utc)) + holdingPerMod
        print(
            "saleDate: ",
            saleDate,
            "\npurchaseDate: ",
            purchaseDate,
            "\nholdingPerMod: ",
            holdingPerMod,
        )

        holdingPeriod = (saleDate - purchaseDate) + holdingPerMod

        if holdingPeriod < datetime.timedelta(days=0):
            print(f"---------Holding Period less than 0------------\n\n")
            print(f"holding")

        longLimit = datetime.timedelta(days=366)
        long = False

        if holdingPeriod >= longLimit:
            long = True

        # holdingPeriod = holdingPeriod.days #holdingPeriod is now a string

        sID = makeID(salePools)

        sPool_dict = {
            "Pool ID": int(sID),
            "Asset Sold": assetSold,
            "Asset Received": assetReceived,
            "Purchase Date": purchaseDate,
            "Sale Date": saleDate,
            "Amount": sellAmount,
            "Sale Price": salePrice,
            "Asset Sold Spot Price": assetSoldSpot,
            "Asset Received Spot Price": assetReceivedSpot,
            "Fee": saleFee,
            "Fee Coin": saleFeeCoin,
            "Fee Coin Spot Price": saleFeeCoinSpot,
            "Fee USD": round(saleFeeUSD, USDdecimals),
            "Purchase Pool ID": pID,
            "Holding Period": holdingPeriod,
            "Long": long,
            "Proceeds": round(proceeds, USDdecimals),
            "Cost Basis": round(costBasis, USDdecimals),
            "Wash Pool ID": washID,
            "Disallowed Loss": round(disallowedLoss, USDdecimals),
            "Net Gain": round(netGain, USDdecimals),
        }

        """
        # Such a weird bug. Changing 1 value at a time to an empty df
        # apparently changes some, but not all, types, even though
        # they have already been initialized
        sPool = getEmptySalePool()
        print('--------------sPool empty--------------------------')
        print(sPool.dtypes)
        sPool.loc[0, 'Pool ID'] = int(sID)
        sPool.at[0, 'Sale Date'] = saleDate
        sPool.loc[0, 'Purchase Date'] = purchaseDate
        sPool.loc[0, 'Asset Sold'] = assetSold
        sPool.loc[0, 'Asset Received'] = assetReceived
        sPool.loc[0, 'Amount'] = sellAmount
        sPool.loc[0, 'Sale Price'] = salePrice
        sPool.loc[0, 'Asset Sold Spot Price'] = assetSoldSpot
        sPool.loc[0, 'Asset Received Spot Price'] = assetReceivedSpot
        sPool.loc[0, 'Fee'] = saleFee
        sPool.loc[0, 'Fee Coin'] = saleFeeCoin
        sPool.loc[0, 'Fee Coin Spot Price'] = saleFeeCoinSpot
        sPool.loc[0, 'Fee USD'] = round(saleFeeUSD, USDdecimals)
        sPool.loc[0, 'Purchase Pool ID'] = pID
        sPool.loc[0, 'Holding Period'] = holdingPeriod
        sPool.loc[0, 'Long'] = bool(long)
        sPool.loc[0, 'Wash Pool ID'] = washID
        sPool.loc[0, 'Cost Basis'] = round(costBasis, USDdecimals)
        sPool.loc[0, 'Proceeds'] = round(proceeds, USDdecimals)
        sPool.loc[0, 'Disallowed Loss'] = round(disallowedLoss, USDdecimals)
        sPool.loc[0, 'Net Gain'] = round(netGain, USDdecimals)

        print('--------------sPool after--------------------------')
        print(sPool.dtypes)
        """
        sPool = getEmptySalePool()
        sPool.loc[0, :] = sPool_dict
        salePools = pd.concat([salePools, sPool], ignore_index=True)

        # now that we have the salePool added, we can go back and check
        # to see if it was a wash sale and modify it
        purchasePools, salePools = washPoolMatches(
            sID, orderType, invMethod, purchasePools, salePools
        )

        # if the sell amount was more than the purchase pool initiate the remaining sale order
        if greaterLessEqual == -1:
            purchasePools, salePools = sellAsset(
                remainingOrder, purchasePools, salePools, invMethod
            )

    elif orderType == "SELL":
        print("Error: How did you end up here selling USD?")
    # Case: BUY asset for USD. No salePool added
    else:
        print("Order is a plain BUY for USD. No sale pool added")

    return purchasePools, salePools


def identifyAssets(order):
    # temp = order.loc[0, 'Market']
    # location is not always indexed to 0, get the first row of the list
    temp = order.iloc[0]["Market"]

    try:
        asset1, asset2 = temp.split("-")
    except:
        asset1 = temp
        asset2 = "USD"

    # orderType = order.loc[0,'Type']
    orderType = order.iloc[0]["Type"]
    orderType = orderType.upper()

    # orderDate = order.loc[0,'Date(UTC)']
    # amount = order.loc[0,'Amount']
    orderDate = order.iloc[0]["Date(UTC)"]
    amount = order.iloc[0]["Amount"]

    return [asset1, amount, asset2, orderType, orderDate]


def executeOrder(order, purchasePools, salePools, invMethod):
    # this function executes the sale or virtual sale (sale initiated by another trade) in 'order'
    # by finding a suitable pool or pools in the 'purchasePools' dataframe and updates
    # the 'purchasePools' and 'salePools' dataframes

    purchasePools, salePools = buyAsset(order, purchasePools, salePools, invMethod)

    purchasePools, salePools = sellAsset(order, purchasePools, salePools, invMethod)

    return purchasePools, salePools


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


def washPoolMatches(ID, orderType, invMethod, purchasePools, salePools):
    # ID is the pool ID of either the new BUY pool (orderType='BUY') or the SELL pool(orderType='SELL').
    USDdecimals = 3  # number of decimal places all USD values are rounded to
    poolLimitUSD = 1  # if a pool split would result in a pool with asset value of less than this, don't split the pool

    if ID == 0:
        print("Error: ---------------ID is 0---------------")

    # get the correct index of the pool ID within purchasePools or salePools
    if orderType == "BUY":
        nbIndex = getIDIndex(purchasePools, ID)
        asset = purchasePools.loc[nbIndex, "Asset"]
        amount = purchasePools.loc[nbIndex, "Amount"]
        exchangeDate = purchasePools.loc[nbIndex, "Purchase Date"]
        # ----PROBLEM!!!!! This purchase date is not the exchange date, but the original pools purchase date
        # at least for recursive washPoolMatches calls

    elif orderType == "SELL":
        sIndex = getIDIndex(salePools, ID)
        asset = salePools.loc[sIndex, "Asset Sold"]
        amount = salePools.loc[sIndex, "Amount"]
        exchangeDate = salePools.loc[sIndex, "Sale Date"]
    else:
        print("Error: unidentifiable transaction method (BUY or SELL).")

    potentialPools = []

    window = datetime.timedelta(days=30)
    cutoffDate = (
        exchangeDate - window
    )  # earliest date for which a previous purchase could be considered a wash

    if orderType == "BUY":
        # (True?) this can be run for previously closed BUY pools if a wash sale triggers a 'cascade' of other wash sales
        # that originally were not (because there was a gain instead of a loss)

        # only ones that matters here are SELLs within the window
        potentialPools = salePools[
            (salePools["Sale Date"] > cutoffDate)
            & (salePools["Asset Sold"] == asset)
            & (salePools["Wash Pool ID"] == 0)
            & (salePools["Net Gain"] < 0)
        ]
        if invMethod == "FIFO":
            potentialPools = potentialPools.sort_values(
                by=["Sale Date"], ascending=True
            )
        elif invMethod == "LIFO":
            potentialPools = potentialPools.sort_values(
                by=["Sale Date"], ascending=False
            )
        else:
            print("Error: Invalid invMethod")

        if len(potentialPools) > 0:  # if there are, in fact, any wash sales identified
            # identify the previous SELL pool
            # washSalePool = potentialPools.iloc[[0]]
            sIndex = potentialPools.iloc[0].name
            sID = salePools.loc[sIndex, "Pool ID"]
            sPoolAmount = salePools.loc[sIndex, "Amount"]
            saleDate = salePools.loc[sIndex, "Sale Date"]
            # should this be some recursive form like holdingPeriodMod = holdingPeriodMod + ...?
            # holdingPeriodMod = (exchangeDate-saleDate)+datetime.timedelta(days = salePools.loc[sIndex, 'Holding Period']) #should be an interval not a date
            # holdingPeriodMod = datetime.timedelta(days = salePools.loc[sIndex, 'Holding Period']) #should be an interval not a date
            holdingPeriodMod = salePools.loc[sIndex, "Holding Period"]  # ALTERED!!!
            # is the new BUY greater, less than, or equal to the previous SELL?
            if amount > sPoolAmount:
                # split the new BUY
                washPercent = sPoolAmount / amount

                # NOTE: the new washSALE/washBUY should always be the newly created pool to maintain consistency with existing pool ID pairs
                washBuyPool = purchasePools.loc[
                    [nbIndex]
                ].copy()  # copy actually isn't necessary here
                washBuyPool.loc[nbIndex, "Amount"] = (
                    washBuyPool.loc[nbIndex, "Amount"] * washPercent
                )
                washBuyPool.loc[nbIndex, "Fee"] = (
                    washBuyPool.loc[nbIndex, "Fee"] * washPercent
                )
                washBuyPool.loc[nbIndex, "Fee USD"] = round(
                    washBuyPool.loc[nbIndex, "Fee USD"] * washPercent, USDdecimals
                )
                washBuyPool.loc[nbIndex, "Initiates Wash"] = sID
                washBuyPool.loc[nbIndex, "Holding Period Modifier"] = holdingPeriodMod
                # update the Cost Basis to account for the reduced amount from splitting
                washBuyPool.loc[nbIndex, "Cost Basis"] = round(
                    washBuyPool.loc[nbIndex, "Cost Basis"] * washPercent, USDdecimals
                )
                # Cost Basis include fees already, correct?
                # Net Gain is negative here as it is a loss
                washBuyPool.loc[nbIndex, "Modified Cost Basis"] = round(
                    washBuyPool.loc[nbIndex, "Cost Basis"]
                    - salePools.loc[sIndex, "Net Gain"],
                    USDdecimals,
                )
                washBuyID = makeID(purchasePools)
                washBuyPool.loc[nbIndex, "Pool ID"] = washBuyID

                # HUH? WHY SHOULD IT ALREADY BE CLOSED?
                print(
                    "purchasePool should already be closed: ",
                    washBuyPool.loc[nbIndex, "Active"],
                )  # why should it already be closed?

                # only split the pool if both parts would have a significant value
                # NOTE: this could also be done as a percentage using percentUsed>0.995 or something of that sort
                if washBuyPool.loc[nbIndex, "Modified Cost Basis"] > poolLimitUSD:
                    # remainingBUY (done after washBuyPool has copied the original value)
                    purchasePools.loc[nbIndex, "Amount"] = purchasePools.loc[
                        nbIndex, "Amount"
                    ] * (1 - washPercent)
                    purchasePools.loc[nbIndex, "Fee"] = purchasePools.loc[
                        nbIndex, "Fee"
                    ] * (1 - washPercent)
                    purchasePools.loc[nbIndex, "Fee USD"] = round(
                        purchasePools.loc[nbIndex, "Fee USD"] * (1 - washPercent),
                        USDdecimals,
                    )
                    purchasePools.loc[nbIndex, "Cost Basis"] = round(
                        purchasePools.loc[nbIndex, "Cost Basis"] * (1 - washPercent),
                        USDdecimals,
                    )
                    purchasePools.loc[nbIndex, "Modified Cost Basis"] = round(
                        purchasePools.loc[nbIndex, "Modified Cost Basis"]
                        * (1 - washPercent),
                        USDdecimals,
                    )

                    remainingBuyID = purchasePools.loc[nbIndex, "Pool ID"]

                    # append the washBUY to the purchasePools list
                    purchasePools = pd.concat(
                        [purchasePools, washBuyPool], ignore_index=True
                    )

                    # absorb the losses by updating the washSalePool
                    salePools.loc[sIndex, "Wash Pool ID"] = washBuyID

                    # Cost Basis include fees already, correct?
                    salePools.loc[sIndex, "Disallowed Loss"] = abs(
                        round(salePools.loc[sIndex, "Net Gain"], USDdecimals)
                    )  # disallowed loss is the previous net gain

                    # Net Gain is negative here as it is a loss
                    salePools.loc[
                        sIndex, "Net Gain"
                    ] = 0  # net gain is added to the cost basis of the new BUY pool

                    # rerun the remainingBUY pool through the identify wash chain again to see if it executes another wash
                    print("chaining washPoolMatches to identify other washes")
                    purchasePools, salePools = washPoolMatches(
                        remainingBuyID, "BUY", invMethod, purchasePools, salePools
                    )
                # if not treat it as if the amounts are equal
                else:
                    purchasePools.loc[nbIndex, "Initiates Wash"] = sID
                    purchasePools.loc[
                        nbIndex, "Holding Period Modifier"
                    ] = holdingPeriodMod
                    # Cost Basis include fees already, correct?
                    # Net Gain is negative here as it is a loss...NEEDS TO BE DONE BEFORE UPDATING THE washSalePool (salePool as sIndex)
                    purchasePools.loc[nbIndex, "Modified Cost Basis"] = round(
                        purchasePools.loc[nbIndex, "Cost Basis"]
                        - salePools.loc[sIndex, "Net Gain"],
                        USDdecimals,
                    )

                    # absorb the losses by updating the washSalePool
                    salePools.loc[
                        sIndex, "Wash Pool ID"
                    ] = ID  # ID is the wash purchasePool ID in this case with 'BUY'
                    # Cost Basis include fees already, correct?
                    salePools.loc[sIndex, "Disallowed Loss"] = abs(
                        round(salePools.loc[sIndex, "Net Gain"], USDdecimals)
                    )  # disallowed loss is the previous net gain

                    # Net Gain is negative here as it is a loss
                    salePools.loc[
                        sIndex, "Net Gain"
                    ] = 0  # net gain is added to the cost basis of the new BUY pool

            elif amount < sPoolAmount:
                # split the previous SELL, absorb the partial losses
                washPercent = amount / sPoolAmount

                # NOTE: the new washSALE/washBUY should always be the newly created pools to maintain consistency with existing pool ID pairs
                washSalePool = salePools.loc[
                    [sIndex]
                ].copy()  # copy actually isn't necessary here
                washSalePool.loc[sIndex, "Amount"] = (
                    washSalePool.loc[sIndex, "Amount"] * washPercent
                )
                washSalePool.loc[sIndex, "Fee"] = (
                    washSalePool.loc[sIndex, "Fee"] * washPercent
                )
                washSalePool.loc[sIndex, "Fee USD"] = round(
                    washSalePool.loc[sIndex, "Fee USD"] * washPercent, USDdecimals
                )
                washSalePool.loc[sIndex, "Cost Basis"] = round(
                    washSalePool.loc[sIndex, "Cost Basis"] * washPercent, USDdecimals
                )
                washSalePool.loc[sIndex, "Proceeds"] = round(
                    washSalePool.loc[sIndex, "Proceeds"] * washPercent, USDdecimals
                )
                washLoss = round(
                    washSalePool.loc[sIndex, "Net Gain"] * washPercent, USDdecimals
                )
                washSaleID = makeID(salePools)
                washSalePool.loc[sIndex, "Pool ID"] = washSaleID
                washSalePool.loc[
                    sIndex, "Wash Pool ID"
                ] = ID  # ID is the wash purchasePool ID in this case with 'BUY'

                # Cost Basis include fees already, correct?
                # Net Gain is negative here as it is a loss
                washSalePool.loc[sIndex, "Disallowed Loss"] = abs(washLoss)
                washSalePool.loc[
                    sIndex, "Net Gain"
                ] = 0  # net gain is added to the cost basis of the new BUY pool

                # append the washSalePool to the salePools list
                salePools = pd.concat([salePools, washSalePool], ignore_index=True)

                # all of the new BUY pool is
                purchasePools.loc[nbIndex, "Initiates Wash"] = washSaleID  # washSALE ID
                purchasePools.loc[nbIndex, "Holding Period Modifier"] = holdingPeriodMod
                # Cost Basis include fees already, correct?
                # Net Gain is negative here as it is a loss...NEEDS TO BE DONE BEFORE UPDATING THE washSalePool (salePool as sIndex)
                purchasePools.loc[nbIndex, "Modified Cost Basis"] = round(
                    purchasePools.loc[nbIndex, "Cost Basis"] - washLoss
                )

                # remaining salePool
                salePools.loc[sIndex, "Amount"] = salePools.loc[sIndex, "Amount"] * (
                    1 - washPercent
                )
                salePools.loc[sIndex, "Fee"] = salePools.loc[sIndex, "Fee"] * (
                    1 - washPercent
                )
                salePools.loc[sIndex, "Fee USD"] = round(
                    salePools.loc[sIndex, "Fee USD"] * (1 - washPercent), USDdecimals
                )
                salePools.loc[sIndex, "Cost Basis"] = round(
                    salePools.loc[sIndex, "Cost Basis"] * (1 - washPercent), USDdecimals
                )
                salePools.loc[sIndex, "Proceeds"] = round(
                    salePools.loc[sIndex, "Proceeds"] * (1 - washPercent), USDdecimals
                )
                salePools.loc[sIndex, "Net Gain"] = (
                    salePools.loc[sIndex, "Proceeds"]
                    - salePools.loc[sIndex, "Cost Basis"]
                )

            elif amount == sPoolAmount:
                # absorb all losses
                purchasePools.loc[nbIndex, "Initiates Wash"] = sID
                purchasePools.loc[nbIndex, "Holding Period Modifier"] = holdingPeriodMod
                # Cost Basis include fees already, correct?
                # Net Gain is negative here as it is a loss...NEEDS TO BE DONE BEFORE UPDATING THE washSalePool (salePool as sIndex)
                purchasePools.loc[nbIndex, "Modified Cost Basis"] = round(
                    purchasePools.loc[nbIndex, "Cost Basis"]
                    - salePools.loc[sIndex, "Net Gain"],
                    USDdecimals,
                )

                # absorb the losses by updating the washSalePool
                salePools.loc[
                    sIndex, "Wash Pool ID"
                ] = ID  # ID is the wash purchasePool ID in this case with 'BUY'
                # Cost Basis include fees already, correct?
                # Net Gain is negative here as it is a loss
                salePools.loc[sIndex, "Disallowed Loss"] = abs(
                    round(salePools.loc[sIndex, "Net Gain"], USDdecimals)
                )  # disallowed loss is the previous net gain
                salePools.loc[
                    sIndex, "Net Gain"
                ] = 0  # net gain is added to the cost basis of the new BUY pool
            else:
                print("Error in Wash calculation")

    elif orderType == "SELL":
        # only ones that matter here are BUYs within window
        # for BUY, -> SELL <-, BUY no wash has occurred yet
        # for BUY, new BUY, ->SELL<- LIFO always gets the new BUY so there is no wash
        if invMethod == "LIFO":
            print("no wash occurs with SELL/LIFO for ID ", sIndex, "and asset", asset)
        elif invMethod == "FIFO":
            potentialPools = purchasePools[
                (purchasePools["Purchase Date"] > cutoffDate)
                & (purchasePools["Asset"] == asset)
            ]
            potentialPools = potentialPools.sort_values(
                by=["Purchase Date"], ascending=True
            )
        else:
            print("Error: Invalid invMethod")
    else:
        print("Error: unidentifiable transaction method (BUY or SELL).")

    return purchasePools, salePools


def prettyPrintPools(poolDB, filename):
    # takes in a pool database or slice and prints the pertinent data in the appropriate format for the IRS
    Cols = [
        "Asset Sold",
        "Purchase Date",
        "Sale Date",
        "Amount",
        "Spot Price (USD)",
        "Fee (USD)",
        "Holding Period (days)",
        "Short/Long",
        "Proceeds (USD)",
        "Cost Basis (USD)",
        "Wash Sale",
        "Disallowed Loss (USD)",
        "Net Gain (USD)",
    ]
    pool = pd.DataFrame(columns=Cols)
    """
    ['Pool ID', 'Asset Sold', 'Asset Received', 'Purchase Date','Sale Date', 'Amount', 'Sale Price',
        'Asset Sold Spot Price', 'Asset Received Spot Price',
        'Fee','Fee Coin', 'Fee Coin Spot Price', 'Fee USD',
        'Purchase Pool ID', 'Holding Period', 'Long',
        'Proceeds', 'Cost Basis', 'Wash Pool ID', 'Disallowed Loss', 'Net Gain']
    """
    pool["Asset Sold"] = poolDB["Asset Sold"]
    pool["Amount"] = poolDB["Amount"]
    pool["Spot Price (USD)"] = poolDB["Asset Sold Spot Price"]
    pool["Fee (USD)"] = poolDB["Fee USD"]
    pool["Holding Period (days)"] = poolDB["Holding Period"].dt.days
    pool["Proceeds (USD)"] = poolDB["Proceeds"]
    pool["Cost Basis (USD)"] = poolDB["Cost Basis"]
    pool["Disallowed Loss (USD)"] = poolDB["Disallowed Loss"]
    pool["Net Gain (USD)"] = poolDB["Net Gain"]

    # Shortened dates, short/long, wash need to be done individually
    for index, _ in poolDB.iterrows():
        sDate = poolDB.loc[index, "Sale Date"]
        pDate = poolDB.loc[index, "Purchase Date"]
        SL = "SHORT"
        Wash = ""
        if poolDB.loc[index, "Long"] == True:
            SL = "LONG"
        if poolDB.loc[index, "Wash Pool ID"] != 0:
            Wash = "W"

        pool.loc[index, "Sale Date"] = sDate.strftime("%x")
        pool.loc[index, "Purchase Date"] = pDate.strftime("%x")
        pool.loc[index, "Short/Long"] = SL
        pool.loc[index, "Wash Sale"] = Wash

    # Merge same day sales of the same asset
    # unique sale date/asset/wash
    unique = pool.drop_duplicates(
        subset=["Asset Sold", "Short/Long", "Sale Date", "Wash Sale"]
    )
    pool_clean = pd.DataFrame(columns=pool.columns)
    for i, row in unique.iterrows():
        asset = row["Asset Sold"]
        sDate = row["Sale Date"]
        Wash = row["Wash Sale"]
        SL = row["Short/Long"]
        # mask that includes rows that could be combined
        mask = (
            (pool["Asset Sold"] == asset)
            & (pool["Sale Date"] == sDate)
            & (pool["Wash Sale"] == Wash)
            & (pool["Short/Long"] == SL)
        )
        multi_sale = pool[mask]
        print(f"multi_sale:\n{multi_sale}")
        if len(multi_sale) > 1:
            pDate = "Various Dates"
            amount = multi_sale["Amount"].sum()
            sum_price = (multi_sale["Amount"] * multi_sale["Spot Price (USD)"]).sum()
            spotPrice = sum_price / amount  # price weighted by amount
            fee = multi_sale["Fee (USD)"].sum()
            holding_period = "Various"
            proceeds = multi_sale["Proceeds (USD)"].sum()
            cost_basis = multi_sale["Cost Basis (USD)"].sum()
            disallowed_loss = multi_sale["Disallowed Loss (USD)"].sum()
            net_gain = multi_sale["Net Gain (USD)"].sum()

            row_dict = {
                "Asset Sold": asset,
                "Purchase Date": pDate,
                "Sale Date": sDate,
                "Amount": amount,
                "Spot Price (USD)": spotPrice,
                "Fee (USD)": fee,
                "Holding Period (days)": holding_period,
                "Short/Long": SL,
                "Proceeds (USD)": proceeds,
                "Cost Basis (USD)": cost_basis,
                "Wash Sale": Wash,
                "Disallowed Loss (USD)": disallowed_loss,
                "Net Gain (USD)": net_gain,
            }
            pool_clean.loc[i, :] = row_dict
        else:
            pool_clean.loc[i, :] = row
        print(f"pool_clean:\n{pool_clean}")
    pool_clean.to_csv(filename, index=False, encoding="utf-8")
    return
