"""Task2 + candidate builders.

A. Rotation-basis replacement (table/polynomial approximation):
   delete the 3 smallest ladder-B rotations
     idx 25738 (2.886e-11 half), 25748 (5.873e-11 half), 25756 (1.159e-10 half)
   = 0th-order (constant-1 / empty-table) approximation: Toffoli +0, n_rot 41->38.
   Expected dScore = -62*dT/4 with the t(n) model (eps41 proxy +/-10x band);
   hypothesis variant adds a +4 CCX explicit-table cost for comparison.

B. Sampled-x phase self-check (verifier-style, NOT a verifier run):
   for a sample of x values, write x into x_reg, run baseline vs candidate with
   the same explicit seed, compare shot-phase delta against the verifier's own
   per-x tolerance (reference_values). Reports max |delta|/tol ratio.

C. Build + write both candidate kmbs:
   artifacts/20261109_xreg_resynth/candidate_rotdrop_3small.kmb (Task2)
   artifacts/20261109_xreg_resynth/candidate_xreg_swap_q25q26.kmb (Task1, dScore 0)
"""
from __future__ import annotations

import io
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

sys.path.insert(0, "data/competition/verifiers/invsqrt")
from verify_submission_invsqrt import (  # noqa: E402
    ProblemSpecInvSqrt, reference_values, to_bits,
)

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
ART = Path("artifacts/20261109_xreg_resynth")
OUT_ROT = ART / "candidate_rotdrop_3small.kmb"
OUT_SWAP = ART / "candidate_xreg_swap_q25q26.kmb"
A, B = 15900, 16800
DROP = [25738, 25748, 25756]  # 3 smallest ladder-B Z_POW q28
EPS41 = 2.434041480874084e-13
Q = 62


def load():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    return c, hdr, ops


def t_of_n(n: int, eps41: float) -> float:
    return n * (0.56 * math.log2(1 / eps41 * n / 41) + 5.3)


def main() -> None:
    c, hdr, ops = load()
    assert len(ops) == 53686
    for i in DROP:
        assert ops[i].startswith("Z_POW q28 "), (i, ops[i])
    angs = [Fraction(ops[i].split()[2]) for i in DROP]
    print("dropping:", [(DROP[k], str(angs[k]), float(angs[k] / 2)) for k in range(3)])
    print("angle-sum turns =", float(sum(angs) / 2))

    # ---- A. estimates ----
    est = {"model": "score=Q*(toffoli+T/4); T=n*(0.56*log2(1/eps)+5.3); eps_n=eps41*41/n",
           "eps41_proxy": EPS41, "dropped_idx": DROP,
           "dropped_angles_half_turns": [str(a) for a in angs],
           "dropped_angle_sum_turns": str(sum(angs) / 2),
           "rows": {}}
    for tag, e in [("proxy", EPS41), ("x0.1", EPS41 * 0.1), ("x10", EPS41 * 10.0)]:
        dt = t_of_n(41, e) - t_of_n(38, e)
        est["rows"][tag] = {
            "dT_41_to_38": dt, "dScore_Q62_no_table": -Q * dt / 4,
            # hypothesis: explicit 3-bit constant table costs +4 CCX (=+248 pts @Q62)
            "dScore_Q62_plus4CCX_table": 62 * 4 - Q * dt / 4,
        }
    print(json.dumps(est["rows"], indent=2))

    # ---- C. build candidates ----
    ops_rot = [l for i, l in enumerate(ops) if i not in set(DROP)]
    c_rot = km.Circuit.from_file(io.StringIO("\n".join(hdr + ops_rot) + "\n"), format="kmx")
    ART.mkdir(parents=True, exist_ok=True)
    c_rot.to_file(str(OUT_ROT), format="kmb")
    print("wrote", OUT_ROT, "ops", len(c_rot))

    def swap_line(line: str) -> str:
        return " ".join("q26" if t == "q25" else ("q25" if t == "q26" else t)
                        for t in line.split())
    ops_swap = ops[:A] + [swap_line(l) for l in ops[A:B]] + ops[B:]
    c_swap = km.Circuit.from_file(io.StringIO("\n".join(hdr + ops_swap) + "\n"), format="kmx")
    c_swap.to_file(str(OUT_SWAP), format="kmb")
    print("wrote", OUT_SWAP, "ops", len(c_swap))

    # ---- B. sampled-x phase self-check ----
    spec = ProblemSpecInvSqrt.for_n_p(10)
    target, tol = reference_values(spec, np.arange(1, spec.max_x + 1, dtype=np.uint64))

    def half_turns_to_u64(ht) -> int:
        n, d = ht.as_integer_ratio()
        return (((n << 64) // d + 1) >> 1) & ((1 << 64) - 1)

    rng = np.random.default_rng(7)
    xs_sample = np.array(sorted(set([1, 2, 3, 22, 1000, 100000, 1000000, 2000000,
                                     3133452, 3133451] + rng.integers(1, 3133453, size=190).tolist())),
                           dtype=np.uint64)
    x_reg = km.array([km.q(i) for i in range(22)])
    worst = (0.0, None)
    n_checked = 0
    for seed in (11, 22):
        for x in xs_sample.tolist():
            ph = {}
            for name, circ in (("base", c), ("rotdrop", c_rot), ("swap", c_swap)):
                sim = km.Simulator(batch_size=1, debug_print=False, seed=seed * 7919 + x)
                sim.clear_for_shot()
                sim.write_across_shots(x_reg, to_bits(np.array([x], dtype=np.uint64), 22))
                sim.do(circ)
                ph[name] = half_turns_to_u64(sim.read_shot_phase(0))
            for name in ("rotdrop", "swap"):
                delta = (int(ph[name]) - int(ph["base"])) & ((1 << 64) - 1)
                if delta >= 1 << 63:
                    delta -= 1 << 64
                ratio = abs(delta) / max(int(tol[x - 1]), 1)
                if ratio > worst[0]:
                    worst = (ratio, {"x": x, "seed": seed, "variant": name,
                                     "delta_turns": delta / 2 ** 64,
                                     "tol_turns": int(tol[x - 1]) / 2 ** 64})
                n_checked += 1
    check = {"n_x": len(xs_sample), "seeds": [11, 22], "cells": n_checked,
             "worst_delta_over_tol": worst[0], "worst_cell": worst[1]}
    print(json.dumps(check, indent=2))
    (ART / "rotdrop_estimates.json").write_text(json.dumps(est, indent=2))
    (ART / "phase_selfcheck.json").write_text(json.dumps(check, indent=2))
    print("PASS-likely" if worst[0] < 1.0 else "FAIL-likely", "for full verifier phase gate")


if __name__ == "__main__":
    main()
