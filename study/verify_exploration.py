"""Check artifact provenance, accounting identities and temporal boundaries."""

from pathlib import Path
import json
import subprocess
import sys

import numpy as np
import pandas as pd
from pypdf import PdfReader

from src.data import sha256

ROOT = Path(__file__).resolve().parent
R = ROOT / "results/exploration"


def main():
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT, check=True)
    for filename, protocol in [("manifest.json", "EXPLORATION_PROTOCOL.md"),
                               ("execution_manifest.json", "EXECUTION_EXTENSION.md")]:
        data = json.loads((R / filename).read_text())
        assert data["status"] == "complete"
        assert data["protocol_sha256"] == sha256(ROOT / protocol)
        for file, digest in data["code_sha256"].items():
            assert sha256(ROOT / file) == digest, file
    report = json.loads((R / "report_manifest.json").read_text())
    assert report["builder_sha256"] == sha256(ROOT / "build_exploration_report.py")
    assert report["pdf_sha256"] == sha256(ROOT / "reports/mechanism_execution_supplement.pdf")
    assert sha256(ROOT / "reports/factor_study_report.pdf") == "21622d311788a8013a43ee76ee11fa8a32a50fb53849e60c536f2ba66401155d"
    p = pd.read_csv(R / "prediction_events.csv", parse_dates=["date", "label_end", "training_max_end"])
    year_start = p.date.dt.to_period("Y").dt.start_time
    assert p.training_max_end.lt(year_start).all()
    assert p.label_end.gt(p.date).all()
    coverage = pd.read_csv(R / "label_coverage.csv")
    assert coverage.observed_n.le(coverage.formed_n).all()
    coefficients = pd.read_csv(R / "coefficient_summary.csv")
    assert coefficients.loc[coefficients.period.eq("extension_2025"), "p"].isna().all()
    assert len(coefficients.loc[coefficients.period.eq("reused_2022_2024")]) == 24
    costs = pd.read_csv(R / "original_cost_waterfall.csv")
    expected = costs.gross_zero_cost_mean_annual - costs.long_fee_annual - costs.short_fee_annual - costs.position_path_effect_annual
    np.testing.assert_allclose(expected, costs.net_mean_annual, atol=1e-10)
    d = pd.read_csv(R / "partial_rebalance_decomposition.csv")
    np.testing.assert_allclose(d.gross_actual_change_annual + d.fee_saving_annual, d.net_change_annual, atol=1e-10)
    pdf = PdfReader(ROOT / "reports/mechanism_execution_supplement.pdf")
    assert len(pdf.pages) == 8 and len(pdf.outline) == 7
    assert all(len(page.extract_text()) > 200 for page in pdf.pages)
    text = "\n".join(page.extract_text() for page in pdf.pages)
    assert "1.48" in text and "-2.03" in text and "探索性" in text
    result = {"tests": 27, "pdf_pages": len(pdf.pages), "bookmarks": len(pdf.outline),
              "protocol_and_source_hashes": "passed", "original_pdf_unchanged": True,
              "temporal_boundaries": "passed", "accounting_identities": "passed",
              "pdf_sha256": report["pdf_sha256"],
              "visual_qa": "Separate manual review; automated checks do not verify layout."}
    (R / "verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
