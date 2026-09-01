"""Fetching history and truth. Every request keyless, every source public.

History fetches are cached to data/ so the weekly job stays light and the
backtest is reproducible from the committed cache.
"""

import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
UA = {"User-Agent": "asotele public forecast ledger "
                    "(github.com/Kenny0bi/asotele)"}

USGS = "https://earthquake.usgs.gov/fdsnws/event/1"
METEO = "https://archive-api.open-meteo.com/v1/archive"


def _get(url, params, retries=3):
    for i in range(retries):
        r = requests.get(url, params=params, headers=UA, timeout=60)
        if r.ok:
            return r
        time.sleep(2 * (i + 1))
    r.raise_for_status()


def quake_count(start, end):
    """Count of M4.5+ events in [start, end) UTC. This IS the truth query."""
    r = _get(f"{USGS}/count", {
        "format": "geojson", "starttime": start.isoformat(),
        "endtime": end.isoformat(), "minmagnitude": 4.5})
    return int(r.json()["count"])


def quake_weekly_history(years=12, refresh=False):
    """Weekly M4.5+ counts, built from yearly count-by-week caching.

    Fetched as one catalogue query per year (the API caps at 20,000 events and
    a year of M4.5+ runs about 7,000), binned locally into Monday weeks.
    """
    cache = DATA / "quakes_weekly.csv"
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["week"])
        return df
    end = date.today()
    start = date(end.year - years, 1, 1)
    frames = []
    for yr in range(start.year, end.year + 1):
        a = date(yr, 1, 1)
        b = min(date(yr + 1, 1, 1), end)
        r = _get(f"{USGS}/query", {
            "format": "csv", "starttime": a.isoformat(),
            "endtime": b.isoformat(), "minmagnitude": 4.5,
            "orderby": "time-asc"})
        from io import StringIO
        frames.append(pd.read_csv(StringIO(r.text), usecols=["time", "mag"]))
        time.sleep(1)
    ev = pd.concat(frames, ignore_index=True)
    ev["time"] = pd.to_datetime(ev["time"], format="ISO8601", utc=True)
    ev["week"] = (ev["time"] - pd.to_timedelta(
        ev["time"].dt.weekday, unit="D")).dt.floor("D").dt.tz_localize(None)
    weekly = ev.groupby("week").size().rename("count").reset_index()
    # drop the first and last partial weeks
    weekly = weekly.iloc[1:-1].reset_index(drop=True)
    weekly.to_csv(cache, index=False)
    return weekly


def tmax_daily_history(lat, lon, tz, start="2000-01-01", end=None,
                       cache_name=None, refresh=False):
    """Daily Tmax from the Open-Meteo archive, cached."""
    cache = DATA / (cache_name or f"tmax_{lat}_{lon}.csv")
    if cache.exists() and not refresh:
        return pd.read_csv(cache, parse_dates=["time"])
    end = end or (date.today() - timedelta(days=6)).isoformat()
    r = _get(METEO, {
        "latitude": lat, "longitude": lon, "daily": "temperature_2m_max",
        "start_date": start, "end_date": end, "timezone": tz})
    d = r.json()["daily"]
    df = pd.DataFrame({"time": pd.to_datetime(d["time"]),
                       "tmax": d["temperature_2m_max"]})
    df = df.dropna().reset_index(drop=True)
    df.to_csv(cache, index=False)
    return df


def tmax_week_truth(lat, lon, tz, monday):
    """Truth for a Tmax target: max daily Tmax over the 7 local days."""
    sunday = monday + timedelta(days=6)
    r = _get(METEO, {
        "latitude": lat, "longitude": lon, "daily": "temperature_2m_max",
        "start_date": monday.isoformat(), "end_date": sunday.isoformat(),
        "timezone": tz})
    vals = [v for v in r.json()["daily"]["temperature_2m_max"]
            if v is not None]
    if len(vals) < 6:
        raise RuntimeError(f"only {len(vals)} of 7 days available for "
                           f"{monday}; truth is not ready")
    return float(max(vals))
