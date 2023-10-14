from cointracker.util.parsing import (
    pool_reg_by_year,
    pool_reg_by_type,
)
from cointracker.process.execute import execute_orderbook
from cointracker.util.file_io import (
    export_pool_reg,
    load_excel_orderbook,
)


def run():
    ob = load_excel_orderbook(None, "Combined")
    pool_reg_washes = execute_orderbook(orderbook=ob, pool_reg=None)

    export_pool_reg(pool_reg=pool_reg_washes, filename=f"2022_EOY_All_Pools")

    years = [2021, 2022]
    pool_regs = pool_reg_by_year(pool_reg=pool_reg_washes, years=years)
    for year in years:
        for key, registry in pool_reg_by_type(pool_reg=pool_regs[year]).items():
            if not registry.is_empty:
                export_pool_reg(
                    pool_reg=registry,
                    filename=f"{year}_{key}_irs",
                    kind="irs",
                )
                export_pool_reg(
                    pool_reg=registry,
                    filename=f"{year}_{key}_irs_consolidated",
                    kind="irs",
                    consolidate=True,
                    by_date="double",
                )
