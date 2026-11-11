"""Small-batch Simulator phase self-checks on gengsr 26ebf39d invsqrt.

Method (after 20261109_tphase_fusion prefix_branch_check):
same explicit seeds across variants => same HMR coin stream => comparable;
tolerance/item reference taken from the verifier's reference_values
(tol(x) = 2^-24/sqrt(x) turns, uint64 units of 2^-64 turns).

Grid: xs = [1,2,3,5,64,161,1000,3133452] (tphase grid; includes worst_x=161
and max_x where tol is tightest), seeds = [101,202,303].

Uses:
 (a) baseline validation (unmodified circuit must PASS the grid),
 (b) Task 2: drop each A3 micro-angle Z_POW (21 levels) one at a time,
 (c) Task 1 arbitration: drop the cleanest guarded-site CCX (S2 @18501).
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np

import kickmix as km

HERE = Path(__file__).parent
MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
OUT = HERE / "sens_check.json"

sys.path.insert(0, str(MAIN / ".worktree/invsqrt/data/competition/verifiers/invsqrt"))
import verify_submission_invsqrt as V  # noqa: E402

SPEC = V.ProblemSpecInvSqrt.for_n_p(10)
XS = np.array([1, 2, 3, 5, 64, 161, 1000, 3133452], dtype=np.uint64)
SEEDS = (101, 202, 303)
TARGET, TOL = V.reference_values(SPEC, XS)
A3LEVELS = [16337, 16347, 16355, 16363, 16371, 16378, 16386, 16394, 16402,
            16410, 16417, 16424, 16431, 16438, 16446, 16454, 16462, 16470,
            16478, 16486, 16493]


def load_kmx() -> tuple[list[str], list[str]]:
    c = km.Circuit.from_file(str(NEW_KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    header = [l for l in buf.getvalue().splitlines()
              if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in buf.getvalue().splitlines()
           if l and not l.startswith(("APPEND", "REGISTER"))]
    assert len(ops) == 36686, len(ops)
    return header, ops


def build_circuit(header: list[str], ops: list[str], drop: set[int]) -> km.Circuit:
    with tempfile.NamedTemporaryFile("w", suffix=".kmx", dir=str(HERE),
                                     delete=False) as f:
        f.write("\n".join(header) + "\n")
        f.write("\n".join(l for i, l in enumerate(ops) if i not in drop))
        f.write("\n")
        name = f.name
    try:
        return km.Circuit.from_file(name)
    finally:
        Path(name).unlink()


def phase_selfcheck(circuit: km.Circuit, xs: np.ndarray = XS,
                    seeds: tuple[int, ...] = SEEDS) -> dict:
    x_reg, scratch = V.validate_registers(circuit, SPEC)
    width = SPEC.width
    per_seed = []
    worst_ratio, worst_x, worst_err, worst_tol = -1.0, -1, "", ""
    n_checked = 0
    for seed in seeds:
        sim = km.Simulator(batch_size=len(xs), seed=seed)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, V.to_bits(xs, width))
        sim.do(circuit)
        if not np.array_equal(V.from_bits(sim.read_across_shots(x_reg)), xs):
            return {"verdict": "FAIL", "reason": "x_not_restored", "seed": seed}
        if len(scratch):
            dirty = sim.read_across_shots(scratch).any(axis=1)
            if dirty.any():
                return {"verdict": "FAIL", "reason": "scratch_dirty",
                        "seed": seed,
                        "qubit": str(scratch[int(np.argmax(dirty))])}
        for i in range(len(xs)):
            theta = V.half_turns_to_units(sim.read_shot_phase(i))
            x = int(xs[i])
            err = (int(theta) - int(TARGET[int(i)])) % 2**64
            if err >= 2**63:
                err -= 2**64  # signed in [-2^63, 2^63)
            used, allow = abs(err), int(TOL[i])
            ratio = used / allow if allow else float("inf")
            n_checked += 1
            if ratio > worst_ratio:
                worst_ratio, worst_x = ratio, x
                worst_err = f"{err / 2**64:.3e}"
                worst_tol = f"{allow / 2**64:.3e}"
        per_seed.append({"seed": seed, "ok": True})
    return {"verdict": "PASS" if worst_ratio <= 1 else "FAIL",
            "worst_ratio": worst_ratio, "worst_x": worst_x,
            "worst_err_turns": worst_err, "tol_turns": worst_tol,
            "n_shots": n_checked, "per_seed": per_seed}


def main() -> None:
    header, ops = load_kmx()
    # sanity: A3 ladder positions/angles
    ladder = [(i, ops[i]) for i in A3LEVELS]
    assert all(l.startswith("Z_POW q28 ") for _, l in ladder), ladder[:2]

    base = build_circuit(header, ops, set())
    r_base = phase_selfcheck(base)
    print("baseline:", json.dumps(r_base))

    # Task 2: single-deletion sensitivity per A3 level
    rows = []
    for idx in A3LEVELS:
        ang = Fraction(ops[idx].split()[2])
        circ = build_circuit(header, ops, {idx})
        r = phase_selfcheck(circ)
        # exact static bound: deletion shifts tracked phase by at most ang/2 turns
        maxd_units = (int(ang.numerator) << 64) // (2 * int(ang.denominator))
        rows.append({"drop_idx": idx, "angle_halfturns": str(ang),
                     "angle_turns": float(ang) / 2,
                     "max_shift_units": maxd_units,
                     "min_tol_units": int(TOL.min()),
                     "static_safe_all_x": bool(maxd_units < int(TOL.min())),
                     **r})
        print(idx, r["verdict"], f'{r["worst_ratio"]:.3f}',
              "@x=" + str(r["worst_x"]), flush=True)
    rows.sort(key=lambda r: (r["worst_ratio"] if r["worst_ratio"] >= 0 else 9e9))

    # Task 1 arbitration: delete guarded-site CCX@18501 (span 7, 6 cond CZ)
    arb = build_circuit(header, ops, {18501})
    r_arb = phase_selfcheck(arb)
    print("arb18501:", json.dumps(r_arb))

    OUT.write_text(json.dumps({
        "grid_xs": XS.tolist(), "seeds": list(SEEDS),
        "target_tol_note": "verifier reference_values; tol(x)=2^-24/sqrt(x) turns",
        "baseline": r_base,
        "a3_sensitivity": rows,
        "task1_arbitration_drop18501": r_arb,
    }, indent=1))


if __name__ == "__main__":
    main()
