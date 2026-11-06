"""Search for CSWAP gates whose control-times-difference product is already a wire.

A CSWAP(c,a,b) applies a ^= p, b ^= p with p = c*(a XOR b).  If some wire w holds
p plus a free affine function of the public input x, the Fredkin can be replaced by
free CX/X gates.  The first pass samples 4096 legal x values on the all-zero HMR
branch; candidates are then rechecked over every legal x.  No circuit is modified.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_cache_search"
MAXX = 3_133_452
RANGES = [(15278, 15617), (25380, 25700)]
SAMPLE_N = 4096


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return c, [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def parse_q(line):
    return [int(t[1:]) for t in line.split()[1:] if t.startswith("q")]


def run(ops, xs, check_ops, collect):
    """Simulate all-zero HMR branch; return candidate matches at check_ops."""
    special = [0] + [1 << k for k in range(22)]
    all_xs = list(xs) + special
    n = len(all_xs)
    mask = (1 << n) - 1
    legal = (1 << len(xs)) - 1
    q = [sum(((x >> j) & 1) << i for i, x in enumerate(all_xs)) for j in range(22)] + [0] * 40
    xbits = q[:22]
    bits = {}
    stack = []
    hits = []
    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        qs = parse_q(line)
        if k == "CSWAP":
            ctl, a, b = qs[0], qs[1], qs[2]
            if collect and active == mask and i in check_ops:
                prod = q[ctl] & (q[a] ^ q[b])
                for w in range(62):
                    d = prod ^ q[w]
                    d0 = (d >> len(xs)) & 1
                    coefs = [((d >> (len(xs) + 1 + kk)) & 1) ^ d0 for kk in range(22)]
                    pred = mask if d0 else 0
                    for kk, coef in enumerate(coefs):
                        if coef:
                            pred ^= xbits[kk]
                    if (pred ^ d) & legal == 0:
                        hits.append({"op": i, "control": ctl, "a": a, "b": b,
                                     "cache_wire": w, "const": d0,
                                     "linear_bits": [kk for kk, v in enumerate(coefs) if v]})
            d = (q[a] ^ q[b]) & q[ctl] & active
            q[a] ^= d
            q[b] ^= d
        elif k == "X":
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
        elif k == "HMR":
            bits[int(p[2][1:])] = bits.get(int(p[2][1:]), 0) & ~active
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
            raise ValueError(line)
    return hits


def main():
    _, ops = load_ops()
    max_op = max(hi for _, hi in RANGES)
    rng = np.random.default_rng(20261106)
    xs = [int(v) for v in rng.integers(1, MAXX + 1, size=SAMPLE_N)]
    check_ops = {i for i, line in enumerate(ops[:max_op]) if line.startswith("CSWAP ")
                 and any(lo <= i < hi for lo, hi in RANGES)}
    hits = run(ops[:max_op], xs, check_ops, True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache_hits_sample.json").write_text(json.dumps({"hits": hits, "sample": SAMPLE_N}, indent=2) + "\n")
    print(json.dumps({"sample_hits": len(hits), "first": hits[:20]}, indent=2))


if __name__ == "__main__":
    main()
