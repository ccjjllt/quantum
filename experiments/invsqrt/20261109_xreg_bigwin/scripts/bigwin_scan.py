"""Big-window cross-register resynthesis probe (Task 1).

Window pool: [2006:14215] (12209 ops, fully unconditional: CX+CCX+X only).
Goal: find >=1 CCX saving under boundary-function invariance via
  (a) dead CCX (product word == 0 for all 3,133,452 inputs),
  (b) exactly-canceling CCX pair (same triple, equal products, target untouched between),
  (c) affine-merge pair (same target, shared control, other-control XOR available),
  (d) long-lived wire swap / affine-line merge enabling boundary CX cancellation.
No conditional/deep/diagonal gates inside -> zero-branch word sim is EXACT here.

Output: bigwin_scan.json
"""
from __future__ import annotations

import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
OUT = Path("experiments/invsqrt/20261109_xreg_bigwin/bigwin_scan.json")
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64
LAST_MASK = np.uint64((1 << (N_INPUTS % 64)) - 1) if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
A, B = 2006, 14215


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
    assert len(ops) == 53686, len(ops)
    seg = ops[A:B]
    kinds = Counter(l.split()[0] for l in seg)
    assert set(kinds) <= {"CX", "CCX", "X"}, kinds

    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    qv = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> np.uint64(bit)) & np.uint64(1)).astype(np.uint64)
        qv[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = LAST_MASK

    # prefix [0:A) then window; record product/target words at each CCX
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
            # kmx order: CX control target (verified by minimal Simulator circuit)
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
    snapA = [w.copy() for w in qv]
    popsA = [int(np.sum(np.bitwise_count(w))) for w in qv]

    ccx_recs = []  # (idx, a, b, t, prod_word, target_before)
    for idx in range(A, B):
        line = ops[idx]
        p = line.split()
        if p[0] == "X":
            qv[int(p[1][1:])] ^= ones
        elif p[0] == "CX":
            # kmx order: CX control target (verified by minimal Simulator circuit)
            qv[int(p[2][1:])] ^= qv[int(p[1][1:])]
        elif p[0] == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = (qv[a_] & qv[b_]).copy()
            ccx_recs.append({"idx": idx, "a": p[1], "b": p[2], "t": p[3],
                             "prod": prod, "tgt_before": qv[t_].copy()})
            qv[t_] ^= qv[a_] & qv[b_]
    snapB = [w.copy() for w in qv]
    popsB = [int(np.sum(np.bitwise_count(w))) for w in qv]

    # (a) dead CCX
    dead = [{"idx": r["idx"], "line": f"CCX {r['a']} {r['b']} {r['t']}"}
            for r in ccx_recs if not np.any(r["prod"])]
    # (b) canceling pairs: same triple, equal prod, target untouched between
    # target touched between = any CX with target==t or CCX with target==t or X on t
    tgt_hits = defaultdict(list)
    for idx in range(A, B):
        p = ops[idx].split()
        if p[0] == "CX":
            tgt_hits[p[2]].append(idx)
        elif p[0] == "CCX":
            tgt_hits[p[3]].append(idx)
        elif p[0] == "X":
            tgt_hits[p[1]].append(idx)
    by_triple = defaultdict(list)
    for r in ccx_recs:
        by_triple[(tuple(sorted([r["a"], r["b"]])), r["t"])].append(r)
    cancel_pairs = []
    for key, v in by_triple.items():
        if len(v) < 2:
            continue
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                if not np.array_equal(v[i]["prod"], v[j]["prod"]):
                    continue
                # target hits strictly between (excluding endpoints which are the CCXs themselves)
                between = [h for h in tgt_hits[v[i]["t"]] if v[i]["idx"] < h < v[j]["idx"]]
                cancel_pairs.append({"key": [list(key[0]), key[1]],
                                     "i": v[i]["idx"], "j": v[j]["idx"],
                                     "tgt_hits_between": between})
    # exact-cancelling = no target touch between
    exact = [c for c in cancel_pairs if not c["tgt_hits_between"]]
    # (c) affine-merge candidates: same target, share exactly one control
    merge_cands = []
    by_tgt = defaultdict(list)
    for r in ccx_recs:
        by_tgt[r["t"]].append(r)
    for t, v in by_tgt.items():
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                si = {v[i]["a"], v[i]["b"]}
                sj = {v[j]["a"], v[j]["b"]}
                if len(si & sj) == 1:
                    eq = bool(np.array_equal(v[i]["prod"], v[j]["prod"]))
                    merge_cands.append({"t": t,
                                        "i": v[i]["idx"], "opi": f"CCX {v[i]['a']} {v[i]['b']} {t}",
                                        "j": v[j]["idx"], "opj": f"CCX {v[j]['a']} {v[j]['b']} {t}",
                                        "shared": sorted(si & sj),
                                        "prod_equal": eq,
                                        "pop_i": int(np.sum(np.bitwise_count(v[i]["prod"]))),
                                        "pop_j": int(np.sum(np.bitwise_count(v[j]["prod"])))})
    # (d) boundary snapshots: exact-duplicate pairs + per-wire delta words
    def dup_pairs(snap):
        d = []
        for i in range(62):
            for j in range(i + 1, 62):
                if np.array_equal(snap[i], snap[j]):
                    d.append([i, j])
        return d
    dA, dB = dup_pairs(snapA), dup_pairs(snapB)
    setA = {tuple(p) for p in dA}
    both = [p for p in dB if tuple(p) in setA]
    delta = {}
    for i in range(62):
        w = snapA[i] ^ snapB[i]
        if np.any(w):
            delta[f"q{i}"] = int(np.sum(np.bitwise_count(w)))
    # affine relations at A: qj == qi xor const?
    const_links_A = []
    for i in range(62):
        for j in range(i + 1, 62):
            if np.array_equal(snapA[i] ^ snapA[j], np.zeros(N_WORDS, dtype=np.uint64)) or \
               np.array_equal(snapA[i] ^ snapA[j], ones):
                const_links_A.append([i, j])
    # long-lived wires: least toggled (fewest CX-target hits in window)
    tgt_count = Counter()
    for idx in range(A, B):
        p = ops[idx].split()
        if p[0] == "CX":
            tgt_count[p[2]] += 1
        elif p[0] == "CCX":
            tgt_count[p[3]] += 1
    # 2500-window CCX density + repeats for window choice
    dens = []
    for s in range(A, B - 2500 + 1, 500):
        w = ops[s:s + 2500]
        cc = Counter(x for x in w if x.startswith("CCX"))
        dens.append({"start": s, "ccx": sum(cc.values()), "distinct": len(cc),
                     "repeats_extra": sum(v - 1 for v in cc.values() if v > 1)})

    out = {
        "window": [A, B], "kinds": dict(kinds),
        "n_ccx": len(ccx_recs),
        "dead_ccx": dead,
        "cancel_pairs_equal_prod": cancel_pairs,
        "exact_cancel_pairs": exact,
        "n_merge_cands_share_one_control": len(merge_cands),
        "merge_cands_sample": merge_cands[:40],
        "dup_pairs_A": dA, "dup_pairs_B": dB, "dup_both": both,
        "zero_wires_A": [i for i, p in enumerate(popsA) if p == 0],
        "zero_wires_B": [i for i, p in enumerate(popsB) if p == 0],
        "ones_wires_A": [i for i, p in enumerate(popsA) if p == N_INPUTS],
        "n_delta_nonzero": len(delta),
        "affine_const_links_A": const_links_A,
        "least_targeted_wires": sorted(tgt_count.items(), key=lambda kv: kv[1])[:12],
        "density_2500": dens,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({k: v for k, v in out.items()
                               if k not in ("merge_cands_sample",)} | {"merge_cands_sample": merge_cands[:40]},
                              indent=2), encoding="utf-8")
    print(json.dumps({"n_ccx": out["n_ccx"], "dead": dead,
                      "cancel_equal": len(cancel_pairs), "exact": exact,
                      "merge_cands": len(merge_cands),
                      "dup_both": both, "zeroA": out["zero_wires_A"],
                      "zeroB": out["zero_wires_B"],
                      "const_links_A": const_links_A,
                      "least_targeted": out["least_targeted_wires"]}, indent=2))
    print("density:", json.dumps(dens, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
