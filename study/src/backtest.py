"""Fractional-share cash-account research simulation, not order-book replay."""

import numpy as np
import pandas as pd


def simulate(open_price, close, target, signal_rows, start, end, cost_bps=10, limit=0.095,
             execution_available=None, rebalance_fraction=1.0):
    if not 0 < rebalance_fraction <= 1:
        raise ValueError("rebalance_fraction must be in (0, 1]")
    opens, closes = open_price.to_numpy(dtype=float), close.to_numpy(dtype=float)
    targets = target.to_numpy(dtype=float)
    availability = None if execution_available is None else execution_available.to_numpy(dtype=bool)
    cash = 1.0
    shares = np.zeros(opens.shape[1])
    marks = np.full(opens.shape[1], np.nan)
    nav_prev = 1.0
    out = []
    signal_rows = set(signal_rows)
    cost = cost_bps / 10000
    for t, day in enumerate(close.index):
        valid_close = np.isfinite(closes[t]) & (closes[t] > 0)
        if day < start:
            marks = np.where(valid_close, closes[t], marks)
            continue
        if day > end:
            break
        traded, fees, blocked_buy, blocked_sell = 0.0, 0.0, 0, 0
        if t - 1 in signal_rows:
            valid_open = np.isfinite(opens[t]) & (opens[t] > 0)
            if availability is not None:
                valid_open &= availability[t]
            at_open = np.where(valid_open, opens[t], marks)
            nav_open = cash + np.nansum(shares * at_open)
            w = np.nan_to_num(targets[t - 1], nan=0.0)
            # Reserve enough cash for fees, then sell before scaling purchases.
            desired = np.divide(nav_open * w / (1 + cost), at_open,
                                out=np.zeros_like(shares), where=at_open > 0)
            if rebalance_fraction < 1:
                desired = shares + rebalance_fraction * (desired - shares)
            gap = np.divide(opens[t], marks, out=np.full_like(shares, np.nan),
                            where=marks > 0) - 1
            sell_ok = valid_open & np.isfinite(gap) & (gap > -limit)
            buy_ok = valid_open & np.isfinite(gap) & (gap < limit)
            sell_qty = np.maximum(shares - desired, 0)
            blocked_sell = int(((sell_qty > 1e-14) & ~sell_ok).sum())
            sell_qty = np.where(sell_ok, sell_qty, 0)
            proceeds = np.nansum(sell_qty * opens[t])
            shares -= sell_qty
            cash += proceeds * (1 - cost)
            buy_qty = np.maximum(desired - shares, 0)
            blocked_buy = int(((buy_qty > 1e-14) & ~buy_ok).sum())
            buy_qty = np.where(buy_ok, buy_qty, 0)
            purchase = np.nansum(buy_qty * opens[t])
            scale = min(1.0, max(cash, 0.0) / (purchase * (1 + cost))) if purchase else 0.0
            buy_qty *= scale
            purchase *= scale
            shares += buy_qty
            cash -= purchase * (1 + cost)
            traded = (proceeds + purchase) / nav_open if nav_open > 0 else 0
            fees = (proceeds + purchase) * cost
        stale = ~valid_close & (shares > 1e-14)
        marks = np.where(valid_close, closes[t], marks)
        nav = cash + np.nansum(shares * marks)
        if nav <= 0 or cash < -1e-9:
            raise ValueError("Invalid cash account")
        out.append({"date": day, "return": nav / nav_prev - 1, "nav": nav,
                    "turnover": traded, "fees": fees / nav_prev,
                    "cash_weight": cash / nav, "holdings": int((shares > 1e-14).sum()),
                    "stale_weight": np.nansum(shares[stale] * marks[stale]) / nav,
                    "blocked_buy": blocked_buy, "blocked_sell": blocked_sell})
        nav_prev = nav
    return pd.DataFrame(out).set_index("date")


def equal_weight(mask):
    weights = mask.astype(float)
    return weights.div(weights.sum(axis=1).replace(0, np.nan), axis=0).fillna(0).astype("float32")


def spread_return(long_net, short_leg_net, short_leg_fees):
    """Subtracting a net long return otherwise incorrectly credits short fees."""
    return long_net - short_leg_net - 2 * short_leg_fees
