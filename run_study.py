"""Run the prespecified study; raw prices remain local and are never committed."""

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

from src.data import extract, load_panel, sha256
from src.factors import compute, quantiles
from src.backtest import simulate, equal_weight
from src.statistics import performance, model_alpha, hac_mean
from src.risk import local_factors, monthly

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'


def save(df,name):
    df.to_csv(RESULTS/name,index=False,float_format='%.10g')


def analyze_events(panel, f, signal_rows):
    dates=panel['close'].index
    forward=panel['open'].where(panel['open']>0).shift(-6)/panel['open'].where(panel['open']>0).shift(-1)-1
    control={'size':np.log(panel['market_cap_ashare'].where(panel['market_cap_ashare']>0)),
             'price':np.log(panel['close_dr'].where(panel['close_dr']>0)),
             'illiquidity':(f['r1'].abs()/panel['money'].where(panel['money']>0)).rolling(20).mean()}
    labels={k:quantiles(v.where(f['eligible']),3) for k,v in control.items()}
    groups={name:quantiles(f[name]) for name in ['PATH','BREADTH','REV']}
    event_rows=[]
    for name in ['PATH','BREADTH']:
        for ctrl in control:
            for t in signal_rows:
                valid=f['eligible'].iloc[t] & control[ctrl].iloc[t].notna()
                for c in range(1,4):
                    for q in range(1,6):
                        mask=valid & labels[ctrl].iloc[t].eq(c) & groups[name].iloc[t].eq(q)
                        y=forward.iloc[t].where(mask).dropna()
                        event_rows.append({'date':dates[t],'factor':name,'control':ctrl,'control_group':c,
                                           'quintile':q,'mean_forward_5d':y.mean(),'formed_n':int(mask.sum()),
                                           'observed_n':len(y)})
    # Original path question: compare concentration within similar loser returns.
    loser=f['eligible'] & (f['r5']<0)
    r_groups=quantiles(f['r5'].where(loser),3)
    c_groups=quantiles(f['loss_concentration'].where(loser),5)
    for t in signal_rows:
        for c in range(1,4):
            for q in range(1,6):
                mask=loser.iloc[t]&r_groups.iloc[t].eq(c)&c_groups.iloc[t].eq(q)
                y=forward.iloc[t].where(mask).dropna()
                event_rows.append({'date':dates[t],'factor':'LOSER_PATH','control':'past_return',
                                   'control_group':c,'quintile':q,'mean_forward_5d':y.mean(),
                                   'formed_n':int(mask.sum()),'observed_n':len(y)})
    event=pd.DataFrame(event_rows)
    save(event,'double_sort_events.csv')
    summaries=[]
    for key,g in event.groupby(['factor','control','control_group','quintile']):
        test=hac_mean(g.mean_forward_5d,2)
        summaries.append(dict(zip(['factor','control','control_group','quintile'],key),
                              **test, formed=int(g.formed_n.sum()),observed=int(g.observed_n.sum())))
    save(pd.DataFrame(summaries),'double_sort_summary.csv')
    spreads=[]
    for key,g in event.groupby(['factor','control','control_group']):
        p=g.pivot(index='date',columns='quintile',values='mean_forward_5d')
        spreads.append(dict(zip(['factor','control','control_group'],key),**hac_mean(p[5]-p[1],2)))
    save(pd.DataFrame(spreads),'double_sort_spreads.csv')
    coefficients=[]
    for t in signal_rows:
        x=pd.DataFrame({'PATH':f['PATH'].iloc[t], 'R5':f['r5'].iloc[t], 'R1':f['r1'].iloc[t],
                        'vol20':f['vol20'].iloc[t], **{k:v.iloc[t] for k,v in control.items()},
                        'y':forward.iloc[t]}).where(f['eligible'].iloc[t],axis=0).dropna()
        if len(x)<100:
            continue
        y=x.pop('y')
        x=x.clip(x.quantile(.01),x.quantile(.99),axis=1)
        x=(x-x.mean())/x.std().replace(0,np.nan)
        x=x.dropna(axis=1)
        beta=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x.to_numpy()]),y.to_numpy(),rcond=None)[0]
        coefficients.append({'date':dates[t],**dict(zip(['const']+list(x.columns),beta)),'n':len(x)})
    coef=pd.DataFrame(coefficients)
    save(coef,'cross_sectional_coefficients.csv')
    save(pd.DataFrame([{'variable':c,**hac_mean(coef[c],2)} for c in coef.columns if c not in ['date','n']]),'cross_sectional_summary.csv')
    # BREADTH and R5 are collinear on each date: test state moderation over time.
    market=f['r1'].where(f['eligible']).mean(axis=1)
    state=[]
    for t in signal_rows:
        g=groups['REV'].iloc[t]
        y=forward.iloc[t]
        state.append({'date':dates[t], 'reversal_spread':y[g==5].mean()-y[g==1].mean(),
                      'breadth':f['breadth'].iloc[t], 'market_r5':market.rolling(5).sum().iloc[t],
                      'market_vol20':market.rolling(20).std().iloc[t]})
    state=pd.DataFrame(state).dropna().set_index('date')
    fit=sm.OLS(state.reversal_spread,sm.add_constant(state[['breadth','market_r5','market_vol20']])).fit(
        cov_type='HAC',cov_kwds={'maxlags':2,'use_correction':True})
    save(pd.DataFrame({'variable':fit.params.index,'coefficient':fit.params.values,'t':fit.tvalues.values,
                       'p':fit.pvalues.values,'n':len(state)}),'breadth_conditioning.csv')
    state.to_csv(RESULTS/'breadth_state_events.csv')


def evaluate(daily_returns, diagnostics, risk_daily, cfg, label='local_proxy'):
    risk_m=monthly(risk_daily)
    return_m=monthly(daily_returns)
    rf_d=risk_daily.RF.reindex(daily_returns.index).fillna((1.015)**(1/252)-1)
    periods={'full':(cfg['signal_start'],cfg['end']),
             'development':(cfg['signal_start'],cfg['development_end']),
             'validation':('2021-01-01',cfg['validation_end']),
             'holdout':(cfg['holdout_start'],cfg['holdout_end'])}
    stats,alphas=[],[]
    for period,(start,end) in periods.items():
        for name in daily_returns:
            r=daily_returns[name].loc[start:end]
            if r.empty:
                continue
            ls='_LS_' in name
            row={'period':period,'portfolio':name,**performance(r,None if ls else rf_d)}
            cost=name.rsplit('_',1)[-1]
            benchmark='EW_'+cost
            if not ls and benchmark in daily_returns:
                row['annual_vs_market']=(r-daily_returns[benchmark].reindex(r.index)).mean()*252
            stats.append(row)
            y=return_m[name].loc[pd.Period(start,'M'):pd.Period(end,'M')]
            for item in model_alpha(y,risk_m,long_short=ls):
                alphas.append({'period':period,'portfolio':name,'source':label,**item})
    stats=pd.DataFrame(stats)
    alpha=pd.DataFrame(alphas)
    mask=(alpha.period=='holdout')&(alpha.model=='Carhart4')&alpha.portfolio.isin(['PATH_LS_c10','BREADTH_LS_c10'])
    if mask.sum()==2:
        alpha.loc[mask,'p_holm_two_primary']=multipletests(alpha.loc[mask,'p'],method='holm')[1]
    save(stats,'performance.csv')
    save(alpha,f'alpha_{label}.csv')
    risk_m.to_csv(RESULTS/f'model_factors_{label}_monthly.csv',index_label='month')
    yearly=[]
    for year,g in daily_returns.groupby(daily_returns.index.year):
        for col in ['PATH_LS_c10','BREADTH_LS_c10','REV_LS_c10','EW_c10']:
            yearly.append({'year':year,'portfolio':col,**performance(g[col],None if '_LS_' in col else rf_d)})
    save(pd.DataFrame(yearly),'annual_performance.csv')
    stats.to_json(RESULTS/'performance.json',orient='records',indent=2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--extract',action='store_true')
    parser.add_argument('--archive',default='data/AStockData.tar.gz')
    parser.add_argument('--data',default='data/extracted/fire_data')
    args=parser.parse_args()
    os.chdir(ROOT)
    cfg=json.loads((ROOT/'config/study.json').read_text())
    RESULTS.mkdir(exist_ok=True)
    if args.extract:
        if Path(args.archive).stat().st_size!=1396296954:
            raise ValueError('Incomplete/wrong F.I.R.E. archive')
        extract(args.archive,args.data)
    print('Loading real files and auditing',flush=True)
    panel,audit=load_panel(args.data,RESULTS)
    cfg['data_archive_sha256']=sha256(args.archive)
    cfg['python']=platform.python_version()
    cfg['code_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    cfg['data_content_audited']=True
    (RESULTS/'run_manifest.json').write_text(json.dumps(cfg,indent=2))
    for key in panel:
        panel[key]=panel[key].loc[:cfg['end']]
    close=panel['close'].where(panel['close']>0)
    opening=panel['open'].where(panel['open']>0)
    print('Computing frozen factor formulas',flush=True)
    f=compute(close,panel['volume'],panel['circulating_market_cap_ashare'],cfg['signal_window'],cfg['warmup_observations'])
    f['eligible'] &= f['eligible'].sum(axis=1).ge(cfg['min_stocks']).to_numpy()[:,None]
    first=int(close.index.searchsorted(cfg['signal_start']))
    signal_rows=list(range(first,len(close)-1,cfg['rebalance_every']))
    info=pd.DataFrame({'breadth':f['breadth'],'breadth_vw':f['breadth_vw'],
                       'breadth_denominator':f['breadth_n'],'eligible_n':f['eligible'].sum(axis=1)})
    info.to_csv(RESULTS/'signal_audit.csv',index_label='date')
    factor_names=['PATH','BREADTH','REV','PATH_HHI','BREADTH_VW']
    factor_summary=[]
    for name in factor_names:
        local=f[name].iloc[signal_rows].copy()
        local.to_parquet(f'data/processed/{name}_formation_scores.parquet')
        factor_summary.append({'factor':name,'formation_dates':len(local),
                               'valid_scores':int(local.notna().sum().sum()),
                               'mean':float(local.stack().mean()),'std':float(local.stack().std())})
    save(pd.DataFrame(factor_summary),'factor_summary.csv')
    series,diag={},[]
    for cost in cfg['cost_grid_bps']:
        names=factor_names if cost==10 else ['PATH','BREADTH']
        bench=simulate(opening,close,equal_weight(f['eligible']),signal_rows,
                       pd.Timestamp(cfg['signal_start']),pd.Timestamp(cfg['end']),cost,cfg['execution_limit_proxy'])
        series[f'EW_c{cost}']=bench['return']
        diag.append({'portfolio':f'EW_c{cost}',**bench.drop(columns=['nav','return']).mean().to_dict()})
        for name in names:
            groups=quantiles(f[name].where(f['eligible']))
            for q in range(1,6):
                key=f'{name}_Q{q}_c{cost}'
                print(f'Cash account: {key}',flush=True)
                result=simulate(opening,close,equal_weight(groups.eq(q)),signal_rows,
                                pd.Timestamp(cfg['signal_start']),pd.Timestamp(cfg['end']),cost,cfg['execution_limit_proxy'])
                series[key]=result['return']
                row={'portfolio':key,**result.drop(columns=['nav','return']).mean().to_dict(),
                     'max_stale_weight':result.stale_weight.max(),
                     'blocked_buy_total':int(result.blocked_buy.sum()),'blocked_sell_total':int(result.blocked_sell.sum())}
                diag.append(row)
                result.to_parquet(f'data/processed/{key}_account.parquet')
            # Both legs pay their own costs; short-leg fees must not become income.
            r5=series[f'{name}_Q5_c{cost}']
            r1=series[f'{name}_Q1_c{cost}']
            short_account=pd.read_parquet(f'data/processed/{name}_Q1_c{cost}_account.parquet')
            series[f'{name}_LS_c{cost}']=r5-r1-2*short_account.fees
    returns=pd.DataFrame(series)
    returns.to_csv(RESULTS/'daily_portfolio_returns.csv',index_label='date',float_format='%.10g')
    diagnostics=pd.DataFrame(diag)
    save(diagnostics,'execution_diagnostics.csv')
    print('Independent double sorts and incremental-information tests',flush=True)
    analyze_events(panel,f,signal_rows)
    print('Constructing prespecified local risk-factor proxies',flush=True)
    risk=local_factors(panel,f['eligible'])
    risk.to_csv(RESULTS/'risk_factors_local_daily.csv',index_label='date',float_format='%.10g')
    evaluate(returns,diagnostics,risk,cfg)
    print('Completed computations; see results/. Generate report separately.',flush=True)


if __name__=='__main__':
    main()
