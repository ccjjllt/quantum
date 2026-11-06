"""Recheck the sampled guard candidates over every legal x on one branch.

The sampled search can miss rare x.  This script loads `guard_stable.json` and
simulates all 3,133,452 legal x on a random HMR branch, recording violations of
the claimed implication.  A nonempty violation list rejects the guard.
"""
from __future__ import annotations

import io
import json
import random
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_guard_search"
MAXX = 3_133_452


def main():
    data = json.loads((OUT / "guard_stable.json").read_text())
    candidates = data["survivors"]
    by_op = {}
    for h in candidates:
        p = h["gate"].split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        by_op[h["op"]] = {**h, "k": k, "qs": qs}
    max_op = max(by_op)
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    mask = (1 << MAXX) - 1
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    rng = random.Random(20261106)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    violations = {}
    for i, (k, qs, p) in enumerate(gates[:max_op + 1]):
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if i in by_op:
            h = by_op[i]
            if h["k"] in {"CCX", "CCZ"}:
                prod = q[h["qs"][0]] & q[h["qs"][1]]
                if h["k"] == "CCZ":
                    prod &= q[h["qs"][2]]
            else:
                prod = q[h["qs"][0]] & (q[h["qs"][1]] ^ q[h["qs"][2]])
            prod &= active
            v = bits.get(h["bit"], 0)
            bad = prod & (v if h.get("complement") else (mask ^ v))
            violations[i] = bad.bit_count()
        if k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = rng.getrandbits(MAXX) & mask
            q[qs[0]] &= ~active
        elif k == "R":
            q[qs[0]] &= ~active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            bid = int(p[1][1:])
            old = bits.get(bid, 0)
            bits[bid] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError((i, p))
    clean = [op for op, n in violations.items() if n == 0]
    result = {"scope": "full legal-x check on one random branch", "candidates": len(candidates),
              "clean": clean, "min_violation": min(violations.values()),
              "violations": violations}
    (OUT / "guard_full_domain.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(candidates), "clean": clean,
                      "min_violation": min(violations.values())}, indent=2))


if __name__ == "__main__":
    main()
