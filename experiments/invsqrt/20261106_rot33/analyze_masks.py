"""First-pass analysis of the 41 extracted fine-rotation masks."""
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


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def bits(v: int, n: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((n + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:n]


def gf2_rank(values: list[int]) -> int:
    basis: dict[int, int] = {}
    for v in values:
        while v:
            p = v.bit_length() - 1
            if p not in basis:
                basis[p] = v
                break
            v ^= basis[p]
    return len(basis)


def in_gf2_span(target: int, columns: list[int]) -> bool:
    basis: dict[int, int] = {}
    for c in columns:
        v = c
        while v:
            p = v.bit_length() - 1
            if p not in basis:
                basis[p] = v
                break
            v ^= basis[p]
    v = target
    while v:
        p = v.bit_length() - 1
        if p not in basis:
            return False
        v ^= basis[p]
    return True


def main() -> None:
    data = json.loads((OUT / "masks_full.json").read_text())
    masks = [int_from_b64(m["mask_b64"]) for m in data["masks"]]
    thetas = [Fraction(t) for t in data["angles_half_turns"]]
    ops = data["ops"]
    targets = data["targets"]
    print("rotations", len(masks))
    print("rank", gf2_rank(masks))
    print("distinct", len(set(masks)))
    for i, (m, t) in enumerate(zip(masks, thetas)):
        print(f"{i:2d} op={ops[i]:5d} q{targets[i]:2d} theta={float(t):.6e} ht "
              f"pop={m.bit_count():8d} frac={m.bit_count()/MAXX:.5f}")

    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    xbits = [((xs >> j) & 1).astype(np.uint8) for j in range(22)]
    columns = [int.from_bytes(np.packbits(b, bitorder="little").tobytes(), "little")
               for b in xbits]
    ones = (1 << MAXX) - 1
    print("\naffine-linear in x?")
    for i, m in enumerate(masks):
        lin = in_gf2_span(m, [ones] + columns)
        print(f"{i:2d} {'affine' if lin else 'nonlinear'}")

    # Target 1/sqrt(x) turns in units of 2^-64 turns.
    MASK64 = (1 << 64) - 1
    r = [math.isqrt((1 << 130) // x) for x in range(1, MAXX + 1)]
    target = np.array([((v + 1) >> 1) & MASK64 for v in r], dtype=np.uint64)
    tol = np.array([min(v >> 25, 1 << 63) for v in r], dtype=np.uint64)

    # Rotation phase only.
    units = [int(round(t * (1 << 63))) for t in thetas]
    phase = np.zeros(MAXX, dtype=np.uint64)
    for m, u in zip(masks, units):
        b = bits(m, MAXX).astype(bool)
        phase[b] += np.uint64(u)
    err = (phase - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    ratio = np.divide(used, tol, out=np.zeros(MAXX), where=tol > 0)
    print("\nrotation phase vs full target (rest phase not subtracted):")
    print(" worst ratio", float(ratio.max()), "at x", int(np.argmax(ratio)) + 1)

    # Sum of the k smallest angles if simply dropped.
    order = sorted(range(41), key=lambda i: abs(float(thetas[i])))
    print("\nsmallest angles and cumulative drop bound (worst-case |sum| in tol units):")
    cum = 0.0
    for rank, i in enumerate(order[:12]):
        cum += abs(float(thetas[i])) * (1 << 63)  # units 2^-64 turns
        print(f" drop {rank+1}: rot{i} theta={float(thetas[i]):.4e} ht cum={cum:.3e} units; "
              f"tol_at_max={int(tol[-1])}; ratio_if_aligned={cum/tol[-1]:.3f}")


if __name__ == "__main__":
    main()
