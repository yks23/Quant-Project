"""Exploratory loss geometry; inputs contain only formation-time observations."""

import numpy as np
import pandas as pd


FEATURES = ["C", "RECENT", "SYNC"]


def leave_one_out_breadth(returns, active):
    valid = np.isfinite(returns) & active
    negative = (returns < 0) & valid
    count = valid.sum(axis=1, keepdims=True) - valid
    down = negative.sum(axis=1, keepdims=True) - negative
    return np.divide(down, count, out=np.full(returns.shape, np.nan), where=count > 0)


def loss_geometry(returns, breadth):
    """Rows are chronological, oldest first; columns are securities."""
    loss = np.maximum(-np.asarray(returns, dtype=float), 0)
    total = loss.sum(axis=0)
    weight = np.divide(loss, total, out=np.full_like(loss, np.nan), where=total > 0)
    clock = np.linspace(0, 1, len(loss))[:, None]
    b = np.asarray(breadth, dtype=float)
    return {
        "C": weight.max(axis=0),
        "RECENT": (weight * clock).sum(axis=0),
        "SYNC": (weight * (b - b.mean(axis=0))).sum(axis=0),
    }


def standardized(frame):
    clipped = frame.clip(frame.quantile(.01), frame.quantile(.99), axis=1)
    scale = clipped.std()
    if (scale <= 1e-12).any():
        raise ValueError("Constant predictor in formed cross-section")
    return (clipped - clipped.mean()) / scale


def conditional_groups(feature, controls, past_return):
    x = np.column_stack([np.ones(len(controls)), controls.to_numpy()])
    residual = feature.to_numpy() - x @ np.linalg.lstsq(x, feature, rcond=None)[0]
    strata = np.ceil(past_return.rank(pct=True, method="average") * 10).astype(int)
    score = pd.Series(residual, index=feature.index)
    groups = score.groupby(strata).rank(pct=True, method="average")
    return strata, np.ceil(groups * 5).astype(int), score


def period_mask(frame, start, end):
    """A label must start and finish inside the requested evaluation period."""
    return frame.date.ge(start) & frame.date.le(end) & frame.label_end.le(end)


def past_training_rows(frame, year):
    cutoff = pd.Timestamp(year=year, month=1, day=1)
    return frame.loc[frame.label_end.lt(cutoff)]
