"""Which checkpoint wires are independent of the HMR branch?

Runs the full-domain bit-parallel trace on random HMR branches and compares
every wire value with the all-zero-branch snapshot from trace_wires.py.
A wire with XOR distance 0 on a branch has the same function of x there.

Output: artifacts/20261107_mask_refit/branch_wires.json
"""
from __future__ import annotations

import io
import json
import random
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261107_mask_refit"
WIRES = OUT / "wires"
MAXX = 3_133_452
NB = (MAXX + 7) // 8


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    raw = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    ops = []
    for line in raw:
        p = line.split()
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        ops.append((p[0], qs, p))
    return ops


def is_rotation(theta: Fraction) -> bool:
    return theta % Fraction(1, 2) != 0 and theta % Fraction(1, 4) != 0


def trace(ops, xs, hmr_bits):
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little")
         for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    full = (1 << len(xs)) - 1
    hmr_index = 0
    snaps = []
    for i, (k, qs, p) in enumerate(ops):
        active = full
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "Z_POW":
            if is_rotation(Fraction(p[2])):
                snaps.append(list(q))
            continue
        if k in {"X", "CX", "CCX", "SWAP", "CSWAP"}:
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
            else:
                a, b = qs[-2:]
                d = (q[a] ^ q[b]) & active & q[qs[0]]
                q[a] ^= d
                q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = hmr_bits[hmr_index]
            hmr_index += 1
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
        elif k in {"Z", "CZ", "CCZ", "NEG"}:
            pass
        else:
            raise ValueError((i, k, p))
    assert not stack
    assert len(snaps) == 41
    return snaps


def load_cp(i: int) -> list[int]:
    z = np.load(WIRES / f"cp_{i:02d}.npz")
    return [int.from_bytes(z[f"w{j}"].tobytes(), "little") for j in range(62)]


def main() -> None:
    t0 = time.time()
    ops = load_ops()
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    n_hmr = sum(1 for k, _, _ in ops if k == "HMR")
    ref = [load_cp(i) for i in range(41)]
    print(f"loaded refs {time.time()-t0:.1f}s, n_hmr={n_hmr}", flush=True)
    result = {"branches": [], "n_hmr": n_hmr}
    for seed in (11, 12, 13):
        rng = random.Random(seed)
        hb = [rng.getrandbits(MAXX) for _ in range(n_hmr)]
        snaps = trace(ops, xs, hb)
        per_cp = []
        for i in range(41):
            diff = [(snaps[i][j] ^ ref[i][j]).bit_count() for j in range(62)]
            same = [j for j, d in enumerate(diff) if d == 0]
            per_cp.append({"rot": i, "same_wires": same,
                           "min_diff": min(diff), "n_diff": sum(1 for d in diff if d)})
        result["branches"].append({"seed": seed, "checkpoints": per_cp})
        print(f"branch seed={seed} done {time.time()-t0:.1f}s; "
              f"rot0 same={len(per_cp[0]['same_wires'])} "
              f"rot15 same={len(per_cp[15]['same_wires'])} "
              f"rot40 same={len(per_cp[40]['same_wires'])}", flush=True)
    (OUT / "branch_wires.json").write_text(json.dumps(result, indent=1) + "\n")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
