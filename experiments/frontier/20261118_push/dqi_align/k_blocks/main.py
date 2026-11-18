"""DQI align line v4: block-level redundancy and the period-4 multiply pattern.

CPU-only Kaggle kernel.  **Static IR read only.  No simulation, no verifier, no
candidate, no submission.**

Confirmed by other lines and not re-measured here: S_i = qubits 12i..12i+11 (70 S
registers), words 70..73 are the pool, 890 qubits, 362,012 CCX.  The two big spans are
multiply streams, not shifts.

This kernel delivers `blocks.json` with

  A. block decomposition of span_fwd [19,508,954, 21,385,877) and span_rev
     [46,230,185, 52,842,219): maximal runs of CCX sharing the same (word, word, word)
     triple with gap <= 80 and size >= 8; per block a *content hash* over
     (wa, wb, wt, n_ccx, sorted bit triples).  For every group of >= 2 blocks with the
     same content, the op ranges, and the interference test: does any operation
     between two members touch any of the 36 qubits the block acts on (and are any of
     them phase gates)?  Only interference-free pairs are deletable.

  B. the full ordered word-triple list plus bit triples for a 200-block window of
     span_fwd (the (6,46,70)/(7,46,48)/(10,46,70)/(11,46,48) period-4 family), and the
     same for the cluster132 dot-product family, so the arithmetic structure can be
     named.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time
from hashlib import blake2b

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def find_inputs():
    xz = irp = None
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        xz = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("vqcc_ir.py"):
        irp = p
        break
    if not (xz and irp):
        raise SystemExit("inputs not found")
    return xz, irp


XZ, IRPY = find_inputs()
raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
t = c.types
N = c.num_ops
say("ops", N, "Q", c.num_qubits, "T", int(c.toffoli_like()))

base = (t & 0x7F)
L2, L3 = ir.L2Q[t], ir.L3Q[t]
cf2 = np.zeros(N + 1, np.int32); cf2[1:] = np.cumsum(L2)
cf3 = np.zeros(N + 1, np.int32); cf3[1:] = np.cumsum(L3)
q0 = np.full(N, -1, np.int16)
q1 = np.full(N, -1, np.int16)
q2 = np.full(N, -1, np.int16)
i2 = np.flatnonzero(L2); k2 = cf2[i2 + 1] - 1
q0[i2] = c.qq0[k2]; q1[i2] = c.qq1[k2]
i3 = np.flatnonzero(L3); k3 = cf3[i3 + 1] - 1
q0[i3] = c.qqq0[k3]; q1[i3] = c.qqq1[k3]; q2[i3] = c.qqq2[k3]
del i2, i3, k2, k3, cf2
say("payloads ready")

ccxp = np.flatnonzero(base == 0x31)
sel_all = ccxp
qq = cf3[sel_all + 1] - 1
CA = c.qqq0[qq].astype(np.int64)
CB = c.qqq1[qq].astype(np.int64)
CT = c.qqq2[qq].astype(np.int64)
del qq
CAw, CBw, CTw = CA // 12, CB // 12, CT // 12
say("ccx arrays", len(ccxp))

PHASE = {0x10, 0x13, 0x30, 0x20, 0x50}      # Z, Z_POW, CCZ, CZ, HMR count as "phase / write"


def blocks_of(lo, hi, min_size=8, gap=80):
    """maximal same-word-triple CCX runs inside [lo,hi)."""
    m = (ccxp >= lo) & (ccxp < hi)
    P = ccxp[m]
    A, B, T = CAw[m], CBw[m], CTw[m]
    out = []
    i = 0
    n = len(P)
    while i < n:
        j = i
        while (j + 1 < n and P[j + 1] - P[j] <= gap
               and A[j + 1] == A[i] and B[j + 1] == B[i] and T[j + 1] == T[i]):
            j += 1
        if j - i + 1 >= min_size:
            bits = sorted(zip((CA[m][i:j + 1] % 12).tolist(),
                              (CB[m][i:j + 1] % 12).tolist(),
                              (CT[m][i:j + 1] % 12).tolist()))
            content = (int(A[i]), int(B[i]), int(T[i]), j - i + 1,
                       tuple(bits))
            h = blake2b(repr(content).encode(), digest_size=12).hexdigest()
            out.append({"op_lo": int(P[i]), "op_hi": int(P[j]),
                        "wa": int(A[i]), "wb": int(B[i]), "wt": int(T[i]),
                        "n": int(j - i + 1), "h": h,
                        "bits": [list(x) for x in bits]})
        i = j + 1
    return out


def touches_between(e1, s2, qubits):
    """does any op in (e1, s2) touch any of `qubits`?  returns (n_touch, n_phase)."""
    if s2 <= e1 + 1:
        return 0, 0
    qs = np.array(sorted(qubits), dtype=np.int16)
    a, b, d = q0[e1 + 1:s2], q1[e1 + 1:s2], q2[e1 + 1:s2]
    hit = np.isin(a, qs) | np.isin(b, qs) | np.isin(d, qs)
    if not hit.any():
        return 0, 0
    idx = np.flatnonzero(hit)
    ph = 0
    for k in idx[:200000]:
        if int(base[e1 + 1 + k]) in PHASE:
            ph += 1
    return int(hit.sum()), int(ph)


def dedup_report(blocks, tag, max_pairs=40):
    groups = {}
    for b in blocks:
        groups.setdefault(b["h"], []).append(b)
    dups = {h: g for h, g in groups.items() if len(g) >= 2}
    rep = {"n_blocks": len(blocks),
           "n_distinct_content": len(groups),
           "n_duplicate_groups": len(dups),
           "n_duplicate_pairs": int(sum(len(g) * (len(g) - 1) // 2
                                        for g in dups.values())),
           "T_in_duplicate_blocks": int(sum(b["n"] for g in dups.values() for b in g)),
           "pairs": []}
    checked = 0
    clean = 0
    for h, g in sorted(dups.items(), key=lambda kv: -len(kv[1]["n"]))[:max_pairs * 5]:
        g = sorted(g, key=lambda x: x["op_lo"])
        for u, v in zip(g, g[1:]):
            qubits = set()
            for wbase, other in ((u["wa"], u["wb"]), (u["wt"], None)):
                qubits.update(range(12 * wbase, 12 * wbase + 12))
            qubits.update(range(12 * u["wb"], 12 * u["wb"] + 12))
            nt, nph = touches_between(u["op_hi"], v["op_lo"], qubits)
            checked += 1
            ok = (nt == 0)
            if ok:
                clean += 1
            if len(rep["pairs"]) < max_pairs:
                rep["pairs"].append({"wa": u["wa"], "wb": u["wb"], "wt": u["wt"],
                                     "n": u["n"],
                                     "op1": [u["op_lo"], u["op_hi"]],
                                     "op2": [v["op_lo"], v["op_hi"]],
                                     "gap_ops": v["op_lo"] - u["op_hi"],
                                     "touching_ops_between": nt,
                                     "phase_ops_between": nph,
                                     "deletable": bool(ok)})
    rep["pairs_checked"] = checked
    rep["pairs_interference_free"] = clean
    rep["T_deletable"] = int(42 * clean)
    say(tag, "blocks", rep["n_blocks"], "distinct", rep["n_distinct_content"],
        "dup groups", rep["n_duplicate_groups"], "clean pairs", clean)
    return rep


BL = {}
for tag, (lo, hi) in (("span_fwd", (19_508_954, 21_385_877)),
                      ("span_rev", (46_230_185, 52_842_219)),
                      ("cluster132", (21_385_877, 21_588_611))):
    b = blocks_of(lo, hi)
    BL[tag] = {"lo": lo, "hi": hi, "n_blocks": len(b),
               "size_hist": {int(k): int(v) for k, v in
                             zip(*np.unique([x["n"] for x in b],
                                            return_counts=True))} if b else {},
               "dedup": dedup_report(b, tag),
               "blocks_head": [{k: x[k] for k in ("op_lo", "op_hi", "wa", "wb", "wt", "n")}
                               for x in b[:60]]}
    if tag == "span_fwd":
        # B: the full period-4 window with complete bit triples, plus the family test
        fam = [x for x in b if x["wb"] == 46]
        ref = None
        fam_rows = []
        for x in fam:
            key = sorted((aa, bb) for aa, bb, _ in x["bits"])
            h = blake2b(repr(key).encode(), digest_size=8).hexdigest()
            if ref is None:
                ref = (x["wa"], x["wt"], key)
            fam_rows.append({"wa": x["wa"], "wt": x["wt"], "n": x["n"],
                             "ab_multiset_hash": h,
                             "same_ab_as_first": bool(key == ref[2]),
                             "op_lo": x["op_lo"]})
        BL["family_wb46"] = {
            "note": "every block with second operand word 46; 'same_ab_as_first' "
                    "compares the sorted (a_bit,b_bit) multiset with the first member",
            "members": fam_rows}
        BL["pattern_span_fwd"] = {
            "note": "200 blocks starting at the first (6,46,...) block, FULL bit triples",
            "blocks": [{k: x[k] for k in ("op_lo", "op_hi", "wa", "wb", "wt", "n")}
                       | {"bits": x["bits"]} for x in b[18:218]]}
    if tag == "cluster132":
        BL["pattern_cluster132"] = {
            "blocks": [{k: x[k] for k in ("op_lo", "op_hi", "wa", "wb", "wt", "n")}
                       | {"bits_head": x["bits"][:6]} for x in b[:40]]}

with open(WORK / "blocks.json", "w") as f:
    json.dump(BL, f, indent=1)
say("blocks.json written")

for tag in ("span_fwd", "span_rev", "cluster132"):
    d = BL[tag]
    print(f"\n== {tag} blocks {d['n_blocks']} sizes {json.dumps(d['size_hist'])}")
    print("   dedup:", json.dumps({k: v for k, v in d["dedup"].items() if k != "pairs"}))
    for p in d["dedup"]["pairs"][:8]:
        print("   pair:", json.dumps(p))
    print("   first blocks:", json.dumps(d["blocks_head"][:14]))
print("\npattern_span_fwd first 40:",
      json.dumps(BL["pattern_span_fwd"]["blocks"][:40])[:2000])
raw.unlink()
say("tape removed, done")
