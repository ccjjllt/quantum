#!/usr/bin/env python3
"""Geometric-mean calculator for a three-leg candidate (pure arithmetic, no simulation).

    python3 scripts/gm.py invsqrt=74797.36535717871 dqi=346413579540.50 chem=294643137.73
    python3 scripts/gm.py --current                 # the shipped 28.15083 triple

REFERENCE costs are the competition's baseline submission, fixed by the task.
Nothing here verifies a circuit: it only converts official verifier costs to the
leaderboard score. Numbers must come from unmodified official verifiers.
"""
from __future__ import annotations

import argparse
import math

REFERENCE = {
    "invsqrt": 2076774.233715,
    "dqi": 24439463583672.93,
    "chem": 3355599588.3155375,
}
CURRENT = {"invsqrt": 74797.36535717871, "dqi": 346413579540.50, "chem": 294643137.73}
GOLD = 28.71339
SILVER_CUT = 28.14702


def gm(costs: dict[str, float]) -> float:
    return math.prod(REFERENCE[k] / costs[k] for k in REFERENCE) ** (1.0 / 3.0)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("legs", nargs="*", help="task=cost (invsqrt, dqi, chem)")
    p.add_argument("--current", action="store_true", help="evaluate the shipped triple")
    a = p.parse_args()
    costs = dict(CURRENT) if a.current or not a.legs else {}
    for item in a.legs:
        k, v = item.split("=", 1)
        costs[k] = float(v)
    missing = set(REFERENCE) - set(costs)
    if missing:
        p.error(f"missing legs: {sorted(missing)}")
    g = gm(costs)
    print(f"costs   : " + "  ".join(f"{k}={costs[k]:.6f}" for k in REFERENCE))
    print(f"ratios  : " + "  ".join(f"{k}={REFERENCE[k]/costs[k]:.6f}" for k in REFERENCE))
    print(f"GM      : {g:.8f}")
    print(f"vs current 28.15083 : {g - 28.15082863:+.5f}")
    print(f"vs gold {GOLD}     : {g - GOLD:+.5f}  "
          f"({'ABOVE' if g >= GOLD else 'below'})")
    print(f"vs silver {SILVER_CUT}: {g - SILVER_CUT:+.5f}")
    for leg in REFERENCE:
        need = g * (REFERENCE[leg] / (REFERENCE[leg] / costs[leg])) ** 0  # placeholder
    # single-leg targets for gold (other two held)
    others = {k: REFERENCE[k] / costs[k] for k in REFERENCE}
    print("\nsingle-leg cost needed for gold, other two held:")
    for leg in REFERENCE:
        prod_others = math.prod(v for k, v in others.items() if k != leg)
        target_ratio = (GOLD ** 3) / prod_others
        print(f"  {leg:8s} <= {REFERENCE[leg] / target_ratio:.6f} "
              f"({(costs[leg] / (REFERENCE[leg] / target_ratio) - 1) * 100:+.3f}% on cost)")


if __name__ == "__main__":
    main()
