"""What gets forecast, and exactly how the truth is decided.

A public track record is only as honest as its resolution rules, so every
target carries its truth procedure in writing: which API, which query, and how
long after the week ends it is allowed to be called. Ambiguity here is how
forecasters grade their own homework.

Weeks run Monday to Sunday. The reference date of a round is the Monday the
target week begins, and a forecast is only valid if its commit predates that
Monday 00:00 UTC, which the git history proves.
"""

from datetime import date, timedelta

# The 23 quantile levels a forecast states. Shared with my FluSight work
# (harmattan), because a track record is more legible when every entry speaks
# the same language.
QUANTILES = [0.01, 0.025, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
             0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90,
             0.95, 0.975, 0.99]

TARGETS = {
    "quakes_m45": {
        "name": "Earthquakes of magnitude 4.5 or greater, worldwide",
        "units": "count in the target week",
        "kind": "count",
        "truth": ("USGS fdsnws event count, minmagnitude=4.5, over the target "
                  "week in UTC, queried no earlier than 7 days after the week "
                  "ends. The catalogue is revised for a few days after an "
                  "event; the 7-day wait lets magnitudes settle, and whatever "
                  "the API returns at scoring time is final for the ledger."),
        "mature_days": 7,
    },
    "nyc_tmax": {
        "name": "Warmest daily maximum in Central Park, New York",
        "units": "degrees C over the target week",
        "kind": "continuous",
        "lat": 40.7789, "lon": -73.9692, "tz": "America/New_York",
        "truth": ("Open-Meteo archive API, daily temperature_2m_max at "
                  "40.7789N 73.9692W, maximum over the 7 local days of the "
                  "target week, queried no earlier than 7 days after the week "
                  "ends."),
        "mature_days": 7,
    },
    "sea_tmax": {
        "name": "Warmest daily maximum at Seattle-Tacoma",
        "units": "degrees C over the target week",
        "kind": "continuous",
        "lat": 47.4444, "lon": -122.3139, "tz": "America/Los_Angeles",
        "truth": ("Open-Meteo archive API, daily temperature_2m_max at "
                  "47.4444N 122.3139W, maximum over the 7 local days of the "
                  "target week, queried no earlier than 7 days after the week "
                  "ends."),
        "mature_days": 7,
    },
}


def next_monday(today=None):
    """The Monday that starts the next full week after `today`."""
    t = today or date.today()
    days = (7 - t.weekday()) % 7
    if days == 0:
        days = 7
    return t + timedelta(days=days)


def week_bounds(monday):
    """[start, end] dates of a Monday-to-Sunday week."""
    return monday, monday + timedelta(days=6)


def is_mature(monday, target_id, today=None):
    """May this round's target be scored yet?"""
    t = today or date.today()
    _, sunday = week_bounds(monday)
    return t >= sunday + timedelta(days=TARGETS[target_id]["mature_days"])
