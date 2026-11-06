"""Rank tests for the three large X/CX/CCX blocks.

For each block:
- `formal_span_rank` is the GF(2) rank of the clean products as quadratic
  forms over the 62 block-input wires.  If it equals the number of clean
  products, no universal linear sharing is possible.
- `domain_product_rank` is the rank of the actual product functions on the
  all-zero HMR branch over all 3,133,452 legal x.  If it equals the number of
  products, no linear recombination on that reachable domain can reduce the
  AND count.

This is a local lower-bound diagnostic, not an official validation.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_structural_negatives"
BLOCKS = [(21434, 23311, "block1"), (33980, 36370, "block2"), (3429, 14081, "block3")]
MAXX = 3_133_452


def load_ops():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]


def pairs_index():
    pairs = [(i, j) for i in range(62) for j in range(i + 1, 62)]
    return pairs, {p: k for k, p in enumerate(pairs)}


def qvec(l1, l2, pidx):
    v = 0
    for i in range(62):
        if not ((l1 >> i) & 1):
            continue
        for j in range(i + 1, 62):
            if (l2 >> j) & 1:
                v ^= 1 << pidx[(i, j)]
    for j in range(62):
        if not ((l2 >> j) & 1):
            continue
        for i in range(j + 1, 62):
            if (l1 >> i) & 1:
                v ^= 1 << pidx[(j, i)]
    for i in range(62):
        if ((l1 >> i) & 1) and ((l2 >> i) & 1):
            v ^= 1 << (len(pidx) + i)
    return v


def span_rank(rows):
    basis = []
    for v in rows:
        x = v
        for b, piv in basis:
            if (x >> piv) & 1:
                x ^= b
        if x:
            piv = x.bit_length() - 1
            basis.append((x, piv))
            basis.sort(key=lambda t: -t[1])
    return len(basis)


def main():
    ops = load_ops()
    pairs, pidx = pairs_index()
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    mask = (1 << MAXX) - 1
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    init = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    result = {"baseline": str(BASE.relative_to(ROOT)), "scope": "local lower-bound diagnostic; no candidate and no official validation", "blocks": []}
    for lo, hi, name in BLOCKS:
        q = init.copy()
        bits = {}
        stack = []
        lin = {w: 1 << w for w in range(62)}
        nonlin = {w: 0 for w in range(62)}
        clean = 0
        products = []
        targets = set()
        for i in range(lo):
            k, qs, p = gates[i]
            active = mask
            for s in stack:
                active &= s
            if "if" in p:
                active &= bits.get(int(p[-1][1:]), 0)
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
                bits[int(p[2][1:])] = 0
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
        clean_forms = []
        for i in range(lo, hi):
            k, qs, p = gates[i]
            if k == "CX":
                lin[qs[1]] ^= lin[qs[0]]
                q[qs[1]] ^= q[qs[0]] & mask
            elif k == "CCX":
                c1, c2, t = qs
                if nonlin[c1] == 0 and nonlin[c2] == 0:
                    clean_forms.append(qvec(lin[c1], lin[c2], pidx))
                    clean += 1
                lin[t] = 0
                nonlin[t] += 1
                target = t
                products.append((q[c1] & q[c2] & mask, target))
                q[t] ^= q[c1] & q[c2] & mask
                targets.add(t)
            elif k == "X":
                q[qs[0]] ^= mask
            else:
                raise ValueError((i, p))
        # domain rank of all actual products
        basis = []
        for prod, _ in products:
            x = prod
            for b, piv in basis:
                if (x >> piv) & 1:
                    x ^= b
            if x:
                piv = x.bit_length() - 1
                basis.append((x, piv))
                basis.sort(key=lambda t: -t[1])
        result["blocks"].append({
            "name": name,
            "window": [lo, hi],
            "ccx": len(products),
            "clean_ccx": clean,
            "dirty_ccx": len(products) - clean,
            "formal_span_rank_clean": span_rank(clean_forms),
            "domain_product_rank": len(basis),
            "targets": sorted(targets),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "block_rank.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
