import polars as pl

pl.Config.set_tbl_rows(40)
pl.Config.set_tbl_width_chars(200)

df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))
IR, CLEAR, CANCEL = "Record Invoice Receipt", "Clear Invoice", "Cancel Invoice Receipt"


def ts(act: str, how: str, name: str) -> pl.Expr:
    col = pl.col("timestamp").filter(pl.col("activity") == act)
    return (col.max() if how == "max" else col.min()).alias(name)


cases = (
    df.group_by("case_id")
    .agg(
        pl.col("item_category").first(),
        ts(IR, "max", "last_ir"),
        ts(CANCEL, "max", "last_cancel"),
        ts(CLEAR, "min", "clear"),
        pl.col("net_worth_eur").max().alias("value_eur"),
    )
    .with_columns((pl.col("last_cancel") > pl.col("last_ir")).fill_null(False).alias("invoice_cancelled"))
)

unc = cases.filter(pl.col("last_ir").is_not_null(), pl.col("clear").is_null())

print(
    unc.group_by("item_category", "invoice_cancelled")
    .agg(pl.len().alias("cases"), pl.col("value_eur").sum().round(0).alias("value_eur"))
    .sort("item_category", "invoice_cancelled")
)

print(
    unc.filter(~pl.col("invoice_cancelled"))
    .group_by(pl.col("last_ir").dt.strftime("%Y-%m").alias("month"))
    .len()
    .sort("month")
)

print("value of cleared items (for scale):", round(cases.filter(pl.col("clear").is_not_null())["value_eur"].sum(), 0))