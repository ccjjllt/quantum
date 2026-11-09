"""500-ops probe + 2500-window candidate build (Task 1/2).

Probe [5300:5800] (500 ops, pure CX/CCX/X): clean equal-product CCX pair
  5564/5646 (CCX q14 q15 q25), target q25 absent strictly between.
Analysis window [5006:7506] (2500 ops, pure unconditional arithmetic).
Candidate: delete both (static -2 CCX).

Checks:
  P1 full-domain words (from bigwin_scan.json): prod equal, q25 untouched+unread between.
  P2 Simulator small-batch (verifier-style, explicit seeds, real x into q0..q21):
     baseline vs candidate full circuits; compare final 62-qubit state + shot phase.
Then writes candidate .kmb (NOT verified here; official verifier run is manual).
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
ART = Path("artifacts/20261109_xreg_bigwin")
OUT_CAND = ART / "candidate_deldup_q25pair.kmb"
OUT_PROBE = Path("experiments/invsqrt/20261109_xreg_bigwin/deldup_probe.json")
PAIR = (5564, 5646)
WIN = (5006, 7506)


def load():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return c, hdr, ops


def half_turns_to_u64(ht) -> int:
    n, d = ht.as_integer_ratio()
    return (((n << 64) // d + 1) >> 1) & ((1 << 64) - 1)


def main() -> None:
    c_base, hdr, ops = load()
    assert len(ops) == 53686, len(ops)
    assert ops[PAIR[0]] == "CCX q14 q15 q25", ops[PAIR[0]]
    assert ops[PAIR[1]] == "CCX q14 q15 q25", ops[PAIR[1]]
    # static no-touch/no-read recheck on the exact pair interval
    between = [k for k in range(PAIR[0] + 1, PAIR[1])
               if "q25" in ops[k].split()[1:]]
    assert between == [], between

    ops_cand = [l for i, l in enumerate(ops) if i not in set(PAIR)]
    assert len(ops_cand) == 53684
    c_cand = km.Circuit.from_file(io.StringIO("\n".join(hdr + ops_cand) + "\n"), format="kmx")
    ART.mkdir(parents=True, exist_ok=True)
    c_cand.to_file(str(OUT_CAND), format="kmb")
    print("wrote", OUT_CAND, "ops", len(c_cand))

    # P2: Simulator small-batch full-circuit comparison
    try:
        from data_competition_helpers import to_bits_helper  # noqa: F401
    except Exception:
        pass
    import sys
    sys.path.insert(0, "data/competition/verifiers/invsqrt")
    from verify_submission_invsqrt import to_bits  # noqa: E402

    width = 22
    x_reg = km.array([km.q(i) for i in range(width)])
    xs = [1, 2, 22, 1000, 100000, 777777, 1600000, 3133452]
    to_b = np.stack([[(x >> b) & 1 for x in xs] for b in range(width)]).astype(bool)
    rows = []
    n_qdiff = n_phdiff = 0
    for seed in (101, 202):
        rec = {"seed": seed, "per_x": []}
        for xi, xv in enumerate(xs):
            outs = {}
            for name, circ in (("base", c_base), ("cand", c_cand)):
                sim = km.Simulator(batch_size=1, debug_print=False, seed=seed * 100003 + xi)
                sim.clear_for_shot()
                sim.write_across_shots(x_reg, to_b[:, xi:xi + 1])
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
    probe = {"pair": list(PAIR), "window": list(WIN), "n_x": len(xs),
             "seeds": [101, 202],
             "cells_with_qdiff": n_qdiff, "cells_with_phasediff": n_phdiff,
             "detail": rows,
             "static_recheck_between_uses": between}
    OUT_PROBE.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROBE.write_text(json.dumps(probe, indent=2), encoding="utf-8")
    print(json.dumps({"cells_with_qdiff": n_qdiff, "cells_with_phasediff": n_phdiff,
                      "static_between_uses": between}, indent=2))
    print("wrote", OUT_PROBE)


if __name__ == "__main__":
    main()
