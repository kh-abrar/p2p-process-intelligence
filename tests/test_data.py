from pathlib import Path

import polars as pl
import pytest

CLEAN = Path("data/interim/events_clean.parquet")
pytestmark = pytest.mark.skipif(not CLEAN.exists(), reason="run `make ingest` first")


@pytest.fixture(scope="module")
def df() -> pl.DataFrame:
    return pl.read_parquet(CLEAN)


def test_counts(df):
    assert df.height == 1_595_923
    assert df["case_id"].n_unique() == 251_734


def test_no_nulls_in_keys(df):
    for col in ("case_id", "activity", "timestamp"):
        assert df[col].null_count() == 0


def test_one_po_creation_per_case(df):
    po = df.filter(pl.col("activity") == "Create Purchase Order Item")
    assert po.height == df["case_id"].n_unique()
    assert po["case_id"].n_unique() == po.height


def test_four_item_categories(df):
    assert df["item_category"].n_unique() == 4


def test_suspect_events_flagged(df):
    assert df["ts_suspect"].sum() == 100
    assert df.filter(pl.col("timestamp").dt.year() < 2000)["ts_suspect"].all()


def test_sorted_within_case(df):
    check = df.group_by("case_id", maintain_order=True).agg(
        (pl.col("timestamp").diff().dt.total_seconds().fill_null(0) >= 0).all().alias("ok")
    )
    assert check["ok"].all()