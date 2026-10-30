"""Explicit local FF-style 2x3 factors, not an official downloaded FF series."""

import numpy as np
import pandas as pd


def weighted(r, cap, mask):
    weights = cap.where(mask & (cap>0))
    denom = weights.sum()
    return float((weights*r.fillna(0)).sum()/denom) if denom>0 else np.nan


def local_factors(panel, eligible, rf_annual=.015):
    c=panel['close'].where(panel['close']>0)
    prices=c.ffill()
    ret=prices.pct_change(fill_method=None)
    caps=panel['market_cap_ashare'].where(panel['market_cap_ashare']>0)
    pb=panel['pb_ratio']
    mom=np.log(c.shift(21)/c.shift(252))
    dates=c.index
    rf=(1+rf_annual)**(1/252)-1
    cohorts={}
    records=[]
    mom_labels=None
    for t in range(1,len(dates)):
        day,prior=dates[t],dates[t-1]
        if day.year!=prior.year or day.month!=prior.month:
            universe=eligible.iloc[t-1] & mom.iloc[t-1].notna() & caps.iloc[t-1].notna()
            m=mom.iloc[t-1].where(universe)
            small=caps.iloc[t-1] <= caps.iloc[t-1].where(universe).median()
            lo,hi=m.quantile([.3,.7])
            mom_labels={(s,v):universe & (small==s) & ((m<=lo) if v=='L' else (m>=hi))
                        for s in [True,False] for v in ['L','H']}
            if day.month==7:
                prev_dec=np.flatnonzero((dates.year==day.year-1)&(dates.month==12))
                if len(prev_dec):
                    # Snapshot B/M in previous December, not future annual reports.
                    bm=(1/pb.iloc[prev_dec[-1]]).where(pb.iloc[prev_dec[-1]]>0)
                    valid=eligible.iloc[t-1] & bm.notna() & caps.iloc[t-1].notna()
                    small=caps.iloc[t-1]<=caps.iloc[t-1].where(valid).median()
                    lo,hi=bm.where(valid).quantile([.3,.7])
                    val=pd.Series(np.select([bm<=lo,bm>=hi],[0,2],default=1),index=c.columns)
                    cohorts={(s,v): valid & (small==s) & (val==v) for s in [True,False] for v in range(3)}
        cap=caps.iloc[t-1]
        market=weighted(ret.iloc[t],cap,eligible.iloc[t-1])
        six={k:weighted(ret.iloc[t],cap,mask) for k,mask in cohorts.items()}
        smb=np.nan if len(six)!=6 else np.mean([six[(True,v)] for v in range(3)])-np.mean([six[(False,v)] for v in range(3)])
        hml=np.nan if len(six)!=6 else (six[(True,2)]+six[(False,2)]-six[(True,0)]-six[(False,0)])/2
        mret={k:weighted(ret.iloc[t],cap,mask) for k,mask in (mom_labels or {}).items()}
        momentum=np.nan if len(mret)!=4 else (mret[(True,'H')]+mret[(False,'H')]-mret[(True,'L')]-mret[(False,'L')])/2
        records.append({'date':day,'MKT':market-rf,'SMB':smb,'HML':hml,'MOM':momentum,'RF':rf})
    return pd.DataFrame(records).set_index('date')


def monthly(daily):
    return (1+daily).groupby(daily.index.to_period('M')).prod(min_count=1)-1
