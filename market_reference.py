"""Download the public CSI300 price index as a descriptive market reference."""

from pathlib import Path
import json
import time
import urllib.request
import pandas as pd
from src.data import sha256
from src.statistics import performance

ROOT=Path(__file__).resolve().parent


def main():
    raw=ROOT/'data/raw/reference'
    raw.mkdir(parents=True,exist_ok=True)
    records,receipts=[],[]
    for year in range(2014,2025):
        url=f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000300,day,{year}-01-01,{year}-12-31,640,qfq'
        path=raw/f'csi300_{year}.json'
        if not path.exists():
            request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=30) as response:
                body=response.read()
            payload=json.loads(body)
            if payload.get('code')!=0 or 'day' not in payload.get('data',{}).get('sh000300',{}):
                raise ValueError(f'Unexpected public index response: {year}')
            path.write_bytes(body)
            time.sleep(.3)
        payload=json.loads(path.read_bytes())
        rows=payload['data']['sh000300']['day']
        selected=[r for r in rows if str(r[0]).startswith(str(year))]
        if len(selected)<200:
            raise ValueError(f'Incomplete index year {year}: {len(selected)}')
        records.extend([{'date':r[0],'close':float(r[2])} for r in selected])
        receipts.append({'year':year,'url':url,'sha256':sha256(path),'rows':len(selected)})
    prices=pd.DataFrame(records).set_index('date').sort_index()
    prices.index=pd.to_datetime(prices.index)
    if prices.index.has_duplicates or not (prices.close>0).all():
        raise ValueError('Invalid index dates/prices')
    idx=pd.read_csv(ROOT/'results/daily_portfolio_returns.csv',index_col=0,parse_dates=True).index
    ret=prices.close.pct_change(fill_method=None).reindex(idx)
    if ret.isna().any():
        raise ValueError('CSI300 does not cover every strategy trading date')
    ret.rename('CSI300_price_index').to_csv(ROOT/'results/market_reference_returns.csv',index_label='date')
    rf=pd.Series((1.015)**(1/252)-1,index=idx)
    out=[]
    for period,start,end in [('full','2015-04-01','2024-12-31'),('holdout','2022-01-01','2024-12-31')]:
        out.append({'period':period,'portfolio':'CSI300_price_index',**performance(ret.loc[start:end],rf)})
    pd.DataFrame(out).to_csv(ROOT/'results/market_reference_performance.csv',index=False)
    (ROOT/'results/market_reference_manifest.json').write_text(json.dumps({
        'source':'Tencent Finance public index day bars','symbol':'sh000300',
        'download_date':'2026-10-31','return_type':'price index, not dividend-reinvested or investable net return',
        'role':'Descriptive broad-market comparison only; not used to choose factors or alter primary tests',
        'files':receipts},indent=2))
    print(f'CSI300 reference validated on {len(ret)} strategy dates.',flush=True)


if __name__=='__main__':
    main()
