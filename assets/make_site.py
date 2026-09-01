"""The public scoreboard. One self-contained page, rebuilt by the weekly job.

Every row links to the forecast file's git history, because the commit
timestamp, not my say-so, is the proof it was made before the outcome.
"""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from asotele.protocol import ledger
from asotele.targets import QUANTILES, TARGETS

REPO = "https://github.com/Kenny0bi/asotele"


def target_rows(rounds):
    rows = []
    for r in rounds:
        fc, sc = r["forecast"], r["score"]
        for tid, t in fc["targets"].items():
            q = t["quantiles"]
            row = {
                "round": fc["round"], "made_on": fc["made_on"], "target": tid,
                "median": q[11], "lo50": q[6], "hi50": q[16],
                "lo95": q[2], "hi95": q[20],
            }
            if sc and tid in sc["targets"]:
                row.update(sc["targets"][tid])
            rows.append(row)
    return rows


def build():
    rounds = ledger()
    rows = target_rows(rounds)
    scored = [r for r in rows if "truth" in r]
    n_rounds = len(rounds)
    n_scored_rounds = len({r["round"] for r in scored})

    tally = {}
    if scored:
        sk = [r["skill"] for r in scored if np.isfinite(r.get("skill", np.nan))]
        tally = {
            "n": len(scored),
            "mean_skill": float(np.mean(sk)) if sk else None,
            "beat_reference": int(sum(s < 1 for s in sk)),
            "cov50": float(np.mean([r["in50"] for r in scored])),
            "cov80": float(np.mean([r["in80"] for r in scored])),
            "cov95": float(np.mean([r["in95"] for r in scored])),
        }

    def fmt_pending(r):
        return (f'<tr>'
                f'<td><a href="{REPO}/commits/main/forecasts/{r["round"]}.json">'
                f'{r["round"]}</a></td>'
                f'<td>{TARGETS[r["target"]]["name"]}</td>'
                f'<td class="num">{r["median"]:g}</td>'
                f'<td class="num">{r["lo50"]:g} to {r["hi50"]:g}</td>'
                f'<td class="num">{r["lo95"]:g} to {r["hi95"]:g}</td>'
                f'<td class="dim">made {r["made_on"]}, awaiting the outcome</td>'
                f'</tr>')

    def fmt_scored(r):
        hit = "hit" if r["in80"] else "miss"
        skill = r.get("skill")
        s_txt = (f'{skill:.2f}' if skill is not None and np.isfinite(skill)
                 else "n/a")
        return (f'<tr class="{hit}">'
                f'<td><a href="{REPO}/commits/main/forecasts/{r["round"]}.json">'
                f'{r["round"]}</a></td>'
                f'<td>{TARGETS[r["target"]]["name"]}</td>'
                f'<td class="num">{r["median"]:g} '
                f'<span class="dim">[{r["lo80" if "lo80" in r else "lo50"]:g}'
                f'..]</span></td>'
                f'<td class="num truth">{r["truth"]:g}</td>'
                f'<td class="num">{r["wis"]:.2f}</td>'
                f'<td class="num">{s_txt}</td>'
                f'<td>{"inside" if r["in80"] else "OUTSIDE"} the 80% interval</td>'
                f'</tr>')

    pending = [r for r in rows if "truth" not in r]
    pending_html = "\n".join(fmt_pending(r) for r in reversed(pending))
    scored_html = "\n".join(fmt_scored(r) for r in reversed(scored))

    tally_html = ""
    if tally:
        tally_html = f"""
  <div class="stat-row">
    <div class="stat"><b>{tally['n']}</b><span>forecasts scored</span></div>
    <div class="stat"><b>{tally['beat_reference']}/{tally['n']}</b><span>beat the naive reference</span></div>
    <div class="stat"><b>{100*tally['cov80']:.0f}%</b><span>of outcomes inside the 80% interval (target 80%)</span></div>
    <div class="stat"><b>{100*tally['cov95']:.0f}%</b><span>inside the 95% (target 95%)</span></div>
  </div>"""
    else:
        tally_html = """
  <p class="dim">No forecast has matured yet. The first scores appear
  automatically once the first target week ends and its revision window
  passes. Until then, the only honest scoreboard is an empty one.</p>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>asotele: a public forecast ledger</title>
<style>
  :root {{ --paper:#10151A; --panel:#19212B; --ink:#E8EDF2; --dim:#8695A4;
          --rule:#27333F; --good:#4ECDC4; --bad:#FF6B6B; --gold:#F4A259; }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ background:var(--paper); color:var(--ink); font-size:15px;
    font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace;
    line-height:1.55; }}
  .serif {{ font-family:'Iowan Old Style',Palatino,Georgia,serif; }}
  main {{ max-width:1060px; margin:0 auto; padding:0 22px 110px; }}
  header {{ padding:78px 0 8px; }}
  .kicker {{ font-size:11px; letter-spacing:.22em; color:var(--dim); }}
  h1 {{ font-size:clamp(30px,5vw,50px); margin:12px 0 14px; font-weight:600; }}
  .standfirst {{ color:var(--dim); max-width:48em;
                 font-size:clamp(15px,2vw,18px); }}
  h2 {{ font-size:clamp(19px,3vw,26px); margin:56px 0 12px; font-weight:600; }}
  p {{ max-width:46em; margin:10px 0; }}
  .dim {{ color:var(--dim); }}
  .stat-row {{ display:flex; gap:34px; flex-wrap:wrap; margin:26px 0; }}
  .stat b {{ display:block; font-size:clamp(24px,4vw,40px);
             font-family:Georgia,serif; }}
  .stat span {{ font-size:12px; color:var(--dim); }}
  table {{ border-collapse:collapse; width:100%; margin:16px 0;
           font-size:13px; }}
  th {{ text-align:left; color:var(--dim); font-weight:normal; font-size:11px;
       letter-spacing:.08em; padding:8px 10px;
       border-bottom:1px solid var(--rule); }}
  td {{ padding:9px 10px; border-bottom:1px solid var(--rule);
       vertical-align:top; }}
  td.num {{ font-variant-numeric:tabular-nums; }}
  td.truth {{ color:var(--gold); font-weight:bold; }}
  tr.hit td:last-child {{ color:var(--good); }}
  tr.miss td:last-child {{ color:var(--bad); font-weight:bold; }}
  a {{ color:var(--good); }}
  .rules {{ background:var(--panel); border-left:3px solid var(--rule);
            padding:16px 20px; margin:22px 0; font-size:13.5px;
            color:var(--dim); max-width:52em; }}
  .rules b {{ color:var(--ink); }}
</style>
</head>
<body>
<main>
<header>
  <div class="kicker">ASOTELE&nbsp;&nbsp;/&nbsp;&nbsp;A PUBLIC FORECAST LEDGER</div>
  <h1 class="serif">Forecasts, filed before the fact</h1>
  <p class="standfirst serif">Every week this repository commits probabilistic
  forecasts of verifiable public quantities, then scores them against what
  actually happened, by a proper scoring rule, forever. Nothing is deleted and
  nothing can be: the git history is the notary.</p>
</header>

{tally_html}

<div class="rules">
  <b>The rules, fixed in advance.</b> Forecasts are 23 quantiles, committed
  before the target week begins (the commit timestamp on each linked file is
  the proof). Outcomes are decided by resolution procedures written per target
  in <a href="{REPO}/blob/main/asotele/targets.py">targets.py</a>, after a
  waiting period that lets source revisions settle. Scoring is the weighted
  interval score, a proper rule: the expected score is minimised by honest
  forecasts, so the only way to look good on this page is to be right.
  A bad week stays on the ledger with the same weight as a good one.
</div>

<h2 class="serif">Open forecasts</h2>
<p class="dim">Filed and frozen. The outcome does not exist yet.</p>
<table>
<tr><th>target week</th><th>quantity</th><th>median</th><th>50% interval</th>
<th>95% interval</th><th>status</th></tr>
{pending_html}
</table>

<h2 class="serif">The record</h2>
<table>
<tr><th>target week</th><th>quantity</th><th>forecast median</th>
<th>outcome</th><th>score (WIS)</th><th>vs naive</th><th>calibration</th></tr>
{scored_html if scored_html else '<tr><td colspan="7" class="dim">nothing has matured yet</td></tr>'}
</table>

<h2 class="serif">What is being forecast</h2>
{"".join(f'<p><b>{t["name"]}</b> ({t["units"]}). <span class="dim">{t["truth"]}</span></p>' for t in TARGETS.values())}

<footer style="margin-top:70px;padding-top:20px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--dim)">
  <p>Models are deliberately simple and validated by backtest before launch
  (held-out coverage 0.50/0.80/0.97 for the earthquake target against nominal
  0.50/0.80/0.95; details in <a href="{REPO}">the repository</a>). The point
  of this page is not the models. It is the protocol: filed first, scored by a
  rule, kept forever.</p>
  <p style="margin-top:8px">asotele is Yoruba for prophecy. Kenny Obidele.</p>
</footer>
</main>
</body>
</html>
"""
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"scoreboard: {n_rounds} rounds, {n_scored_rounds} scored, "
          f"{len(pending)} open forecasts -> {out}")


if __name__ == "__main__":
    build()
