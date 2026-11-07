from pathlib import Path

import polars as pl

IN = Path("data/interim/events.parquet")
OUT = Path("data/interim/events_clean.parquet")
SUSPECT_DAYS = 365
DATE_ONLY = [
    "Vendor creates invoice",
    "Vendor creates debit memo",
    "Create Purchase Requisition Item",
]


def main() -> None:
    df = pl.read_parquet(IN)
    po = (
        df.filter(pl.col("activity") == "Create Purchase Order Item")
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("po_ts"))
    )
    df = (
        df.join(po, on="case_id", how="left")
        .with_columns(
            (pl.col("po_ts") - pl.col("timestamp")).dt.total_days().alias("days_before_po"),
            pl.col("activity").is_in(DATE_ONLY).alias("date_only"),
            pl.col("event_id").cast(pl.Int64).alias("event_id_int"),
        )
        .with_columns((pl.col("days_before_po") > SUSPECT_DAYS).alias("ts_suspect"))
        .sort(["case_id", "timestamp", "event_id_int"])
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print("rows:", df.height, "| suspect events:", df["ts_suspect"].sum())


if __name__ == "__main__":
    main()