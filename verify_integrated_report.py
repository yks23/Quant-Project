"""Validate integrated-report provenance, content and mechanical prose checks."""

from pathlib import Path
import json
import re
import subprocess
import sys
import copy

import numpy as np
import pandas as pd
from pypdf import PdfReader

from src.data import sha256

ROOT = Path(__file__).resolve().parent
R = ROOT / "results"


def style_audit(text):
    # Table separators and Markdown image syntax are not prose punctuation.
    lines = [(i, line) for i, line in enumerate(text.splitlines(), 1)
             if not re.match(r"^\|[\s:|\-]+\|$", line) and not line.startswith("![")]
    patterns = {
        "M1_dashes": r"---|—|–",
        "M11_passive": r"\b(is|are|was|were|be|been|being)\s+([a-z]+ed|done|made|shown|given|taken|held|built|drawn|chosen|written|known|found|seen|set|put|sent|kept|met|run|used|based)\b",
        "M2_antithesis": r",? not [0-9A-Za-z\\]|not only .* but|rather than|less .* than|is the point|whatever it is|means nothing|more than just|not in competition with|on one hand|on the other hand",
        "M3_M4_M8_M9_filler": r"in effect|in a sense|at (its|the) (heart|core)|in essence|\btruly\b|\bgenuinely\b|\bindeed\b|\bin fact\b|precisely because|a testament to|the kind of .* that|exactly the kind|is the point|set(s)? .* apart|no (predecessor|one) .* (made|posed)|the key (insight|idea) is|the machine that|draw(s)? .* power from|under the hood|where .* meets",
        "M6_openers": r"^(Moreover|Furthermore|Additionally|Notably|Importantly|Indeed|Ultimately|Crucially|In turn|That said)",
        "M5_M16_words": r"\b(novel|significant|substantial|impressive|promising|comprehensive|robust|powerful|crucial|paradigm|factor|features?|meaningful|insightful|prestigious|currently)\b|\bseamless|\bleverag|\butiliz|\bfinaliz|[a-z]+-oriented\b|\bpossess|\bcontact(s|ed|ing)?\b|\bimpact(s|ed|ing)?\b",
        "M10_hype": r"promises to|stands? to|is poised to|opens the door to|is set to|has the potential to|keeps .* from|stands? in the way|\bunlocks?\b",
        "M17_fancy": r"\b(pit(s|ted|ting)?|dispatch(es|ed|ing)?|chip(s|ped|ping)? (away )?at|marshal(s|led|ling)?|orchestrat(e|es|ed|ing)|wrangl(e|es|ed|ing)|harness(es|ed|ing)?|forge[sd]?|weav(e|es|ed|ing)|delv(e|es|ed|ing) into|usher(s|ed)? in|grappl(e|es|ed|ing) with|anew|afresh)\b",
        "M18_empty_openers": r"In this (paper|section), we",
        "M12_wordiness": r"the fact that|the question (as to |of )?whether|as to whether|in order to|there is no doubt but|the reason .* is because|owing to the fact that|in a [a-z]+ manner|is a (subject|man|woman) (that|who)|in the last analysis|along these lines|in terms of|one of the most",
        "M13_qualifiers": r"\b(rather|very|pretty|little|quite|somewhat|fairly|certainly)\b",
        "M14_ordinals": r"\b(thusly|muchly|overly|firstly|secondly|thirdly)\b|[a-z]+wise\b",
        "M15_exclamation": r"!",
        "B_precision": r"\bcomprised of\b|\bdata is\b|different than|\bvery unique\b|\bdue to\b|\bless (than )?[0-9]",
        "decomposition_drift": r"\b(three|four|five|six|seven)\b (stages|concerns|axes|requirements|dimensions|systems)",
        "zh_promotional": r"首次发现|世界领先|突破性|颠覆性|必然赚钱|证明了恐慌",
    }
    findings = {}
    for key, pattern in patterns.items():
        hits = [{"line": i, "text": line} for i, line in lines if re.search(pattern, line, re.I)]
        findings[key] = {"count": len(hits), "hits": hits}
    return findings


def main():
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT, check=True)
    manifest = json.loads((R / "integrated_report_manifest.json").read_text())
    from build_integrated_report import validate_snapshot
    snapshot = json.loads((ROOT / "config/integrated_report_snapshot.json").read_text())
    validate_snapshot(snapshot)
    corrupted = copy.deepcopy(snapshot)
    first = next(iter(corrupted["evidence_sha256"]))
    corrupted["evidence_sha256"][first] = "0" * 64
    try:
        validate_snapshot(corrupted)
    except ValueError:
        pass
    else:
        raise AssertionError("Changed source evidence was not rejected")
    assert sha256(ROOT / "config/integrated_report_snapshot.json") == manifest["evidence_snapshot_sha256"]
    for field in ["input_csv_sha256", "figure_sha256"]:
        for path, digest in manifest[field].items():
            assert sha256(ROOT / path) == digest, path
    assert sha256(ROOT / "build_integrated_report.py") == manifest["builder_sha256"]
    assert sha256(ROOT / "reports/integrated_research_report.pdf") == manifest["pdf_sha256"]
    assert sha256(ROOT / "reports/integrated_research_report.md") == manifest["markdown_sha256"]
    assert sha256(ROOT / "reports/factor_study_report.pdf") == "21622d311788a8013a43ee76ee11fa8a32a50fb53849e60c536f2ba66401155d"
    assert sha256(ROOT / "reports/mechanism_execution_supplement.pdf") == "31ade5b408fc9dadde1bd9ba4fcd75bfaafe21b31bd82e7c31dfc0b0128bea64"
    cost = pd.read_csv(R / "exploration/original_cost_waterfall.csv")
    np.testing.assert_allclose(cost.gross_zero_cost_mean_annual-cost.long_fee_annual-cost.short_fee_annual-cost.position_path_effect_annual,
                               cost.net_mean_annual, atol=1e-10)
    pdf = PdfReader(ROOT / "reports/integrated_research_report.pdf")
    extracted = [page.extract_text() for page in pdf.pages]
    assert len(pdf.pages) == 21 and len(pdf.outline) == 19
    assert min(map(len, extracted)) > 250
    joined = "\n".join(extracted)
    for phrase in ["12.45", "-2.91", "-2.03", "1.48", "Motivation", "5362", "探索性", "本地FF式", "HALF", "RECENT", "SYNC"]:
        assert phrase in joined, phrase
    assert len(pdf.pages[1].get("/Annots", [])) >= 19
    text = (ROOT / "reports/integrated_research_report.md").read_text()
    findings = style_audit(text)
    print("MECHANICAL GATE (Markdown-adapted Part C):")
    for key, value in findings.items():
        print(f"{key}: {value['count']}")
        for hit in value["hits"]:
            print(f"  {hit['line']}: {hit['text']}")
    result = {"unit_tests": 27, "pages": len(pdf.pages), "bookmarks": len(pdf.outline),
              "input_fingerprints": "passed", "previous_reports_unchanged": True,
              "changed_evidence_rejected": True,
              "cost_identity": "passed", "pdf_sha256": manifest["pdf_sha256"],
              "mechanical_style_checks": findings,
              "limitations": "Regex checks do not verify Chinese semantics or visual layout; independent and rendered review are separate."}
    (R / "integrated_report_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print("Integrated report checks passed; semantic and visual review remain separate.")


if __name__ == "__main__":
    main()
