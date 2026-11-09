"""s7_broadcast.py: stable-pair broadcast fragment + prefix-slice verification.

Fragment (0-based lines, unextract, depth 0, controls stable):
  orig:
    52710777: CCX q887 q874 q846
    52710778: CCX q891 q846 q864
    52710779: CCX q887 q874 q846
  rewritten (fresh ancilla q892 + scratch bit b300000, Isabe template):
    R q892
    CCX q887 q874 q892
    CX q892 q846
    CCX q891 q846 q864
    CX q892 q846
    HMR q892 b300000
    CZ q887 q874 if b300000
  static paid: 3 CCX -> 2 CCX (net -1; +1R/+2CX/+1HMR/+1CZ free).

Slices: header + [unextract_entry .. 52710779+TAIL] for orig vs rewritten,
same random init (rng 0xD91), sim seed 99, batch 4. Compare q0..q891 reads
and all-bit reads except b300000. Determinism rerun of rewritten.

Writes artifacts/20261109_dqi_decoder_struct/s7_broadcast.json and
s7_broadcast.diff (unified fragment diff).
"""
from __future__ import annotations
import difflib
import json
from pathlib import Path
import numpy as np
import kickmix as km

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_decoder_struct/s7_broadcast.json")
DIFF = Path("artifacts/20261109_dqi_decoder_struct/s7_broadcast.diff")
HEADER_END = 54145
ENTRY = 52196517
L1, MID, L2 = 52710777, 52710778, 52710779
import os
TAIL = int(os.environ.get("S7_TAIL", "0"))
OUT = Path(os.environ.get("S7_OUT", "artifacts/20261109_dqi_decoder_struct/s7_broadcast.json"))
DIFF = Path(os.environ.get("S7_DIFF", "artifacts/20261109_dqi_decoder_struct/s7_broadcast.diff"))
W = 892
SCRATCH_B = 300000


def sim_slice(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb)
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb)
    sim.do(c)
    return sim, c


def main() -> None:
    print("loading lines...", flush=True)
    with open(KMX) as f:
        lines = f.readlines()
    assert lines[L1].strip() == "CCX q887 q874 q846", lines[L1][:50]
    assert lines[MID].strip() == "CCX q891 q846 q864", lines[MID][:50]
    assert lines[L2].strip() == "CCX q887 q874 q846", lines[L2][:50]
    header = lines[:HEADER_END]
    end = L2 + 1 + TAIL
    orig_mid = lines[L1:L2 + 1]
    new_mid = [
        "R q892\n",
        "CCX q887 q874 q892\n",
        "CX q892 q846\n",
        lines[MID],
        "CX q892 q846\n",
        f"HMR q892 b{SCRATCH_B}\n",
        f"CZ q887 q874 if b{SCRATCH_B}\n",
    ]
    tO = "".join(header + lines[ENTRY:L1] + orig_mid + lines[L2 + 1:end])
    tR = "".join(header + lines[ENTRY:L1] + new_mid + lines[L2 + 1:end])
    # fragment diff (with context)
    ctx0, ctx1 = L1 - 3, L2 + 4
    a = [f"{i}:{lines[i]}" for i in range(ctx0, ctx1)]
    b = ([f"{L1-3}:{lines[L1-3]}", f"{L1-2}:{lines[L1-2]}", f"{L1-1}:{lines[L1-1]}"] +
         [f"{L1}+:{l}" for l in new_mid] +
         [f"{L2+1}:{lines[L2+1]}", f"{L2+2}:{lines[L2+2]}", f"{L2+3}:{lines[L2+3]}"])
    diff = "".join(difflib.unified_diff(a, b, fromfile="orig_fragment", tofile="rewritten_fragment"))
    DIFF.write_text(diff)
    print(f"wrote {DIFF} ({len(diff)} chars)", flush=True)
    c0 = km.Circuit(tO)
    c1 = km.Circuit(tR)
    nq = max(c0.num_qubits, c1.num_qubits)
    nb = max(c0.num_bits, c1.num_bits)
    print(f"slice circuits: orig q/b={c0.num_qubits}/{c0.num_bits} rewritten q/b={c1.num_qubits}/{c1.num_bits}", flush=True)
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
    print("sim rewritten...", flush=True)
    simR, cR = sim_sized(tR, 99)
    print("sim rewritten again (determinism)...", flush=True)
    simR2, _ = sim_sized(tR, 99)
    nbits_common = min(cO.num_bits, cR.num_bits)
    qO = [ [bool(v) for v in simO.read_across_shots(km.q(i))] for i in range(W)]
    qR = [ [bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    qmis = [i for i in range(W) if qO[i] != qR[i]]
    qeq = (len(qmis) == 0)
    qdet = (qR == qR2)
    # bits: compare all except scratch
    ncmp, bmis = 0, []
    for i in range(nbits_common):
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
    res = {"fragment": {"L1": L1, "L2": L2, "tail": TAIL, "end": end},
           "static_paid_orig": 3, "static_paid_new": 2, "static_delta": -1,
           "qubits_compared": W, "qubits_equal": qeq, "qubit_mismatches": qmis,
           "qubits_deterministic": qdet,
           "bits_compared": ncmp, "bit_mismatches": bmis,
           "scratch_outcomes": scratch}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "scratch_outcomes"}, indent=1))
    print("scratch outcomes:", scratch)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
