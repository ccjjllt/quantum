"""Constraint-generating LP for a fixed 33-rotation subset (public fit method).

For a given removal set, iterate:
  solve LP on the current x sample,
  scan all 3,133,452 x,
  add the worst 2000 margins to the sample,
until the LP margin agrees with the full-domain margin.
"""
from __future__ import annotations

import base64
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
SHIFT = 24
BOUND = 200_000  # +-1.8e-7 turns, public fit bound


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def unpack(v: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((MAXX + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:MAXX].astype(bool)


def main(remove: list[int]) -> None:
    data = json.loads((OUT / "masks_full.json").read_text())
    thetas = np.array([int(round(Fraction(t) * (1 << 63))) for t in data["angles_half_turns"]],
                      dtype=np.int64)
    masks = [unpack(int_from_b64(m["mask_b64"])) for m in data["masks"]]
    T_full = np.load(OUT / "T_units.npy").astype(np.int64)
    tol_full = np.load(OUT / "tol_units.npy").astype(np.int64)
    kept = [j for j in range(41) if j not in remove]
    print("removed", remove, "kept", len(kept), flush=True)

    # Base phase of all 41, units 2^-40 turns.
    phase41 = np.zeros(MAXX, dtype=np.uint64)
    for j in range(41):
        phase41[masks[j]] += np.uint64(thetas[j])
    E_full = (T_full - phase41.astype(np.int64)).astype(np.float64) / 2**SHIFT
    T_full_s = T_full.astype(np.float64) / 2**SHIFT
    tol_full_s = tol_full.astype(np.float64) / 2**SHIFT

    rng = np.random.default_rng(20261112)
    idx = np.unique(np.concatenate([
        np.arange(8192),
        rng.integers(0, MAXX, 10000),
        np.argsort(tol_full - np.abs(T_full - phase41.astype(np.int64)))[:1000],
    ]))

    F = None  # built per iteration from the masks to avoid a 1 GB matrix
    old = thetas / 2**SHIFT
    history = []
    for it in range(30):
        A = np.stack([masks[j][idx].astype(np.float64) for j in kept], axis=1)
        E = E_full[idx]
        Ts = tol_full_s[idx]
        AA = np.vstack([np.c_[A, np.ones(len(idx))],
                        np.c_[-A, np.ones(len(idx))]])
        bb = np.r_[Ts - E, Ts + E]
        c = np.r_[np.zeros(len(kept)), -1.0]
        bounds = [(-BOUND, BOUND)] * len(kept) + [(None, None)]
        sol = linprog(c, A_ub=AA, b_ub=bb, bounds=bounds, method="highs")
        if not sol.success:
            print("LP failure", sol.message, flush=True)
            break
        d = sol.x[:len(kept)]
        eps = sol.x[-1]
        new_theta = np.zeros(41, dtype=np.int64)
        new_theta[kept] = thetas[kept] + np.round(d * 2**SHIFT).astype(np.int64)
        # Full-domain scan.
        phase = np.zeros(MAXX, dtype=np.uint64)
        for j in kept:
            phase[masks[j]] += np.uint64(new_theta[j])
        err = (phase.astype(np.int64) - T_full).view(np.int64)
        used = np.abs(err).view(np.uint64)
        ratio = np.divide(used, tol_full.astype(np.uint64),
                          out=np.zeros(MAXX), where=tol_full > 0)
        margin = (tol_full - used.astype(np.int64))
        imin = int(np.argmin(margin))
        min_margin_turns = float(margin[imin] / 2**64)
        worst_ratio = float(ratio.max())
        row = {"iter": it, "constraints": len(idx), "lp_eps_turns": float(eps * 2**-40),
               "full_min_margin_turns": min_margin_turns,
               "full_worst_ratio": worst_ratio,
               "full_worst_x": int(np.argmax(ratio)) + 1,
               "min_margin_x": imin + 1}
        history.append(row)
        print(json.dumps(row), flush=True)
        if eps * 2**-40 - min_margin_turns < 2e-7 * 2**-40:
            break
        worst = np.argpartition(margin, min(2000, MAXX - 1))[:2000]
        idx = np.unique(np.r_[idx, worst])

    result = {"remove": remove, "kept": kept, "history": history,
              "final_worst_ratio": history[-1]["full_worst_ratio"] if history else None,
              "new_theta_units": new_theta.tolist() if history else None}
    name = "subset_lp_" + "_".join(map(str, remove)) + ".json"
    (OUT / name).write_text(json.dumps(result, indent=2) + "\n")
    print("WROTE", name, flush=True)


if __name__ == "__main__":
    rem = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [15, 16, 17, 18, 19, 20, 21, 22]
    main(rem)
