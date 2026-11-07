import gzip
import io
from pathlib import Path

import polars as pl

RAW = Path("data/raw/BPI_Challenge_2019.csv.gz")
OUT = Path("data/interim/events.parquet")

RENAME = {
    "eventID": "event_id",
    "case concept:name": "case_id",
    "event concept:name": "activity",
    "event time:timestamp": "timestamp",
    "event org:resource": "resource",
    "event User": "user",
    "event Cumulative net worth (EUR)": "net_worth_eur",
    "case Item Category": "item_category",
    "case Vendor": "vendor",
    "case Company": "company",
    "case Spend area text": "spend_area",
    "case Sub spend area text": "sub_spend_area",
    "case Document Type": "document_type",
    "case Item Type": "item_type",
    "case GR-Based Inv. Verif.": "gr_based_iv",
    "case Goods Receipt": "goods_receipt_flag",
    "case Purchasing Document": "po_number",
    "case Item": "po_item",
}


def main() -> None:
    # Source file is cp1252-encoded (e.g. 0x96 en dashes in item text), not UTF-8.
    with gzip.open(RAW, "rb") as f:
        text = f.read().decode("cp1252")
    df = pl.read_csv(io.StringIO(text), infer_schema_length=0)  # read everything as text first
    del text
    df = df.rename({c: c.strip() for c in df.columns})
    df = df.rename(RENAME)
    df = df.with_columns(
        pl.col("timestamp").str.to_datetime("%d-%m-%Y %H:%M:%S%.f"),
        pl.col("net_worth_eur").cast(pl.Float64),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print(df.shape)


if __name__ == "__main__":
    main()