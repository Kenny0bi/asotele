"""The figures, hand-built SVG. Dark ledger theme matching the scoreboard."""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GROUND = "#10151A"
PANEL = "#19212B"
INK = "#E8EDF2"
DIM = "#8695A4"
GRID = "#27333F"
GOOD = "#4ECDC4"
BAD = "#FF6B6B"
GOLD = "#F4A259"
VIOLET = "#A78BFA"
SERIF = "'Iowan Old Style', Palatino, Georgia, serif"
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace")

import html as _html


def esc(s):
    return _html.escape(str(s), quote=True)


def T(x, y, s, size=12, fill=INK, anchor="start", weight="normal",
      family=None, opacity=1.0, ls=None):
    a = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-size="{size}"',
         f'fill="{fill}"', f'text-anchor="{anchor}"']
    if weight != "normal":
        a.append(f'font-weight="{weight}"')
    if family:
        a.append(f'font-family="{family}"')
    if opacity != 1:
        a.append(f'opacity="{opacity}"')
    if ls:
        a.append(f'letter-spacing="{ls}"')
    return f'<text {" ".join(a)}>{esc(s) if "<" not in str(s) else s}</text>'


def L(x1, y1, x2, y2, stroke=GRID, w=1.0, op=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" opacity="{op}"{d}/>')


def R(x, y, w, h, fill, op=1.0, rx=0):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" '
            f'height="{max(h,0):.1f}" fill="{fill}" opacity="{op}" rx="{rx}"/>')


def C(cx, cy, r, fill, op=1.0, stroke=None, sw=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
            f'opacity="{op}"{s}/>')


def PL(pts, stroke, w=1.5, op=1.0, dash=None):
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{w}" '
            f'opacity="{op}" stroke-linejoin="round"{da}/>')


def BAND(top, bot, fill, op):
    d = ("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in top)
         + " L " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in reversed(bot))
         + " Z")
    return f'<path d="{d}" fill="{fill}" opacity="{op}"/>'


def head(W, H, title, sub, kicker):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
        R(0, 0, W, H, GROUND),
        T(40, 42, kicker, 11, DIM, ls=2.2),
        T(40, 80, title, 29, INK, family=SERIF),
        T(40, 106, sub, 13, DIM),
    ]


def close(p, name):
    p.append("</svg>")
    (ROOT / "assets" / name).write_text("\n".join(p))
    print(name)


# --------------------------------------------------------------- calibration

def fig_calibration():
    bt = pd.read_csv(ROOT / "benchmarks" / "backtest.csv",
                     parse_dates=["monday"])
    later = bt[bt["monday"] >= bt["monday"].max() - pd.Timedelta(days=455)]
    chosen = later[later["model"].isin(
        ["10y window", "climatology + trend + spread"])]

    W, H = 1320, 700
    p = head(W, H, "Calibrated before a single forecast was filed",
             "130-week backtest, settings frozen on the earlier half, "
             "coverage reported on the held-out later half.",
             "ASOTELE  /  THE PRE-LAUNCH EVIDENCE")

    names = {"quakes_m45": "earthquakes M4.5+",
             "nyc_tmax": "NYC warmest day", "sea_tmax": "Seattle warmest day"}
    x0, pw, gap = 120, 330, 60
    y0, ph = 240, 300

    for i, (tid, g) in enumerate(chosen.groupby("target")):
        px = x0 + i * (pw + gap)
        p.append(T(px, y0 - 40, names[tid], 14, INK))
        p.append(T(px, y0 - 22, f"{len(g)} held-out weeks", 10.5, DIM))
        p.append(R(px, y0, pw, ph, PANEL, 0.4, rx=3))
        for j, nominal in enumerate((0.5, 0.8, 0.95)):
            col = f"in{int(nominal*100)}"
            actual = float(g[col].mean())
            cx = px + pw * (j + 0.5) / 3
            bar_h = ph * 0.78
            yb = y0 + ph - 26
            p.append(R(cx - 34, yb - bar_h * nominal, 30, bar_h * nominal,
                       GRID, 0.9, rx=2))
            good = abs(actual - nominal) < 0.08
            p.append(R(cx + 4, yb - bar_h * actual, 30, bar_h * actual,
                       GOOD if good else GOLD, 0.95, rx=2))
            p.append(T(cx - 19, yb - bar_h * nominal - 8,
                       f"{int(nominal*100)}%", 10.5, DIM, anchor="middle"))
            p.append(T(cx + 19, yb - bar_h * actual - 8,
                       f"{100*actual:.0f}%", 10.5,
                       GOOD if good else GOLD, anchor="middle"))
            p.append(T(cx, yb + 18, "interval", 9.5, DIM, anchor="middle"))

    p.append(T(120, y0 + ph + 64,
               "grey is the promise, colour is the delivery. A ledger whose "
               "intervals do not hold their stated rates is theatre, so this "
               "was measured first.", 12, DIM))
    p.append(T(W - 40, H - 24, "benchmarks/backtest.py", 10, DIM,
               anchor="end"))
    close(p, "calibration.svg")


# ----------------------------------------------------------------- the quake

def fig_quakes():
    weekly = pd.read_csv(ROOT / "data" / "quakes_weekly.csv",
                         parse_dates=["week"])
    fc = json.loads(sorted((ROOT / "forecasts").glob("*.json"))[-1].read_text())
    q = fc["targets"]["quakes_m45"]["quantiles"]

    W, H = 1320, 680
    Lm, Rm, Tm, Bm = 90, 1140, 200, 560
    lo, hi = 0, 480
    t0, t1 = weekly["week"].min(), pd.Timestamp(fc["round"]) + pd.Timedelta(days=40)

    def X(t):
        return Lm + (Rm - Lm) * ((t - t0) / (t1 - t0))

    def Y(v):
        return Bm - (Bm - Tm) * (min(v, hi) - lo) / (hi - lo)

    p = head(W, H, "Twelve years of weeks, and the first wager",
             "Weekly count of M4.5+ earthquakes worldwide, and the quantiles "
             "this ledger has filed for the week ahead.",
             "ASOTELE  /  THE FIRST ROUND, IN CONTEXT")

    for v in range(0, 481, 120):
        p.append(L(Lm, Y(v), Rm, Y(v), GRID, 1, 0.5, dash="2 6"))
        p.append(T(Lm - 12, Y(v) + 4, str(v), 10.5, DIM, anchor="end"))
    for yr in range(2014, 2027, 2):
        t = pd.Timestamp(f"{yr}-01-01")
        p.append(T(X(t), Bm + 22, str(yr), 10.5, DIM, anchor="middle"))

    pts = [(X(t), Y(v)) for t, v in zip(weekly["week"], weekly["count"])]
    p.append(PL(pts, GOOD, 1.0, 0.75))

    # weeks beyond the axis, each labelled with its own date: assuming a
    # narrative for a spike is how I nearly mislabelled the Kamchatka
    # sequence as Turkey-Syria
    over = weekly[weekly["count"] > hi]
    for _, r in over.iterrows():
        p.append(T(X(r["week"]), Tm - 22, f"{int(r['count'])}", 10, BAD,
                   anchor="middle"))
        p.append(T(X(r["week"]), Tm - 10,
                   r["week"].strftime("%b %Y"), 8.5, DIM, anchor="middle"))
        p.append(L(X(r["week"]), Tm, X(r["week"]), Tm + 14, BAD, 1.6))
    p.append(T(Lm, Tm - 22, "off this axis:", 10.5, BAD))

    # the filed fan
    fx = X(pd.Timestamp(fc["round"]) + pd.Timedelta(days=3))
    pairs = [(2, 20, 0.16), (6, 16, 0.30)]
    for li, ui, op in pairs:
        p.append(R(fx - 9, Y(q[ui]), 18, Y(q[li]) - Y(q[ui]), GOLD, op, rx=3))
    p.append(L(fx - 12, Y(q[11]), fx + 12, Y(q[11]), GOLD, 3))
    p.append(T(fx + 18, Y(q[11]) + 4, f"filed median {q[11]:.0f}", 11.5, GOLD))
    p.append(T(fx + 18, Y(q[2]) + 4, f"95% up to {q[20]:.0f}", 10.5, DIM))
    p.append(T(fx, Bm + 40, f"the filed week: {fc['round']}", 11, GOLD,
               anchor="end"))

    p.append(T(W - 40, H - 24,
               "USGS fdsnws, M>=4.5 worldwide, 660 complete weeks", 10, DIM,
               anchor="end"))
    close(p, "quakes.svg")


# ------------------------------------------------------------------ seasonal

def fig_seasonal():
    from asotele.models import tmax_week_quantiles
    daily = pd.read_csv(ROOT / "data" / "tmax_nyc.csv", parse_dates=["time"])
    fc = json.loads(sorted((ROOT / "forecasts").glob("*.json"))[-1].read_text())
    qf = fc["targets"]["nyc_tmax"]["quantiles"]

    mondays = pd.date_range("2025-01-06", "2025-12-29", freq="W-MON")
    ribbons = []
    for m in mondays:
        q = tmax_week_quantiles(daily[daily["time"] < m], m.date())
        ribbons.append((m.dayofyear, q))

    W, H = 1320, 680
    Lm, Rm, Tm, Bm = 90, 1140, 200, 560
    lo, hi = -6, 42

    def X(doy):
        return Lm + (Rm - Lm) * doy / 366

    def Y(v):
        return Bm - (Bm - Tm) * (v - lo) / (hi - lo)

    p = head(W, H, "The shape of a year, and where this week sits",
             "The model's quantile ribbon for New York's warmest day of the "
             "week, drawn for every week of a year.",
             "ASOTELE  /  CLIMATOLOGY WITH ITS UNCERTAINTY SHOWING")

    for v in range(0, 41, 10):
        p.append(L(Lm, Y(v), Rm, Y(v), GRID, 1, 0.5, dash="2 6"))
        p.append(T(Lm - 12, Y(v) + 4, f"{v}°C", 10.5, DIM, anchor="end"))
    for mth, lab in ((15, "Jan"), (74, "Mar"), (135, "May"), (196, "Jul"),
                     (258, "Sep"), (319, "Nov")):
        p.append(T(X(mth), Bm + 22, lab, 10.5, DIM, anchor="middle"))

    for li, ui, op in ((2, 20, 0.14), (6, 16, 0.26)):
        top = [(X(d), Y(q[ui])) for d, q in ribbons]
        bot = [(X(d), Y(q[li])) for d, q in ribbons]
        p.append(BAND(top, bot, VIOLET, op))
    med = [(X(d), Y(q[11])) for d, q in ribbons]
    p.append(PL(med, VIOLET, 2.2, 0.95))

    doy = pd.Timestamp(fc["round"]).dayofyear + 3
    p.append(L(X(doy), Tm - 6, X(doy), Bm, GOLD, 1.6, 0.9, dash="4 3"))
    p.append(C(X(doy), Y(qf[11]), 5, GOLD))
    p.append(T(X(doy) + 10, Y(qf[11]) - 10,
               f"this week's filing: median {qf[11]:.1f}°C, "
               f"95% [{qf[2]:.1f}, {qf[20]:.1f}]", 11.5, GOLD))

    p.append(T(Lm, Bm + 52,
               "bands are the filed 50% and 95% intervals; the ribbon is what "
               "the same model files in any other week of the year", 12, DIM))
    p.append(T(W - 40, H - 24,
               "Open-Meteo archive, 27 years of daily Tmax at Central Park",
               10, DIM, anchor="end"))
    close(p, "seasonal.svg")


# --------------------------------------------------------------------- skill

def fig_skill():
    bt = pd.read_csv(ROOT / "benchmarks" / "backtest.csv",
                     parse_dates=["monday"])
    chosen = bt[bt["model"].isin(["10y window",
                                  "climatology + trend + spread"])]

    W, H = 1320, 640
    Lm, Rm, Tm, Bm = 210, 1160, 210, 520
    p = head(W, H, "Every backtest week, scored like the ledger will be",
             "Weighted interval score per week across the 130-week walk, "
             "shown per target on its own scale.",
             "ASOTELE  /  WHAT NORMAL LOOKS LIKE")

    names = {"quakes_m45": ("earthquakes", GOOD),
             "nyc_tmax": ("NYC warmest day", GOLD),
             "sea_tmax": ("Seattle warmest day", VIOLET)}
    lanes = list(names)
    lane_h = (Bm - Tm) / len(lanes)

    t0, t1 = chosen["monday"].min(), chosen["monday"].max()

    def X(t):
        return Lm + (Rm - Lm) * ((t - t0) / (t1 - t0))

    for i, tid in enumerate(lanes):
        g = chosen[chosen["target"] == tid].sort_values("monday")
        base = Tm + (i + 1) * lane_h - 14
        label, col = names[tid]
        vmax = float(g["wis"].quantile(0.98)) * 1.1
        p.append(T(Lm - 14, base - lane_h * 0.35, label, 12, col, anchor="end"))
        p.append(L(Lm, base, Rm, base, GRID, 1, 0.6))
        med = float(g["wis"].median())
        for _, r in g.iterrows():
            h = min(r["wis"] / vmax, 1.0) * (lane_h * 0.78)
            p.append(L(X(r["monday"]), base, X(r["monday"]), base - h, col,
                       2.0, 0.75))
        p.append(L(Lm, base - min(med / vmax, 1) * lane_h * 0.78,
                   Rm, base - min(med / vmax, 1) * lane_h * 0.78,
                   INK, 1, 0.45, dash="3 4"))
        p.append(T(Rm + 10, base - min(med / vmax, 1) * lane_h * 0.78 + 4,
                   f"median {med:.1f}", 10.5, DIM))

    for yr in ("2024-07-01", "2025-01-01", "2025-07-01", "2026-01-01",
               "2026-07-01"):
        t = pd.Timestamp(yr)
        if t0 <= t <= t1:
            p.append(T(X(t), Bm + 24, yr[:7], 10, DIM, anchor="middle"))

    p.append(T(Lm, Bm + 52,
               "spikes are the weeks the world surprised the model; the "
               "ledger will grow the same picture in public, one week at a "
               "time", 12, DIM))
    close(p, "skill.svg")


if __name__ == "__main__":
    want = sys.argv[1:]
    for f in (fig_calibration, fig_quakes, fig_seasonal, fig_skill):
        if not want or f.__name__.replace("fig_", "") in want:
            f()
