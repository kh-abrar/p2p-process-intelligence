import polars as pl

pl.Config.set_tbl_rows(40)
pl.Config.set_tbl_width_chars(220)

REWORK = [
    "Change Price",
    "Change Quantity",
    "Cancel Invoice Receipt",
    "Cancel Goods Receipt",
    "Remove Payment Block",
    "Set Payment Block",
]
THREE_WAY = ["3-way match, invoice before GR", "3-way match, invoice after GR"]

df = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))


def has(act: str) -> pl.Expr:
    return (pl.col("activity") == act).any().alias(act)


cases = (
    df.group_by("case_id")
    .agg(
        pl.col("item_category").first(),
        pl.col("timestamp").filter(pl.col("activity") == "Create Purchase Order Item").min().alias("po"),
        pl.col("timestamp").filter(pl.col("activity") == "Clear Invoice").min().alias("clear"),
        has("Delete Purchase Order Item"),
        has("Record Goods Receipt"),
        has("Record Invoice Receipt"),
        *[has(a) for a in REWORK],
    )
    .with_columns(
        pl.col("clear").is_not_null().alias("cleared"),
        ((pl.col("clear") - pl.col("po")).dt.total_seconds() / 86400).alias("po_to_clear"),
        pl.any_horizontal(*[pl.col(a) for a in REWORK]).alias("any_rework"),
    )
)

# A) why do items never clear? (consignment excluded: no invoice flow by design)
totals = cases.group_by("item_category").agg(pl.len().alias("total"))
uncleared = (
    cases.filter(~pl.col("cleared"), pl.col("item_category") != "Consignment")
    .with_columns(
        pl.when(pl.col("Delete Purchase Order Item")).then(pl.lit("deleted"))
        .when(pl.col("Record Invoice Receipt")).then(pl.lit("invoice recorded, never cleared"))
        .when(pl.col("Record Goods Receipt")).then(pl.lit("goods received, no invoice"))
        .otherwise(pl.lit("ordered only"))
        .alias("status")
    )
    .group_by("item_category", "status")
    .agg(pl.len().alias("n"))
    .join(totals, on="item_category")
    .with_columns((pl.col("n") / pl.col("total")).round(3).alias("share_of_cases"))
    .sort("item_category", "n", descending=[False, True])
)
print(uncleared)

# B) rework: how common, and how much longer do cleared 3-way items take?
cleared = cases.filter(pl.col("cleared"), pl.col("item_category").is_in(THREE_WAY))
rows = []
for a in REWORK:
    with_a = cleared.filter(pl.col(a))["po_to_clear"]
    without = cleared.filter(~pl.col(a))["po_to_clear"]
    rows.append((a, cases.filter(pl.col(a)).height, with_a.len(), with_a.median(), without.median()))
print(
    pl.DataFrame(
        rows,
        schema=["rework", "cases_all", "cases_cleared", "median_days_with", "median_days_without"],
        orient="row",
    )
)

# C) touchless share among cleared 3-way items
touchless = cleared.filter(~pl.col("any_rework"))["po_to_clear"]
touched = cleared.filter(pl.col("any_rework"))["po_to_clear"]
print(
    f"touchless: {touchless.len()} of {cleared.height} "
    f"({touchless.len() / cleared.height:.1%}), median {touchless.median():.1f} days; "
    f"with rework: median {touched.median():.1f} days"
)