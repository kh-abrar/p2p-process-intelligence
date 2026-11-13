from pathlib import Path

import polars as pl
import pytest

from p2p.kpis import KPIS, baselines, case_table, cohort

CLEAN = Path("data/interim/events_clean.parquet")
pytestmark = pytest.mark.skipif(not CLEAN.exists(), reason="run `make ingest` first")


@pytest.fixture(scope="module")
def cases() -> pl.DataFrame:
    return case_table(pl.read_parquet(CLEAN))


@pytest.fixture(scope="module")
def base(cases) -> dict[str, float]:
    b, _ = baselines(cases)
    return dict(zip(b["kpi_id"], b["baseline"], strict=True))


def test_cohort_size(cases):
    assert cohort(cases).height == 155_761


def test_all_kpis_present(base):
    assert set(base) == {k for k, *_ in KPIS}


@pytest.mark.parametrize(
    ("kpi", "expected", "tol"),
    [
        ("K1a", 79.3, 0.05),  # median days, mining/notes/04
        ("K1b", 129.1, 0.05),
        ("K2", 46.1, 0.05),
        ("K3", 0.938, 0.0005),
        ("K4", 0.0914, 0.0005),  # 11,815 of 129,244
        ("K5", 0.017, 0.0005),
        ("K6", 0.637, 0.0005),  # 86,505 of 135,721
        ("K7", 48.5, 0.05),
        ("K8", 0.2775, 0.0005),  # 37,667 of 135,721
    ],
)
def test_baselines(base, kpi, expected, tol):
    assert base[kpi] == pytest.approx(expected, abs=tol)


def test_monthly_covers_cohort_months(cases):
    _, monthly = baselines(cases)
    assert sorted(monthly["po_month"].unique()) == [f"2018-{m:02d}" for m in range(1, 8)]
