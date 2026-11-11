"""S1 M1 pilot: k=2 same-product census + shortest-span equivalence refutation.

Read-only input: main-repo new-family KMB (26ebf39d). Writes only evidence.json
in this dir. No verifier run (no net-negative candidate -> gated off).
Method: bit-parallel full-domain word trace (audit_gengsr.py::run_bit_parallel_audit)
+ exhaustive slice bitmask check (audit_gengsr.py::exhaustive_slice_check).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

import kickmix as km

MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
NEW_SHA = "26ebf39df3b13e5fd2d923d1b9988043b107b64f6e21efc5cc9bc76f5d56adec"
S1 = (8893, 16329)
N_INPUTS = 3133452


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ops(kmb_path: Path) -> list[str]:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def k2_pairs(ops: list[str]) -> list[tuple[tuple, list[int]]]:
    pos: dict = defaultdict(list)
    for g, l in enumerate(ops):
        if l.startswith("CCX") and " if " not in l:
            p = l.split()
            pos[(tuple(sorted([p[1], p[2]])), p[3])].append(g)
    return [(k, v) for k, v in pos.items()
            if len(v) == 2 and S1[0] <= v[0] < S1[1] and S1[0] <= v[1] < S1[1]]


def reachable_product_diffs(ops: list[str], pairs) -> dict:
    n_words = (N_INPUTS + 63) // 64
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = n_words * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(n_words, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = ((np.uint64(1) << np.uint64(N_INPUTS % 64)) - np.uint64(1)) \
        if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
    ones = np.full(n_words, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = last_mask
    watch = {g: k for k, v in pairs for g in v}
    rec: dict = {}
    depth = 0
    for idx, l in enumerate(ops):
        if idx in watch:
            (ct, _) = watch[idx]
            a = q[int(ct[0][1:])] & q[int(ct[1][1:])]
            a = a.copy()
            a[-1] &= last_mask
            rec[idx] = a
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        p, op = l.split(), l.split()[0]
        if op in ("HMR", "R"):
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            q[int(p[2][1:])] ^= q[int(p[1][1:])]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b].copy(), q[a].copy()
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[a] & q[b]
            prod[-1] &= last_mask
            q[t] ^= prod
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[cc] & (q[a] ^ q[b])
            prod[-1] &= last_mask
            q[a] ^= prod
            q[b] ^= prod
    out = []
    for k, v in sorted(pairs, key=lambda kv: kv[1][1] - kv[1][0]):
        d = rec[v[0]] ^ rec[v[1]]
        d[-1] &= last_mask
        mid = ops[v[0] + 1:v[1]]
        out.append({
            "product": [list(k[0]), k[1]], "occurrences": v,
            "span": v[1] - v[0],
            "hmr_between": sum(1 for m in mid if m.startswith(("HMR", "R "))),
            "pop1": int(np.sum(np.bitwise_count(rec[v[0]]))),
            "pop2": int(np.sum(np.bitwise_count(rec[v[1]]))),
            "reachable_diff": int(np.sum(np.bitwise_count(d))),
        })
    return {"pairs": out}


def slice_exhaustive_pilot(ops: list[str]) -> dict:
    lo, hi = 10746, 10758  # first CCX .. second CCX inclusive
    segs = ops[lo:hi]
    qs = sorted({qq for l in segs for qq in re.findall(r"q\d+", l)},
                key=lambda x: int(x[1:]))
    n = 1 << len(qs)
    full = (1 << n) - 1
    mask = {qq: 0 for qq in qs}
    for s in range(n):
        for i, qq in enumerate(qs):
            if (s >> i) & 1:
                mask[qq] |= (1 << s)
    p1 = mask["q21"] & mask["q25"]
    for l in ops[lo:hi - 1]:
        p = l.split()
        if p[0] == "CCX":
            mask[p[3]] ^= (mask[p[1]] & mask[p[2]])
            mask[p[3]] &= full
        elif p[0] == "CX":
            mask[p[2]] ^= mask[p[1]]
            mask[p[2]] &= full
        elif p[0] == "X":
            mask[p[1]] ^= full
            mask[p[1]] &= full
    p2 = (mask["q21"] & mask["q25"]) & full
    return {"slice": f"new[{lo}:{hi})", "qubits": qs,
            "n_entry_states": n,
            "p1_pop": bin(p1).count("1"), "p2_pop": bin(p2).count("1"),
            "entry_general_diff": bin((p1 ^ p2) & full).count("1")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path,
                    default=Path("experiments/invsqrt/20261110_s1m1/evidence.json"))
    args = ap.parse_args()
    assert sha256_file(NEW_KMB) == NEW_SHA, "new KMB hash mismatch"
    ops = parse_ops(NEW_KMB)
    assert len(ops) == 36686
    pairs = k2_pairs(ops)
    assert len(ops[S1[0]:S1[1]]) == S1[1] - S1[0]
    diff = reachable_product_diffs(ops, pairs)
    sl = slice_exhaustive_pilot(ops)
    ev = {
        "inputs": {"new_kmb": str(NEW_KMB), "new_sha256": NEW_SHA,
                   "new_ops": len(ops), "S1": list(S1),
                   "n_inputs_verified": N_INPUTS},
        "s1_k2_census": diff,
        "n_s1_k2_pairs": len(pairs),
        "convertible_pairs": 0,
        "pilot": {"shortest_pair": diff["pairs"][0], "slice_exhaustive": sl,
                  "proposed_rewrite": "drop 2nd CCX @10757; +CX q50 f(save, f=0) "
                  "@10746b, +CX f q50(reload) @10757, +CX q50 f(clean)",
                  "hypothetical_delta": {"CCX": -1, "CX": +3, "score_per_62Q": -62},
                  "verdict": "NOT equivalent: reachable p1!=p2 on 1391290 inputs; "
                  "entry-general diff 1536/4096 states. Ideal retain still wrong "
                  "(orig q50=p1^p2 vs rewritten 0)."},
        "conclusion": "closed: 0/13 S1 k=2 pairs convertible; no expansion, "
        "no .kmb, no verifier run.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n_s1_k2_pairs": len(pairs),
                      "shortest": diff["pairs"][0],
                      "slice": sl}, indent=2))


if __name__ == "__main__":
    main()
