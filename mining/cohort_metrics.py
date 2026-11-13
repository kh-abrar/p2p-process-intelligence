"""Cohort metrics: POs created Jan-Jul 2018 (unbiased by Jan-2019 clearing truncation)."""

from datetime import datetime

import polars as pl

START, END = datetime(2018, 1, 1), datetime(2018, 8, 1)  # POs created Jan-Jul 2018
REWORK = [
    "Change Price",
    "Change Quantity",
    "Cancel Invoice Receipt",
    "Cancel Goods Receipt",
    "Remove Payment Block",
    "Set Payment Block",
]
THREE_WAY = ["3-way match, invoice before GR", "3-way match, invoice after GR"]
MAIN = "3-way match, invoice before GR"

# suspect dates are excluded from durations
ev = pl.read_parquet("data/interim/events_clean.parquet").filter(~pl.col("ts_suspect"))


def first(act: str, name: str) -> pl.Expr:
    return pl.col("timestamp").filter(pl.col("activity") == act).min().alias(name)


def has(act: str) -> pl.Expr:
    return (pl.col("activity") == act).any().alias(act)


cases = ev.group_by("case_id").agg(
    pl.col("item_category").first(),
    first("Create Purchase Order Item", "po"),
    first("Record Goods Receipt", "gr"),
    first("Record Invoice Receipt", "ir"),
    first("Clear Invoice", "clear"),
    *[has(a) for a in REWORK],
    has("Delete Purchase Order Item"),
)

days = lambda end, start: (pl.col(end) - pl.col(start)).dt.total_seconds() / 86400

cohort = cases.filter((pl.col("po") >= START) & (pl.col("po") < END)).with_columns(
    pl.col("clear").is_not_null().alias("cleared"),
    days("clear", "po").alias("po_to_clear"),
    days("clear", "ir").alias("ir_to_clear"),
    pl.any_horizontal(REWORK).alias("any_rework"),
)
print(f"Cohort: {cohort.height:,} items (POs created {START:%Y-%m-%d} to {END:%Y-%m-%d})\n")

# 1. cycle time per category
print("== Cycle time per category ==")
print(
    cohort.group_by("item_category")
    .agg(
        pl.len().alias("items"),
        pl.col("cleared").mean().round(3).alias("cleared_share"),
        pl.col("po_to_clear").median().round(1).alias("median_days"),
        pl.col("po_to_clear").quantile(0.9).round(1).alias("p90_days"),
        pl.col("ir_to_clear").median().round(1).alias("ir_to_clear_median"),
    )
    .sort("items", descending=True)
)

# 2. invoice before goods receipt (main category, items with both events)
both = cohort.filter((pl.col("item_category") == MAIN) & pl.col("gr").is_not_null() & pl.col("ir").is_not_null())
n_early = both.filter(pl.col("ir") < pl.col("gr")).height
print(f"\n== IR before GR ==\n{n_early:,} of {both.height:,} ({n_early / both.height:.1%})")

# 3. rework gaps (cleared 3-way items)
cl = cohort.filter(pl.col("cleared") & pl.col("item_category").is_in(THREE_WAY))
rows = []
for a in REWORK:
    w, wo = cl.filter(pl.col(a))["po_to_clear"], cl.filter(~pl.col(a))["po_to_clear"]
    rows.append(
        {
            "rework": a,
            "items_with": w.len(),
            "median_with": round(w.median(), 1) if w.len() else None,
            "median_without": round(wo.median(), 1),
            "gap_days": round(w.median() - wo.median(), 1) if w.len() else None,
        }
    )
print("\n== Rework gaps (cleared 3-way items) ==")
print(pl.DataFrame(rows).sort("gap_days", descending=True, nulls_last=True))

# 4. touchless vs rework
t, r = cl.filter(~pl.col("any_rework"))["po_to_clear"], cl.filter(pl.col("any_rework"))["po_to_clear"]
print(f"\n== Touchless ==\n{t.len():,} of {cl.height:,} cleared items ({t.len() / cl.height:.1%})")
for label, s in [("touchless", t), ("with rework", r)]:
    print(f"{label:12s} median {s.median():.1f}  P90 {s.quantile(0.9):.1f}")
print(f"gap: {r.median() - t.median():+.1f} days ({r.median() / t.median() - 1:+.0%})")

# 5. what happened to uncleared items (excluding consignment, which has no invoice flow)
print("\n== Uncleared cohort items ==")
unc = (
    cohort.filter(~pl.col("cleared"), pl.col("item_category") != "Consignment")
    .with_columns(
        pl.when(pl.col("Delete Purchase Order Item")).then(pl.lit("deleted"))
        .when(pl.col("ir").is_not_null()).then(pl.lit("invoice recorded, never cleared"))
        .when(pl.col("gr").is_not_null()).then(pl.lit("goods received, no invoice"))
        .otherwise(pl.lit("ordered only"))
        .alias("status")
    )
    .group_by("item_category", "status")
    .agg(pl.len().alias("n"))
    .join(cohort.group_by("item_category").agg(pl.len().alias("total")), on="item_category")
    .with_columns((pl.col("n") / pl.col("total")).round(3).alias("share_of_cases"))
    .sort("item_category", "n", descending=[False, True])
)
print(unc)
# 6. is "goods received, never invoiced" (invoice after GR) a truncation artefact?
# If the share rises toward July, invoices may simply not have arrived before the log ends.
last_ir = ev.filter(pl.col("activity") == "Record Invoice Receipt")["timestamp"].max()
print(f"\n== Goods received, no invoice (invoice after GR) ==\nlast invoice receipt in log: {last_ir}")
print(
    cohort.filter(pl.col("item_category") == "3-way match, invoice after GR", pl.col("gr").is_not_null())
    .group_by(pl.col("po").dt.strftime("%Y-%m").alias("po_month"))
    .agg(
        pl.len().alias("items_with_gr"),
        pl.col("ir").is_null().mean().round(3).alias("share_no_invoice"),
    )
    .sort("po_month")
)
