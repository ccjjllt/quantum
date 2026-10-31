"""Manual invsqrt diagnosis.

Prints resource statistics for an explicit parameter set. A sample run compares
the circuit with the integer model (input restored, scratch clear, phase).
This entry does not import or call the official verifier.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import kickmix as km  # noqa: E402
import hsplit as H  # noqa: E402
import model as M  # noqa: E402
from generate_circuit import UNITS, build_from_tables  # noqa: E402
from recipe_io import load_recipe, params_from_recipe, phase_angles, tables_from_recipe  # noqa: E402


def half_turns_to_units(half_turns) -> int:
    n, d = half_turns.as_integer_ratio()
    return (((n << 64) // d + 1) >> 1) & M.MASK64


def bits_of(values, width):
    return (values[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1 == 1


def ints_of(bits):
    return (bits.astype(np.uint64) << np.arange(len(bits), dtype=np.uint64)[:, None]).sum(axis=0)


UNIFORM_DRAW_SEED = 20261030
SIMULATOR_SEEDS = (101, 202, 303)
ARTIFACTS = Path(__file__).resolve().parents[3] / "artifacts" / "20261031_invsqrt_generator_rebuild"


def existing_uniform() -> np.ndarray:
    """The fixed 8192-draw from the 2026-10-30 audit, not redrawn per simulator seed."""
    rng = np.random.default_rng(UNIFORM_DRAW_SEED)
    return rng.integers(1, M.MAX_X + 1, 8192, dtype=np.int64)


def existing_boundary() -> np.ndarray:
    """The audit boundary set, padded with np.resize to a multiple of 256 (2816 slots)."""
    boundary = sorted(set(range(1, 1025)) | set(range(M.MAX_X - 1023, M.MAX_X + 1)) |
                      {2**k + d for k in range(22) for d in range(-3, 4) if 1 <= 2**k + d <= M.MAX_X} |
                      {k * k + d for k in range(1, 257) for d in (-1, 0, 1) if 1 <= k * k + d <= M.MAX_X})
    boundary = np.array(boundary, dtype=np.int64)
    padded = int(np.ceil(len(boundary) / 256) * 256)
    return np.resize(boundary, padded)


def segment_endpoints(seg_bits: int) -> np.ndarray:
    """Endpoints of every mantissa bin, denormalized by a 0- or 1-bit shift.

    For 7 bits this is 383 inputs. Occupied-segment minima and maxima are
    included as well, so a bin edge that only appears at a larger shift is kept.
    """
    delta_bits = 21 - seg_bits
    found = set()
    for parity in (0, 1):
        for seg in range(1 << seg_bits):
            base = (1 << 21) + (seg << delta_bits)
            for delta in (0, (1 << delta_bits) - 1):
                x = (base + delta) >> parity
                if 1 <= x <= M.MAX_X:
                    found.add(int(x))
    xs = np.arange(1, M.MAX_X + 1, dtype=np.int64)
    _t, xn, parity_bits, _s = M.decompose(xs)
    address = (parity_bits << seg_bits) | ((xn >> delta_bits) & ((1 << seg_bits) - 1))
    order = np.argsort(address, kind="stable")
    address = address[order]
    ordered = xs[order]
    change = np.flatnonzero(np.diff(address))
    starts = np.r_[0, change + 1]
    ends = np.r_[change, len(ordered) - 1]
    found.update(int(v) for v in ordered[starts])
    found.update(int(v) for v in ordered[ends])
    return np.array(sorted(found), dtype=np.int64)


def recorded_counterexamples() -> np.ndarray:
    """First failures and worst inputs from the grid and cubic artifacts."""
    found = {1, 2, 65, 193, 2049, 1032289, 966657, 753025, 2206945, 2621345, 161, 888}
    for name in ("grid_margin.json", "cubic_control.json"):
        path = ARTIFACTS / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text())
        rows = payload.get("rows", [])
        if name.startswith("cubic") and isinstance(payload.get("newton"), dict):
            found.add(int(payload["newton"]["sample_worst_x"]))
        for row in rows:
            for key in ("first_bad_x", "worst_x", "sample_worst_x"):
                value = row.get(key)
                if isinstance(value, int) and 1 <= value <= M.MAX_X:
                    found.add(value)
    values = np.array(sorted(found), dtype=np.int64)
    padded = int(np.ceil(len(values) / 256) * 256)
    return np.resize(values, padded)


def sample_inputs(mode: str, seed: int):
    if mode == "smoke":
        return np.array([1, 2, 161, 888, 1024, 3133452], dtype=np.int64)
    if mode == "batch":
        rng = np.random.default_rng(seed)
        return rng.integers(1, M.MAX_X + 1, 256, dtype=np.int64)
    return {
        "uniform": existing_uniform(),
        "boundary": existing_boundary(),
        "segment_endpoints": np.unique(np.r_[segment_endpoints(6), segment_endpoints(7)]),
        "counterexamples": recorded_counterexamples(),
    }


def run_batch(circ, tables, prm, xs, seed: int) -> dict:
    regs = circ.register_data
    xreg = km.array(list(regs["x"]))
    scratch = km.array([km.q(i) for i in range(circ.num_qubits) if km.q(i) not in set(regs["x"])])
    sim = km.Simulator(batch_size=len(xs), seed=seed, counting_operations=True)
    sim.clear_for_shot()
    sim.write_across_shots(xreg, bits_of(xs.astype(np.uint64), 22))
    sim.do(circ)
    got = ints_of(sim.read_across_shots(xreg))
    dirty = sim.read_across_shots(scratch).any(axis=0)
    phase = np.array([half_turns_to_units(sim.read_shot_phase(i)) for i in range(len(xs))], dtype=np.uint64)
    model = M.phase_units(xs.astype(np.int64), tables, prm, check=False)
    stats = sim.operation_statistics()
    return {
        "shots": int(len(xs)),
        "seed": seed,
        "x_restoration_errors": int(np.count_nonzero(got != xs)),
        "dirty_scratch_shots": int(np.count_nonzero(dirty)),
        "phase_mismatches_vs_model": int(np.count_nonzero(phase != model)),
        "executed_toffoli_like_mean": float(stats.num_toffoli_like / len(xs)),
        "executed_t_like_mean": float(stats.num_t_like / len(xs)),
        "executed_rotations_mean": float(stats.num_z_pow(min_clifford_hierarchy_level=4) / len(xs)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "batch", "local"), default="smoke")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--retire", type=int, default=3)
    parser.add_argument("--prefix", type=int, default=0)
    parser.add_argument("--LB", type=int, default=21)
    parser.add_argument("--S", type=int, default=20)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    loaded = load_recipe()
    recipe = loaded["recipe"]
    prm = params_from_recipe(recipe)
    tables = tables_from_recipe(recipe)
    angles = phase_angles()
    plan = args.plan or loaded["options"]["plan"]
    circ, resources = build_from_tables(
        tables, prm, angles, lb=args.LB, s=args.S, plan=plan,
        retire=args.retire, initial_lookup=True, last=False, prefix=args.prefix,
    )
    lay = H.layout(tables, prm, args.LB, args.S)
    M.PHASE_FN = lambda xs: H.phases_multi(H.regs(tables, prm, lay, xs), angles)
    print(json.dumps({
        "official_verifier_called": False,
        "qubits": resources["qubits"],
        "static_toffoli_like": resources["static_toffoli_like"],
        "operations": resources["operations"],
        "plan": plan,
        "units_restated": True,
    }, indent=2))
    print(UNITS.split("phase units:")[0].strip())
    records = []
    input_sets = None
    if args.mode == "local":
        input_sets = sample_inputs("local", UNIFORM_DRAW_SEED)
        sets = [(name, seed, values) for seed in SIMULATOR_SEEDS for name, values in input_sets.items()]
        for name, seed, xs in sets:
            for offset in range(0, len(xs), 256):
                row = run_batch(circ, tables, prm, xs[offset:offset + 256], seed)
                row["set"] = name
                records.append(row)
                print(json.dumps(row), flush=True)
    else:
        xs = sample_inputs(args.mode, args.seed)
        row = run_batch(circ, tables, prm, xs, args.seed)
        records.append(row)
        print(json.dumps(row, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"resources": resources, "records": records, "official_verifier_called": False,
                   "five_percent_target": "still open"}
        if input_sets is not None:
            payload["inputs"] = {name: [int(v) for v in values] for name, values in input_sets.items()}
            payload["input_notes"] = {
                "uniform_draw_seed": UNIFORM_DRAW_SEED,
                "simulator_seeds": list(SIMULATOR_SEEDS),
                "uniform_count": int(len(input_sets["uniform"])),
                "boundary_count": int(len(input_sets["boundary"])),
                "boundary_unique": int(len(np.unique(input_sets["boundary"]))),
                "segment_endpoint_count": int(len(input_sets["segment_endpoints"])),
                "counterexample_slots": int(len(input_sets["counterexamples"])),
                "counterexample_unique": [int(v) for v in np.unique(input_sets["counterexamples"])],
            }
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
    bad = [r for r in records if r["x_restoration_errors"] or r["dirty_scratch_shots"] or r["phase_mismatches_vs_model"]]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
