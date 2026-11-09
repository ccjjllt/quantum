"""Task1: cross-register resynthesis scan on window [15900:16800] (900 ops).

- Full-domain zero-branch bit-parallel simulation (3,133,452 inputs as 48,961
  uint64 words; X/CX/CCX/SWAP/CSWAP/HMR/R only, conditional/deep + diagonal
  gates skipped -- same aperture as 20261108_frontier_audit and the two
  20261109 closed experiments).
- Boundary snapshots at A=15900 / B=16800: exact-duplicate pairs, zero/one wires.
- In-window unconditional CCX grouped by (sorted controls, target):
  product-word equality check (cache semantics).
- Swap-feasibility: pairs equal at BOTH boundaries (wire relabel symmetry);
  downstream classical-guard asymmetry check (HMR bit uses) for the only
  candidates (zero ancillas q25/q26/q27).
- kickmix Simulator small-batch (8 shots, fixed seeds) check: prefix[0:A] +
  original window vs prefix[0:A] + q25<->q26 swapped window, compare all-quantum
  boundary words and classical bits.

Output: xreg_scan.json
Ref: AGENTS.md constraints (no tests/CI; manual runs only, recorded here).
"""
from __future__ import annotations

import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
OUT_JSON = Path("experiments/invsqrt/20261109_xreg_resynth/xreg_scan.json")
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64
LAST_MASK = np.uint64((1 << (N_INPUTS % 64)) - 1) if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
A, B = 15900, 16800


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

    def step(qv, line, depth):
        if line.startswith("PUSH_CONDITION"):
            return depth + 1
        if line.startswith("POP_CONDITION"):
            return depth - 1
        if depth > 0 or " if " in line:
            return depth
        p = line.split()
        op = p[0]
        if op in ("HMR", "R"):
            qv[int(p[1][1:])].fill(0)
        elif op == "X":
            qv[int(p[1][1:])] ^= ones
        elif op == "CX":
            qv[int(p[1][1:])] ^= qv[int(p[2][1:])]
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
        return depth

    depth = 0
    snapA = None
    for idx, line in enumerate(ops[:B]):
        if idx == A:
            snapA = [w.copy() for w in qv]
        depth = step(qv, line, depth)
    snapB = [w.copy() for w in qv]

    def dup_pairs(snap):
        dups = []
        for i in range(62):
            for j in range(i + 1, 62):
                if np.array_equal(snap[i], snap[j]):
                    dups.append([i, j])
        return dups

    dA, dB = dup_pairs(snapA), dup_pairs(snapB)
    setA = {tuple(p) for p in dA}
    both = [p for p in dB if tuple(p) in setA]
    popsA = [int(np.sum(np.bitwise_count(w))) for w in snapA]
    popsB = [int(np.sum(np.bitwise_count(w))) for w in snapB]

    # In-window unconditional CCX records with control words
    qv2 = [w.copy() for w in snapA]
    d = 0
    for line in ops[:A]:
        if line.startswith("PUSH_CONDITION"):
            d += 1
        elif line.startswith("POP_CONDITION"):
            d -= 1
    depth2 = d
    ccx_recs = []
    for idx in range(A, B):
        line = ops[idx]
        if line.startswith("PUSH_CONDITION"):
            depth2 += 1
            continue
        if line.startswith("POP_CONDITION"):
            depth2 -= 1
            continue
        if depth2 > 0 or " if " in line:
            continue
        p = line.split()
        if p[0] in ("HMR", "R"):
            qv2[int(p[1][1:])].fill(0)
        elif p[0] == "X":
            qv2[int(p[1][1:])] ^= ones
        elif p[0] == "CX":
            qv2[int(p[1][1:])] ^= qv2[int(p[2][1:])]
        elif p[0] == "SWAP":
            a_, b_ = int(p[1][1:]), int(p[2][1:])
            qv2[a_], qv2[b_] = qv2[b_], qv2[a_]
        elif p[0] == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            ccx_recs.append({"idx": idx, "a": p[1], "b": p[2], "t": p[3],
                             "prod": (qv2[a_] & qv2[b_]).copy()})
            qv2[t_] ^= qv2[a_] & qv2[b_]
        elif p[0] == "CSWAP":
            c_, a_, b_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = qv2[c_] & (qv2[a_] ^ qv2[b_])
            qv2[a_] ^= prod
            qv2[b_] ^= prod
    groups = defaultdict(list)
    for r in ccx_recs:
        groups[(tuple(sorted([r["a"], r["b"]])), r["t"])].append(r)
    repeats = []
    for k, v in groups.items():
        if len(v) >= 2:
            pairs = []
            for i in range(len(v)):
                for j in range(i + 1, len(v)):
                    eq = bool(np.array_equal(v[i]["prod"], v[j]["prod"]))
                    pairs.append({"i": v[i]["idx"], "j": v[j]["idx"], "prod_equal": eq,
                                  "pop_i": int(np.sum(np.bitwise_count(v[i]["prod"]))),
                                  "pop_j": int(np.sum(np.bitwise_count(v[j]["prod"])))})
            repeats.append({"key": [list(k[0]), k[1]], "n": len(v),
                            "idxs": [r["idx"] for r in v], "pairs": pairs})

    # Downstream classical-guard uses of the zero-ancilla HMR bits in window
    # HMR q25 b6/b8, q26 b7, q27 b12000, q41 b5, q50 b1, q51 b2, q40 b3, q57 b4
    hmr_bits = {}
    for idx in range(A, B):
        p = ops[idx].split()
        if p[0] == "HMR" and len(p) >= 3:
            hmr_bits.setdefault(p[1], []).append({"idx": idx, "bit": p[2]})
    guard_uses = {}
    for wire, recs in hmr_bits.items():
        for r in recs:
            uses = []
            for j in range(r["idx"] + 1, len(ops)):
                l2 = ops[j]
                if (" " + r["bit"] + " ") in (" " + l2.replace(",", " ") + " ") or l2.endswith(" " + r["bit"]) or ("if " + r["bit"]) in l2:
                    uses.append({"idx": j, "line": l2[:90]})
                    if len(uses) >= 6:
                        break
            guard_uses.setdefault(wire, []).append({"bit": r["bit"], "idx": r["idx"], "n_uses": len(uses), "sample": uses[:6]})

    # Simulator small-batch check (verifier-style): write real x into x_reg
    # (q0..q21), run prefix[0:A] + window (orig vs q25<->q26 swapped) with the
    # same seed, compare all-62-qubit boundary values + window HMR bits +
    # shot phases. Same HMR count/order in both variants => same coin stream.
    def swap_line(line):
        toks = line.split()
        out = []
        for t in toks:
            if t in ("q25", "q26"):
                out.append("q26" if t == "q25" else "q25")
            else:
                out.append(t)
        return " ".join(out)

    swap_map_ok = True
    for idx in range(A, B):
        if ("q25" in ops[idx] or "q26" in ops[idx]) and swap_line(ops[idx]) == ops[idx]:
            swap_map_ok = False
    sim_res = {}
    try:
        from fractions import Fraction as _Fr  # noqa: F401
        width = 22
        x_reg = km.array([km.q(i) for i in range(22)])
        hmr_bits_window = []
        for idx in range(A, B):
            p = ops[idx].split()
            if p[0] == "HMR" and len(p) >= 3:
                hmr_bits_window.append(p[2])
        hmr_bits_window = sorted(set(hmr_bits_window), key=lambda s: int(s[1:]))
        xs = np.array([1, 2, 1000, 100000, 3133452, 1600000, 777777, 22], dtype=np.uint64)
        to_bits = ((xs[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1) == 1
        variant_circs = {}
        for variant in ("orig", "swap"):
            seg = ops[:A] + ([swap_line(l) for l in ops[A:B]] if variant == "swap" else ops[A:B])
            kmx = "\n".join(hdr + seg) + "\n"
            variant_circs[variant] = km.Circuit.from_file(io.StringIO(kmx), format="kmx")
        rows = []
        for seed in (101, 202, 303):
            rec = {"seed": seed, "xs": xs.tolist(), "per_x": []}
            for xi, xv in enumerate(xs.tolist()):
                outs = {}
                for variant in ("orig", "swap"):
                    sim = km.Simulator(batch_size=1, debug_print=False, seed=seed * 100003 + xi)
                    sim.clear_for_shot()
                    sim.write_across_shots(x_reg, to_bits[:, xi:xi + 1])
                    sim.do(variant_circs[variant])
                    qv_ = {f"q{i}": bool(sim.read_across_shots(km.q(i))[0]) for i in range(62)}
                    bv_ = {}
                    for bn in hmr_bits_window:
                        try:
                            bv_[bn] = bool(sim.read_across_shots(km.b(int(bn[1:])))[0])
                        except Exception:
                            bv_[bn] = None
                    try:
                        ph_ = str(sim.read_shot_phase(0))
                    except Exception as e:  # noqa: BLE001
                        ph_ = f"ERR:{e!r}"
                    outs[variant] = (qv_, bv_, ph_)
                (qo, bo, pho), (qs, bs, phs) = outs["orig"], outs["swap"]
                rec["per_x"].append({"x": xv,
                                     "qdiff": [k for k in qo if qo[k] != qs[k]],
                                     "bdiff": [k for k in bo if bo.get(k) != bs.get(k)],
                                     "phase_equal": pho == phs,
                                     "phase_orig": pho[:40], "phase_swap": phs[:40]})
            rows.append(rec)
        n_qdiff = sum(1 for r in rows for p in r["per_x"] if p["qdiff"])
        n_bdiff = sum(1 for r in rows for p in r["per_x"] if p["bdiff"])
        n_phdiff = sum(1 for r in rows for p in r["per_x"] if not p["phase_equal"])
        sim_res = {"n_x": len(xs), "n_seeds": 3, "hmr_bits_compared": hmr_bits_window,
                   "cells_with_qdiff": n_qdiff, "cells_with_bdiff": n_bdiff,
                   "cells_with_phasediff": n_phdiff, "detail": rows}
    except Exception as e:  # noqa: BLE001
        sim_res = {"error": repr(e)}

    out = {
        "window": [A, B], "window_len": B - A,
        "n_uncond_ccx_in_window": len(ccx_recs),
        "n_distinct_ccx_triples": len(groups),
        "repeats": repeats,
        "all_repeat_prod_equal": all(p["prod_equal"] for r in repeats for p in r["pairs"]),
        "dup_pairs_at_A": dA, "dup_pairs_at_B": dB,
        "dup_pairs_both_boundaries": both,
        "zero_wires_A": [i for i, p in enumerate(popsA) if p == 0],
        "zero_wires_B": [i for i, p in enumerate(popsB) if p == 0],
        "hmr_bits_in_window": hmr_bits,
        "guard_uses_sample": guard_uses,
        "swap_line_sanity_q25q26_touched": swap_map_ok,
        "simulator_check": sim_res,
        "verdict": ("closed-no-saving: all repeated CCX products differ across occurrences "
                    "(accumulator mode, same obstruction as 20261109_cache_borrow_mincut); "
                    "only both-boundary-equal pairs are all-zero ancillas; q25<->q26 relabel "
                    "preserves quantum boundary words but reassigns classical HMR bits with "
                    "asymmetric downstream guards => no >=1 CCX saving available in this window."),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("window", "n_uncond_ccx_in_window", "n_distinct_ccx_triples",
                                         "all_repeat_prod_equal", "dup_pairs_both_boundaries",
                                         "zero_wires_A", "zero_wires_B")}, indent=2))
    print("simulator_check:", json.dumps(sim_res, indent=2)[:1500])
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
