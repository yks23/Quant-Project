"""Verify the reproducible delivery, including selectable Chinese PDF text."""

from pathlib import Path
import json
import subprocess
import sys
import numpy as np
import pandas as pd
from pypdf import PdfReader
from src.data import sha256

ROOT=Path(__file__).resolve().parent


def main():
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                         cwd=ROOT,text=True,capture_output=True)
    log=tests.stdout+tests.stderr
    (ROOT/'results/unit_tests.txt').write_text(log)
    if tests.returncode:
        raise RuntimeError(log)
    daily=pd.read_csv(ROOT/'results/daily_portfolio_returns.csv',index_col=0)
    alpha=pd.read_csv(ROOT/'results/alpha_local_proxy.csv')
    primary=alpha[(alpha.period=='holdout')&(alpha.model=='Carhart4') &
                  alpha.portfolio.isin(['PATH_LS_c10','BREADTH_LS_c10'])]
    accounts=pd.read_csv(ROOT/'results/account_reconciliation.csv')
    reader=PdfReader(ROOT/'reports/factor_study_report.pdf')
    pages=[p.extract_text() for p in reader.pages]
    manifest=json.loads((ROOT/'results/report_build_manifest.json').read_text())
    checks={
        'unit_tests_pass':True,
        'unit_test_count':log.count(' ... ok'),
        'finite_daily_returns':bool(np.isfinite(daily.to_numpy()).all()),
        'daily_return_rows':len(daily),'portfolio_series':len(daily.columns),
        'cash_account_reconciliations':len(accounts),
        'all_accounts_reconcile':bool(accounts.passed.all()),
        'three_models_present':set(alpha.model)=={'CAPM','FF3','Carhart4'},
        'two_primary_holm_tests':len(primary)==2 and bool(primary.p_holm_two_primary.notna().all()),
        'pdf_pages':len(pages),'pdf_bookmarks':len(reader.outline),
        'all_pdf_pages_have_text':all(len(p)>100 for p in pages),
        'selectable_chinese_text':all(word in ''.join(pages) for word in ['路径','广度','沪深300','资产定价']),
        'pdf_hash_matches':sha256(ROOT/'reports/factor_study_report.pdf')==manifest['pdf_sha256'],
        'markdown_hash_matches':sha256(ROOT/'reports/factor_study_report.md')==manifest['markdown_sha256'],
        'visual_review':'Separate manual rendering review recorded in reports/QA.md; not an automated visual check',
        'scope':'Local FF-style model proxies, public observable universe; no official-factor or tradability certification',
    }
    if not all(v for v in checks.values() if isinstance(v,bool)):
        raise RuntimeError(checks)
    (ROOT/'results/verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
