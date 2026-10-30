"""All signal inputs are dated at or before the formation close."""

import numpy as np
import pandas as pd


def quantiles(values, n=5):
    """Preserve ties rather than use ticker order to split identical signals."""
    rank = values.rank(axis=1, pct=True, method="average")
    return np.ceil(rank * n).fillna(0).astype("int8")


def compute(close, volume, cap, window=5, warmup=60):
    price = close.where(close > 0)
    ret = np.log(price / price.shift(1))
    active = price.notna() & (volume > 0)
    eligible = active & price.notna().cumsum().ge(warmup)
    eligible &= ret.rolling(window, min_periods=window).count().eq(window)
    r5 = ret.rolling(window, min_periods=window).sum()
    loss, gain = (-ret).clip(lower=0), ret.clip(lower=0)
    loss_sum = loss.rolling(window).sum().replace(0, np.nan)
    gain_sum = gain.rolling(window).sum().replace(0, np.nan)
    cm = loss.rolling(window).max() / loss_sum
    cp = gain.rolling(window).max() / gain_sum
    hm = loss.pow(2).rolling(window).sum() / loss_sum.pow(2)
    hp = gain.pow(2).rolling(window).sum() / gain_sum.pow(2)
    path = cm.where(r5 < 0, -cp).where(r5 != 0, 0).where(eligible)
    path_hhi = hm.where(r5 < 0, -hp).where(r5 != 0, 0).where(eligible)
    valid_b = active & ret.notna()
    breadth_day = ((ret < 0) & valid_b).sum(axis=1) / valid_b.sum(axis=1).replace(0, np.nan)
    breadth = breadth_day.rolling(window, min_periods=window).mean()
    # Lag capitalization: weighting cannot incorporate a future observation.
    weights = cap.shift(1).where(valid_b & (cap.shift(1) > 0))
    breadth_vw = weights.where(ret < 0, 0).sum(axis=1) / weights.sum(axis=1).replace(0, np.nan)
    breadth_vw = breadth_vw.rolling(window, min_periods=window).mean()
    reversal = (-r5).where(eligible)
    return {
        "PATH": path.astype("float32"),
        "BREADTH": reversal.mul(2 * breadth - 1, axis=0).astype("float32"),
        "REV": reversal.astype("float32"),
        "PATH_HHI": path_hhi.astype("float32"),
        "BREADTH_VW": reversal.mul(2 * breadth_vw - 1, axis=0).astype("float32"),
        "r5": r5.astype("float32"), "r1": ret.astype("float32"),
        "vol20": ret.rolling(20, min_periods=20).std().astype("float32"),
        "loss_concentration": cm.astype("float32"),
        "eligible": eligible, "breadth": breadth,
        "breadth_day": breadth_day, "breadth_vw": breadth_vw,
        "breadth_n": valid_b.sum(axis=1),
    }
