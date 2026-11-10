"""Static audit of gengsr 25.2268 invsqrt (26ebf39d) vs Public Frontier 7c10edba.

Read-only inputs (main repo artifacts); writes only evidence JSON to this dir.
No verifier run here (only justified if a net-positive candidate is built).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import numpy as np

import kickmix as km

MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
BASE_KMB = MAIN / "artifacts/20261108_public_frontier/release/invsqrt.kmb"
NEW_SHA = "26ebf39df3b13e5fd2d923d1b9988043b107b64f6e21efc5cc9bc76f5d56adec"
BASE_SHA = "7c10edbac5835e441fe8f40782bd7dbc7b36834718c3a4e3509607a9d2a454d3"


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


def census(ops: list[str]) -> dict:
    return dict(Counter(l.split()[0] for l in ops))


def toffoli_like(cnt: dict) -> int:
    return cnt.get("CCX", 0) + cnt.get("CCZ", 0) + cnt.get("CSWAP", 0)


def cswap_clusters(ops: list[str], gap: int = 300) -> list[list[int]]:
    idxs = [i for i, l in enumerate(ops) if l.startswith("CSWAP")]
    if not idxs:
        return []
    clusters, cur = [], [idxs[0]]
    for a, b in zip(idxs, idxs[1:]):
        if b - a > gap:
            clusters.append(cur)
            cur = [b]
        else:
            cur.append(b)
    clusters.append(cur)
    return clusters


def paid_qubit_use(ops: list[str]) -> dict:
    ccx_tgt, ccx_ctl, cswap_ctl, ccz_use = Counter(), Counter(), Counter(), Counter()
    hmr_tgt = Counter()
    for l in ops:
        p = l.split()
        if p[0] == "CCX" and " if " not in l:
            ccx_ctl[p[1]] += 1
            ccx_ctl[p[2]] += 1
            ccx_tgt[p[3]] += 1
        elif p[0] == "CSWAP" and " if " not in l:
            cswap_ctl[p[1]] += 1
        elif p[0] == "CCZ" and " if " not in l:
            ccz_use[p[1]] += 1
            ccz_use[p[2]] += 1
            ccz_use[p[3]] += 1
        elif p[0] == "HMR":
            hmr_tgt[p[1]] += 1
    return {"ccx_target": dict(ccx_tgt), "ccx_control": dict(ccx_ctl),
            "cswap_control": dict(cswap_ctl), "ccz_qubit": dict(ccz_use),
            "hmr_target": dict(hmr_tgt)}


def check_hmr_liveness(ops: list[str]) -> dict:
    unread, guarded = 0, 0
    for idx, l in enumerate(ops):
        p = l.split()
        if p[0] not in ("HMR", "R"):
            continue
        q = p[1]
        saw_zpow = False
        for j in range(idx - 1, -1, -1):
            p2 = ops[j].split()
            if p2[0] in ("PUSH_CONDITION", "POP_CONDITION"):
                continue
            if q not in p2:
                continue
            if p2[0] in ("Z", "Z_POW", "CZ", "CCZ"):
                saw_zpow = True
                continue
            if p2[0] == "CCX" and p2[3] == q and (" if " not in ops[j]):
                if saw_zpow:
                    guarded += 1
                else:
                    unread += 1
            break
    return {"unread_ccx_before_hmr": unread, "zpow_guarded_ccx_before_hmr": guarded}


def run_bit_parallel_audit(ops: list[str]) -> dict:
    n_inputs, n_words = 3133452, (3133452 + 63) // 64
    xs = np.arange(1, n_inputs + 1, dtype=np.uint64)
    pad = n_words * 64 - n_inputs
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(n_words, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = ((np.uint64(1) << np.uint64(n_inputs % 64)) - np.uint64(1)) if n_inputs % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
    ones = np.full(n_words, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = last_mask
    depth, degenerate = 0, 0
    for l in ops:
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        p, op = l.split(), l.split()[0]
        if op == "HMR" or op == "R":
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            q[int(p[2][1:])] ^= q[int(p[1][1:])]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b], q[a]
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[a] & q[b]
            prod[-1] &= last_mask
            if not np.any(prod):
                degenerate += 1
            q[t] ^= prod
        elif op == "CSWAP":
            c, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = q[c] & (q[a] ^ q[b])
            prod[-1] &= last_mask
            if not np.any(prod):
                degenerate += 1
            q[a] ^= prod
            q[b] ^= prod
    resid = {}
    for w in range(22, 62):
        arr = q[w].copy()
        arr[-1] &= last_mask
        resid[f"q{w}"] = int(np.sum(np.bitwise_count(arr)))
    return {"n_inputs_verified": n_inputs, "degenerate_uncond_paid_gates": degenerate,
            "ancilla_q22_q61_all_zero_at_end": all(v == 0 for v in resid.values()),
            "residual_popcounts": resid}


def exhaustive_slice_check() -> dict:
    # Novel primitive slice: new[16342:16350] (CSWAP/CX recycle of q28 scratch).
    # Exhaustive over all 2^9 basis states of involved qubits, Python-int bitmask engine.
    # Semantics: X flips, CX xors, CCX xors AND, CSWAP xors (c & (a^b)) into a,b,
    # HMR measures (deterministic on basis states) then resets to 0.
    qs = ["q0", "q3", "q5", "q18", "q21", "q23", "q27", "q28", "q52"]
    k = len(qs)
    idx = {name: i for i, name in enumerate(qs)}
    n = 1 << k
    full = (1 << n) - 1
    # state bit s of mask[q] = value of qubit q in basis state s
    mask = {name: 0 for name in qs}
    for s in range(n):
        for i, name in enumerate(qs):
            if (s >> i) & 1:
                mask[name] |= (1 << s)
    prog = [("CSWAP", "q18", "q28", "q0"), ("CSWAP", "q27", "q28", "q3"),
            ("CX", "q23", "q21"), ("CSWAP", "q21", "q5", "q28"),
            ("CX", "q23", "q21"), ("HMR", "q28"), ("CX", "q52", "q28")]
    # Z_POW is diagonal: no bit effect. No conditional ops in this slice.
    for op in prog:
        if op[0] == "CX":
            _, c, t = op
            mask[t] ^= mask[c]
            mask[t] &= full
        elif op[0] == "CSWAP":
            _, c, a, b = op
            prod = mask[c] & (mask[a] ^ mask[b])
            mask[a] ^= prod
            mask[b] ^= prod
        elif op[0] == "HMR":
            mask[op[1]] = 0
    init = {name: 0 for name in qs}
    for s in range(n):
        for i, name in enumerate(qs):
            if (s >> i) & 1:
                init[name] |= (1 << s)
    controls = ["q18", "q21", "q23", "q27", "q52"]
    routed = ["q0", "q3", "q5"]
    return {"slice": "new[16342:16350) = CSWAP q18 q28 q0; CSWAP q27 q28 q3; "
                     "CX q23 q21; CSWAP q21 q5 q28; CX q23 q21; HMR q28; CX q52 q28 "
                     "(Z_POW diagonal: no bit effect)",
            "n_basis_states": n,
            "control_qubits_bitwise_preserved": bool(
                all(mask[w] == init[w] for w in controls)),
            "scratch_q28_recycled_to_input_q52": bool(mask["q28"] == init["q52"]),
            "data_qubits_q0_q3_q5_routed_not_preserved_as_expected": bool(
                any(mask[w] != init[w] for w in routed))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path,
                    default=Path("experiments/invsqrt/20261110_gengsr_audit/evidence.json"))
    args = ap.parse_args()

    assert sha256_file(NEW_KMB) == NEW_SHA, "new KMB hash mismatch"
    assert sha256_file(BASE_KMB) == BASE_SHA, "base KMB hash mismatch"
    new, base = parse_ops(NEW_KMB), parse_ops(BASE_KMB)
    assert len(new) == 36686 and len(base) == 53686

    cn, cb = census(new), census(base)
    info_tags = {"new": cn.get("INFO_TAG", 0), "base": cb.get("INFO_TAG", 0)}

    # Anchor blocks: exact-order verbatim CSWAP runs shared by both families.
    cl_n, cl_b = cswap_clusters(new), cswap_clusters(base)
    seqs_n = [[new[i] for i in c] for c in cl_n]
    seqs_b = [[base[i] for i in c] for c in cl_b]
    anchor36 = next(s for s in seqs_n if len(s) == 36)
    anchor49 = next(s for s in seqs_n if len(s) == 49)
    assert anchor36 in seqs_b and anchor49 in seqs_b, "anchors must exist verbatim in base"
    a1 = next(c for c, s in zip(cl_n, seqs_n) if s == anchor36)
    a5 = next(c for c, s in zip(cl_n, seqs_n) if s == anchor49)
    b1 = next(c for c, s in zip(cl_b, seqs_b) if s == anchor36)
    b5 = next(c for c, s in zip(cl_b, seqs_b) if s == anchor49)
    a1r, a5r, b1r, b5r = (a1[0], a1[-1] + 1), (a5[0], a5[-1] + 1), (b1[0], b1[-1] + 1), (b5[0], b5[-1] + 1)
    # big-middle clusters: largest non-anchor clusters
    big_n = max((c for c, s in zip(cl_n, seqs_n) if len(s) not in (36, 49)), key=len)
    big_b = max((c for c, s in zip(cl_b, seqs_b) if len(s) not in (36, 49)), key=len)

    bounds_n = [0, a1r[0], a1r[1], big_n[0], big_n[-1] + 1, a5r[0], a5r[1], len(new)]
    bounds_b = [0, b1r[0], b1r[1], big_b[0], big_b[-1] + 1, b5r[0], b5r[1], len(base)]
    names = ["S0 pre-A1 (priority-encode + normalize shifter)",
             "A1 36-CSWAP selector (verbatim anchor)",
             "S1 A1 -> big-middle (second arithmetic block)",
             "A3 big-middle shift-select (novel family pattern)",
             "S2 big-middle -> end (newton/phase/denorm-prefix)",
             "A5 49-CSWAP unnormalize (verbatim anchor)", "S3 tail"]
    regions = []
    for name, (s0, e0), (s1, e1) in zip(names, zip(bounds_n, bounds_n[1:]), zip(bounds_b, bounds_b[1:])):
        r0, r1 = Counter(l.split()[0] for l in new[s0:e0]), Counter(l.split()[0] for l in base[s1:e1])
        regions.append({"name": name, "new_range": [s0, e0], "base_range": [s1, e1],
                        "new": dict(r0), "base": dict(r1)})

    # front/middle CSWAP multiset diffs
    front_n = [new[i] for i in cl_n[0]]
    front_b = [base[i] for i in cl_b[0]]
    mid_n = [new[i] for i in big_n]
    mid_b = [base[i] for i in big_b]
    cn_f, cb_f, cn_m, cb_m = (Counter(x) for x in (front_n, front_b, mid_n, mid_b))
    summary = {
        "inputs": {"new_kmb": str(NEW_KMB), "new_sha256": NEW_SHA, "new_ops": len(new),
                   "base_kmb": str(BASE_KMB), "base_sha256": BASE_SHA, "base_ops": len(base),
                   "notebook": "gengsr/lb-25-2268-shifter-46-own-chemistry-loaders (v1)",
                   "companions": ["ozertuu/25-218-starter-notebook (v91)",
                                  "maoxin123/lb-25-218-combined-invsqrt-refit-chem (v2)"]},
        "full_census": {"new": cn, "base": cb,
                        "delta": {k: cn.get(k, 0) - cb.get(k, 0) for k in sorted(set(cn) | set(cb))},
                        "static_toffoli_like": {"new": toffoli_like(cn), "base": toffoli_like(cb)}},
        "info_tag_present": info_tags,
        "verbatim_anchors": {"A1_36_order_identical": True, "A5_49_order_identical": True,
                             "A1_new_range": list(a1r), "A5_new_range": list(a5r)},
        "regions": regions,
        "cswap_clusters": {
            "new": [{"range": [c[0], c[-1]], "n": len(c),
                               "controls": dict(Counter(new[i].split()[1] for i in c))} for c in cl_n],
            "base": [{"range": [c[0], c[-1]], "n": len(c),
                                "controls": dict(Counter(base[i].split()[1] for i in c))} for c in cl_b]},
        "front_shifter_46_vs_47": {
            "new_n": len(front_n), "base_n": len(front_b),
            "new_only": sorted(set(cn_f) - set(cb_f)), "base_only": sorted(set(cb_f) - set(cn_f)),
            "common": len(set(cn_f) & set(cb_f))},
        "bigmid_70_vs_92": {
            "new_n": len(mid_n), "base_n": len(mid_b),
            "removed_in_new": {k: cb_m[k] for k in sorted(set(cb_m) - set(cn_m))},
            "added_in_new": {k: cn_m[k] for k in sorted(set(cn_m) - set(cb_m))},
            "count_changes": {k: (cn_m[k], cb_m[k]) for k in sorted(set(cn_m) & set(cb_m)) if cn_m[k] != cb_m[k]}},
        "paid_qubit_use": {"new": paid_qubit_use(new), "base": paid_qubit_use(base)},
        "hmr_peephole_new": check_hmr_liveness(new),
        "full_domain_classical_new": run_bit_parallel_audit(new),
        "novel_primitive_slice_check": exhaustive_slice_check(),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("inputs", "info_tag_present", "verbatim_anchors",
                       "hmr_peephole_new", "novel_primitive_slice_check")}, indent=2))
    fd = summary["full_domain_classical_new"]
    print(json.dumps({k: fd[k] for k in ("n_inputs_verified", "degenerate_uncond_paid_gates",
                                        "ancilla_q22_q61_all_zero_at_end")}, indent=2))


if __name__ == "__main__":
    main()
