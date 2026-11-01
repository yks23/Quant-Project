"""Check deck claims and preservation against versioned research artifacts."""

from pathlib import Path
import hashlib
import json
import re
import subprocess

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
BASE = "46f31ae4b6e84977c1ad4941258c52660ff79321"


def main():
    text = (ROOT / "slides/quant-study.md").read_text()
    assert not re.search(r"\{\{|TODO|TBD", text)
    assert not re.search(r"^(header|footer):|<!-- _(header|footer):", text, re.M)
    visible = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    assert not re.search(r"\[[1-6](?:[–-][1-6])?\]|# 问题来源与可复核材料|# 从每项主张回到代码和结果", visible)
    alpha = pd.read_csv(ROOT / "study/results/alpha_local_proxy.csv")
    group_alpha = alpha[alpha.period.eq("holdout") & alpha.portfolio.str.match(r"(PATH|BREADTH)_Q[1-5]_c10$")]
    appendix = text.split("# Q1–Q5 的三模型年化 Alpha")[1].split("\n---")[0]
    for account, rows in group_alpha.groupby("portfolio"):
        factor, group, _ = account.split("_")
        row = next(line for line in appendix.splitlines() if line.startswith(f"| {factor} {group} |"))
        values = [float(cell.strip().replace("−", "-").replace("%", "")) for cell in row.split("|")[2:5]]
        expected = rows.set_index("model").loc[["CAPM", "FF3", "Carhart4"], "alpha_annual"]
        assert all(abs(actual - round(want * 100, 2)) < 1e-9 for actual, want in zip(values, expected)), account

    perf = pd.read_csv(ROOT / "study/results/performance.csv")
    core = text.split("# 两个正 Alpha 主假设均未获支持")[1].split("\n---")[0]
    for factor in ["PATH", "BREADTH"]:
        for cost in [0, 10]:
            row = perf[perf.period.eq("holdout") & perf.portfolio.eq(f"{factor}_LS_c{cost}")].iloc[0]
            value = f"{row.annual_mean * 100:.2f}%".replace("-", "−")
            assert value in core, value
        row = alpha[alpha.period.eq("holdout") & alpha.portfolio.eq(f"{factor}_LS_c10") & alpha.model.eq("Carhart4")].iloc[0]
        assert f"{row.p_holm_two_primary:.3f}" in core

    pdf = PdfReader(ROOT / "slides/dist/quant-study.pdf")
    pages = [page.extract_text() for page in pdf.pages]
    assert len(pages) == 29
    assert all(len(page) >= 70 for page in pages), [len(page) for page in pages]
    assert len(pdf.outline) >= 29
    assert "同样的跌幅" in pages[0]
    assert "12.45" in pages[15] and "2.91" in pages[15]
    assert "RECENT" in pages[18] and "SYNC" in pages[18]
    joined = "\n".join(pages)
    assert "Quant-Project" not in joined
    assert "SHA-256" not in joined

    tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
    preserved = []
    for name in tracked:
        if (name.endswith(".py") or name.startswith(("config/", "reports/")) or
            name.endswith(".csv") or name in ["PROTOCOL.md", "PROXY_MODELS.md", "EXPLORATION_PROTOCOL.md", "EXECUTION_EXTENSION.md"]):
            old = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
            new = (ROOT / "study" / name).read_bytes()
            assert old == new, f"Research artifact changed during move: {name}"
            preserved.append(name)
    result = {"slides": len(pdf.pages), "bookmarks": len(pdf.outline), "group_alpha_cells_verified": 30,
              "no_running_headers_footers_or_inline_reference_numbers": True,
              "headline_returns_and_primary_p": "passed", "original_artifacts_byte_identical": len(preserved),
              "baseline_commit": BASE, "pdf_sha256": hashlib.sha256((ROOT / "slides/dist/quant-study.pdf").read_bytes()).hexdigest()}
    (ROOT / "slides/qa/content.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
