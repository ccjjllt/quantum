"""Check whether the 41 rotation masks depend on the HMR branch on random x."""
from __future__ import annotations

import io
import json
import random
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rot33"
MAXX = 3_133_452
N = 4096


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = []
    for line in buf.getvalue().splitlines():
        if line.startswith(("APPEND", "REGISTER")):
            continue
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return ops


def classify(t: Fraction) -> str:
    if t % Fraction(1, 2) == 0:
        return "clifford"
    if t % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def trace(ops, xs, hmr_bits=None):
    n = len(xs)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8),
                                    bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    full = (1 << n) - 1
    hi = 0
    masks = []
    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "Z_POW" and classify(Fraction(p[2])) == "rotation":
            masks.append(q[qs[0]] & active)
        if k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k == "SWAP":
            a, b = qs
            d = (q[a] ^ q[b]) & active
            q[a] ^= d
            q[b] ^= d
        elif k == "CSWAP":
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & q[qs[0]] & active
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = 0 if hmr_bits is None else hmr_bits[hi]
            hi += 1
            q[qs[0]] = 0
        elif k == "R":
            q[qs[0]] = 0
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            b = int(p[1][1:])
            old = bits.get(b, 0)
            bits[b] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, k, p))
    return masks


def main() -> None:
    ops = load_ops()
    n_hmr = sum(1 for k, _, _ in ops if k == "HMR")
    rng = np.random.default_rng(20261113)
    xs = rng.integers(1, MAXX + 1, N, dtype=np.uint64)
    zero = trace(ops, xs, None)
    out = {"n": N, "n_hmr": n_hmr, "branches": {}}
    for seed in (1, 2, 3, 4):
        rr = random.Random(seed)
        hb = [rr.getrandbits(N) for _ in range(n_hmr)]
        m = trace(ops, xs, hb)
        dist = [(a ^ b).bit_count() for a, b in zip(zero, m)]
        out["branches"][f"seed_{seed}"] = {"xor_distance_vs_zero": dist,
                                           "max_distance": max(dist),
                                           "total_distance": sum(dist)}
    out["conclusion"] = ("all 41 masks branch-independent on this sample"
                         if all(v["total_distance"] == 0 for v in out["branches"].values())
                         else "branch dependence detected")
    (OUT / "branch_check_random.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["branches"], indent=2))
    print(out["conclusion"])


if __name__ == "__main__":
    main()
