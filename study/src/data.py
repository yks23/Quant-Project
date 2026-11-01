"""Read actual archived Feather files; never call upstream synthetic fallbacks."""

from pathlib import Path
import hashlib
import json
import shutil
import tarfile
import numpy as np
import pandas as pd

FIELDS = ["open", "close", "volume", "money", "close_dr", "market_cap_ashare",
          "circulating_market_cap_ashare", "turnover_ratio", "pb_ratio", "return_adj"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def extract(archive, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    wanted = {f"fire_data/{field}.feather" for field in FIELDS}
    found = set()
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if member.name in wanted:
                if not member.isfile():
                    raise ValueError(f"Unexpected archive entry {member.name}")
                target = destination / Path(member.name).name
                with tar.extractfile(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                found.add(member.name)
    if found != wanted:
        raise ValueError(f"Missing fields: {sorted(wanted-found)}")


def load_panel(folder, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frames, rows = {}, []
    for name in FIELDS:
        path = Path(folder) / f"{name}.feather"
        frame = pd.read_feather(path)
        frame.index = pd.to_datetime(frame.index)
        frame = frame.sort_index()
        if frame.index.has_duplicates or frame.columns.has_duplicates:
            raise ValueError(f"Duplicate index in {name}")
        # Include only SZ/SH A-share code prefixes, not funds, B shares or BSE.
        keep = [str(x) for x in frame.columns if
                (str(x).endswith('.SZ') and str(x).startswith(('000','001','002','003','300','301')))
                or (str(x).endswith('.SH') and str(x).startswith(('600','601','603','605','688','689')))]
        raw_n = frame.shape[1]
        frame = frame.loc[:,keep].astype('float32')
        rows.append({"field":name, "dates":len(frame), "raw_columns":raw_n,
                     "ashare_columns":len(keep), "start":str(frame.index.min().date()),
                     "end":str(frame.index.max().date()),
                     "missing_fraction":float(frame.isna().to_numpy().mean()),
                     "zero_fraction":float(frame.eq(0).to_numpy().mean()),
                     "sha256":sha256(path)})
        frames[name] = frame
    base = frames['close']
    for name, frame in frames.items():
        if not frame.index.equals(base.index) or not frame.columns.equals(base.columns):
            raise ValueError(f"Misaligned field {name}")
    pd.DataFrame(rows).to_csv(output/'data_fields.csv',index=False)
    valid = base.gt(0) & frames['volume'].gt(0)
    observed = base.gt(0)
    coverage = pd.DataFrame({"positive_close":observed.sum(axis=1),
                            "trading_records":valid.sum(axis=1),
                            "positive_cap":frames['market_cap_ashare'].gt(0).sum(axis=1)})
    coverage.to_csv(output/'coverage_daily.csv',index_label='date')
    meta = []
    for code in base.columns:
        ids = np.flatnonzero(observed[code].to_numpy())
        meta.append({"symbol":code, "positive_observations":len(ids),
                     "first":str(base.index[ids[0]].date()) if len(ids) else '',
                     "last":str(base.index[ids[-1]].date()) if len(ids) else '',
                     "all_zero_or_missing":not len(ids)})
    # Instrument metadata remain local, while aggregate audit is published.
    Path('data/processed').mkdir(parents=True,exist_ok=True)
    pd.DataFrame(meta).to_csv('data/processed/instrument_audit.csv',index=False)
    ret = base.where(base>0).pct_change(fill_method=None)
    declared = frames['return_adj']
    sample = (ret-declared).abs().stack().dropna()
    sample_pct = (ret-declared/100).abs().stack().dropna()
    unit = 'decimal' if sample.median() < sample_pct.median() else 'percentage'
    check = declared if unit == 'decimal' else declared/100
    diff = (ret-check).abs()
    audit = {"source":"F.I.R.E. asset 256635084", "n_dates":len(base),
             "n_securities":base.shape[1], "return_adj_inferred_unit":unit,
             "return_price_median_abs_difference":float(diff.stack().median()),
             "return_price_p99_abs_difference":float(diff.stack().quantile(.99)),
             "all_zero_or_missing_securities":sum(x['all_zero_or_missing'] for x in meta),
             "histories_ending_before_last_date":sum(bool(x['last']) and x['last']<str(base.index[-1].date()) for x in meta),
             "abs_daily_return_over_30pct_count":int(ret.abs().gt(.30).sum().sum()),
             "history_completeness":"No authoritative listing/delisting master: cannot certify survivor-free coverage."}
    (output/'data_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    return frames, audit
