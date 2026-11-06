"""Fit target: exact 33-bit fixed-point truncation of the fine-rotation phase.

The fine phase T (after removing the exact Clifford/T part) is represented in
half-turns.  Its binary expansion needs at most 34 bits: weights 2^-2 down to
2^-35.  A 33-rotation set uses weights 2^-2..2^-34 and drops the 2^-35 bit,
whose maximum contribution is one ulp, below tolerance on the whole domain.
This script checks that budget and writes the 33 ideal bit functions.
"""
from __future__ import annotations

import base64
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
MASK64 = (1 << 64) - 1
UNIT61 = 1 << 61
WEIGHTS = list(range(2, 35))  # 2^-2 .. 2^-34, 33 terms


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def bits(v: int, n: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((n + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:n]


def main() -> None:
    data = json.loads((OUT / "masks_full.json").read_text())
    masks = [int_from_b64(m["mask_b64"]) for m in data["masks"]]
    thetas = [Fraction(t) for t in data["angles_half_turns"]]

    r = [math.isqrt((1 << 130) // x) for x in range(1, MAXX + 1)]
    target = np.array([((v + 1) >> 1) & MASK64 for v in r], dtype=np.uint64)
    tol = np.array([min(v >> 25, 1 << 63) for v in r], dtype=np.uint64)

    phase = np.zeros(MAXX, dtype=np.uint64)
    for m, t in zip(masks, thetas):
        phase[bits(m, MAXX).astype(bool)] += np.uint64(int(round(t * (1 << 63))))

    delta = (target - phase).astype(np.uint64)
    low = (delta & np.uint64(UNIT61 - 1)).astype(np.uint64).astype(np.int64)
    low = np.where(low > (1 << 60), low - UNIT61, low)
    rest = (delta.astype(np.int64) - low).astype(np.uint64)
    T = (target - rest).astype(np.uint64)
    N = (T >> np.uint64(28)).astype(np.int64)  # floor(T_half * 2^35)
    print("N max", int(N.max()), "bit length", int(N.max()).bit_length())

    recon = np.zeros(MAXX, dtype=np.uint64)
    g = {}
    for w in WEIGHTS:
        bitpos = 35 - w
        gw = ((N >> bitpos) & 1).astype(bool)
        g[w] = gw
        recon[gw] += np.uint64(1 << (63 - w))
    residual = (T - recon).view(np.int64)
    ratio = np.divide(np.abs(residual).view(np.uint64), tol,
                      out=np.zeros(MAXX), where=tol > 0)
    print("dropped-bit residual max", int(residual.max()), "units =",
          float(residual.max() / 2**63), "half-turns")
    print("33-term truncation worst ratio", float(ratio.max()),
          "at x", int(np.argmax(ratio)) + 1)
    print("popcounts:", [int(g[w].sum()) for w in WEIGHTS])

    # Save as packed bitsets for the span test.
    packed = {f"w{w}": np.packbits(g[w], bitorder="little") for w in WEIGHTS}
    np.savez_compressed(OUT / "g_bits.npz", **packed)
    np.save(OUT / "T_units.npy", T)
    np.save(OUT / "N.npy", N.astype(np.int64))
    np.save(OUT / "tol_units.npy", tol)
    np.save(OUT / "target_units.npy", target)
    with open(OUT / "g_meta.json", "w") as f:
        json.dump({"weights_half_turn_exponents": WEIGHTS,
                   "dropped_weight": 35,
                   "truncation_worst_ratio": float(ratio.max()),
                   "truncation_worst_x": int(np.argmax(ratio)) + 1,
                   "N_max": int(N.max()), "N_bit_length": int(N.max()).bit_length(),
                   "popcounts": {str(w): int(g[w].sum()) for w in WEIGHTS}}, f, indent=2)


if __name__ == "__main__":
    main()
