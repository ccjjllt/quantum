"""Phase-unit + cond-off + PUSH-snapshot probes. Manual run only."""
import json, io
from pathlib import Path
from fractions import Fraction
import kickmix as km
import numpy as np

OUT = Path("artifacts/20261103_baseline_patch_round2/invsqrt/probe_phase.json")
N = 400
res = {}
HDR = ("APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n"
       "APPEND_TO_REGISTER q2 r0\nAPPEND_TO_REGISTER q3 r0\n"
       "REGISTER r0 \"x\"\n"
       "APPEND_TO_REGISTER b0 r1\nAPPEND_TO_REGISTER b1 r1\n"
       "APPEND_TO_REGISTER b2 r1\nAPPEND_TO_REGISTER b3 r1\n"
       "REGISTER r1 \"c\"\n")


def run_kmx(lines, seed=7):
    circ = km.Circuit.from_file(io.StringIO(HDR + "\n".join(lines) + "\n"),
                                format="kmx")
    sim = km.Simulator(N, counting_operations=True, seed=seed)
    sim.do(circ)
    return circ, sim


def phases(sim):
    return np.array([float(sim.read_shot_phase(i)) for i in range(N)])


def bit(sim, j):
    return np.asarray(sim.read_across_shots(km.b(j))).astype(int)


# E2: HMR phase correlation: |1> --HMR--> b0; phase vs outcome
_, s = run_kmx(["X q0", "HMR q0 b0"])
ph, b0 = phases(s), bit(s, 0)
res["E2_hmr_phase_vals"] = sorted(set(np.round(ph, 6).tolist()))
res["E2_corr_phase_outcome"] = float(np.corrcoef(ph, b0)[0, 1])
print("E2 phases:", res["E2_hmr_phase_vals"], "corr:", res["E2_corr_phase_outcome"])

# E3: HMR on |0>: outcome determinism + phase
_, s = run_kmx(["HMR q0 b0"])
print("E3 |0> HMR: outcomes:", sorted(set(bit(s, 0).tolist())),
      "phases:", sorted(set(np.round(phases(s), 6).tolist())))

# E4: R phase on |1> (no output bit)
_, s = run_kmx(["X q0", "R q0"])
print("E4 R|1> phases:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["R q0"])
print("E4b R|0> phases:", sorted(set(np.round(phases(s), 6).tolist())))

# E5: cond-off HMR no-write: b0 preset 1, HMR under false stack cond
_, s = run_kmx(["BIT_STORE1 b0", "X q0",
                "PUSH_CONDITION if b1", "HMR q0 b0", "POP_CONDITION"])
print("E5 cond-off: b0=", sorted(set(bit(s, 0).tolist())),
      "q0 =", np.asarray(s.read_across_shots(km.q(0))).astype(int).mean())

# E6: PUSH snapshot: stack keeps False even after b0 set to 1
_, s = run_kmx(["PUSH_CONDITION if b0", "BIT_STORE1 b0", "X q1",
                "POP_CONDITION"])
print("E6 snapshot: q1 mean (expect 0):",
      np.asarray(s.read_across_shots(km.q(1))).astype(int).mean(),
      "b0:", sorted(set(bit(s, 0).tolist())))

# E7: NEG / Z / CZ / CCZ phase units on |1..>
_, s = run_kmx(["X q0", "NEG"])
print("E7 NEG phase:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["X q0", "Z q0"])
print("E7 Z|1> phase:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["X q0", "X q1", "CZ q0 q1"])
print("E7 CZ|11> phase:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["X q0", "X q1", "X q2", "CCZ q0 q1 q2"])
print("E7 CCZ|111> phase:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["X q0", "Z_POW q0 0.5"])
print("E7 ZPOW(0.5)|1> phase:", sorted(set(np.round(phases(s), 6).tolist())))
_, s = run_kmx(["X q0", "Z_POW q0 0.25"])
print("E7 ZPOW(0.25)|1> phase:", sorted(set(np.round(phases(s), 6).tolist())))

OUT.write_text(json.dumps(res, indent=1) + "\n")
print("done")
