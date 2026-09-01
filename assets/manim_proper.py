"""Why this ledger cannot be gamed: the pinball loss is a proper score.

The claim, made precise and then drawn: if the outcome Y has distribution F,
the expected pinball loss at level tau is minimised by stating the true
quantile q* = F^{-1}(tau). Say anything else, higher or lower, and your
expected score gets worse. So the only strategy that wins on the scoreboard is
believing your own forecast.

The curve on screen is computed from the same normal example the test suite
uses; the minimum lands exactly on the true 80th percentile.

Render (Manim CE lives only in the ember venv on this machine; needs TinyTeX
on PATH for real LaTeX):

  PATH="$HOME/Library/TinyTeX/bin/universal-darwin:/usr/local/bin:$PATH" \\
  ../ember/.venv/bin/manim -qh assets/manim_proper.py ProperScore
"""

import numpy as np
from manim import *
from scipy import stats

GROUND = "#10151A"
INK = "#E8EDF2"
DIM = "#8695A4"
GOOD = "#4ECDC4"
BAD = "#FF6B6B"
GOLD = "#F4A259"

TAU = 0.8
MU, SD = 100.0, 15.0
QSTAR = float(stats.norm.ppf(TAU, MU, SD))


def expected_pinball(q):
    """E[pinball_tau(Y, q)] for Y ~ N(MU, SD), in closed form via simulation."""
    rng = np.random.default_rng(0)
    y = rng.normal(MU, SD, 200000)
    d = y - q
    return float(np.mean(np.where(d >= 0, TAU * d, (TAU - 1) * d)))


class ProperScore(Scene):
    def construct(self):
        self.camera.background_color = GROUND

        title = Text("Why the scoreboard cannot be gamed", font_size=38,
                     color=INK)
        sub = Text("the pinball loss is a proper score", font_size=23,
                   color=DIM).next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(title, shift=UP * 0.3), run_time=1.1)
        self.play(FadeIn(sub), run_time=0.6)
        self.wait(1.1)
        self.play(FadeOut(title), FadeOut(sub), run_time=0.6)

        # ------------------------------------------------------- the setup
        setup = VGroup(
            Text("You must state the 80th percentile of next week's number.",
                 font_size=24, color=INK),
            Text("You will be scored, in public, when it lands.",
                 font_size=24, color=DIM),
        ).arrange(DOWN, buff=0.3).to_edge(UP, buff=0.7)
        self.play(FadeIn(setup), run_time=0.9)

        loss = MathTex(
            r"L_\tau(y, q) \;=\; \begin{cases}"
            r"\tau\,(y - q) & y \ge q\\[2pt]"
            r"(1-\tau)\,(q - y) & y < q\end{cases}",
            font_size=40).set_color(INK)
        loss.next_to(setup, DOWN, buff=0.6)
        self.play(Write(loss), run_time=2.0)
        note = Text("miss from below and pay 0.8 per unit; from above, 0.2",
                    font_size=21, color=DIM).next_to(loss, DOWN, buff=0.35)
        self.play(FadeIn(note), run_time=0.7)
        self.wait(1.6)
        self.play(FadeOut(setup), FadeOut(loss), FadeOut(note), run_time=0.7)

        # ------------------------------------------- the expected-loss curve
        ax = Axes(x_range=[85, 145, 10], y_range=[3.5, 9.0, 1],
                  x_length=9.6, y_length=4.6,
                  axis_config={"color": DIM, "stroke_width": 2,
                               "include_tip": False, "font_size": 20},
                  x_axis_config={"numbers_to_include": [90, 100, 110, 120,
                                                        130, 140]})
        ax.shift(DOWN * 0.6)
        xl = Text("the quantile you choose to state", font_size=20, color=DIM)
        xl.next_to(ax, DOWN, buff=0.4)
        yl = Text("expected score (lower is better)", font_size=20, color=DIM)
        yl.rotate(PI / 2).next_to(ax.y_axis, LEFT, buff=0.35)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), run_time=1.2)

        curve = ax.plot(lambda q: expected_pinball(q), x_range=[86, 144, 1.0],
                        color=GOOD, stroke_width=4)
        self.play(Create(curve), run_time=2.0)

        qdot = Dot(ax.c2p(QSTAR, expected_pinball(QSTAR)), color=GOLD,
                   radius=0.09)
        qline = DashedLine(ax.c2p(QSTAR, 3.5),
                           ax.c2p(QSTAR, expected_pinball(QSTAR)),
                           color=GOLD, stroke_width=3, dash_length=0.12)
        qlab = MathTex(rf"q^* = F^{{-1}}(0.8) = {QSTAR:.1f}", font_size=32,
                       color=GOLD)
        qlab.next_to(qdot, UP, buff=0.9)
        self.play(Create(qline), FadeIn(qdot), Write(qlab), run_time=1.4)
        truth = Text("the minimum sits exactly on the true quantile",
                     font_size=22, color=GOLD).to_edge(UP, buff=0.7)
        self.play(FadeIn(truth), run_time=0.8)
        self.wait(1.4)

        # ---------------------------------------------------- try to game it
        for q_try, label, colour in ((128.0, "overstate it, score worse", BAD),
                                     (101.0, "understate it, score worse", BAD)):
            d = Dot(ax.c2p(q_try, expected_pinball(q_try)), color=colour,
                    radius=0.09)
            lab = Text(label, font_size=21, color=colour)
            lab.next_to(d, UR if q_try > QSTAR else UL, buff=0.2)
            self.play(FadeIn(d), FadeIn(lab), run_time=0.9)
            self.wait(0.7)
            self.play(FadeOut(d), FadeOut(lab), run_time=0.4)

        moral = Text("stating anything but your true belief costs you,\n"
                     "in expectation, every single week",
                     font_size=23, color=INK, line_spacing=0.9)
        moral.next_to(truth, DOWN, buff=0.35)
        self.play(Transform(truth, moral), run_time=1.0)
        self.wait(1.9)

        self.play(FadeOut(truth), FadeOut(curve), FadeOut(ax), FadeOut(xl),
                  FadeOut(yl), FadeOut(qdot), FadeOut(qline), FadeOut(qlab),
                  run_time=0.9)

        end = Text("asotele", font_size=46, color=GOOD)
        end2 = Text("forecasts filed before the fact, scored by a proper rule",
                    font_size=21, color=DIM).next_to(end, DOWN, buff=0.3)
        self.play(FadeIn(end, shift=UP * 0.2), FadeIn(end2), run_time=1.1)
        self.wait(1.6)
