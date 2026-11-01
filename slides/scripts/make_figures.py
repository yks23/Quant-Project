"""Redraw presentation figures from frozen aggregate evidence; never rerun trades."""

from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "study"
OUT = ROOT / "slides/assets"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "slides/.build/mpl"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

GREEN, RED, GREY = "#20594f", "#813c44", "#6f7772"
INPUTS = {}
OUTPUTS = {}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name, **kwargs):
    path = STUDY / "results" / name
    INPUTS[str(path.relative_to(ROOT))] = digest(path)
    return pd.read_csv(path, **kwargs)


def save(fig, name, note):
    fig.tight_layout(pad=1.1)
    path = OUT / f"{name}.svg"
    fig.savefig(path, facecolor="white", metadata={"Date": None, "Description": note})
    plt.close(fig)
    OUTPUTS[str(path.relative_to(ROOT))] = {"sha256": digest(path), "description": note}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads((STUDY / "config/integrated_report_snapshot.json").read_text())
    for name, expected in snapshot["evidence_sha256"].items():
        if digest(STUDY / name) != expected:
            raise ValueError(f"Frozen evidence changed: {name}")
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 15,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#bac3bd", "axes.labelcolor": "#202422",
        "xtick.color": "#3f4942", "ytick.color": "#3f4942",
        "axes.grid": True, "grid.color": "#e4e9e5", "grid.linewidth": .7,
        "axes.axisbelow": True, "svg.fonttype": "path", "svg.hashsalt": "quant-lecture-v1",
        "legend.frameon": False,
    })

    fig, ax = plt.subplots(figsize=(11.6, 3.7))
    for values, label, color, style in [
        ([-5, 0, 0, 0, 0], "A: early shock", GREEN, "-"),
        ([0, 0, 0, 0, -5], "B: recent shock", RED, "--"),
        ([-1, -1, -1, -1, -1], "C: gradual decline", GREY, "-."),
    ]:
        cumulative = np.r_[0, np.cumsum(values)]
        ax.plot(range(6), cumulative, marker="o", lw=2.5, label=label, color=color, ls=style)
    ax.set(xticks=range(6), xlabel="Trading day", ylabel="Cumulative log return (%)", ylim=(-5.7, .4))
    ax.legend(loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0), fontsize=14)
    save(fig, "motivation", "Constructed illustration only; all three paths sum to -5% log return.")

    perf = read("performance.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 3.8), sharey=True)
    for ax, factor, color in zip(axes, ["PATH", "BREADTH"], [GREEN, RED]):
        selected = perf[perf.period.eq("holdout")].set_index("portfolio")
        values = selected.loc[[f"{factor}_Q{q}_c10" for q in range(1, 6)], "annual_excess"] * 100
        ax.bar(range(1, 6), values, color=color, width=.6)
        ax.axhline(0, color="#202422", lw=1)
        for q, y in enumerate(values, 1):
            ax.text(q, y + (1 if y >= 0 else -1.4), f"{y:.1f}", ha="center", va="bottom" if y >= 0 else "top", fontsize=13)
        ax.set(xticks=range(1, 6), xticklabels=[f"Q{q}" for q in range(1, 6)], title=factor, ylim=(-26, 8))
    axes[0].set_ylabel("Annual mean above RF (%)")
    save(fig, "quintiles", "2022-2024 Q1-Q5 long-only accounts; 10 bp one-way; excess above assumed RF, not alpha.")

    daily = read("daily_portfolio_returns.csv", index_col=0, parse_dates=True)
    index = read("market_reference_returns.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 3.8))
    series = [(daily["PATH_LS_c10"], "PATH LS", GREEN, "-"),
              (daily["BREADTH_LS_c10"], "BREADTH LS", RED, "-"),
              (daily["REV_LS_c10"], "REV LS", "#496e90", "--"),
              (daily["EW_c10"], "EW long", GREY, "-."),
              (index.iloc[:, 0].reindex(daily.index), "CSI300 price", "#a88b46", ":")]
    for values, label, color, style in series:
        if values.isna().any():
            raise ValueError(f"Missing aligned daily values for {label}")
        nav = (1 + values).cumprod()
        drawdown = nav / nav.cummax().clip(lower=1) - 1
        axes[0].plot(nav.index, nav - 1, lw=1.8, label=label, color=color, ls=style)
        axes[1].plot(drawdown.index, drawdown, lw=1.5, color=color, ls=style)
    axes[0].set_ylabel("Cumulative return")
    axes[1].set_ylabel("Drawdown")
    for ax in axes:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.tick_params(axis="x", labelsize=12)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=5, fontsize=12, bbox_to_anchor=(.5, 1.02))
    fig.subplots_adjust(top=.8)
    save(fig, "returns", "2015-04-01 to 2024-12-31; synthetic LS and EW at 10 bp; CSI300 price index has no fees/dividends. Exposures differ.")

    cost = read("exploration/original_cost_waterfall.csv").set_index("factor").loc["PATH"]
    deltas = np.array([cost.gross_zero_cost_mean_annual, -cost.long_fee_annual,
                       -cost.short_fee_annual, -cost.position_path_effect_annual]) * 100
    levels = np.cumsum(deltas)
    assert np.isclose(levels[-1], cost.net_mean_annual * 100, atol=1e-8)
    fig, ax = plt.subplots(figsize=(11.6, 3.8))
    for i, delta in enumerate(deltas):
        start = 0 if i == 0 else levels[i - 1]
        ax.bar(i, abs(delta), bottom=min(start, start + delta), color=GREEN if delta > 0 else RED, width=.57)
        ax.text(i, max(start, start + delta) + .6, f"{delta:+.4f}", ha="center", fontsize=16)
        if i < 3:
            ax.plot([i + .285, i + .715], [levels[i], levels[i]], color=GREY, lw=1, ls=":")
    ax.bar(4, abs(levels[-1]), bottom=min(0, levels[-1]), color="#323c36", width=.57)
    ax.text(4, .6, f"{levels[-1]:+.4f}", ha="center", fontsize=16)
    ax.set(xticks=range(5), xticklabels=["Gross", "Long fees", "Short fees", "Path effect", "Net"], ylabel="Annual mean / percentage points", ylim=(-5, 16))
    ax.axhline(0, color="#202422", lw=1)
    save(fig, "cost-waterfall", "Exact PATH 2022-2024 arithmetic-mean decomposition, not CAGR. Fees use actual traded notional.")

    coeff = read("exploration/coefficient_summary.csv")
    strong = coeff[coeff.period.eq("reused_2022_2024") & coeff.control.eq("strong")]
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 3.8), sharey=True)
    for ax, horizon, title in zip(axes, ["gap", "d5"], ["Before entry: overnight gap", "After entry: 5 days"]):
        values = strong[strong.horizon.eq(horizon)].set_index("feature").loc[["C", "RECENT", "SYNC"]]
        means = values["mean"].to_numpy() * 1e4
        se = np.abs(means / values.t.to_numpy())
        ax.errorbar(means, np.arange(3), xerr=1.96 * se, fmt="o", ms=8, color=GREEN, capsize=5, lw=2)
        ax.axvline(0, color=GREY, ls="--", lw=1)
        ax.set(yticks=range(3), yticklabels=["C", "RECENT", "SYNC"], title=title, xlabel="Log-return bp / SD")
        ax.set_ylim(2.5, -.5)
    save(fig, "timing", "Reused 2022-2024 exploratory sample; strong controls; individual 95% HAC intervals. See Holm-adjusted tests separately.")

    pred = read("exploration/prediction_summary.csv")
    fig, ax = plt.subplots(figsize=(11.6, 3.8))
    x = np.arange(len(pred))
    ax.bar(x - .17, pred.baseline_ic, width=.32, label="Daily-return baseline", color=GREY)
    ax.bar(x + .17, pred.augmented_ic, width=.32, label="Baseline + C / RECENT / SYNC", color=GREEN)
    for offset, col in [(-.17, "baseline_ic"), (.17, "augmented_ic")]:
        for xx, yy in zip(x + offset, pred[col]):
            ax.text(xx, yy + .002, f"{yy:.4f}", ha="center", fontsize=13)
    ax.set(xticks=x, xticklabels=["2018-2020", "2021", "2022-2024", "2025 Jan-Apr"], ylabel="Mean rank IC", ylim=(0, .1))
    ax.legend(loc="upper center", ncol=2, fontsize=13)
    save(fig, "prediction", "Yearly frozen prediction; baseline vs enhanced rank IC. 2022-2024 is reused, 2025 has only 15 complete labels.")

    manifest = {"purpose": "Presentation-only redrawing; no new backtest", "inputs_sha256": INPUTS,
                "outputs": OUTPUTS, "generator_sha256": digest(__file__)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Created {len(OUTPUTS)} figures from {len(INPUTS)} frozen CSV files.")


if __name__ == "__main__":
    main()
