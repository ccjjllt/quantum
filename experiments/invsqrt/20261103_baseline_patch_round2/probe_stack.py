"""PUSH-snapshot redo + conditional-phase gating. Manual run only."""
import json, io
from pathlib import Path
import kickmix as km
import numpy as np

N = 400
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


def qmean(sim, j):
    return float(np.asarray(sim.read_across_shots(km.q(j))).astype(int).mean())


def bset(sim, j):
    return sorted(set(np.asarray(sim.read_across_shots(km.b(j))).astype(int).tolist()))


# E6r: snapshot True, then b0 flipped twice inside; q1/q2 witness
_, s = run_kmx(["BIT_STORE1 b0", "PUSH_CONDITION if b0", "BIT_STORE0 b0",
                "X q1", "BIT_STORE1 b0", "X q2", "POP_CONDITION"])
print("E6r snapshot: q1 (expect 1):", qmean(s, 1), " q2 (1=snapshot,0=live):",
      qmean(s, 2), " b0:", bset(s, 0))

# E6r2: nested stack
_, s = run_kmx(["BIT_STORE1 b0", "PUSH_CONDITION if b0", "BIT_STORE1 b1",
                "PUSH_CONDITION if b1", "X q1",
                "BIT_STORE0 b1", "X q2",
                "POP_CONDITION", "X q3", "POP_CONDITION"])
print("E6r2 nested: q1 (1):", qmean(s, 1), " q2 (1=snap,0=live):", qmean(s, 2),
      " q3 (1):", qmean(s, 3))

# E9: conditional CZ gated off -> no phase
_, s = run_kmx(["X q0", "X q1", "CZ q0 q1 if b0"])
print("E9 CZ-off phase (expect 0):",
      sorted(set(float(sim.read_shot_phase(i)) for sim in [s] for i in range(N))))
_, s = run_kmx(["X q0", "X q1", "BIT_STORE1 b0", "CZ q0 q1 if b0"])
print("E9 CZ-on phase (expect 1):",
      sorted(set(float(s.read_shot_phase(i)) for i in range(N))))
_, s = run_kmx(["BIT_STORE1 b0", "NEG if b0"])
print("E9 NEG-on phase (expect 1):",
      sorted(set(float(s.read_shot_phase(i)) for i in range(N))))
_, s = run_kmx(["NEG if b0"])
print("E9 NEG-off phase (expect 0):",
      sorted(set(float(s.read_shot_phase(i)) for i in range(N))))
print("done")
