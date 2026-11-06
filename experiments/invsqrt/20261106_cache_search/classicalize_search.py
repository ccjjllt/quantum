"""Search rotation-cluster paid gates for a product in the span of measurement bits.

For a paid gate with product p, if p = const XOR XOR(bits) on a generic
measurement branch, the gate can be replaced by a classically controlled free
gate.  This script samples branches and solves the GF(2) span relation.  It does
not modify a circuit.
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
OUT = ROOT / "artifacts/20261106_cache_search"
RANGES = [(15278, 15617), (25380, 25700)]
N = 4000
PAID = {"CCX", "CCZ", "CSWAP"}


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return c, [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def solve(prod, bits, mask):
    ids = sorted(bits)
    rows = []
    for idx, b in enumerate(ids):
        v = bits[b]
        if v not in (0, mask):
            rows.append((v, 1 << idx))
    rows.append((mask, 1 << len(ids)))
    basis = []
    for v, c in rows:
        x, cc = v, c
        while x:
            piv = x.bit_length() - 1
            hit = None
            for bb, pc in basis:
                if bb.bit_length() - 1 == piv:
                    hit = (bb, pc)
                    break
            if hit is None:
                basis.append((x, cc))
                basis.sort(key=lambda t: -t[0].bit_length())
                break
            x ^= hit[0]
            cc ^= hit[1]
    x, cc = prod, 0
    while x:
        piv = x.bit_length() - 1
        hit = None
        for bb, pc in basis:
            if bb.bit_length() - 1 == piv:
                hit = (bb, pc)
                break
        if hit is None:
            return None
        x ^= hit[0]
        cc ^= hit[1]
    chosen = [ids[i] for i in range(len(ids)) if (cc >> i) & 1]
    const = (cc >> len(ids)) & 1
    return chosen, const


def run(seed):
    rng = random.Random(seed)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    hits = []
    ops = load_ops()[1]
    for i, line in enumerate(ops):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k in PAID and i < max(hi for _, hi in RANGES):
            if active == mask and any(lo <= i < hi for lo, hi in RANGES):
                if k == "CCX":
                    prod = q[qs[0]] & q[qs[1]]
                elif k == "CCZ":
                    prod = q[qs[0]] & q[qs[1]] & q[qs[2]]
                else:
                    prod = q[qs[0]] & (q[qs[1]] ^ q[qs[2]])
                rel = solve(prod, bits, mask)
                if rel is not None:
                    hits.append({"op": i, "gate": line, "bits": rel[0], "const": rel[1],
                                 "prod_ones": prod.bit_count()})
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
            bid = int(p[2][1:])
            old = bits.get(bid, 0)
            r = rng.getrandbits(N) & mask
            bits[bid] = (old & ~active) | (r & active)
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
    hits = run(20261106)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "classicalize_sample.json").write_text(json.dumps({"hits": hits, "N": N}, indent=2) + "\n")
    print(json.dumps({"hits": len(hits), "first": hits[:20]}, indent=2))


if __name__ == "__main__":
    main()
