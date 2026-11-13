import polars as pl

pl.Config.set_tbl_rows(40)
pl.Config.set_tbl_width_chars(200)

PO, GR = "Create Purchase Order Item", "Record Goods Receipt"
IR, CLEAR = "Record Invoice Receipt", "Clear Invoice"

df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))


def first_ts(act: str, name: str) -> pl.Expr:
    return pl.col("timestamp").filter(pl.col("activity") == act).min().alias(name)


cases = df.group_by("case_id").agg(
    pl.col("item_category").first(),
    first_ts(PO, "po"),
    first_ts(GR, "gr"),
    first_ts(IR, "ir"),
    first_ts(CLEAR, "clear"),
)


def days(a: str, b: str) -> pl.Expr:
    return (pl.col(b) - pl.col(a)).dt.total_seconds() / 86400


seg = cases.with_columns(
    days("po", "clear").alias("po_to_clear"),
    days("po", "gr").alias("po_to_gr"),
    days("gr", "ir").alias("gr_to_ir"),
    days("ir", "clear").alias("ir_to_clear"),
)

metrics = ["po_to_clear", "po_to_gr", "gr_to_ir", "ir_to_clear"]
long = (
    seg.select("item_category", *metrics)
    .unpivot(index="item_category", variable_name="metric", value_name="days")
    .drop_nulls("days")
)
stats = (
    long.group_by("item_category", "metric")
    .agg(
        pl.len().alias("n"),
        pl.col("days").median().round(1).alias("median_days"),
        pl.col("days").quantile(0.9).round(1).alias("p90_days"),
        (pl.col("days") < 0).sum().alias("negative"),
    )
    .sort("item_category", "metric")
)
print(stats)

print(
    cases.group_by("item_category").agg(
        pl.len().alias("cases"),
        pl.col("clear").is_not_null().sum().alias("with_clearing"),
    )
)