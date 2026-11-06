"""Inspect the 8 overlapping angle-weight pairs and the low-byte sum."""
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


def unpack(v: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(v.to_bytes((MAXX + 7) // 8, "little"),
                                       dtype=np.uint8), bitorder="little")[:MAXX].astype(bool)


def main() -> None:
    data = json.loads((OUT / "masks_full.json").read_text())
    thetas = [Fraction(t) for t in data["angles_half_turns"]]
    masks = [unpack(int_from_b64(m["mask_b64"])) for m in data["masks"]]
    weights = [round(-math.log2(float(t))) for t in thetas]
    from collections import defaultdict
    by_w = defaultdict(list)
    for i, w in enumerate(weights):
        by_w[w].append(i)
    print("weight multiplicities:", sorted((w, len(v), v) for w, v in by_w.items()))
    report = {}
    for w in sorted(by_w):
        if len(by_w[w]) < 2:
            continue
        i, j = by_w[w]
        a, b = masks[i], masks[j]
        both = int(np.count_nonzero(a & b))
        onlya = int(np.count_nonzero(a & ~b))
        onlyb = int(np.count_nonzero(~a & b))
        info = {"rots": [i, j], "both": both, "only_a": onlya, "only_b": onlyb,
                "disjoint": both == 0, "a_subset_b": onlya == 0, "b_subset_a": onlyb == 0,
                "jaccard": both / (both + onlya + onlyb)}
        report[f"w{w}"] = info
        print(f"2^-{w:2d}: rot{i:2d} pop={int(a.sum()):8d} rot{j:2d} pop={int(b.sum()):8d} "
              f"both={both:8d} only_a={onlya:8d} only_b={onlyb:8d} "
              f"disjoint={info['disjoint']} jaccard={info['jaccard']:.4f}")

    # Integer words: A from rot0-14 (weights -17..-3), B from rot15-35 (-35..-15),
    # C from rot36-40 (-14..-10).
    print("\nChecking word reconstruction...")
    A = np.zeros(MAXX, dtype=np.int64)
    B = np.zeros(MAXX, dtype=np.int64)
    C = np.zeros(MAXX, dtype=np.int64)
    for k in range(15):
        A += masks[k].astype(np.int64) << k       # weight 2^-(17-k)
    for k in range(21):
        B += masks[15 + k].astype(np.int64) << k  # weight 2^-(35-k)
    for k in range(5):
        C += masks[36 + k].astype(np.int64) << (k + 21)  # weight 2^-(35-k)? check
    # C rotations 36..40 have weights -14..-10, which are B bits 21..25.
    print("A range", int(A.min()), int(A.max()), "bits", int(A.max()).bit_length())
    print("B range", int(B.min()), int(B.max()), "bits", int(B.max()).bit_length())
    print("C contribution range", int(C.min()), int(C.max()), "bits", int(C.max()).bit_length())

    # Sum of the 8 smallest-angle rotations 15..22.
    D = np.zeros(MAXX, dtype=np.int64)
    for k in range(8):
        D += masks[15 + k].astype(np.int64) << k
    print("low byte W range", int(D.min()), int(D.max()), "popcount of W>0", int((D > 0).sum()),
          "distinct", len(np.unique(D)))
    vals, cnts = np.unique(D, return_counts=True)
    print("low byte distribution top:", [(int(v), int(c)) for v, c in sorted(zip(vals, cnts), key=lambda z: -z[1])[:10]])

    (OUT / "pair_structure.json").write_text(json.dumps(report, indent=2) + "\n")
    np.save(OUT / "low_byte_W.npy", D)


if __name__ == "__main__":
    main()
