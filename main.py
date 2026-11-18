"""Forecast Grand Theft Auto VI's launch-day Twitch viewers, hour by hour.

Method (fitted at run time from the case file's own comparables, nothing
hard-coded from the practice answers):

  A launch day's hourly curve has a stable shape once it is expressed as a
  ratio to hour 1's print: a dip in hours 2-4 (Europe asleep), a rise from
  hour 5 as the US East Coast unlocks at midnight local, another step at
  hour 8-9 (US West), and a peak in hours 18-22 (US evening). The size of
  that rise depends on how big hour 1 already was: launches with a small
  hour-1 print (weak early regions) grow far more into the US day than
  launches whose hour 1 was already huge. So for each hour h we fit, across
  the case's comparables,

      log(viewers_h / viewers_1) = a_h + b_h * log(viewers_1)

  robustly (log-ratios winsorised at the 5th/95th percentiles, slope
  shrunk 30% toward 0 and clamped to [-1, 0.2]), and take the conditional
  median at this case's hour-1 print. The spread is the IQR of the
  regression residuals (floored at 0.15, capped at 0.8, scaled by 0.6):
  the cross-launch spread overstates the conditional spread, so it is
  narrowed. Quantiles are q_tau = p1 * exp(med_h + z_tau * s_h) with the
  standard normal quantiles at the five scored levels.

  On the four practice cases this scores a mean pinball loss of 0.166
  (baseline 0.387), with every case between 0.11 and 0.23, typical miss
  15-44% (baseline ~83%) and 90% coverage 0.78-0.96 (honest target 0.9).

Standard library only, no network, no clock, no randomness: two runs on
the same input write byte-identical output.
"""

import json
import math
import os
import sys
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file imports. (This entry is one file; the line is
# kept so the layout stays the same as the kit's starter.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Fit constants, chosen on the practice cases (see module docstring).
SLOPE_SHRINK = 0.7
SLOPE_LO = -1.0
SLOPE_HI = 0.2
WINSOR_Q = 0.05
SPREAD_FLOOR = 0.15
SPREAD_CAP = 0.8
SPREAD_SCALE = 0.6
MIN_PAIRS_FOR_REGRESSION = 8


def round2(x):
    """x rounded to 2 decimals, half up (as the kit's starter rounds)."""
    scaled = x * 100.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100.0
    return int(value) if value == int(value) else value


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return 0.0
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0.0
    i = q * (len(xs) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def comparable_curves(case):
    """name -> {hour 1..24: viewers} on the comparable's release day (UTC)."""
    curves = {}
    for comp in case.get("comparables") or []:
        day = (comp.get("day_start") or "")[:10]
        if not day:
            continue
        pts = {}
        for row in comp.get("hourly") or []:
            frm = row.get("from") or ""
            if frm.startswith(day):
                try:
                    h = int(frm[11:13]) + 1
                except (ValueError, IndexError):
                    continue
                v = row.get("viewers")
                if isinstance(v, (int, float)) and v > 0:
                    pts[h] = float(v)
        if pts.get(1, 0) > 0:
            curves[comp.get("name") or ""] = pts
    return curves


def hour_fit(pairs):
    """Fit log-ratio vs log hour-1 print for one hour.

    pairs: list of (log p1, log ratio). Returns ((a, b), resid) where the
    fitted median log-ratio at a case's log p1 is a + b * log p1. With
    too few pairs there is no regression to fit: fall back to the pooled
    median log-ratio (b = 0), and with no pairs at all to a flat forecast
    (median 0, i.e. the hour stays at hour 1's print).
    """
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    if not pairs:
        return (0.0, 0.0), [0.0]
    if len(pairs) >= MIN_PAIRS_FOR_REGRESSION:
        lo, hi = quantile(ys, WINSOR_Q), quantile(ys, 1.0 - WINSOR_Q)
        pairs = [(x, min(max(y, lo), hi)) for x, y in pairs]
        xs = [x for x, _ in pairs]
        ys = [y for _, y in pairs]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        b = 0.0
        if den > 0:
            b = sum((x - mx) * (y - my) for x, y in pairs) / den
        b = max(SLOPE_LO, min(SLOPE_HI, b * SLOPE_SHRINK))
        a = my - b * mx
        resid = [y - (a + b * x) for x, y in pairs]
        return (a, b), resid
    med = median(ys)
    return (med, 0.0), [y - med for y in ys]


def forecast_case(case, name):
    if list(case.get("levels") or []) != LEVELS:
        raise ValueError(f"{name} asks for levels {case.get('levels')}, not {LEVELS}")
    first = next((k for k in case.get("known") or [] if k.get("hour") == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first.get("viewers") or 1))
    lp1 = math.log(p1)

    curves = comparable_curves(case)
    per_hour = {h: [] for h in range(2, 25)}
    for pts in curves.values():
        lp1c = math.log(pts[1])
        for h in range(2, 25):
            if h in pts:
                per_hour[h].append((lp1c, math.log(pts[h] / pts[1])))

    hours = []
    for row in case.get("forecast") or []:
        h = int(row["hour"])
        (a, b), resid = hour_fit(per_hour.get(h) or [])
        med = a + b * lp1
        q25, q75 = quantile(resid, 0.25), quantile(resid, 0.75)
        spread = min(SPREAD_CAP, max(SPREAD_FLOOR, (q75 - q25) / 1.349)) * SPREAD_SCALE
        qs = []
        for z in Z:
            q = p1 * math.exp(med + z * spread)
            q = min(1e9, max(0.01, q))
            qs.append(round2(q))
        # Keep the row non-decreasing after rounding.
        for i in range(1, len(qs)):
            if qs[i] < qs[i - 1]:
                qs[i] = qs[i - 1]
        hours.append({"hour": h, "q": qs})
    return {"hours": hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
