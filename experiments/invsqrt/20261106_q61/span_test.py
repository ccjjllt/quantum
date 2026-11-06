"""GF(2) span test: at every use of a scratch wire, is its value an XOR of other wires?

Sampled-x necessity test (512 random legal x, several HMR branches).  If the test fails on
the sample, the wire is not a linear form there.  If it passes, a separate exact check is
needed.  This is a structural screen, not a proof.
"""
from __future__ import annotations

import collections
import json
import random
import sys

import numpy as np

import common

MAXX = 3133452
N = 512


def run(gates, xs, hmr_value=0):
    """Return states[i] = list of 62 python ints (bit j = x_j value) before op i."""
    n = len(xs)
    q = [sum(((x >> j) & 1) << i for i, x in enumerate(xs)) for j in range(22)] + [0] * 40
    stack = []
    states = []
    for i, (k, qs, p) in enumerate(gates):
        states.append(list(q))
        if k in {"X", "R", "HMR"}:
            q[qs[0]] = 0 if k in {"R", "HMR"} else q[qs[0]] ^ ((1 << n) - 1)
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]]
        elif k == "SWAP":
            q[qs[0]], q[qs[1]] = q[qs[1]], q[qs[0]]
        elif k == "CSWAP":
            c, a, b = qs
            d = (q[a] ^ q[b]) & q[c]
            q[a] ^= d
            q[b] ^= d
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]]
    return states


def in_span(target, vectors, n):
    """Whether `target` lies in the GF(2) span of `vectors` (ints with n bits)."""
    basis = {}
    for v in vectors:
        x = v
        while x:
            p = x.bit_length() - 1
            if p in basis:
                x ^= basis[p]
            else:
                basis[p] = x
                break
    x = target
    while x:
        p = x.bit_length() - 1
        if p in basis:
            x ^= basis[p]
        else:
            return False
    return True


def main():
    seeds = [int(a) for a in sys.argv[1:]] or [0]
    _, ops, gates, stacks = common.load_ops()
    use_ops = {q: [i for i, (k, qs, p) in enumerate(gates) if q in qs] for q in range(22, 62)}
    totals = collections.Counter()
    hits = collections.Counter()
    per_op = collections.defaultdict(dict)
    for seed in seeds:
        rng = random.Random(seed)
        xs = [rng.randint(1, MAXX) for _ in range(N)]
        states = run(gates, xs, seed)
        allmask = (1 << N) - 1
        for q in range(22, 62):
            for i in use_ops[q]:
                st = states[i]
                vecs = [st[w] for w in range(62) if w != q]
                ok = in_span(st[q], vecs, N)
                totals[q] += 1
                hits[q] += ok
                if ok:
                    per_op[q][i] = per_op[q].get(i, 0) + 1
    rows = []
    for q in range(22, 62):
        rows.append({"q": q, "uses": totals[q], "span_hits": hits[q],
                     "hit_ops": sorted(k for k, v in per_op[q].items() if v == len(seeds))})
    rows.sort(key=lambda r: -r["span_hits"])
    print(f"seeds={seeds} sample={N} x per seed")
    for r in rows:
        print(f"q{r['q']:>2}: uses={r['uses']:>5} linear_on_all_seeds={r['span_hits']:>5} "
              f"ops={r['hit_ops'][:12]}")
    (common.OUT / "span_test.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
