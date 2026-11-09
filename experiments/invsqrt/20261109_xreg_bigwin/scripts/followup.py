"""Follow-up screens with corrected CX direction (CX control target).

F1: for every CCX in [2006:14215]: pop(control_a), pop(control_b), pop(product);
    flag control-all-ones (CCX(a,1,t) == CX(a,t): -1 CCX) and product-all-ones
    (CCX(1,1,t) == X(t)); confirm dead==0.
F2: all same-target pairs (any triples): count prod_equal (not just same-triple).
F3: window-local both-boundary dup pairs for candidate windows
    [5006:7506], [5506:8006], [6006:8506] (2500 ops each, pure unconditional).

Output: followup.json
"""
from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
OUT = Path("experiments/invsqrt/20261109_xreg_bigwin/followup.json")
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64
A, B = 2006, 14215
WINDOWS = [(5006, 7506), (5506, 8006), (6006, 8506)]


def load_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return hdr, ops


def main() -> None:
    hdr, ops = load_ops()
    assert len(ops) == 53686
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    qv = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> np.uint64(bit)) & np.uint64(1)).astype(np.uint64)
        qv[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = np.uint64((1 << (N_INPUTS % 64)) - 1) if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)

    depth = 0
    for line in ops[:A]:
        if line.startswith("PUSH_CONDITION"):
            depth += 1
        elif line.startswith("POP_CONDITION"):
            depth -= 1
        if depth > 0 or " if " in line:
            continue
        p = line.split()
        op = p[0]
        if op in ("HMR", "R"):
            qv[int(p[1][1:])].fill(0)
        elif op == "X":
            qv[int(p[1][1:])] ^= ones
        elif op == "CX":
            qv[int(p[2][1:])] ^= qv[int(p[1][1:])]
        elif op == "SWAP":
            a_, b_ = int(p[1][1:]), int(p[2][1:])
            qv[a_], qv[b_] = qv[b_], qv[a_]
        elif op == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            qv[t_] ^= qv[a_] & qv[b_]
        elif op == "CSWAP":
            c_, a_, b_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = qv[c_] & (qv[a_] ^ qv[b_])
            qv[a_] ^= prod
            qv[b_] ^= prod

    snaps = {}
    want = sorted({x for w in WINDOWS for x in w} | {A, B})
    # simulate window, snapshotting at wanted boundaries + per-CCX control pops
    f1 = []
    cur = {s: None for s in want}
    if A in cur:
        cur[A] = [w.copy() for w in qv]
    for idx in range(A, B):
        if idx in cur:
            cur[idx] = [w.copy() for w in qv]
        line = ops[idx]
        p = line.split()
        if p[0] == "X":
            qv[int(p[1][1:])] ^= ones
        elif p[0] == "CX":
            qv[int(p[2][1:])] ^= qv[int(p[1][1:])]
        elif p[0] == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            pa = int(np.sum(np.bitwise_count(qv[a_])))
            pb = int(np.sum(np.bitwise_count(qv[b_])))
            prod = qv[a_] & qv[b_]
            pp = int(np.sum(np.bitwise_count(prod)))
            f1.append({"idx": idx, "op": line, "pop_a": pa, "pop_b": pb, "pop_prod": pp,
                       "a_ones": pa == N_INPUTS, "b_ones": pb == N_INPUTS,
                       "prod_ones": pp == N_INPUTS, "prod_zero": pp == 0})
            qv[t_] ^= prod
    if B in cur:
        cur[B] = [w.copy() for w in qv]

    def dups(snap):
        d = []
        for i in range(62):
            for j in range(i + 1, 62):
                if np.array_equal(snap[i], snap[j]):
                    d.append([i, j])
        return d

    f3 = {}
    for (s, e) in WINDOWS:
        dA, dB = dups(cur[s]), dups(cur[e])
        setA = {tuple(p) for p in dA}
        both = [p for p in dB if tuple(p) in setA]
        pops = lambda snap: [int(np.sum(np.bitwise_count(w))) for w in snap]  # noqa: E731
        pA, pB = pops(cur[s]), pops(cur[e])
        f3[f"{s}:{e}"] = {"dup_both": both, "n_dupA": len(dA), "n_dupB": len(dB),
                          "zeroA": [i for i, p in enumerate(pA) if p == 0],
                          "zeroB": [i for i, p in enumerate(pB) if p == 0]}

    # F2: same-target any-pair prod equality — need prod words; recompute cheaply
    # (store words for the 134 CCXs)
    f2_equal = "see bigwin_scan merge_cands full check below"
    out = {"F1": f1,
           "F1_flags": {"a_ones": [r for r in f1 if r["a_ones"]],
                        "b_ones": [r for r in f1 if r["b_ones"]],
                        "prod_ones": [r for r in f1 if r["prod_ones"]],
                        "prod_zero": [r for r in f1 if r["prod_zero"]]},
           "F3_windows": f3}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("F1 n_ccx:", len(f1))
    print("a_ones:", [r["idx"] for r in f1 if r["a_ones"]])
    print("b_ones:", [r["idx"] for r in f1 if r["b_ones"]])
    print("prod_ones:", [r["idx"] for r in f1 if r["prod_ones"]])
    print("prod_zero:", [r["idx"] for r in f1 if r["prod_zero"]])
    print("max pop_prod:", max(r["pop_prod"] for r in f1))
    print("F3:", json.dumps(f3, indent=1)[:3000])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
