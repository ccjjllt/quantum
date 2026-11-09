"""Zero-diff reorder candidate in declared window [5006:7506] (Task 2).

Context (see bigwin_scan.json / followup.json / merge_check.json, corrected
CX direction CX-control-target verified by minimal Simulator circuits):
  [2006:14215] is fully unconditional (CX/CCX/X only). Exact full-domain
  word sim (validated cell-for-cell against real Simulator at cut 7506):
  dead CCX 0/134; equal-product same-target pairs 0; constant-1 controls 0;
  both-boundary equal pairs: none (big window nor [5006:7506]/[5506:8006]/
  [6006:8506]); affine-merge feasible 0/117 (all shared controls unstable).
  => No >=1 CCX saving available. This candidate is a provably-zero-diff
  reorder (adjacent disjoint-wire commute) to validate the chain + arbiter.

Edit: swap ops 5006/5007 (CX q42 q54 | CX q59 q14, disjoint wires).
Checks:
  W  full-domain words at window end (7506): base vs reordered equal, all wires.
  S  Simulator small-batch full-circuit base vs candidate: final 62q + phase.
Then writes candidate .kmb (official verifier run is manual, not here).
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
ART = Path("artifacts/20261109_xreg_bigwin")
OUT_CAND = ART / "candidate_reorder_k5006.kmb"
OUT_JSON = Path("experiments/invsqrt/20261109_xreg_bigwin/reorder_probe.json")
WIN = (5006, 7506)
SWAP_AT = 5006
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64


def load_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return c, hdr, ops


def sim_words(ops, upto):
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
    for line in ops[:upto]:
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
    return qv


def half_turns_to_u64(ht) -> int:
    n, d = ht.as_integer_ratio()
    return (((n << 64) // d + 1) >> 1) & ((1 << 64) - 1)


def main() -> None:
    c_base, hdr, ops = load_ops()
    assert len(ops) == 53686
    assert ops[SWAP_AT] == "CX q42 q54", ops[SWAP_AT]
    assert ops[SWAP_AT + 1] == "CX q59 q14", ops[SWAP_AT + 1]
    assert not ({"q42", "q54"} & {"q59", "q14"})
    ops_r = ops.copy()
    ops_r[SWAP_AT], ops_r[SWAP_AT + 1] = ops_r[SWAP_AT + 1], ops_r[SWAP_AT]

    # W: full-domain boundary words at window end
    w_base = sim_words(ops, WIN[1])
    w_r = sim_words(ops_r, WIN[1])
    wdiff = [i for i in range(62) if not np.array_equal(w_base[i], w_r[i])]

    # build + write candidate
    c_cand = km.Circuit.from_file(io.StringIO("\n".join(hdr + ops_r) + "\n"), format="kmx")
    ART.mkdir(parents=True, exist_ok=True)
    c_cand.to_file(str(OUT_CAND), format="kmb")
    n_ccx = sum(1 for l in ops_r if l.startswith("CCX"))
    print("wrote", OUT_CAND, "ops", len(c_cand), "CCX", n_ccx)

    # S: Simulator small-batch full-circuit comparison
    import sys
    sys.path.insert(0, "data/competition/verifiers/invsqrt")
    from verify_submission_invsqrt import to_bits  # noqa: E402
    width = 22
    x_reg = km.array([km.q(i) for i in range(width)])
    xs = [1, 2, 22, 1000, 100000, 777777, 1600000, 3133452]
    rows = []
    n_qdiff = n_phdiff = 0
    for seed in (101, 202):
        rec = {"seed": seed, "per_x": []}
        for xi, xv in enumerate(xs):
            outs = {}
            for name, circ in (("base", c_base), ("cand", c_cand)):
                sim = km.Simulator(batch_size=1, debug_print=False, seed=seed * 100003 + xi)
                sim.clear_for_shot()
                sim.write_across_shots(x_reg, to_bits(np.array([xv], dtype=np.uint64), width))
                sim.do(circ)
                qv_ = tuple(bool(sim.read_across_shots(km.q(i))[0]) for i in range(62))
                try:
                    ph_ = half_turns_to_u64(sim.read_shot_phase(0))
                except Exception as e:  # noqa: BLE001
                    ph_ = f"ERR:{e!r}"
                outs[name] = (qv_, ph_)
            qd = [i for i in range(62) if outs["base"][0][i] != outs["cand"][0][i]]
            pheq = outs["base"][1] == outs["cand"][1]
            n_qdiff += bool(qd)
            n_phdiff += not pheq
            rec["per_x"].append({"x": xv, "qdiff": qd, "phase_equal": pheq})
        rows.append(rec)
    probe = {"window": list(WIN), "swap_at": SWAP_AT,
             "edit": [ops[SWAP_AT], ops[SWAP_AT + 1]],
             "fulldomain_boundary_wdiff_at_7506": wdiff,
             "n_x": len(xs), "seeds": [101, 202],
             "cells_with_qdiff": n_qdiff, "cells_with_phasediff": n_phdiff,
             "detail": rows,
             "static_ccx": n_ccx, "static_delta_ccx": 0}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(probe, indent=2), encoding="utf-8")
    print(json.dumps({"wdiff": wdiff, "cells_with_qdiff": n_qdiff,
                      "cells_with_phasediff": n_phdiff}, indent=2))
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
