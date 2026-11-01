"""Prespecified auxiliary summaries, without modifying positions or signal signs."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from src.statistics import hac_mean, model_alpha
from src.risk import monthly

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'


def main():
    events = pd.read_csv(OUT/'double_sort_events.csv', parse_dates=['date'])
    coef = pd.read_csv(OUT/'cross_sectional_coefficients.csv', parse_dates=['date'])
    state = pd.read_csv(OUT/'breadth_state_events.csv', parse_dates=['date']).set_index('date')
    groups, spreads, regressions, conditions = [], [], [], []
    for period, start, end in [('full','2015-04-01','2024-12-31'),
                               ('holdout','2022-01-01','2024-12-31')]:
        e = events[events.date.between(start,end)]
        for key,g in e.groupby(['factor','control','control_group','quintile']):
            groups.append(dict(zip(['factor','control','control_group','quintile'],key),
                               period=period,**hac_mean(g.mean_forward_5d,2),
                               formed=int(g.formed_n.sum()),observed=int(g.observed_n.sum())))
        for key,g in e.groupby(['factor','control','control_group']):
            p=g.pivot(index='date',columns='quintile',values='mean_forward_5d')
            spreads.append(dict(zip(['factor','control','control_group'],key),
                                period=period,**hac_mean(p[5]-p[1],2)))
        c=coef[coef.date.between(start,end)]
        for variable in c.columns.drop(['date','n']):
            regressions.append({'period':period,'variable':variable,**hac_mean(c[variable],2)})
        s=state.loc[start:end]
        fit=sm.OLS(s.reversal_spread,sm.add_constant(s[['breadth','market_r5','market_vol20']])).fit(
            cov_type='HAC',cov_kwds={'maxlags':2,'use_correction':True})
        conditions.extend([{'period':period,'variable':v,'mean':fit.params[v],
                            't':fit.tvalues[v],'p':fit.pvalues[v],'n':len(s)} for v in fit.params.index])
    for rows,filename in [(groups,'double_sort_by_period'),(spreads,'double_sort_spreads_by_period'),
                           (regressions,'incremental_by_period'),(conditions,'breadth_by_period')]:
        pd.DataFrame(rows).to_csv(OUT/f'{filename}.csv',index=False)
    daily=pd.read_csv(OUT/'daily_portfolio_returns.csv',index_col=0,parse_dates=True)
    risk=pd.read_csv(OUT/'risk_factors_local_daily.csv',index_col=0,parse_dates=True)
    absolute_market=risk.MKT+risk.RF
    sens=[]
    for rf in [0,.015,.03]:
        f=risk.copy()
        f['RF']=(1+rf)**(1/252)-1
        f['MKT']=absolute_market-f.RF
        fm=monthly(f)
        for name in ['PATH_LS_c10','BREADTH_LS_c10','PATH_Q5_c10','BREADTH_Q5_c10']:
            y=monthly(daily[[name]])[name].loc['2022-01':'2024-12']
            for result in model_alpha(y,fm,long_short='_LS_' in name):
                sens.append({'rf_assumption':rf,'portfolio':name,**result})
    pd.DataFrame(sens).to_csv(OUT/'rf_sensitivity.csv',index=False)
    fields=pd.read_csv(OUT/'data_fields.csv')
    coverage=pd.read_csv(OUT/'coverage_daily.csv',index_col=0,parse_dates=True)
    signal=pd.read_csv(OUT/'signal_audit.csv',index_col=0,parse_dates=True)
    audit=json.loads((OUT/'data_audit.json').read_text())
    diagnostics=pd.read_csv(OUT/'execution_diagnostics.csv')
    account=pd.read_parquet(ROOT/'data/processed/PATH_Q5_c10_account.parquet')
    active_days=account.index[account.holdings>0]
    tests={
        'all_portfolio_returns_finite':bool(np.isfinite(daily.to_numpy()).all()),
        'no_portfolio_day_loses_more_than_100pct':bool((daily>-1).all().all()),
        'no_duplicate_dates':not daily.index.has_duplicates,
        'no_negative_average_cash':bool((diagnostics.cash_weight>=-1e-8).all()),
        'matching_fields':bool(fields.dates.nunique()==1 and fields.ashare_columns.nunique()==1),
        'max_stale_weight':float(diagnostics.max_stale_weight.max()),
        'eligible_at_first_date':int(signal.loc[daily.index[0],'eligible_n']),
        'eligible_at_last_date':int(signal.loc[daily.index[-1],'eligible_n']),
        'trade_days':len(daily),'first_signal_date':str(daily.index[0].date()),
        'first_possible_entry_date':str(daily.index[1].date()),
        'first_positive_eligible_date':str(signal.index[signal.eligible_n>0][0].date()),
        'first_actual_entry_date':str(active_days[0].date()),
        'last_valuation_date':str(daily.index[-1].date()),
        'breadth_above_half_fraction':float((signal.loc[daily.index,'breadth']>.5).mean()),
        'return_reconciliation_p99':audit['return_price_p99_abs_difference'],
    }
    if not all(tests[k] for k in ['all_portfolio_returns_finite',
                                  'no_portfolio_day_loses_more_than_100pct',
                                  'no_duplicate_dates','no_negative_average_cash','matching_fields']):
        raise ValueError(f'Result integrity check failed: {tests}')
    (OUT/'integrity_checks.json').write_text(json.dumps(tests,indent=2))
    reconciliations=[]
    for path in sorted((ROOT/'data/processed').glob('*_account.parquet')):
        name=path.name.removesuffix('_account.parquet')
        a=pd.read_parquet(path)
        error=float(np.max(np.abs(a.nav.to_numpy()-(1+daily[name]).cumprod().to_numpy())))
        valid=bool(error<1e-7 and (a.fees>=0).all() and (a.cash_weight>=-1e-9).all())
        reconciliations.append({'portfolio':name,'max_nav_reconciliation_error':error,'passed':valid})
    reconciliation=pd.DataFrame(reconciliations)
    reconciliation.to_csv(OUT/'account_reconciliation.csv',index=False)
    if not reconciliation.passed.all():
        raise ValueError('Account NAV reconciliation failed')
    annual=coverage.join(signal.eligible_n).groupby(coverage.index.year).agg(['min','median','max'])
    annual.to_csv(OUT/'coverage_annual.csv')
    print('Auxiliary summaries and integrity checks complete.',flush=True)


if __name__=='__main__':
    main()
