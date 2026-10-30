"""Performance and HAC inference; no sign or parameter selection."""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def hac_mean(series, lags=10):
    y = pd.Series(series).replace([np.inf, -np.inf], np.nan).dropna()
    if len(y) < 20:
        return {"mean": float(y.mean()), "t": np.nan, "p": np.nan, "n": len(y)}
    fit = sm.OLS(y.to_numpy(), np.ones((len(y), 1))).fit(
        cov_type="HAC", cov_kwds={"maxlags": min(lags, len(y)-2), "use_correction": True})
    return {"mean": float(fit.params[0]), "t": float(fit.tvalues[0]),
            "p": float(fit.pvalues[0]), "n": len(y)}


def performance(r, rf=None):
    r = r.dropna()
    excess = r if rf is None else r - rf.reindex(r.index).fillna(0)
    nav = (1 + r).cumprod()
    high = nav.cummax().clip(lower=1)
    test = hac_mean(excess)
    return {"n_days": len(r), "annual_mean": r.mean()*252,
            "annual_excess": excess.mean()*252,
            "cagr": nav.iloc[-1]**(252/len(r))-1 if len(r) else np.nan,
            "sharpe": excess.mean()/excess.std()*np.sqrt(252) if excess.std()>0 else np.nan,
            "max_drawdown": (nav/high-1).min(), "mean_t": test["t"],
            "mean_p": test["p"], "total_return": nav.iloc[-1]-1 if len(r) else np.nan}


def model_alpha(y, factors, long_short=False, lags=3):
    joined = pd.concat([y.rename("portfolio"), factors], axis=1).dropna()
    models = {"CAPM": ["MKT"], "FF3": ["MKT", "SMB", "HML"],
              "Carhart4": ["MKT", "SMB", "HML", "MOM"]}
    result = []
    for name, cols in models.items():
        if len(joined) < 12:
            continue
        dep = joined.portfolio if long_short else joined.portfolio - joined.RF
        fit = sm.OLS(dep, sm.add_constant(joined[cols], has_constant="add")).fit(
            cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True})
        row = {"model": name, "alpha_month": fit.params["const"],
               "alpha_annual": fit.params["const"]*12, "t": fit.tvalues["const"],
               "p": fit.pvalues["const"], "r2": fit.rsquared, "n_months": len(joined),
               "start": str(joined.index[0]), "end": str(joined.index[-1])}
        row.update({f"beta_{c}": fit.params[c] for c in cols})
        result.append(row)
    return result
