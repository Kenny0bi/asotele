"""Proper scoring, shared vocabulary with my FluSight work.

Pinball loss per quantile level, and the weighted interval score as twice the
mean pinball loss, which is the identity checked to 1e-9 in harmattan's tests
and re-checked here.

A proper score is the whole reason this ledger means anything: under pinball
loss the expected score is minimised by stating your true beliefs, so there is
no way to game the record except by forecasting well.
"""

import numpy as np

from .targets import QUANTILES

LEVELS = np.array(QUANTILES)


def pinball(y, q, tau):
    y = np.asarray(y, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    tau = np.asarray(tau, dtype=np.float64)
    diff = y - q
    return np.where(diff >= 0, tau * diff, (tau - 1.0) * diff)


def wis(y, quantiles):
    q = np.asarray(quantiles, dtype=np.float64)
    return float(2.0 * pinball(float(y), q, LEVELS).mean())


def interval_hits(y, quantiles):
    """Which central intervals contained the outcome. For the calibration tally."""
    q = np.asarray(quantiles, dtype=np.float64)
    out = {}
    for nominal in (0.5, 0.8, 0.95):
        lo_level = (1 - nominal) / 2
        li = int(np.argmin(np.abs(LEVELS - lo_level)))
        ui = int(np.argmin(np.abs(LEVELS - (1 - lo_level))))
        out[f"in{int(nominal*100)}"] = bool(q[li] <= y <= q[ui])
    return out


def skill_vs(y, quantiles, reference_quantiles):
    """WIS relative to a stated reference forecast. Below 1 beats it."""
    a = wis(y, quantiles)
    b = wis(y, reference_quantiles)
    return a / b if b > 0 else np.nan
