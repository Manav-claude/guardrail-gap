"""Vendor-agnostic stateful wrappers (spec §7). These operate on the per-turn
`last`-config score stream a product already produced, so they add state
without new API calls.

- CUSUM: S_t = max(0, S_{t-1} + (r_t - delta)); alarm if S_t > h. Detects
  gradual escalation that no single-turn threshold catches.
- BSD buffer: keep the m highest-scoring prior turns as context (conceptual
  precedent; implemented at scoring time by the runner when enabled).

Calibration picks (delta, h) on benign score streams to hit a target FPR.
"""
from __future__ import annotations
import numpy as np


def cusum_alarm_turn(r_series: list[float], delta: float, h: float) -> int | None:
    """First turn index (1-based) where the CUSUM statistic exceeds h, else None."""
    S = 0.0
    for t, r in enumerate(r_series, start=1):
        S = max(0.0, S + (r - delta))
        if S > h:
            return t
    return None


def cusum_detect(r_series: list[float], delta: float, h: float) -> int:
    return 1 if cusum_alarm_turn(r_series, delta, h) is not None else 0


def calibrate_cusum(benign_streams: list[list[float]], target_fpr: float,
                    delta_grid=None, h_grid=None) -> tuple[float, float]:
    """Grid-search (delta, h) so the benign false-positive rate <= target_fpr,
    preferring the setting that alarms earliest on average (most sensitive
    subject to the FPR budget). Returns (delta, h)."""
    allr = [r for s in benign_streams for r in s]
    if delta_grid is None:
        qs = np.quantile(allr, [0.5, 0.7, 0.8, 0.9]) if allr else [0.3, 0.5]
        delta_grid = sorted(set(float(q) for q in qs))
    if h_grid is None:
        h_grid = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    best = (delta_grid[-1], h_grid[-1], -1.0)   # (delta, h, sensitivity)
    for delta in delta_grid:
        for h in h_grid:
            fires = [cusum_detect(s, delta, h) for s in benign_streams]
            fpr = float(np.mean(fires)) if fires else 1.0
            if fpr <= target_fpr:
                # most sensitive setting within the budget = the one that uses the
                # most of the benign FPR allowance (lower h / lower delta fire more).
                sens = fpr
                if sens > best[2]:
                    best = (delta, h, sens)
    return best[0], best[1]


def bsd_buffer_units(turns: list[str], scores: list[float], m: int = 3):
    """Yield, per turn, the unit = concatenation of the m highest-scoring prior
    user turns plus the current turn (spec §7.3). For runner integration."""
    buf: list[tuple[float, str]] = []
    for u, r in zip(turns, scores):
        unit = "\n".join([b for _, b in sorted(buf, reverse=True)[:m]] + [u])
        yield unit
        buf.append((r, u))
