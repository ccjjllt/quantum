"""Probe HMR/R semantics and whether a classically-conditioned rotation can replace a value.

Findings produced by this script (batch 1024, seed 5):
  X q1; Z q1                          -> phase 1 (pi) for all shots
  X q1; HMR q1 b0                     -> phase random 0/1  (HMR = H, measure, reset)
  X q1; HMR q1 b0; X q2; Z q2 if b0; X q2 -> phase 0 for all shots (repair works)
  HMR q2 b0 on |0>                    -> tracked phase 0, but the classical bit is random
So the HMR outcome is a uniform coin independent of the state, and the phase kickback is
pi * m * (pre-measurement value).  A live wire's value therefore cannot be extracted into a
classical bit and restored later.
"""
from __future__ import annotations

import collections

import kickmix as km


def phases(ops, n=1024, seed=5):
    c = km.Circuit("\n".join(ops))
    sim = km.Simulator(batch_size=n, seed=seed, counting_operations=True)
    sim.clear_for_shot()
    sim.do(c)
    return collections.Counter(str(sim.read_shot_phase(i)) for i in range(n))


CASES = [
    ("X,Z q1", ["X q1", "Z q1"]),
    ("X;HMR q1", ["X q1", "HMR q1 b0"]),
    ("X;HMR q1;Zanc if b0", ["X q1", "HMR q1 b0", "X q2", "Z q2 if b0", "X q2"]),
    ("AND(0,0);HMR;CZ", ["CCX q0 q1 q2", "HMR q2 b0", "CZ q0 q1 if b0"]),
    ("AND(1,0);HMR;CZ", ["X q0", "CCX q0 q1 q2", "HMR q2 b0", "CZ q0 q1 if b0"]),
    ("AND(1,1);HMR;CZ", ["X q0", "X q1", "CCX q0 q1 q2", "HMR q2 b0", "CZ q0 q1 if b0"]),
    ("HMR |0>", ["HMR q2 b0"]),
    ("HMR |0>;Zanc if b0", ["HMR q2 b0", "X q3", "Z q3 if b0", "X q3"]),
    ("R on |1>", ["X q0", "R q0"]),
]


def main():
    for name, ops in CASES:
        print(f"{name:26s} -> {dict(phases(ops))}")


if __name__ == "__main__":
    main()
