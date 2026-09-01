"""The ledger itself: making a round, scoring a round, tallying the record.

The honesty guarantees, and where each one lives:

  committed before the outcome   forecasts/<monday>.json is committed to git
                                 before the target week begins; the commit
                                 timestamp is the proof, and the scoreboard
                                 links straight to the file's history.
  scored by a fixed rule         the truth procedure is written in
                                 targets.py per target, and scoring waits out
                                 the maturity delay so revisions settle.
  nothing is ever deleted        scoring appends; a bad week stays on the
                                 ledger with the same weight as a good one.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np

from . import data
from .models import quake_quantiles, tmax_week_quantiles
from .scoring import interval_hits, skill_vs, wis
from .targets import QUANTILES, TARGETS, is_mature, next_monday, week_bounds

ROOT = Path(__file__).resolve().parents[1]
FORECASTS = ROOT / "forecasts"
SCORES = ROOT / "scores"


def make_round(today=None, monday=None):
    """Forecast the next full week for every target. Returns the file path."""
    monday = monday or next_monday(today)
    out = FORECASTS / f"{monday.isoformat()}.json"
    if out.exists():
        return out                        # a round is made once, then frozen

    weekly = data.quake_weekly_history(refresh=True)
    entry = {
        "round": monday.isoformat(),
        "week": [d.isoformat() for d in week_bounds(monday)],
        "made_on": (today or date.today()).isoformat(),
        "quantile_levels": QUANTILES,
        "targets": {},
    }
    entry["targets"]["quakes_m45"] = {
        "quantiles": [float(x) for x in quake_quantiles(weekly)],
        "model": "empirical quantiles, trailing 10y of weekly counts",
    }
    for tid, cache in (("nyc_tmax", "tmax_nyc.csv"),
                       ("sea_tmax", "tmax_sea.csv")):
        spec = TARGETS[tid]
        daily = data.tmax_daily_history(spec["lat"], spec["lon"], spec["tz"],
                                        cache_name=cache, refresh=True)
        entry["targets"][tid] = {
            "quantiles": [float(x) for x in
                          tmax_week_quantiles(daily, monday)],
            "model": "windowed climatology + decade trend shift, spread 1.2",
        }
    body = json.dumps(entry, indent=1)
    entry["sha256"] = hashlib.sha256(body.encode()).hexdigest()
    out.write_text(json.dumps(entry, indent=1))
    return out


def reference_quantiles(target_id, monday):
    """The naive reference each score is compared against: last week's value
    (quakes) or plain climatology (temperature), as a flat point forecast."""
    if target_id == "quakes_m45":
        weekly = data.quake_weekly_history()
        past = weekly[weekly["week"] < np.datetime64(monday)]
        last = float(past.iloc[-1]["count"])
        return np.full(len(QUANTILES), last)
    spec = TARGETS[target_id]
    cache = "tmax_nyc.csv" if target_id == "nyc_tmax" else "tmax_sea.csv"
    daily = data.tmax_daily_history(spec["lat"], spec["lon"], spec["tz"],
                                    cache_name=cache)
    q = tmax_week_quantiles(daily[daily["time"] < np.datetime64(monday)],
                            monday, trend_years=100, spread=1.0)
    med = float(np.quantile(q, 0.5))
    return np.full(len(QUANTILES), med)


def fetch_truth(target_id, monday):
    a, b = week_bounds(monday)
    if target_id == "quakes_m45":
        from datetime import timedelta
        return float(data.quake_count(a, b + timedelta(days=1)))
    spec = TARGETS[target_id]
    return data.tmax_week_truth(spec["lat"], spec["lon"], spec["tz"], a)


def score_matured(today=None):
    """Score every round whose targets have matured and are not yet scored."""
    today = today or date.today()
    done = []
    for f in sorted(FORECASTS.glob("*.json")):
        monday = date.fromisoformat(f.stem)
        out = SCORES / f.name
        if out.exists():
            continue
        if not all(is_mature(monday, t, today) for t in TARGETS):
            continue
        fc = json.loads(f.read_text())
        rec = {"round": fc["round"], "scored_on": today.isoformat(),
               "targets": {}}
        for tid, t in fc["targets"].items():
            truth = fetch_truth(tid, monday)
            q = np.array(t["quantiles"])
            ref = reference_quantiles(tid, monday)
            rec["targets"][tid] = {
                "truth": truth,
                "wis": round(wis(truth, q), 3),
                "reference_wis": round(wis(truth, ref), 3),
                "skill": round(skill_vs(truth, q, ref), 3),
                **interval_hits(truth, q),
            }
        out.write_text(json.dumps(rec, indent=1))
        done.append(out)
    return done


def ledger():
    """Everything, joined, for the scoreboard and the tests."""
    rounds = []
    for f in sorted(FORECASTS.glob("*.json")):
        fc = json.loads(f.read_text())
        sc_path = SCORES / f.name
        sc = json.loads(sc_path.read_text()) if sc_path.exists() else None
        rounds.append({"forecast": fc, "score": sc})
    return rounds
