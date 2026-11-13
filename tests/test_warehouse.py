import polars as pl
import pytest
from conftest import needs_data

from p2p.kpis import baselines, case_table
from p2p.warehouse import CLEAN, CONFORMANCE

pytestmark = needs_data


def one(con, sql: str):
    return con.execute(sql).fetchall()[0][0]


@pytest.mark.parametrize(
    ("table", "rows"),
    [
        ("fact_event", 1_595_923),
        ("fact_item", 251_734),
        ("dim_item", 251_734),
        ("dim_activity", 42),
        ("dim_company", 4),
    ],
)
def test_row_counts(con, table, rows):
    assert one(con, f"SELECT count(*) FROM {table}") == rows


def test_every_event_date_in_dim_date(con):
    assert one(con, "SELECT count(*) FROM fact_event e ANTI JOIN dim_date d USING (date_key)") == 0


def test_activity_flags(con):
    assert one(con, "SELECT count(*) FROM dim_activity WHERE is_rework") == 6
    assert one(con, "SELECT count(*) FROM dim_activity WHERE is_modelled") == 9
    assert one(con, "SELECT count(*) FROM dim_activity WHERE is_date_only") == 3


def test_seq_in_item_is_dense(con):
    bad = one(
        con,
        """SELECT count(*) FROM (
               SELECT item_key, max(seq_in_item) AS m, count(*) AS n FROM fact_event GROUP BY 1
           ) WHERE m <> n""",
    )
    assert bad == 0


def test_cohort_and_status(con):
    assert one(con, "SELECT count(*) FROM fact_item WHERE in_cohort") == 155_761
    rows = dict(
        con.execute(
            """SELECT status, count(*) FROM v_item
               WHERE in_cohort AND item_category = '3-way match, invoice after GR' GROUP BY 1"""
        ).fetchall()
    )
    assert rows["received not invoiced"] == 1_347  # mining/notes/04
    assert rows["invoice not cleared"] == 476


def test_kpi_view_matches_python(con):
    sql_cols = {
        "K1a": "k1a_cycle_median_days",
        "K1b": "k1b_cycle_p90_days",
        "K2": "k2_ir_to_clear_median_days",
        "K3": "k3_clearing_rate",
        "K4": "k4_ir_before_gr_rate",
        "K5": "k5_vi_before_po_rate",
        "K6": "k6_touchless_rate",
        "K7": "k7_rework_per_100",
        "K8": "k8_payment_block_rate",
    }
    b, _ = baselines(case_table(pl.read_parquet(CLEAN)))
    for kid, value in zip(b["kpi_id"], b["baseline"], strict=True):
        got = one(con, f"SELECT {sql_cols[kid]} FROM v_kpi WHERE po_month = 'all'")
        assert got == pytest.approx(value, rel=1e-6), kid


@pytest.mark.skipif(not CONFORMANCE.exists(), reason="run `make mining` first")
def test_conformance_loaded(con):
    assert one(con, "SELECT count(*) FROM conformance_variant") > 0
    fitting = one(con, "SELECT sum(cases) FILTER (WHERE fit) / sum(cases) FROM conformance_variant WHERE ended")
    assert fitting == pytest.approx(0.916, abs=0.0005)  # mining/notes/05
