"""b_detect.py: detection-only R-guard fragment at unextract flag-carry zone.

Zone (0-based): 52712857 PUSH if b99553 .. 52712865 POP
  body: X q848; X q875; X q856; CCZ q848 q875 q856; X q848; X q875; X q856
  (phase repayment on a=b=t=0, conditioned on forward flag HMR q846 b99553).
  Static per zone: 1 CCZ (Toffoli-like).

Guard (detection ONLY, no correction -> transparent by construction):
  R q892; R q893
  CCX q848 q875 q893
  CCX q893 q856 q892
  HMR q892 b300000
Data lines only read as controls; X-restored values post-POP are stable.
Static delta: +2 CCX (unconditional -> mean T +2). Q option A: fresh q892/q893
(Q 892->894); option B: reuse idle wire (52/52 pressure per deepfix §4 -> none).

Slices: header + [ENTRY..DET_END] (TAIL=0), orig vs guarded, batch 4,
input rng 0xD91, sim seed 99. Compare q0..q891 + all bits except b300000.
Determinism rerun of guarded. Writes b_detect.json + b_detect.diff.
"""
from __future__ import annotations
import difflib
import json
from pathlib import Path

import numpy as np
import kickmix as km

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_r_nonw17/b_detect.json")
DIFF = Path("artifacts/20261109_dqi_r_nonw17/b_detect.diff")
HEADER_END = 54145
ENTRY = 52196517
PUSH, POP = 52712857, 52712865
W = 892
SCRATCH_B = 300000
NEW_Q = (892, 893)


def main() -> None:
    print("loading lines...", flush=True)
    with open(KMX) as f:
        lines = f.readlines()
    assert lines[PUSH].strip() == "PUSH_CONDITION if b99553", lines[PUSH][:60]
    assert lines[PUSH + 4].strip() == "CCZ q848 q875 q856", lines[PUSH + 4][:60]
    assert lines[POP].strip() == "POP_CONDITION", lines[POP][:60]
    assert lines[PUSH - 1].strip() == "HMR q846 b99553", lines[PUSH - 1][:60]
    header = lines[:HEADER_END]
    det = [
        "R q892\n",
        "R q893\n",
        "CCX q848 q875 q893\n",
        "CCX q893 q856 q892\n",
        f"HMR q892 b{SCRATCH_B}\n",
    ]
    tO = "".join(header + lines[ENTRY:POP + 1])
    tR = "".join(header + lines[ENTRY:POP + 1] + det)
    ctx0, ctx1 = PUSH - 3, POP + 4
    a = [f"{i}:{lines[i]}" for i in range(ctx0, ctx1)]
    b = ([f"{i}:{lines[i]}" for i in range(ctx0, POP + 1)]
         + [f"{POP}+ins:{l}" for l in det]
         + [f"{i}:{lines[i]}" for i in range(POP + 1, ctx1)])
    DIFF.write_text("".join(difflib.unified_diff(a, b, fromfile="orig_fragment", tofile="guarded_fragment")))
    print(f"wrote {DIFF}", flush=True)

    c0 = km.Circuit(tO)
    c1 = km.Circuit(tR)
    nq = max(c0.num_qubits, c1.num_qubits)
    nb = max(c0.num_bits, c1.num_bits)
    print(f"orig q/b={c0.num_qubits}/{c0.num_bits} guarded q/b={c1.num_qubits}/{c1.num_bits}", flush=True)
    rng = np.random.default_rng(0xD91)
    qb = rng.integers(0, 2, size=(nq, 4)).astype(np.bool_)
    bb = rng.integers(0, 2, size=(nb, 4)).astype(np.bool_)

    def sim_sized(text, seed):
        c = km.Circuit(text)
        sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
        sim.use_same_registers_as(c)
        sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
        sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
        sim.do(c)
        return sim, c

    print("sim original...", flush=True)
    simO, cO = sim_sized(tO, 99)
    print("sim guarded...", flush=True)
    simR, cR = sim_sized(tR, 99)
    print("sim guarded again...", flush=True)
    simR2, _ = sim_sized(tR, 99)
    qO = [[bool(v) for v in simO.read_across_shots(km.q(i))] for i in range(W)]
    qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    qmis = [i for i in range(W) if qO[i] != qR[i]]
    nbits = min(cO.num_bits, cR.num_bits)
    bmis, ncmp = [], 0
    for i in range(nbits):
        if i == SCRATCH_B:
            continue
        rO = [bool(v) for v in simO.read_across_shots(km.b(i))]
        rR = [bool(v) for v in simR.read_across_shots(km.b(i))]
        ncmp += 1
        if rO != rR:
            bmis.append(i)
            if len(bmis) > 10:
                break
    scratch = [bool(v) for v in simR.read_across_shots(km.b(SCRATCH_B))]
    res = {
        "fragment": {"push": PUSH, "pop": POP, "entry": ENTRY,
                     "static_orig_zone_paid": 1, "static_guard_paid": 2, "static_delta": +2},
        "circuits": {"orig": [cO.num_qubits, cO.num_bits], "guarded": [cR.num_qubits, cR.num_bits]},
        "qubits_compared": W, "qubits_equal": len(qmis) == 0, "qubit_mismatches": qmis,
        "qubits_deterministic": qR == qR2,
        "bits_compared": ncmp, "bit_mismatches": bmis,
        "detector_outcomes": scratch,
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "detector_outcomes"}, indent=1))
    print("detector outcomes:", scratch)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
