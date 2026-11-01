"""Run the fixed second-round diagnostics without changing original results."""

from pathlib import Path
import json
import math
import subprocess
import time

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from src.data import sha256
from src.mechanisms import (FEATURES, loss_geometry, leave_one_out_breadth,
                            standardized, conditional_groups, period_mask,
                            past_training_rows)
from src.statistics import hac_mean

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/exploration"
PERIODS = {
    "development": ("2015-04-01", "2020-12-31"),
    "validation_reused": ("2021-01-01", "2021-12-31"),
    "reused_2022_2024": ("2022-01-01", "2024-12-31"),
    "extension_2025": ("2025-01-01", "2025-04-30"),
}
WEAK = ["R5", "RET0", "vol20", "size", "price", "illiquidity"]
STRONG = [f"RET{i}" for i in range(5)] + ["vol20", "size", "price", "illiquidity"]
HORIZONS = {"gap": 0, "d1": 1, "d5": 5, "d20": 20}


def save(frame, filename):
    frame.to_csv(OUT / filename, index=False, float_format="%.12g")


def summarize(coefficients, groups, predictions):
    rows = []
    for period, (start, end) in PERIODS.items():
        part = coefficients.loc[period_mask(coefficients, start, end)]
        for (control, horizon), group in part.groupby(["control", "horizon"]):
            for variable in FEATURES:
                test = hac_mean(group[variable], max(2, math.ceil(HORIZONS[horizon] / 5)))
                rows.append({"period": period, "control": control, "horizon": horizon,
                             "feature": variable, **test})
    summary = pd.DataFrame(rows)
    summary["p_holm_main3"] = np.nan
    summary["p_holm_all24"] = np.nan
    for period in PERIODS:
        main = (summary.period.eq(period) & summary.control.eq("strong") &
                summary.horizon.eq("d5") & summary.p.notna())
        all_tests = summary.period.eq(period) & summary.p.notna()
        for mask, field in [(main, "p_holm_main3"), (all_tests, "p_holm_all24")]:
            if mask.any():
                summary.loc[mask, field] = multipletests(summary.loc[mask, "p"], method="holm")[1]
    save(summary, "coefficient_summary.csv")
    matched = []
    spreads = []
    for period, (start, end) in PERIODS.items():
        part = groups.loc[period_mask(groups, start, end)]
        for (feature, horizon, quintile), g in part.groupby(["feature", "horizon", "quintile"]):
            matched.append({"period": period, "feature": feature, "horizon": horizon,
                            "quintile": quintile, **hac_mean(g.mean_log_return, 4 if horizon == "d20" else 2),
                            "formed_n": int(g.formed_n.sum()), "observed_n": int(g.observed_n.sum()),
                            "mean_R5": g.mean_R5.mean(), "mean_raw_feature": g.mean_raw_feature.mean()})
        for (feature, horizon), g in part.groupby(["feature", "horizon"]):
            pivot = g.pivot(index="date", columns="quintile", values="mean_log_return")
            spreads.append({"period": period, "feature": feature, "horizon": horizon,
                            **hac_mean(pivot[5] - pivot[1], 4 if horizon == "d20" else 2)})
    save(pd.DataFrame(matched), "matched_quintiles.csv")
    spread = pd.DataFrame(spreads)
    spread["p_holm_all12"] = np.nan
    for period in PERIODS:
        mask = spread.period.eq(period) & spread.p.notna()
        if mask.any():
            spread.loc[mask, "p_holm_all12"] = multipletests(spread.loc[mask, "p"], method="holm")[1]
    save(spread, "matched_spreads.csv")
    stats = []
    for period, (start, end) in PERIODS.items():
        p = predictions.loc[period_mask(predictions, start, end)]
        if p.empty:
            continue
        delta = p.ic_augmented - p.ic_baseline
        stats.append({"period": period, "baseline_ic": p.ic_baseline.mean(),
                      "augmented_ic": p.ic_augmented.mean(),
                      "ic_difference": delta.mean(), **hac_mean(delta, 2),
                      "relative_mse_reduction": 1 - p.mse_augmented.mean() / p.mse_baseline.mean(),
                      "training_max_end": str(p.training_max_end.max())})
    save(pd.DataFrame(stats), "prediction_summary.csv")


def cost_waterfall():
    rows = []
    daily = pd.read_csv(ROOT / "results/daily_portfolio_returns.csv", index_col=0, parse_dates=True)
    for factor in ["PATH", "BREADTH"]:
        legs = [pd.read_parquet(ROOT / f"data/processed/{factor}_Q{q}_c10_account.parquet").loc["2022":"2024"]
                for q in [1, 5]]
        short, long = legs
        zero = daily.loc["2022":"2024", f"{factor}_LS_c0"]
        net = long["return"] - short["return"] - 2 * short.fees
        gross_actual = long["return"] + long.fees - short["return"] - short.fees
        error = (gross_actual - net - long.fees - short.fees).abs().max()
        assert error < 1e-12
        rows.append({"factor": factor, "gross_zero_cost_mean_annual": zero.mean() * 252,
                     "long_fee_annual": long.fees.mean() * 252,
                     "short_fee_annual": short.fees.mean() * 252,
                     "position_path_effect_annual": (zero - gross_actual).mean() * 252,
                     "net_mean_annual": net.mean() * 252, "max_identity_error": error,
                     "fixed_position_break_even_bps": gross_actual.mean() / (long.fees + short.fees).mean() * 10})
    save(pd.DataFrame(rows), "original_cost_waterfall.csv")


def main():
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/extracted/fire_data"
    symbols = pd.read_parquet(ROOT / "data/processed/PATH_formation_scores.parquet").columns
    fields = ["close", "open", "volume", "money", "market_cap_ashare", "close_dr"]
    manifest = {
        "status": "running", "protocol_date": "2026-11-01", "protocol_sha256": sha256(ROOT / "EXPLORATION_PROTOCOL.md"),
        "code_sha256": {f: sha256(ROOT / f) for f in ["run_mechanisms.py", "src/mechanisms.py"]},
        "parent_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_sha256": {f: sha256(source / f"{f}.feather") for f in fields},
        "status_of_old_holdout": "reused; exploratory only",
        "event_returns": "log price labels, not executable strategy returns; no transaction costs",
        "inference_min_dates": 20, "periods": PERIODS,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    panels = {}
    for field in fields:
        frame = pd.read_feather(source / f"{field}.feather").loc[:, symbols].astype("float32")
        frame.index = pd.to_datetime(frame.index)
        panels[field] = frame.sort_index()
    close = panels["close"].where(panels["close"] > 0)
    opening = panels["open"].where(panels["open"] > 0)
    ret = np.log(close / close.shift(1))
    warm = close.notna().cumsum().ge(60)
    active = panels["volume"].gt(0) & close.notna() & ret.notna()
    vol = ret.rolling(20, min_periods=20).std()
    illiq = (ret.abs() / panels["money"].where(panels["money"] > 0)).rolling(20).mean()
    dates = close.index
    assert dates[-1] == pd.Timestamp("2025-04-30")
    first = int(dates.searchsorted("2015-04-01"))
    coefficients, group_rows, coverage, predictions = [], [], [], []
    training_base, training_aug = [], []
    frozen = {}
    forming = list(range(first, len(dates) - 1, 5))
    print(f"Fixed diagnostics: {len(forming)} formation dates, {len(symbols)} columns", flush=True)
    for step, t in enumerate(forming):
        r = ret.iloc[t-4:t+1].to_numpy(dtype=float)
        a = active.iloc[t-4:t+1].to_numpy()
        geometry = loss_geometry(r, leave_one_out_breadth(r, a))
        r5 = r.sum(axis=0)
        eligible = a.all(axis=0) & warm.iloc[t].to_numpy() & (r5 < 0)
        x = pd.DataFrame({"R5": r5, **{f"RET{i}": r[-i-1] for i in range(5)},
                          "vol20": vol.iloc[t].to_numpy(),
                          "size": np.log(panels["market_cap_ashare"].iloc[t].where(lambda s: s > 0)).to_numpy(),
                          "price": np.log(panels["close_dr"].iloc[t].where(lambda s: s > 0)).to_numpy(),
                          "illiquidity": illiq.iloc[t].to_numpy(), **geometry}, index=symbols)
        x = x.loc[eligible].replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) < 100:
            continue
        z = standardized(x)
        sorter = {}
        for feature in FEATURES:
            controls = z[STRONG + [f for f in FEATURES if f != feature]]
            sorter[feature] = conditional_groups(z[feature], controls, x.R5)
        for horizon, days in HORIZONS.items():
            end_idx = t + 1 + days
            if end_idx >= len(dates):
                continue
            numerator = opening.iloc[end_idx]
            denominator = close.iloc[t] if horizon == "gap" else opening.iloc[t+1]
            y = np.log(numerator / denominator).reindex(x.index).replace([np.inf, -np.inf], np.nan)
            valid = y.notna()
            end_date = dates[end_idx]
            coverage.append({"date": dates[t], "label_end": end_date, "horizon": horizon,
                             "formed_n": len(x), "observed_n": int(valid.sum()),
                             "tradable_entry_n": int(panels["volume"].iloc[t+1].reindex(x.index).gt(0).sum())})
            if valid.sum() < 100:
                continue
            for control, columns in [("weak", WEAK), ("strong", STRONG)]:
                names = columns + FEATURES
                design = np.column_stack([np.ones(valid.sum()), z.loc[valid, names].to_numpy()])
                beta, _, rank, _ = np.linalg.lstsq(design, y[valid], rcond=None)
                if rank != len(names) + 1:
                    raise ValueError(f"Rank deficient design on {dates[t]} {control}")
                row = {"date": dates[t], "label_end": end_date, "control": control,
                       "horizon": horizon, "n": int(valid.sum()),
                       **dict(zip(["const"] + names, beta))}
                coefficients.append(row)
                if control == "strong" and horizon == "d5":
                    year = dates[t].year
                    if year not in frozen:
                        history_aug = pd.DataFrame(training_aug)
                        history_base = pd.DataFrame(training_base)
                        if len(history_aug):
                            ha = past_training_rows(history_aug, year)
                            hb = past_training_rows(history_base, year)
                            if len(ha) >= 100:
                                frozen[year] = (hb[STRONG].mean(), ha[names].mean(),
                                                ha.label_end.max(), len(ha))
                    if year in frozen:
                        b0, b1, max_end, ntrain = frozen[year]
                        assert max_end < pd.Timestamp(year=year, month=1, day=1)
                        pred0 = z.loc[valid, STRONG] @ b0
                        pred1 = z.loc[valid, names] @ b1
                        yy = y[valid] - y[valid].mean()
                        predictions.append({"date": dates[t], "label_end": end_date,
                                            "training_max_end": max_end, "training_dates": ntrain,
                                            "ic_baseline": pred0.corr(y[valid], method="spearman"),
                                            "ic_augmented": pred1.corr(y[valid], method="spearman"),
                                            "mse_baseline": ((yy - (pred0 - pred0.mean())) ** 2).mean(),
                                            "mse_augmented": ((yy - (pred1 - pred1.mean())) ** 2).mean()})
                    training_aug.append(row)
                    base_design = np.column_stack([np.ones(valid.sum()), z.loc[valid, STRONG].to_numpy()])
                    base_beta = np.linalg.lstsq(base_design, y[valid], rcond=None)[0]
                    training_base.append({"date": dates[t], "label_end": end_date,
                                          **dict(zip(["const"] + STRONG, base_beta))})
            for feature in FEATURES:
                strata, quintiles, _ = sorter[feature]
                frame = pd.DataFrame({"stratum": strata, "quintile": quintiles,
                                      "y": y, "R5": x.R5, "raw": x[feature]})
                for q in range(1, 6):
                    cell = frame.loc[frame.quintile.eq(q)]
                    means = cell.groupby("stratum").y.mean()
                    # All ten R5 strata must be represented for a comparable spread.
                    value = means.mean() if means.notna().sum() == 10 else np.nan
                    group_rows.append({"date": dates[t], "label_end": end_date,
                                       "feature": feature, "horizon": horizon, "quintile": q,
                                       "mean_log_return": value, "formed_n": len(cell),
                                       "observed_n": int(cell.y.notna().sum()),
                                       "mean_R5": cell.groupby("stratum").R5.mean().mean(),
                                       "mean_raw_feature": cell.groupby("stratum").raw.mean().mean()})
        if step % 50 == 0:
            print(f"{dates[t].date()}: {len(x)} formed losers; {time.time()-started:.1f}s", flush=True)
    coefs = pd.DataFrame(coefficients)
    groups = pd.DataFrame(group_rows)
    pred = pd.DataFrame(predictions)
    save(coefs, "date_coefficients.csv")
    save(groups, "matched_events.csv")
    save(pd.DataFrame(coverage), "label_coverage.csv")
    save(pred, "prediction_events.csv")
    summarize(coefs, groups, pred)
    cost_waterfall()
    manifest.update(status="complete", seconds=time.time() - started,
                    formation_dates=int(coefs.date.nunique()), n_symbols=len(symbols),
                    first=str(coefs.date.min().date()), last=str(coefs.date.max().date()))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Diagnostics complete; original results unchanged.", flush=True)


if __name__ == "__main__":
    main()
