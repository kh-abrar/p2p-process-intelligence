"""What-if simulation of the main purchase-to-pay flow (SimPy), for brief question 5.

Model (one SimPy process per PO item, "3-way match, invoice before GR"):

    PO created --+-- goods receipt (t_gr) ---------------------------------------+
                 +-- vendor invoice (t_vi) --+-- invoice booked (t_ir) ----------+-- cleared when all
                                             +-- payment due (t_vi + wait) ------+   three are done

Each item has two rework flags, drawn from the observed mix:
- order rework: Change Price, Change Quantity, Cancel Goods Receipt or Cancel Invoice Receipt
- payment block: Remove or Set Payment Block
The order-side times (t_vi, t_gr, t_ir) come together from one observed item with the same flags.
The payment wait (days from vendor invoice to clearing) comes from another observed item with the
same flags and a similar invoice-booking delay (t_ir - t_vi, in quintiles), because late booking
goes with late payment. Clearing cannot happen before both receipts (three-way match).
A scenario removes a share of one kind of rework; the affected items then take their times from
items without that rework. impact/README.md has the evidence for this structure.

Uncertainty: every replication bootstraps the item pool (parameter uncertainty) and simulates a
fresh sample (simulation noise). Scenarios share random numbers with the baseline inside a
replication, so differences are paired. The 95% interval is the 2.5-97.5 percentile of the
per-replication differences.

Run: uv run python src/p2p/simulation.py   (or `make simulate`; needs `make warehouse`)
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
import simpy

DB = Path("data/warehouse/p2p.duckdb")
OUT = Path("impact/outputs")

POOL_SQL = """
WITH flags AS (
    SELECT e.item_key,
           bool_or(a.activity IN ('Change Price', 'Change Quantity', 'Cancel Goods Receipt',
                                  'Cancel Invoice Receipt')) AS order_rework,
           bool_or(a.activity IN ('Remove Payment Block', 'Set Payment Block')) AS block
    FROM fact_event e JOIN dim_activity a USING (activity_key)
    WHERE NOT e.ts_suspect
    GROUP BY 1
)
SELECT epoch(gr_ts - po_ts) / 86400 AS t_gr,
       epoch(ir_ts - po_ts) / 86400 AS t_ir,
       epoch(vendor_invoice_ts - po_ts) / 86400 AS t_vi,
       epoch(clear_ts - vendor_invoice_ts) / 86400 AS wait,
       po_to_clear_days,
       order_rework,
       block
FROM v_item JOIN flags USING (item_key)
WHERE in_cohort AND cleared AND item_category = '3-way match, invoice before GR'
  AND gr_ts IS NOT NULL AND ir_ts IS NOT NULL AND vendor_invoice_ts IS NOT NULL
"""
LAG_BINS = 5


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    cut_order_rework: float = 0.0  # share of order-rework items that become right first time
    cut_block: float = 0.0  # share of blocked items that are no longer blocked


SCENARIOS = [
    Scenario("S0 baseline", "As-is: observed rework mix"),
    Scenario("S1 right-first-time PO", "Half of price/quantity changes and receipt cancellations avoided",
             cut_order_rework=0.5),
    Scenario("S2 block prevention", "Half of payment blocks avoided", cut_block=0.5),
    Scenario("S3 both", "S1 and S2 together", cut_order_rework=0.5, cut_block=0.5),
]
SENSITIVITY = [
    Scenario("S1 at 25%", "A quarter of order rework avoided", cut_order_rework=0.25),
    Scenario("S1 at 75%", "Three quarters of order rework avoided", cut_order_rework=0.75),
    Scenario("S2 at 25%", "A quarter of payment blocks avoided", cut_block=0.25),
    Scenario("S2 at 75%", "Three quarters of payment blocks avoided", cut_block=0.75),
]


def load_pool(db: Path = DB) -> pl.DataFrame:
    """Observed items with phase times, rework flags and booking-delay quintile (lag_bin, 0-4)."""
    with duckdb.connect(str(db), read_only=True) as con:
        pool = con.sql(POOL_SQL).pl()
    lag = (pool["t_ir"] - pool["t_vi"]).to_numpy()
    edges = np.quantile(lag, [i / LAG_BINS for i in range(1, LAG_BINS)])
    return pool.with_columns(pl.Series("lag_bin", np.searchsorted(edges, lag, side="right")))


def _pick(arr: np.ndarray, u: float):
    return arr[min(int(u * len(arr)), len(arr) - 1)]


class _Cells:
    """Observed times by rework flags (order side) and by flags + booking-delay bin (payment wait)."""

    def __init__(self, pool: pl.DataFrame):
        self.flags = pool.select("order_rework", "block").to_numpy().astype(bool)
        self.order, self.wait = {}, {}
        for (o, b), c in pool.group_by("order_rework", "block"):
            self.order[(o, b)] = c.select("t_vi", "t_gr", "t_ir", "lag_bin").to_numpy()
            for (k,), cb in c.group_by("lag_bin"):
                self.wait[(o, b, int(k))] = cb["wait"].to_numpy()

    def draw(self, cell: tuple[bool, bool], u_order: float, u_wait: float) -> tuple[float, float, float, float]:
        t_vi, t_gr, t_ir, k = _pick(self.order[cell], u_order)
        waits = self.wait[(*cell, int(k))]
        return float(t_vi), float(t_gr), float(t_ir), float(_pick(waits, u_wait))


def _item(env: simpy.Environment, t_vi: float, t_gr: float, t_ir: float, wait: float, out: list):
    start = env.now
    goods = env.timeout(max(t_gr, 0.0))
    booked = env.timeout(max(t_ir, 0.0))
    due = env.timeout(max(t_vi + wait, 0.0))
    yield goods & booked & due  # three-way match, then pay on the due date
    out.append(env.now - start)


def _arrivals(env, rate_per_day: float, rng: np.random.Generator, plan: list, out: list):
    for times in plan:
        env.process(_item(env, *times, out))
        yield env.timeout(rng.exponential(1 / rate_per_day))


def simulate(
    cells: _Cells, scenario: Scenario, n: int, seed: int, rate_per_day: float = 600.0
) -> dict[str, float]:
    """One replication of one scenario. Same seed -> same random numbers for every scenario."""
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(cells.flags), n)  # whose observed flags each item starts with
    u_switch_o, u_switch_b, u_order, u_wait = rng.random((4, n))
    arrival_rng = np.random.default_rng(seed + 1)

    plan, touchless = [], 0
    for i in range(n):
        o, b = cells.flags[pick[i]]
        o = bool(o and u_switch_o[i] >= scenario.cut_order_rework)
        b = bool(b and u_switch_b[i] >= scenario.cut_block)
        touchless += not (o or b)
        plan.append(cells.draw((o, b), u_order[i], u_wait[i]))

    env, out = simpy.Environment(), []
    env.process(_arrivals(env, rate_per_day, arrival_rng, plan, out))
    env.run()
    c = np.array(out)
    return {
        "median_days": float(np.median(c)),
        "p90_days": float(np.quantile(c, 0.9)),
        "mean_days": float(c.mean()),
        "touchless": touchless / n,
    }


def run(
    pool: pl.DataFrame,
    scenarios: list[Scenario],
    reps: int = 50,
    n: int = 10_000,
    seed: int = 2019,
) -> pl.DataFrame:
    """All scenarios x replications. Each replication bootstraps the pool once (shared by scenarios)."""
    rows = []
    for r in range(reps):
        boot = pool.sample(fraction=1.0, with_replacement=True, seed=seed + 1000 * r)
        cells = _Cells(boot)
        for s in scenarios:
            rows.append({"rep": r, "scenario": s.name, **simulate(cells, s, n, seed + r)})
    return pl.DataFrame(rows)


def summarise(results: pl.DataFrame, baseline: str = "S0 baseline") -> pl.DataFrame:
    """Per scenario: mean value and the paired difference to baseline with a 95% interval."""
    metrics = ["median_days", "p90_days", "mean_days", "touchless"]
    base = results.filter(pl.col("scenario") == baseline).select("rep", *[pl.col(m).alias(f"{m}_base") for m in metrics])
    d = results.join(base, on="rep").with_columns(
        *[(pl.col(m) - pl.col(f"{m}_base")).alias(f"{m}_diff") for m in metrics]
    )
    order = {s: i for i, s in enumerate(results["scenario"].unique(maintain_order=True))}
    return (
        d.group_by("scenario")
        .agg(
            *[pl.col(m).mean() for m in metrics],
            *[
                expr
                for m in metrics
                for expr in (
                    pl.col(f"{m}_diff").mean().alias(f"{m}_diff"),
                    pl.col(f"{m}_diff").quantile(0.025, "linear").alias(f"{m}_diff_lo"),
                    pl.col(f"{m}_diff").quantile(0.975, "linear").alias(f"{m}_diff_hi"),
                )
            ],
            pl.len().alias("reps"),
        )
        .sort(pl.col("scenario").replace_strict(order, return_dtype=pl.Int32))
    )


def validate(pool: pl.DataFrame, results: pl.DataFrame) -> pl.DataFrame:
    """Simulated baseline against the observed items it was built from."""
    b = results.filter(pl.col("scenario") == "S0 baseline")
    obs = pool["po_to_clear_days"]
    touch = (~pool["order_rework"] & ~pool["block"]).mean()
    return pl.DataFrame(
        {
            "measure": ["median_days", "p90_days", "mean_days", "touchless"],
            "observed": [obs.median(), obs.quantile(0.9, "linear"), obs.mean(), touch],
            "simulated": [b[m].mean() for m in ["median_days", "p90_days", "mean_days", "touchless"]],
        }
    ).with_columns((pl.col("simulated") - pl.col("observed")).alias("difference"))


def main(reps: int = 50, n: int = 10_000) -> None:
    pool = load_pool()
    print(f"pool: {pool.height:,} cleared main-category cohort items with vendor invoice and both receipts")
    print(pool.group_by("order_rework", "block").agg(
        pl.len().alias("items"),
        pl.max_horizontal("t_gr", "t_ir").median().alias("receipts_done_median"),
        pl.col("wait").median().alias("invoice_to_clear_median"),
        pl.col("po_to_clear_days").median().alias("po_to_clear_median"),
    ).sort("order_rework", "block"))

    results = run(pool, SCENARIOS + SENSITIVITY, reps=reps, n=n)
    OUT.mkdir(parents=True, exist_ok=True)
    results.write_csv(OUT / "replications.csv")
    summary = summarise(results)
    summary.write_csv(OUT / "summary.csv")
    val = validate(pool, results)
    val.write_csv(OUT / "validation.csv")

    pl.Config.set_tbl_rows(20)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(250)
    print(f"\n== Validation (simulated baseline vs observed, {reps} reps x {n:,} items) ==")
    print(val.with_columns(pl.col(pl.Float64).round(3)))
    print("\n== Scenario results (difference to baseline, 95% interval) ==")
    print(
        summary.select(
            "scenario",
            pl.col("median_days").round(1),
            pl.format("{} [{}, {}]", *[pl.col(c).round(1) for c in ("median_days_diff", "median_days_diff_lo",
                                                                      "median_days_diff_hi")]).alias("median_diff"),
            pl.format("{} [{}, {}]", *[pl.col(c).round(1) for c in ("p90_days_diff", "p90_days_diff_lo",
                                                                      "p90_days_diff_hi")]).alias("p90_diff"),
            pl.format("{} [{}, {}]", *[(pl.col(c) * 100).round(1) for c in ("touchless_diff", "touchless_diff_lo",
                                                                               "touchless_diff_hi")]).alias(
                "touchless_diff_pp"),
        )
    )


if __name__ == "__main__":
    main()
