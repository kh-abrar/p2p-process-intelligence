from pathlib import Path

import polars as pl

pl.Config.set_fmt_str_lengths(400)
pl.Config.set_tbl_width_chars(300)
pl.Config.set_tbl_rows(30)

# suspect-date events are dropped here because their timestamps would misplace them in the trace
df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))

traces = (
    df.group_by("case_id", maintain_order=True)
    .agg(
        pl.col("item_category").first(),
        pl.col("activity").alias("trace"),
    )
    .with_columns(pl.col("trace").list.join(" > ").alias("variant"))
)

v = (
    traces.group_by("item_category", "variant")
    .agg(pl.len().alias("cases"))
    .sort(["item_category", "cases"], descending=[False, True])
    .with_columns(
        (pl.col("cases") / pl.col("cases").sum().over("item_category")).alias("share")
    )
    .with_columns(pl.col("share").cum_sum().over("item_category").alias("cum_share"))
)

Path("mining/outputs").mkdir(parents=True, exist_ok=True)
v.write_csv("mining/outputs/variants.csv")

# 1) how many variants per category, and how many cover 80% of cases
print(
    v.group_by("item_category").agg(
        pl.len().alias("n_variants"),
        ((pl.col("cum_share") < 0.8).sum() + 1).alias("variants_to_reach_80pct"),
    )
)

# 2) top 10 variants of the dominant category
main = v.filter(pl.col("item_category") == "3-way match, invoice before GR").head(10)
print(main.select("cases", "share", "variant"))

# 3) cases with no clearing event (open, incomplete or never invoiced)
print(
    traces.with_columns(pl.col("trace").list.contains("Clear Invoice").alias("cleared"))
    .group_by("item_category")
    .agg(pl.len().alias("cases"), (~pl.col("cleared")).sum().alias("no_clearing"))
)