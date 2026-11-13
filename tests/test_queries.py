"""Dashboard query layer (src/p2p/queries.py) against the notes and v_kpi (DR-5)."""

import pytest
from conftest import needs_data

from p2p import queries as q

pytestmark = needs_data
DEFAULT = q.Filters()


def test_kpis_match_v_kpi(con):
    k = q.kpis(con, DEFAULT)
    view = con.sql("SELECT * FROM v_kpi WHERE po_month = 'all'").pl().to_dicts()[0]
    cols = {
        "K1a": "k1a_cycle_median_days", "K1b": "k1b_cycle_p90_days", "K2": "k2_ir_to_clear_median_days",
        "K3": "k3_clearing_rate", "K4": "k4_ir_before_gr_rate", "K5": "k5_vi_before_po_rate",
        "K6": "k6_touchless_rate", "K7": "k7_rework_per_100", "K8": "k8_payment_block_rate",
    }
    for kid, col in cols.items():
        assert k[kid] == pytest.approx(view[col], rel=1e-9), kid
    assert k["items"] == 155_761


def test_monthly_has_seven_months(con):
    assert q.kpis_monthly(con, DEFAULT)["po_month"].to_list() == list(q.COHORT_MONTHS)


def test_phases(con):
    ph = {r["phase"]: r for r in q.phases(con, DEFAULT).iter_rows(named=True)}
    assert ph["Invoice receipt to clearing"]["median_days"] == pytest.approx(46.1, abs=0.05)
    assert ph["PO to clearing (total)"]["median_days"] == pytest.approx(79.3, abs=0.05)


def test_compliance_rates(con):
    assert q.compliance_rate(con, DEFAULT, "K4") == (pytest.approx(0.0914, abs=1e-4), 129_244, 11_815)
    _, n, b = q.compliance_rate(con, DEFAULT, "K5", all_items=True)
    assert (n, b) == (209_888, 3_618)  # README / note 04, all cases


def test_compliance_items_match_count(con):
    assert q.compliance_items(con, DEFAULT, "K4").height == 11_815
    top = q.compliance_breakdown(con, DEFAULT, "K4", "vendor_id").row(0, named=True)
    one_vendor = q.compliance_items(con, DEFAULT, "K4", "vendor_id", top["grp"])
    assert one_vendor.height == top["breaches"]


def test_rework_types(con):
    rt = {r["activity"]: r for r in q.rework_types(con, DEFAULT).iter_rows(named=True)}
    assert rt["Change Quantity"]["items_with"] == 10_035
    assert rt["Change Quantity"]["gap_days"] == pytest.approx(21.8, abs=0.05)
    assert rt["Remove Payment Block"]["items_with"] == 37_667
    assert rt["Set Payment Block"]["gap_days"] is None  # 19 items, under MIN_N


def test_touchless_vs_rework(con):
    qd = {r["grp"]: r for r in q.cycle_quantiles(con, DEFAULT, "rework").iter_rows(named=True)}
    assert qd["Touchless"]["median"] == pytest.approx(73.4, abs=0.05)
    assert qd["With rework"]["median"] == pytest.approx(91.0, abs=0.05)


def test_rankings_respect_min_n(con):
    for df in (
        q.ranking(con, DEFAULT, "vendor_id"),
        q.compliance_breakdown(con, DEFAULT, "K5", "spend_area"),
        q.block_breakdown(con, DEFAULT, "vendor_id"),
    ):
        assert df["items"].min() >= q.MIN_N


def test_filters_narrow_the_population(con):
    f = q.Filters(months=("2018-03", "2018-05"), category="3-way match, invoice after GR", spend_areas=("Packaging",))
    k = q.kpis(con, f)
    assert 0 < k["items"] < 155_761
    assert q.top_variants(con, f, 5).height <= 5


def test_conformance(con):
    s, groups = q.conformance(con)
    if not s["finished"]:
        pytest.skip("conformance results not loaded")
    assert s["fitting"] / s["finished"] == pytest.approx(0.916, abs=0.0005)
    assert groups["reason"][0].startswith("repeated activity")


def test_item_detail(con):
    item, events = q.item_detail(con, "4507004931_00020")
    assert item["status"] == "cleared"
    assert events["seq"].to_list() == list(range(1, events.height + 1))
    assert q.item_detail(con, "no-such-item")[0] is None
