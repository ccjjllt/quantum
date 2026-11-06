"""Validate extracted rotation phase against the official error profile."""
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
MASK61 = (1 << 61) - 1


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
        u = int(round(t * (1 << 63)))
        phase[bits(m, MAXX).astype(bool)] += np.uint64(u)

    rest = (target - phase).astype(np.uint64)  # simulated Clifford/T part + error
    low = (rest & np.uint64(MASK61)).astype(np.uint64)
    # Signed distance to nearest multiple of 2^61.
    signed = low.astype(np.int64)
    signed = np.where(signed > (1 << 60), signed - (1 << 61), signed)
    used = np.abs(signed).view(np.uint64)
    ratio = np.divide(used, tol, out=np.zeros(MAXX), where=tol > 0)
    print("residual mod 2^61 (simulated error) stats, units 2^-64 turns:")
    print("  min/max signed", int(signed.min()), int(signed.max()))
    print("  worst ratio", float(ratio.max()), "at x", int(np.argmax(ratio)) + 1)
    order = np.argsort(ratio)[-15:][::-1]
    print("  top: ", [(int(i) + 1, float(ratio[i]), int(signed[i])) for i in order])
    print("  official worst: 0.9993237694056958 at x=161")
    print("  count ratio>1:", int((ratio > 1).sum()))

    # Save the residual for the fit target bookkeeping.
    np.save(OUT / "rotation_phase_units.npy", phase)
    np.save(OUT / "target_units.npy", target)
    np.save(OUT / "tol_units.npy", tol)


if __name__ == "__main__":
    main()
