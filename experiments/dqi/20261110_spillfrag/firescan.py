"""Fire-condition scan (counterexample hunt for spillfrag borrow fragment).

Window CCX q18 q143 q22 fires iff AND(q18,q143)==1 at op 16391916.
Victim q22 is live-after (read @16393282), so any firing input makes the
borrow rewrite semantically wrong. This script scans orig-only TAIL=0 slices
for firing inputs:
  mode init-seeds: random qb/bb from seed 0xE00.. (sim seed fixed 99);
  mode real-init:  qb=bb=0 with varying sim seeds (HMR-outcome variation).
Observed (2026-11-10): 124 init-seeds x4-shot + 60 sim-seeds x4-shot,
zero fires. Method record; counts are evidence in README §4.
"""
from __future__ import annotations

import os
import sys

import numpy as np

import kickmix as km

KMX = os.environ.get("SPILL_KMX",
                      "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
HEADER_END = 54146
ENTRY = 12006935
F_R = 16446733
F_CX2 = 16446736


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "init-seeds"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else (100 if mode == "init-seeds" else 60)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    header = lines[:HEADER_END]
    tO = "".join(header + lines[ENTRY:F_R] + lines[F_R:F_CX2 + 1])
    c0 = km.Circuit(tO)

    def run(seed, qb, bb):
        c = km.Circuit(tO)
        sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
        sim.use_same_registers_as(c)
        sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
        sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
        sim.do(c)
        return sim

    found = None
    if mode == "init-seeds":
        for k in range(n):
            iseed = 0xE00 + k
            rng = np.random.default_rng(iseed)
            qb = rng.integers(0, 2, size=(892, 4)).astype(np.bool_)
            bb = rng.integers(0, 2, size=(c0.num_bits, 4)).astype(np.bool_)
            sO = run(99, qb, bb)
            v18 = [bool(x) for x in sO.read_across_shots(km.q(18))]
            v143 = [bool(x) for x in sO.read_across_shots(km.q(143))]
            if any(a and b for a, b in zip(v18, v143)):
                print(f"FIRE init=0x{iseed:X} q18={v18} q143={v143}", flush=True)
                found = iseed
                break
    else:
        qb = np.zeros((c0.num_qubits, 4), dtype=np.bool_)
        bb = np.zeros((c0.num_bits, 4), dtype=np.bool_)
        for seed in range(n):
            sO = run(seed, qb, bb)
            v18 = [bool(x) for x in sO.read_across_shots(km.q(18))]
            v143 = [bool(x) for x in sO.read_across_shots(km.q(143))]
            if any(a and b for a, b in zip(v18, v143)):
                print(f"FIRE simseed={seed} q18={v18} q143={v143}", flush=True)
                found = seed
                break
    print(f"done mode={mode} n={n} found={found}", flush=True)


if __name__ == "__main__":
    main()
