import polars as pl

pl.Config.set_tbl_width_chars(250)
pl.Config.set_tbl_cols(20)

df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))


def first_ts(act: str, name: str) -> pl.Expr:
    return pl.col("timestamp").filter(pl.col("activity") == act).min().alias(name)


def n_events(act: str, name: str) -> pl.Expr:
    return (pl.col("activity") == act).sum().alias(name)


cases = df.group_by("case_id").agg(
    pl.col("item_category").first(),
    first_ts("Create Purchase Order Item", "po"),
    first_ts("Vendor creates invoice", "vi"),
    first_ts("Record Goods Receipt", "gr"),
    first_ts("Record Invoice Receipt", "ir"),
    n_events("Record Goods Receipt", "n_gr"),
    n_events("Record Invoice Receipt", "n_ir"),
    n_events("Vendor creates invoice", "n_vi"),
)


def day(c: str) -> pl.Expr:
    return pl.col(c).dt.date()


flags = cases.with_columns(
    (day("vi") < day("po")).alias("vendor_inv_before_po_day"),
    (pl.col("ir") < pl.col("gr")).alias("ir_before_gr"),
    (day("ir") < day("gr")).alias("ir_before_gr_day"),
    (day("ir") < day("vi")).alias("ir_before_vendor_inv_day"),
    (pl.col("n_gr") > 1).alias("multi_gr"),
    (pl.col("n_ir") > 1).alias("multi_ir"),
    (pl.col("n_vi") > 1).alias("multi_vi"),
)

summary = (
    flags.group_by("item_category")
    .agg(
        pl.len().alias("cases"),
        pl.col("vi").is_not_null().sum().alias("has_vi"),
        (pl.col("gr").is_not_null() & pl.col("ir").is_not_null()).sum().alias("has_gr_ir"),
        pl.col("vendor_inv_before_po_day").sum().alias("vi_before_po"),
        pl.col("ir_before_gr").sum().alias("ir_before_gr"),
        pl.col("ir_before_gr_day").sum().alias("ir_before_gr_day"),
        pl.col("ir_before_vendor_inv_day").sum().alias("ir_before_vi_day"),
        pl.col("multi_gr").sum().alias("multi_gr"),
        pl.col("multi_ir").sum().alias("multi_ir"),
        pl.col("multi_vi").sum().alias("multi_vi"),
    )
    .sort("cases", descending=True)
)
print(summary)
flags.write_parquet("data/interim/case_flags.parquet")