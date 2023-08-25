from pathlib import Path
from cointracker.objects.pool import PoolRegistry
from cointracker.settings.config import read_config
from cointracker.util.parsing import pool_reg_from_df

cfg = read_config()


def export_pool_reg(pool_reg: PoolRegistry, filename: str, iso=True) -> None:
    if ".xlsx" not in filename:
        filename = filename + ".xlsx"
    filepath = cfg.paths.data / filename
    df = pool_reg.to_df(ascending=True, kind="default")

    if iso:
        df.purchase_date = df.purchase_date.apply(lambda x: x.isoformat())
        df.sale_date = df.sale_date.apply(lambda x: x.isoformat())

    # excel cannot handle timezone aware datetimes, convert to string
    df = df.astype({"purchase_date": "str", "sale_date": "str"})
    df.to_excel(filepath, "All Pools", index=False)
