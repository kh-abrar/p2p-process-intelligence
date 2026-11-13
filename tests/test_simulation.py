"""What-if simulation (src/p2p/simulation.py): model mechanics, validation and scenario direction."""

import polars as pl
import pytest
import simpy
from conftest import needs_data

from p2p import simulation as sim


def test_item_clears_when_receipts_and_due_date_are_done():
    env, out = simpy.Environment(), []
    env.process(sim._item(env, t_vi=5, t_gr=20, t_ir=8, wait=40, out=out))  # due at day 45
    env.process(sim._item(env, t_vi=5, t_gr=60, t_ir=8, wait=40, out=out))  # goods receipt last
    env.run()
    assert sorted(out) == [45, 60]


@pytest.fixture(scope="module")
def pool(warehouse_db):
    return sim.load_pool(warehouse_db)


@pytest.fixture(scope="module")
def results(pool):
    return sim.run(pool, sim.SCENARIOS, reps=3, n=4_000, seed=7)


@needs_data
def test_pool(pool):
    assert pool.height == 127_830
    assert sorted(pool["lag_bin"].unique().to_list()) == list(range(sim.LAG_BINS))


@needs_data
def test_baseline_reproduces_observed(pool, results):
    v = {r["measure"]: r for r in sim.validate(pool, results).iter_rows(named=True)}
    assert abs(v["median_days"]["difference"]) < 4
    assert abs(v["p90_days"]["difference"]) < 5
    assert abs(v["touchless"]["difference"]) < 0.02


@needs_data
def test_scenarios_reduce_time_and_rework(results):
    s = {r["scenario"]: r for r in sim.summarise(results).iter_rows(named=True)}
    assert s["S0 baseline"]["median_days_diff"] == 0
    for name in ("S1 right-first-time PO", "S2 block prevention", "S3 both"):
        assert s[name]["mean_days_diff"] < 0, name
        assert s[name]["touchless_diff"] > 0, name
    assert s["S3 both"]["mean_days_diff"] < s["S2 block prevention"]["mean_days_diff"]


@needs_data
def test_same_seed_same_result(pool):
    a = sim.run(pool, sim.SCENARIOS[:1], reps=1, n=500, seed=3)
    b = sim.run(pool, sim.SCENARIOS[:1], reps=1, n=500, seed=3)
    assert a.equals(b)
    assert isinstance(a, pl.DataFrame)
