# Integrated report verification

Reviewed edition: 2026-11-01. This edition integrates existing evidence; it does not change or rerun the research backtests.

## Reproducibility

- `python build_integrated_report.py` generates the PDF, Markdown, one new figure, and source manifest.
- `python verify_integrated_report.py` passed all 27 unit tests, the cost identity, source/output fingerprints, and previous-report preservation checks.
- The PDF contains 21 pages and 19 section bookmarks. Text extraction and the clickable contents-page annotation checks passed.
- `config/integrated_report_snapshot.json` locks 37 evidence files. The builder rejects changed evidence before generating output. The independent reviewer tested all 37 digest mismatches in memory and confirmed rejection for each.
- Original PDFs `factor_study_report.pdf` and `mechanism_execution_supplement.pdf` retain their original SHA-256 hashes.
- Machine-readable records: `results/integrated_report_manifest.json` and `results/integrated_report_verification.json`.

## Independent review

The initial read-only review checked 148 table cells against source results, recomputed five daily-series means/CAGRs and 24 HAC/Holm tests, inspected training cutoffs for 354 prediction records, and ran the 27 tests. It identified two major and three minor issues. All five were addressed:

1. Distinguished the first-round simple-return event label and its estimation sample from the second-round log-return labels.
2. Bound static narrative and generated tables to a single immutable evidence snapshot.
3. Defined portfolio ordering, Amihud, and the short-leg fee denominator at first relevant use.
4. Clarified that the approximately 153-times annual traded notional sums two independently NAV-normalized legs.
5. Revised two unnecessary passive constructions.

The final read-only closure review reported zero critical, major, or minor findings. It retained the exploratory status of round two, the short 2025 extension, local risk-factor proxy qualifications, entry-timing distinctions, and synthetic-short limitations. This closure was a text/source review, not another full backtest run or PDF visual review.

## Writing and visual checks

The verification script's 16 mechanical pattern categories had zero hits after excluding Markdown table separators and image syntax. Independent checking found two `PIT` abbreviation false positives and no unresolved writing findings. These checks do not prove semantic correctness.

All 21 rendered pages were inspected in contact sheets, with full-resolution inspections of the motivation, factor definition, execution, quintile results, and prediction/execution pages. After final revisions, pages 7, 9, 17, and 21 were inspected again at full resolution. No clipped text or incoherent overlap was observed. Chinese text is searchable and copyable, and the Chinese font is embedded. The PDF's unused default Helvetica resource is not embedded.

Local render previews live under ignored `outputs/integrated_qa/`; the delivered PDF and its reproducible source are versioned.
