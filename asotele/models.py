"""The forecasters. Simple on purpose, and validated before use.

The point of this ledger is the protocol, not model sophistication: forecasts
committed before outcomes, scored by a proper rule, in public. But simple must
not mean sloppy, so each forecaster is chosen by backtest (benchmarks/backtest
.py) and its calibration is a test, not a hope.

Both speak in the shared 23 quantile levels.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from .targets import QUANTILES

LEVELS = np.array(QUANTILES)


def quake_quantiles(weekly, window_weeks=520):
    """Weekly M4.5+ count: empirical quantiles of the trailing window.

    The window was chosen by backtest: ten years beat three on held-out WIS
    (29.9 against 30.6) with coverage of 0.50/0.80/0.97 at nominal
    0.50/0.80/0.95. The week of 2025-07-28 sits inside that window at 878
    events (the Kamchatka M8.8 and its aftershocks), a reminder of why the
    upper tail must stay heavy.
    """
    counts = weekly["count"].to_numpy(dtype=np.float64)[-window_weeks:]
    q = np.quantile(counts, LEVELS)
    return np.round(np.sort(q), 1)


def tmax_week_quantiles(daily, target_monday, halfwidth_days=10,
                        trend_years=10, spread=1.2):
    """Warmest day of the target week: windowed climatology plus a trend nudge.

    For every past year, compute the warmest daily Tmax in the 7-day window
    aligned with the target week (padded by `halfwidth_days` on each side of
    the window centre before taking the 7-day-max samples). The predictive
    quantiles are the empirical quantiles of those annual samples, shifted by
    the difference between the recent decade's mean and the full-history mean,
    which is the cheapest honest way to stop a warming climate from making
    every summer forecast run cold.
    """
    d = daily.copy()
    d["doy"] = d["time"].dt.dayofyear
    d["year"] = d["time"].dt.year
    centre = pd.Timestamp(target_monday) + pd.Timedelta(days=3)
    c_doy = int(centre.dayofyear)

    samples = []
    years = sorted(d["year"].unique())
    current_year = d["time"].max().year
    for yr in years:
        if yr == current_year and c_doy > d[d["year"] == yr]["doy"].max() - 3:
            continue                      # the target week itself, or later
        lo, hi = c_doy - 3 - halfwidth_days, c_doy + 3 + halfwidth_days
        span = d[(d["year"] == yr) & (d["doy"].between(lo, hi))]
        if len(span) < 10:
            continue
        # the statistic is the 7-day max; slide a 7-day window and take the
        # sample for the aligned week plus jittered neighbours
        v = span.sort_values("doy")["tmax"].to_numpy()
        for s in range(0, max(len(v) - 6, 1), 3):
            samples.append(float(np.max(v[s:s + 7])))
    samples = np.asarray(samples)

    recent = d[d["year"] >= current_year - trend_years]["tmax"].mean()
    alltime = d["tmax"].mean()
    shift = float(recent - alltime)

    q = np.quantile(samples, LEVELS)
    # The overlapping 7-day windows make the climatology samples correlated,
    # which understates spread. The widening was chosen on the backtest's
    # SELECTION half only, by a rule stated before the held-out half was
    # looked at: the smallest spread whose selection coverage met nominal at
    # the 80% and 95% intervals. That gave 1.2 for both cities.
    med = np.quantile(samples, 0.5)
    q = med + (q - med) * spread + shift
    return np.round(np.sort(q), 1)
