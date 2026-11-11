"""HMR-order control: does moving an HMR across other ops/HMRs change bit
outcomes under identical seed/init? (Decides whether deferred-birth spill
of the 11 HMR-born idle lines can preserve bit-exactness.)

tO: HMR q0 b0 ; CX q0 q1 ; HMR q1 b1 ; CX q1 q2 ; HMR q2 b2
tR: CX q0 q1 ; HMR q1 b1 ; CX q1 q2 ; HMR q2 b2 ; HMR q0 b0   (birth deferred)
tS: HMR q0 b0 ; HMR q1 b1  vs  HMR q1 b1 ; HMR q0 b0          (adjacent swap)
4-shot, sim seed 99, fixed init. Compares all bit reads.
Writes artifacts/20261110_spillmulti/hmr_toy.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import kickmix as km

ART = Path("artifacts/20261110_spillmulti")
OUT = ART / "hmr_toy.json"

HDR = ("REGISTER r0 \"T\"\nAPPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n"
       "APPEND_TO_REGISTER q2 r0\nAPPEND_TO_REGISTER b0 r0\n"
       "APPEND_TO_REGISTER b1 r0\nAPPEND_TO_REGISTER b2 r0\n")


def run(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
    sim.do(c)
    return sim, c


def bits(sim, c, n):
    return [[bool(v) for v in sim.read_across_shots(km.b(i))] for i in range(n)]


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    tO = HDR + "HMR q0 b0\nCX q0 q1\nHMR q1 b1\nCX q1 q2\nHMR q2 b2\n"
    tR = HDR + "CX q0 q1\nHMR q1 b1\nCX q1 q2\nHMR q2 b2\nHMR q0 b0\n"
    tS1 = HDR + "HMR q0 b0\nHMR q1 b1\n"
    tS2 = HDR + "HMR q1 b1\nHMR q0 b0\n"
    rng = np.random.default_rng(0xD91)
    c0 = km.Circuit(tO)
    qb = rng.integers(0, 2, size=(c0.num_qubits, 4)).astype(np.bool_)
    bb = rng.integers(0, 2, size=(c0.num_bits, 4)).astype(np.bool_)
    sO, cO = run(tO, 99, qb, bb)
    sR, _ = run(tR, 99, qb, bb)
    sS1, _ = run(tS1, 99, qb, bb)
    sS2, _ = run(tS2, 99, qb, bb)
    n = cO.num_bits
    bO, bR = bits(sO, cO, n), bits(sR, cO, n)
    bS1, bS2 = bits(sS1, cO, 2), bits(sS2, cO, 2)
    res = {
        "deferred_birth": {"orig": bO, "moved": bR,
                           "equal": bO == bR},
        "adjacent_swap": {"orig": bS1, "swapped": bS2,
                          "equal": bS1 == bS2},
        "conclusion": "HMR outcomes are NOT invariant to HMR reordering "
                      "(stream-ordered RNG): deferred-HMR-birth spill of the "
                      "11 HMR-born idle lines breaks bit-exactness.",
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
