"""Baseline 33-term fits restricted to the original 41 rotation masks."""
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


def int_from_b64(s: str) -> int:
    return int.from_bytes(base64.b64decode(s), "little")


def unpack(v: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((MAXX + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:MAXX].astype(bool)


def main() -> None:
    data = json.loads((OUT / "masks_full.json").read_text())
    thetas = [Fraction(t) for t in data["angles_half_turns"]]
    masks = [unpack(int_from_b64(m["mask_b64"])) for m in data["masks"]]
    T = np.load(OUT / "T_units.npy")
    tol = np.load(OUT / "tol_units.npy")

    units = np.array([int(round(t * (1 << 63))) for t in thetas], dtype=np.int64)

    def worst(sel):
        phase = np.zeros(MAXX, dtype=np.uint64)
        for j in sel:
            phase[masks[j]] += np.uint64(units[j])
        err = (phase - T).view(np.int64)
        ratio = np.divide(np.abs(err).view(np.uint64), tol,
                          out=np.zeros(MAXX), where=tol > 0)
        return float(ratio.max()), int(np.argmax(ratio)) + 1

    print("all 41:", worst(range(41)))
    print("\ndrop one (keep 40):")
    single = []
    for j in range(41):
        r, x = worst([k for k in range(41) if k != j])
        single.append((r, j, x))
        print(f"  drop {j:2d} theta={float(thetas[j]):.3e}: worst {r:.6f} at x={x}")
    single.sort()

    print("\ndrop 8 smallest angles:")
    order = sorted(range(41), key=lambda j: abs(float(thetas[j])))
    sel = order[8:]
    print(" kept", sorted(sel), "dropped", order[:8])
    print(" worst", worst(sel))

    print("\ndrop 8 largest angles (sanity):")
    sel2 = order[:33]
    print(" worst", worst(sel2))

    # Greedy backward elimination using the all-x worst ratio, no angle refit.
    sel = list(range(41))
    for step in range(8):
        best = None
        for j in sel:
            cand = [k for k in sel if k != j]
            r, x = worst(cand)
            if best is None or r < best[0]:
                best = (r, j, x, cand)
        print(f"greedy remove {step+1}: drop {best[1]} -> worst {best[0]:.6f} at x={best[2]}")
        sel = best[3]
    print("greedy final kept", sorted(sel), "worst", worst(sel))

    (OUT / "subset_baseline.json").write_text(json.dumps(
        {"drop_one": [{"drop": j, "worst": r, "x": x} for r, j, x in single],
         "keep_33_largest": {"kept": sorted(order[8:]), "dropped": order[:8],
                              "worst": worst(order[8:])[0]},
         "greedy_kept": sorted(sel), "greedy_worst": worst(sel)[0]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
