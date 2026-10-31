"""Full-domain classical screen of one coefficient table.

Reports segment endpoints, centers, normalization boundaries, carry boundaries,
x=161 and x=888, then every legal input. A pass here is not a circuit pass
and not an official verifier pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import hsplit as H  # noqa: E402
import model as M  # noqa: E402
from recipe_io import load_recipe, params_from_recipe, phase_angles, tables_from_recipe  # noqa: E402


def interesting_inputs() -> dict[str, list[int]]:
    max_x = M.MAX_X
    norm = [1, 2, 3, 4]
    for k in range(0, 22):
        for d in (-1, 0, 1):
            v = (1 << k) + d
            if 1 <= v <= max_x:
                norm.append(v)
    centers = []
    endpoints = []
    carries = []
    for p in (0, 1):
        for seg in range(128):
            base = (1 << 21) + (seg << 14)
            # Representative normalized words: segment endpoints and the center bit.
            for delta in (0, 1, 8191, 8192, 8193, 16383):
                word = base + delta
                # Invert one even normalization. t = p, s = 0, x = word >> p, must stay in range.
                x = int(word >> p)
                if 1 <= x <= max_x:
                    (endpoints if delta in (0, 16383) else centers if delta in (8191, 8192, 8193) else carries).append(x)
    return {
        "normalization_boundaries": sorted(set(norm)),
        "segment_endpoints": sorted(set(endpoints))[:64],
        "segment_centers": sorted(set(centers))[:64],
        "carry_boundaries": sorted(set(carries))[:64],
        "tight_points": [161, 888],
    }


def screen_values(xs: np.ndarray, tables, prm, angles, lay) -> dict:
    target, tol = M.reference()
    phase = H.phases_multi(H.regs(tables, prm, lay, xs), angles)
    err = np.abs((phase - target[xs - 1]).view(np.int64)).view(np.uint64)
    tl = tol[xs - 1]
    overflow = 0
    try:
        _t, xn, p, _s = M.decompose(xs)
        M.model_Yp(xn, p, tables, prm, check=True)
    except OverflowError:
        overflow = int(len(xs))
    bad = err > tl
    return {
        "count": int(len(xs)),
        "tolerance_violations": int(np.count_nonzero(bad)),
        "overflows": overflow,
        "min_absolute_margin_units": int((tl - err).min()),
        "max_error_over_tolerance": float((err / tl.astype(np.float64)).max()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    loaded = load_recipe()
    prm = params_from_recipe(loaded["recipe"])
    tables = tables_from_recipe(loaded["recipe"])
    angles = phase_angles()
    lay = H.layout(tables, prm, int(loaded["recipe"]["LB"]), int(loaded["recipe"]["S"]))
    named = {}
    for name, values in interesting_inputs().items():
        xs = np.array(sorted(set(values)), dtype=np.int64)
        named[name] = screen_values(xs, tables, prm, angles, lay)
        named[name]["inputs_head"] = [int(v) for v in xs[:12]]
    xs = np.arange(1, M.MAX_X + 1, dtype=np.int64)
    full = screen_values(xs, tables, prm, angles, lay)
    payload = {
        "scope": "classical model of the published recipe; not a circuit verification and not an official PASS",
        "legal_inputs": M.MAX_X,
        "named": named,
        "full_domain": full,
        "official_verifier_called": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"full_domain": full, "tight": {k: named[k] for k in ("tight_points",)}}, indent=2))
    return 0 if full["tolerance_violations"] == 0 and full["overflows"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
