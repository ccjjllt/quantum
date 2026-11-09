"""Precise affine-merge feasibility (Task 1, corrected CX direction).

For each same-target CCX pair sharing exactly one control d (117 pairs):
  M1: d stable as a function between the two points (word equality).
  M2: every op strictly between commutes with CCX(a1,d,t) [bubble-down rule]:
      - CX(c1,c2): BLOCKS iff c2 in {a1,d} (rewrites a control) or c1 == t (reads t).
      - CCX(a2,b2,t2): BLOCKS iff t2 in {a1,d} or t in {a2,b2}.
        (XORs into same target commute; disjoint reads commute.)
      - X(w): BLOCKS iff w in {a1,d}. (X on t commutes.)
      - HMR/R on {a1,d,t}: BLOCKS (reset); elsewhere commutes.
      - classical-only (NEG/BIT_*): commute. Diagonal sharing a wire: BLOCKS.
      - PUSH/POP/'if' (conditional): BLOCKS (conservative; window has none).
  If M1+M2: pair can be made adjacent and rewritten
     CCX(a,d,t);CCX(b,d,t) -> CX a b; CCX(b,d,t); CX a b   (net -1 CCX, +2 free CX).
Output: merge_check.json
"""
from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
OUT = Path("experiments/invsqrt/20261109_xreg_bigwin/merge_check.json")
A, B = 2006, 14215
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64


def load_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return hdr, ops


def blocks(op_line: str, a: str, d: str, t: str) -> bool:
    p = op_line.split()
    op = p[0]
    if op == "CX":
        c1, c2 = p[1], p[2]
        return c2 in (a, d) or c1 == t
    if op == "CCX":
        a2, b2, t2 = p[1], p[2], p[3]
        return t2 in (a, d) or t in (a2, b2)
    if op == "X":
        return p[1] in (a, d)
    if op in ("HMR", "R"):
        return p[1] in (a, d, t)
    if op in ("NEG", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
        return False
    if op in ("Z", "CZ"):
        # diagonal: commutes with CCX only if disjoint wires
        wires = set(p[1:3])
        return bool(wires & {a, d, t})
    if op in ("SWAP", "CSWAP"):
        # conservative: any shared wire blocks (window has none; keep exact)
        wires = set(p[1:4])
        return bool(wires & {a, d, t})
    if " if " in op_line or op.startswith("PUSH") or op.startswith("POP"):
        return True
    return True  # unknown op: conservative block


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
    ones[-1] = np.uint64((1 << (N_INPUTS % 64)) - 1)

    for line in ops[:A]:
        if " if " in line:
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
            x_, y_ = int(p[1][1:]), int(p[2][1:])
            qv[x_], qv[y_] = qv[y_], qv[x_]
        elif op == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            qv[t_] ^= qv[a_] & qv[b_]
        elif op == "CSWAP":
            c_, a_, b_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            pr = qv[c_] & (qv[a_] ^ qv[b_])
            qv[a_] ^= pr
            qv[b_] ^= pr

    # per-CCX snapshots of control words: simulate window, record words at each CCX
    recs = []
    for idx in range(A, B):
        p = ops[idx].split()
        if p[0] == "X":
            qv[int(p[1][1:])] ^= ones
        elif p[0] == "CX":
            qv[int(p[2][1:])] ^= qv[int(p[1][1:])]
        elif p[0] == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            recs.append({"idx": idx, "a": p[1], "b": p[2], "t": p[3],
                         "wa": qv[a_].copy(), "wb": qv[b_].copy()})
            qv[t_] ^= qv[a_] & qv[b_]

    by_tgt = defaultdict(list)
    for r in recs:
        by_tgt[r["t"]].append(r)
    pairs = []
    for t, v in by_tgt.items():
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                si = {v[i]["a"], v[i]["b"]}
                sj = {v[j]["a"], v[j]["b"]}
                if len(si & sj) == 1:
                    pairs.append((v[i], v[j], sorted(si & sj)[0]))
    res = {"n_pairs": len(pairs), "m1_stable": 0, "m2_commutable": 0, "feasible": [],
           "block_reasons": defaultdict(int), "min_gap": None}
    gaps = []
    for r1, r2, d in pairs:
        gaps.append(r2["idx"] - r1["idx"])
        # M1: shared-control stability (word equality at both points)
        w1 = r1["wa"] if r1["a"] == d else r1["wb"]
        w2 = r2["wa"] if r2["a"] == d else r2["wb"]
        if not np.array_equal(w1, w2):
            res["block_reasons"]["M1-shared-control-unstable"] += 1
            continue
        res["m1_stable"] += 1
        # M2: bubble r1 down: every op between must commute with CCX(a1,d,t)
        a1 = r1["b"] if r1["a"] == d else r1["a"]
        t = r1["t"]
        blocker = None
        for k in range(r1["idx"] + 1, r2["idx"]):
            if blocks(ops[k], a1, d, t):
                blocker = (k, ops[k])
                break
        if blocker is None:
            res["m2_commutable"] += 1
            res["feasible"].append({"i": r1["idx"], "j": r2["idx"], "t": t,
                                    "shared": d, "other": [a1, r2["b"] if r2["a"] == d else r2["a"]]})
        else:
            res["block_reasons"][f"M2-blocked-by-{blocker[1].split()[0]}"] += 1
    res["min_gap"] = min(gaps) if gaps else None
    res["block_reasons"] = dict(res["block_reasons"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "feasible"}, indent=2))
    print("feasible:", json.dumps(res["feasible"][:10], indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
