"""One fixed half-rebalance experiment, not a parameter search."""

from pathlib import Path
import json
import time

import numpy as np
import pandas as pd

from src.backtest import simulate, equal_weight
from src.data import sha256
from src.factors import compute, quantiles
from src.statistics import performance
from run_mechanisms import PERIODS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/exploration"


def block_sharpe_difference(left, right, block=20, draws=2000, seed=20261101):
    rng = np.random.default_rng(seed)
    values = pd.concat([left, right], axis=1).dropna().to_numpy()
    n = len(values)
    diffs = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        indices = (starts[:, None] + np.arange(block)).ravel()[:n]
        sample = values[indices]
        sharpes = sample.mean(axis=0) / sample.std(axis=0, ddof=1) * np.sqrt(252)
        diffs.append(sharpes[0] - sharpes[1])
    return {"mean_difference": float(np.mean(diffs)),
            "ci_low": float(np.quantile(diffs, .025)), "ci_high": float(np.quantile(diffs, .975)),
            "draws": draws, "block_days": block, "seed": seed}


def main():
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"status": "running", "protocol_sha256": sha256(ROOT / "EXECUTION_EXTENSION.md"),
                "code_sha256": {f: sha256(ROOT / f) for f in ["run_execution_extension.py", "src/backtest.py"]},
                "rebalance_fractions": [1., .5], "costs_bps": [0, 10],
                "sample_status": "exploratory; not new holdout evidence"}
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, indent=2))
    symbols = pd.read_parquet(ROOT / "data/processed/PATH_formation_scores.parquet").columns
    panel = {}
    for field in ["close", "open", "volume", "circulating_market_cap_ashare"]:
        frame = pd.read_feather(ROOT / f"data/extracted/fire_data/{field}.feather").loc[:, symbols].astype("float32")
        frame.index = pd.to_datetime(frame.index)
        panel[field] = frame.sort_index()
    close, opening = panel["close"].where(panel["close"] > 0), panel["open"].where(panel["open"] > 0)
    f = compute(close, panel["volume"], panel["circulating_market_cap_ashare"])
    f["eligible"] &= f["eligible"].sum(axis=1).ge(100).to_numpy()[:, None]
    rows = list(range(int(close.index.searchsorted("2015-04-01")), len(close)-1, 5))
    accounts, stats, checks = {}, [], []
    for factor in ["PATH", "REV"]:
        groups = quantiles(f[factor].where(f["eligible"]))
        target = equal_weight(groups.eq(5))
        for mode, fraction in [("FULL", 1.), ("HALF", .5)]:
            for cost in [0, 10]:
                key = f"{factor}_{mode}_c{cost}"
                print(key, flush=True)
                account = simulate(opening, close, target, rows, pd.Timestamp("2015-04-01"), close.index[-1],
                                   cost_bps=cost, execution_available=panel["volume"].gt(0),
                                   rebalance_fraction=fraction)
                accounts[key] = account
                if mode == "FULL":
                    original = ROOT / f"data/processed/{factor}_Q5_c{cost}_account.parquet"
                    if original.exists():
                        prior = pd.read_parquet(original)
                        error = (prior - account.reindex(prior.index)).abs().max().max()
                        assert error < 1e-10, (key, error)
                        checks.append({"account": key, "maximum_original_reconciliation_error": error})
                for period, (start, end) in PERIODS.items():
                    part = account.loc[start:end]
                    rf = pd.Series((1.015)**(1/252)-1, index=part.index)
                    stats.append({"portfolio": key, "period": period,
                                  **performance(part["return"], rf),
                                  "gross_actual_annual_mean": (part["return"] + part.fees).mean() * 252,
                                  "fee_annual": part.fees.mean() * 252,
                                  "turnover_annual": part.turnover.mean() * 252,
                                  "cash_weight": part.cash_weight.mean(),
                                  "mean_holdings": part.holdings.mean(),
                                  "max_stale_weight": part.stale_weight.max()})
        short = simulate(opening, close, equal_weight(groups.eq(1)), rows,
                         pd.Timestamp("2015-04-01"), close.index[-1], cost_bps=0,
                         execution_available=panel["volume"].gt(0))
        accounts[f"{factor}_LS_c0"] = pd.DataFrame({"return": accounts[f"{factor}_FULL_c0"]["return"] - short["return"]})
    summary = pd.DataFrame(stats)
    summary.to_csv(OUT / "partial_rebalance_performance.csv", index=False, float_format="%.12g")
    pd.DataFrame({k: v["return"] for k, v in accounts.items()}).to_csv(
        OUT / "execution_daily_returns.csv", index_label="date", float_format="%.12g")
    decomposition = []
    for period in PERIODS:
        for factor in ["PATH", "REV"]:
            full = summary.loc[summary.period.eq(period) & summary.portfolio.eq(f"{factor}_FULL_c10")].iloc[0]
            half = summary.loc[summary.period.eq(period) & summary.portfolio.eq(f"{factor}_HALF_c10")].iloc[0]
            gross_delta = half.gross_actual_annual_mean - full.gross_actual_annual_mean
            saving = full.fee_annual - half.fee_annual
            net_delta = half.annual_mean - full.annual_mean
            assert abs(net_delta - gross_delta - saving) < 1e-12
            decomposition.append({"period": period, "factor": factor, "net_change_annual": net_delta,
                                  "gross_actual_change_annual": gross_delta, "fee_saving_annual": saving})
    pd.DataFrame(decomposition).to_csv(OUT / "partial_rebalance_decomposition.csv", index=False, float_format="%.12g")
    comparison = []
    for period, (start, end) in PERIODS.items():
        left = accounts["PATH_LS_c0"]["return"].loc[start:end]
        right = accounts["REV_LS_c0"]["return"].loc[start:end]
        if len(left) < 100:
            continue
        comparison.append({"period": period, "path_sharpe": performance(left)["sharpe"],
                           "rev_sharpe": performance(right)["sharpe"],
                           **block_sharpe_difference(left, right)})
    pd.DataFrame(comparison).to_csv(OUT / "gross_spread_sharpe_bootstrap.csv", index=False, float_format="%.12g")
    manifest.update(status="complete", seconds=time.time()-started, original_account_checks=checks)
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Execution extension complete.", flush=True)


if __name__ == "__main__":
    main()
