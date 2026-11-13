import polars as pl

pl.Config.set_tbl_rows(60)

df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))
CLEAR = "Clear Invoice"

# 1) when do clearing events happen? Is there a hard cut-off date?
print(
    df.filter(pl.col("activity") == CLEAR)
    .group_by(pl.col("timestamp").dt.strftime("%Y-%m").alias("month"))
    .len()
    .sort("month")
)

cases = df.group_by("case_id").agg(
    pl.col("item_category").first(),
    pl.col("timestamp").filter(pl.col("activity") == "Create Purchase Order Item").min().alias("po"),
    pl.col("timestamp").filter(pl.col("activity") == CLEAR).min().alias("clear"),
    pl.col("timestamp").filter(pl.col("activity") == "Record Invoice Receipt").max().alias("last_ir"),
)

# 2) share cleared by month the PO was created (main category)
main = cases.filter(pl.col("item_category") == "3-way match, invoice before GR")
print(
    main.group_by(pl.col("po").dt.strftime("%Y-%m").alias("po_month"))
    .agg(
        pl.len().alias("cases"),
        pl.col("clear").is_not_null().mean().round(3).alias("share_cleared"),
        ((pl.col("clear") - pl.col("po")).dt.total_seconds() / 86400).median().round(1).alias("median_days_to_clear"),
    )
    .sort("po_month")
)

# 3) among items with an invoice receipt: share cleared by month of the last invoice receipt
print(
    cases.filter(pl.col("last_ir").is_not_null())
    .group_by(pl.col("last_ir").dt.strftime("%Y-%m").alias("ir_month"))
    .agg(pl.len().alias("cases"), pl.col("clear").is_not_null().mean().round(3).alias("share_cleared"))
    .sort("ir_month")
)