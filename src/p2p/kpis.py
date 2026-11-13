"""KPI baselines for the catalogue in kpis/catalogue.md.

All KPIs use the cohort of POs created Jan-Jul 2018 (clearing is cut off in Jan 2019, see
mining/notes/03-censoring.md) and exclude events with ts_suspect = true.
Run: uv run python src/p2p/kpis.py
"""

from datetime import datetime
from pathlib import Path

import polars as pl

CLEAN = Path("data/interim/events_clean.parquet")
OUT = Path("kpis/outputs")
START, END = datetime(2018, 1, 1), datetime(2018, 8, 1)  # POs created Jan-Jul 2018
MAIN = "3-way match, invoice before GR"
THREE_WAY = [MAIN, "3-way match, invoice after GR"]
REWORK = [
    "Change Price",
    "Change Quantity",
    "Cancel Invoice Receipt",
    "Cancel Goods Receipt",
    "Remove Payment Block",
    "Set Payment Block",
]

# id, name, unit, which direction is better
KPIS = [
    ("K1a", "Cycle time PO to clearing, median", "days", "lower"),
    ("K1b", "Cycle time PO to clearing, P90", "days", "lower"),
    ("K2", "Wait from invoice receipt to clearing, median", "days", "lower"),
    ("K3", "Clearing rate", "share", "higher"),
    ("K4", "Invoice receipt before goods receipt rate", "share", "lower"),
    ("K5", "Vendor invoice before PO rate", "share", "lower"),
    ("K6", "Touchless rate", "share", "higher"),
    ("K7", "Rework events per 100 items", "per 100", "lower"),
    ("K8", "Payment-block removal rate", "share", "lower"),
]


def _first(act: str, name: str) -> pl.Expr:
    return pl.col("timestamp").filter(pl.col("activity") == act).min().alias(name)


def case_table(ev: pl.DataFrame) -> pl.DataFrame:
    """One row per case with the timestamps and flags the KPIs need."""
    ev = ev.filter(~pl.col("ts_suspect"))
    days = lambda end, start: (pl.col(end) - pl.col(start)).dt.total_seconds() / 86400
    return (
        ev.group_by("case_id")
        .agg(
            pl.col("item_category").first(),
            _first("Create Purchase Order Item", "po"),
            _first("Vendor creates invoice", "vi"),
            _first("Record Goods Receipt", "gr"),
            _first("Record Invoice Receipt", "ir"),
            _first("Clear Invoice", "clear"),
            pl.col("activity").is_in(REWORK).sum().alias("n_rework"),
            (pl.col("activity") == "Remove Payment Block").any().alias("payment_block"),
        )
        .with_columns(
            pl.col("clear").is_not_null().alias("cleared"),
            days("clear", "po").alias("po_to_clear"),
            days("clear", "ir").alias("ir_to_clear"),
            pl.col("po").dt.strftime("%Y-%m").alias("po_month"),
        )
    )


def cohort(cases: pl.DataFrame) -> pl.DataFrame:
    return cases.filter((pl.col("po") >= START) & (pl.col("po") < END))


def kpi_values(c: pl.DataFrame) -> dict[str, tuple[float, int]]:
    """KPI id -> (value, denominator in items) for a set of cohort cases."""
    main = c.filter(pl.col("item_category") == MAIN)
    main_cl = main.filter(pl.col("cleared"))
    both = main.filter(pl.col("gr").is_not_null() & pl.col("ir").is_not_null())
    with_vi = c.filter(pl.col("vi").is_not_null())
    cl3 = c.filter(pl.col("cleared") & pl.col("item_category").is_in(THREE_WAY))
    wait = main_cl["ir_to_clear"].drop_nulls()
    return {
        "K1a": (main_cl["po_to_clear"].median(), main_cl.height),
        "K1b": (main_cl["po_to_clear"].quantile(0.9), main_cl.height),
        "K2": (wait.median(), wait.len()),
        "K3": (main["cleared"].mean(), main.height),
        "K4": ((both["ir"] < both["gr"]).mean(), both.height),
        "K5": ((with_vi["vi"].dt.date() < with_vi["po"].dt.date()).mean(), with_vi.height),
        "K6": ((cl3["n_rework"] == 0).mean(), cl3.height),
        "K7": (100 * cl3["n_rework"].mean(), cl3.height),
        "K8": (cl3["payment_block"].mean(), cl3.height),
    }


def baselines(cases: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Cohort baseline per KPI (with best cohort month) and the monthly values."""
    c = cohort(cases)
    total = kpi_values(c)
    monthly = pl.DataFrame(
        [
            {"po_month": m, "kpi_id": k, "value": v, "items": n}
            for m in sorted(c["po_month"].unique())
            for k, (v, n) in kpi_values(c.filter(pl.col("po_month") == m)).items()
        ]
    )
    rows = []
    for kid, name, unit, better in KPIS:
        m = monthly.filter(pl.col("kpi_id") == kid).sort("value", descending=better == "higher")
        rows.append(
            {
                "kpi_id": kid,
                "kpi": name,
                "unit": unit,
                "better": better,
                "baseline": total[kid][0],
                "items": total[kid][1],
                "best_month": m["po_month"][0],
                "best_month_value": m["value"][0],
                "worst_month_value": m["value"][-1],
            }
        )
    return pl.DataFrame(rows), monthly


def main() -> None:
    cases = case_table(pl.read_parquet(CLEAN))
    base, monthly = baselines(cases)
    OUT.mkdir(parents=True, exist_ok=True)
    base.write_csv(OUT / "kpi_baselines.csv")
    monthly.write_csv(OUT / "kpi_monthly.csv")

    pl.Config.set_tbl_rows(20)
    pl.Config.set_tbl_width_chars(220)
    pl.Config.set_fmt_str_lengths(60)
    print(f"Cohort: {cohort(cases).height:,} items (POs created {START:%Y-%m} to {END:%Y-%m}, exclusive)\n")
    print(base.with_columns(pl.col(pl.Float64).round(4)))
    print("\nMonthly values:")
    print(monthly.pivot("kpi_id", index="po_month", values="value").with_columns(pl.col(pl.Float64).round(3)))

    # cross-check against the all-cases figure in the README (3,618 of 209,888)
    vi = cases.filter(pl.col("vi").is_not_null())
    n = (vi["vi"].dt.date() < vi["po"].dt.date()).sum()
    print(f"\nK5 on all cases (not cohort): {n:,} of {vi.height:,} ({n / vi.height:.1%})")


if __name__ == "__main__":
    main()
