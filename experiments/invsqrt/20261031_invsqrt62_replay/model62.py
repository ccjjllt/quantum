"""Classical domain check of the replayed 62-qubit invsqrt circuit.

Every legal x is prepared as a computational-basis state and executed in kickmix.
The tracked phase is compared with the official 2^-64-turn target and tolerance.
Scratch uses the official read_across_shots(...).any(axis=1) predicate.
This is not an official PASS. The 87-qubit table and its 44 angles are not loaded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import kickmix  # noqa: E402

ART = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"
CIRCUIT_PATH = ART / "ahmed.kmb"
MAX_X = 3_133_452


def main():
    circuit = kickmix.Circuit.from_file(CIRCUIT_PATH)
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    if spec.max_x != MAX_X:
        raise SystemExit(f"unexpected max_x {spec.max_x}")
    x_reg, scratch = official.validate_registers(circuit, spec)
    target, tol = official.reference_values(spec, np.arange(1, MAX_X + 1, dtype=np.uint64))
    min_margin = 1 << 64
    phase_failures = 0
    x_failures = 0
    scratch_shot_failures = 0
    official_dirty_batches = 0
    worst_ratio = 0.0
    worst_x = 0

    def consume(sim, xs):
        nonlocal min_margin, phase_failures, x_failures, scratch_shot_failures, official_dirty_batches, worst_ratio, worst_x
        n = len(xs)
        got = official.from_bits(sim.read_across_shots(x_reg))
        # Tail batches may be padded; compare the real prefix only.
        if not np.array_equal(got[:n], xs):
            x_failures += int(np.count_nonzero(got[:n] != xs))
        bits = np.asarray(sim.read_across_shots(scratch))
        official_dirty = bits.any(axis=1)
        if official_dirty.any():
            official_dirty_batches += 1
        if bits.shape[0] == len(scratch):
            shot_dirty = bits.any(axis=0)
        else:
            shot_dirty = bits.any(axis=1)
        scratch_shot_failures += int(np.count_nonzero(shot_dirty[:n]))
        theta = np.array(
            [official.half_turns_to_units(sim.read_shot_phase(i)) for i in range(n)],
            dtype=np.uint64,
        )
        allowed = tol[xs - np.uint64(1)]
        error = (theta - target[xs - np.uint64(1)]).view(np.int64)
        used = np.abs(error).view(np.uint64)
        phase_failures += int(np.count_nonzero(used > allowed))
        margins = allowed - used
        min_margin = min(min_margin, int(margins.min()))
        ratio = np.divide(used, allowed, out=np.zeros(n), where=allowed > 0)
        top = float(ratio.max())
        if top >= worst_ratio:
            worst_ratio = top
            worst_x = int(xs[int(np.argmax(ratio))])

    full = 256
    n_full = MAX_X // full
    sim = kickmix.Simulator(batch_size=full, seed=101)
    for batch in range(n_full):
        start = batch * full + 1
        xs = np.arange(start, start + full, dtype=np.uint64)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(xs, spec.width))
        sim.do(circuit)
        consume(sim, xs)
    done = n_full * full
    tail = MAX_X - done
    if tail:
        xs = np.arange(done + 1, MAX_X + 1, dtype=np.uint64)
        sim_tail = kickmix.Simulator(batch_size=tail, seed=101)
        sim_tail.clear_for_shot()
        sim_tail.write_across_shots(x_reg, official.to_bits(xs, spec.width))
        sim_tail.do(circuit)
        consume(sim_tail, xs)

    report = {
        "domain_size": MAX_X,
        "circuit": str(CIRCUIT_PATH.resolve()),
        "seed": 101,
        "register_range_failures": x_failures + scratch_shot_failures,
        "x_restoration_failures": x_failures,
        "scratch_shot_failures": scratch_shot_failures,
        "official_scratch_predicate": "read_across_shots(scratch).any(axis=1)",
        "official_dirty_batches": official_dirty_batches,
        "phase_tolerance_failures": phase_failures,
        "minimum_absolute_margin_units": min_margin,
        "minimum_absolute_margin_turns": min_margin / 2**64,
        "worst_error_over_tolerance": worst_ratio,
        "worst_x": worst_x,
        "official_pass": False,
        "note": "Classical domain check of basis-state kickmix phases for every legal x. Not an official PASS.",
        "loaded_87q_table": False,
        "integer_horner_layout": "待证实",
        "layout_hypothesis": {"F0": 28, "G0": 1, "S": 20, "LB": 18, "FT": 19, "F2": 8},
    }
    text = json.dumps(report, indent=2) + "\n"
    (ART / "model_check.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
