"""Contracts for the ledger. These are what make the record trustworthy."""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asotele.models import quake_quantiles, tmax_week_quantiles
from asotele.scoring import LEVELS, interval_hits, pinball, wis
from asotele.targets import (QUANTILES, TARGETS, is_mature, next_monday,
                             week_bounds)

ROOT = Path(__file__).resolve().parents[1]


def test_weeks_are_mondays_and_seven_days():
    for d in (date(2026, 9, 1), date(2026, 9, 7), date(2026, 12, 31)):
        m = next_monday(d)
        assert m.weekday() == 0
        assert m > d
        a, b = week_bounds(m)
        assert (b - a).days == 6


def test_maturity_waits_out_the_revision_window():
    m = date(2026, 9, 7)                       # week ends Sunday the 13th
    assert not is_mature(m, "quakes_m45", today=date(2026, 9, 14))
    assert not is_mature(m, "quakes_m45", today=date(2026, 9, 19))
    assert is_mature(m, "quakes_m45", today=date(2026, 9, 20))


def test_wis_is_twice_mean_pinball_and_proper():
    """The identity, and the propriety property that makes gaming impossible:
    against a known distribution, stating the true quantiles scores better in
    expectation than shading them."""
    rng = np.random.default_rng(0)
    draws = rng.normal(100, 15, 40000)
    true_q = np.quantile(draws, QUANTILES)
    shaded = true_q + 6            # a forecaster talking their book
    honest = np.mean([wis(y, true_q) for y in draws[:4000]])
    gamed = np.mean([wis(y, shaded) for y in draws[:4000]])
    assert honest < gamed
    y = 123.4
    assert abs(wis(y, true_q) - 2 * pinball(y, true_q, LEVELS).mean()) < 1e-12


def test_every_committed_forecast_is_valid():
    files = sorted((ROOT / "forecasts").glob("*.json"))
    assert files, "the ledger must open with at least one real forecast"
    for f in files:
        d = json.loads(f.read_text())
        monday = date.fromisoformat(d["round"])
        assert monday.weekday() == 0
        assert date.fromisoformat(d["made_on"]) < monday, \
            "a forecast dated after its target week is not a forecast"
        assert d["quantile_levels"] == QUANTILES
        assert set(d["targets"]) == set(TARGETS)
        for tid, t in d["targets"].items():
            q = np.array(t["quantiles"])
            assert len(q) == len(QUANTILES)
            assert np.all(np.diff(q) >= -1e-9), f"{f.name}:{tid} quantiles cross"
            assert np.all(np.isfinite(q))
            if TARGETS[tid]["kind"] == "count":
                assert q[0] >= 0


def test_scores_never_orphan_and_never_precede():
    for f in sorted((ROOT / "scores").glob("*.json")):
        assert (ROOT / "forecasts" / f.name).exists(), \
            "a score without its forecast is a fabrication"
        s = json.loads(f.read_text())
        monday = date.fromisoformat(s["round"])
        _, sunday = week_bounds(monday)
        assert date.fromisoformat(s["scored_on"]) > sunday


def test_quake_forecaster_from_cached_history():
    import pandas as pd
    weekly = pd.read_csv(ROOT / "data" / "quakes_weekly.csv",
                         parse_dates=["week"])
    q = quake_quantiles(weekly)
    assert q[0] > 50 and q[-1] < 1000
    assert 100 < q[11] < 200                  # the median of a known regime
    assert np.all(np.diff(q) >= 0)


def test_tmax_forecaster_tracks_the_seasons():
    import pandas as pd
    daily = pd.read_csv(ROOT / "data" / "tmax_nyc.csv", parse_dates=["time"])
    q_summer = tmax_week_quantiles(daily, date(2025, 7, 14))
    q_winter = tmax_week_quantiles(daily, date(2025, 1, 13))
    assert q_summer[11] > q_winter[11] + 15, \
        "July in New York must forecast far warmer than January"
    assert 24 < q_summer[11] < 38
    assert -5 < q_winter[11] < 15


def test_interval_hits_are_what_they_say():
    q = np.quantile(np.random.default_rng(1).normal(0, 1, 20000), QUANTILES)
    h = interval_hits(0.0, q)
    assert h["in50"] and h["in80"] and h["in95"]
    h2 = interval_hits(9.9, q)
    assert not (h2["in50"] or h2["in80"] or h2["in95"])


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in fns:
        fn()
        print("ok  ", name, flush=True)
    print(f"\n{len(fns)} passed")
