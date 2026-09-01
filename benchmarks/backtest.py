"""Validate the forecasters before a single public forecast is made.

Walk the last ~130 weeks as if live: fit each forecaster on data strictly
before the target week, forecast, score against what happened. This is the
evidence that the models behind the ledger are calibrated, and it is where the
window and trend settings were chosen (on the EARLIER half of the walk; the
later half is reported untouched).

Writes benchmarks/backtest.csv.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from asotele import data
from asotele.models import quake_quantiles, tmax_week_quantiles
from asotele.scoring import interval_hits, wis
from asotele.targets import TARGETS

N_WEEKS = 130


def main():
    rows = []

    # ---- quakes: truth comes straight from the cached weekly history
    weekly = data.quake_weekly_history()
    for i in range(len(weekly) - N_WEEKS, len(weekly)):
        past = weekly.iloc[:i]
        truth = float(weekly.iloc[i]["count"])
        monday = weekly.iloc[i]["week"].date()
        for window, label in ((156, "3y window"), (520, "10y window")):
            q = quake_quantiles(past, window_weeks=window)
            rows.append({"target": "quakes_m45", "model": label,
                         "monday": monday, "truth": truth,
                         "wis": wis(truth, q), **interval_hits(truth, q)})

    # ---- tmax: reconstruct each target week's truth from the daily cache
    for tid, cache in (("nyc_tmax", "tmax_nyc.csv"),
                       ("sea_tmax", "tmax_sea.csv")):
        spec = TARGETS[tid]
        daily = data.tmax_daily_history(spec["lat"], spec["lon"], spec["tz"],
                                        cache_name=cache)
        last = daily["time"].max()
        mondays = pd.date_range(end=last - pd.Timedelta(days=7),
                                periods=N_WEEKS, freq="W-MON")
        for m in mondays:
            week = daily[(daily["time"] >= m)
                         & (daily["time"] <= m + pd.Timedelta(days=6))]
            if len(week) < 7:
                continue
            truth = float(week["tmax"].max())
            past = daily[daily["time"] < m]
            for label, kw in (("climatology + trend + spread",
                               dict(trend_years=10, spread=1.2)),
                              ("climatology only",
                               dict(trend_years=100, spread=1.0))):
                q = tmax_week_quantiles(past, m.date(), **kw)
                rows.append({"target": tid, "model": label,
                             "monday": m.date(), "truth": truth,
                             "wis": wis(truth, q), **interval_hits(truth, q)})

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "benchmarks" / "backtest.csv", index=False)

    later = df[df["monday"] >= df["monday"].max() - timedelta(days=455)]
    print("HELD-OUT half of the walk (settings chosen on the earlier half)")
    g = later.groupby(["target", "model"]).agg(
        n=("wis", "size"), wis=("wis", "mean"),
        cov50=("in50", "mean"), cov80=("in80", "mean"),
        cov95=("in95", "mean")).round(3)
    print(g.to_string())


if __name__ == "__main__":
    main()
