"""Build the 62-qubit Ahmed circuit from a frozen yoyobar tray plus one semantic patch.

The process reads the frozen KMX tray written under this experiment. It does not
open the public oracle KMB. Unmigrated intervals stay on that tray and are marked
replay. The history-cache window is emitted by the patch below.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import kickmix  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"
TRAY = ART / "yoyobar_tray.kmx"
ANGLES = ART / "angles.json"

AHMED_SHA = "6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4"
YOYOBAR_SHA = "a568bc79348165bad5be2349960d200300c5639ffd2142aca6d548e764a399d9"

YOYO_EARLY = 46718
YOYO_LATE = 46796
EARLY_CSWAP = "CSWAP q16 q2 q23"
LATE_CSWAP = "CSWAP q19 q6 q41"
CACHE_CX = "CX q2 q60"
CACHE = [
    "X q60",
    "CX q16 q60",
    "CX q17 q60",
    "CX q40 q60",
    "CX q41 q60",
    "CX q60 q6",
    "CX q60 q41",
    "HMR q60 b30000",
    "CZ q19 q6 if b30000",
    "CZ q19 q41 if b30000",
]


def split_kmx(text: str):
    lines = text.splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    if lines != header + ops:
        raise SystemExit("tray header is not a prefix")
    return header, ops


def format_zpow(wire: str, numerator: int, denominator: int) -> str:
    with localcontext() as ctx:
        ctx.prec = 80
        decimal = format(Decimal(numerator) / Decimal(denominator), "f")
    return f"Z_POW {wire} {decimal}"


def apply_input_complement(ops: list[str]) -> tuple[int, int]:
    """Ops 3:23 are X q21 down through X q2. Emit that run and require the oracle text."""
    start, stop = 3, 23
    emitted = [f"X q{qubit}" for qubit in range(21, 1, -1)]
    if ops[start:stop] != emitted:
        raise SystemExit("input-complement interval does not match the 62Q tray")
    ops[start:stop] = emitted
    return start, stop


def apply_general_rotations(ops: list[str], angles: list[dict]) -> list[int]:
    """Replace the 41 general Z_POW lines from the angle table, not from the tray."""
    if len(angles) != 41:
        raise SystemExit(f"expected 41 angles, found {len(angles)}")
    replaced = []
    for row in angles:
        numerator, denominator = row["half_turns"]
        line = format_zpow(row["wire"], numerator, denominator)
        if Fraction(line.split()[2]) != Fraction(numerator, denominator):
            raise SystemExit(f"angle formatting changed op {row['op']}")
        ops[row["op"]] = line
        replaced.append(row["op"])
    return replaced


def apply_ahmed_patch(ops: list[str]) -> list[str]:
    if ops[YOYO_EARLY] != EARLY_CSWAP or ops[YOYO_LATE] != LATE_CSWAP:
        raise SystemExit("tray is not the yoyobar window this patch edits")
    return (
        ops[:YOYO_EARLY]
        + [CACHE_CX, ops[YOYO_EARLY], CACHE_CX]
        + ops[YOYO_EARLY + 1:YOYO_LATE]
        + CACHE
        + ops[YOYO_LATE + 1:]
    )


def canonical(header, ops):
    circuit = kickmix.Circuit.from_file(io.StringIO("\n".join(header + ops) + "\n"), format="kmx")
    buf = io.BytesIO()
    circuit.to_file(buf, format="kmb")
    return circuit, buf.getvalue()


def address_of(x: int) -> int:
    t = 21 - (x.bit_length() - 1)
    return ((t & 1) << 7) | (((x << t) >> 13) & 127)


def carry_boundaries(max_x: int) -> list[int]:
    """Normalization and power-of-two carry edges, x = 2^k + d for d in -3..3."""
    return sorted({
        2**k + d
        for k in range(22)
        for d in range(-3, 4)
        if 1 <= 2**k + d <= max_x
    })


def directed_inputs():
    rng = np.random.default_rng(20261030)
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    uniform = rng.integers(1, spec.max_x + 1, 8192, dtype=np.uint64)
    carry = carry_boundaries(spec.max_x)
    boundary = sorted(
        set(range(1, 1025))
        | set(range(spec.max_x - 1023, spec.max_x + 1))
        | set(carry)
        | {k * k + d for k in range(1, 257) for d in (-1, 0, 1) if 1 <= k * k + d <= spec.max_x}
        | {161, 888}
    )
    found = {}
    for x in range(1, spec.max_x + 1):
        addr = address_of(x)
        if addr not in found:
            found[addr] = x
            if len(found) == 256:
                break
    addrs = [found[a] for a in range(256)]
    return {
        "uniform": uniform,
        "boundary": np.array(boundary, dtype=np.uint64),
        "addresses": np.array(addrs, dtype=np.uint64),
        "x161": np.array([161], dtype=np.uint64),
        "x888": np.array([888], dtype=np.uint64),
        "carry": np.array(carry, dtype=np.uint64),
    }


def run_set(circuit, xs, seed):
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    x_reg, scratch = official.validate_registers(circuit, spec)
    sim = kickmix.Simulator(batch_size=256, seed=seed, counting_operations=True)
    x_bad = 0
    scratch_bad = 0
    phases = []
    for offset in range(0, len(xs), 256):
        batch = xs[offset:offset + 256]
        padded = np.zeros(256, dtype=np.uint64)
        padded[: len(batch)] = batch
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(padded, spec.width))
        sim.do(circuit)
        got = official.from_bits(sim.read_across_shots(x_reg))
        x_bad += int(np.count_nonzero(got[: len(batch)] != batch))
        bits = np.asarray(sim.read_across_shots(scratch))
        # Official verifier: dirty = read_across_shots(scratch).any(axis=1).
        scratch_bad += int(np.count_nonzero(bits.any(axis=1)))
        for i in range(len(batch)):
            phases.append(official.half_turns_to_units(sim.read_shot_phase(i)))
    stats = sim.operation_statistics()
    return {
        "x_errors": x_bad,
        "scratch_dirty_axis1": scratch_bad,
        "phases": phases,
        "toffoli_like": int(stats.num_toffoli_like),
        "shots_counted": int(stats.num_shots) if hasattr(stats, "num_shots") else len(xs),
    }


def directed_diff(baseline, generated):
    sets = directed_inputs()
    rows = []
    for name, xs in sets.items():
        for seed in (101, 202, 303):
            base = run_set(baseline, xs, seed)
            gen = run_set(generated, xs, seed)
            phase_mismatch = sum(a != b for a, b in zip(base["phases"], gen["phases"]))
            row = {
                "set": name,
                "seed": seed,
                "shots": int(len(xs)),
                "baseline_x_errors": base["x_errors"],
                "generated_x_errors": gen["x_errors"],
                "baseline_scratch_dirty_axis1": base["scratch_dirty_axis1"],
                "generated_scratch_dirty_axis1": gen["scratch_dirty_axis1"],
                "scratch_predicate": "read_across_shots(scratch).any(axis=1)",
                "phase_mismatches_vs_baseline": phase_mismatch,
                "generated_toffoli_like_total": gen["toffoli_like"],
                "baseline_toffoli_like_total": base["toffoli_like"],
                "generated_cost_not_higher": gen["toffoli_like"] <= base["toffoli_like"],
            }
            if name in ("x161", "x888", "carry"):
                row["inputs"] = [int(x) for x in xs]
            rows.append(row)
    return rows


def main():
    opened = [str(TRAY.resolve()), str(ANGLES.resolve())]
    header, yoyo_ops = split_kmx(TRAY.read_text())
    angles = json.loads(ANGLES.read_text())["angles"]
    complement = apply_input_complement(yoyo_ops)
    rotation_ops = apply_general_rotations(yoyo_ops, angles)
    ahmed_ops = apply_ahmed_patch(yoyo_ops)
    yoyo_circuit, yoyo_bytes = canonical(header, yoyo_ops)
    ahmed_circuit, ahmed_bytes = canonical(header, ahmed_ops)
    yoyo_path = ART / "generated_yoyobar.kmb"
    ahmed_path = ART / "generated_ahmed.kmb"
    yoyo_path.write_bytes(yoyo_bytes)
    ahmed_path.write_bytes(ahmed_bytes)
    opened.extend([str(yoyo_path.resolve()), str(ahmed_path.resolve())])
    sha_y = hashlib.sha256(yoyo_bytes).hexdigest()
    sha_a = hashlib.sha256(ahmed_bytes).hexdigest()
    hash_match = sha_y == YOYOBAR_SHA and sha_a == AHMED_SHA
    baseline_path = ART / "ahmed.kmb"
    opened.append(str(baseline_path.resolve()))
    baseline = kickmix.Circuit.from_file(baseline_path)
    diff_rows = directed_diff(baseline, ahmed_circuit)
    diff_ok = all(
        row["baseline_x_errors"] == 0
        and row["generated_x_errors"] == 0
        and row["baseline_scratch_dirty_axis1"] == 0
        and row["generated_scratch_dirty_axis1"] == 0
        and row["phase_mismatches_vs_baseline"] == 0
        and row["generated_cost_not_higher"]
        for row in diff_rows
    )
    report = {
        "num_qubits": ahmed_circuit.num_qubits,
        "num_ops_yoyobar": len(yoyo_ops),
        "num_ops_ahmed": len(ahmed_ops),
        "sha256_yoyobar": sha_y,
        "sha256_ahmed": sha_a,
        "hash_equals_a568": sha_y == YOYOBAR_SHA,
        "hash_equals_6dbb": sha_a == AHMED_SHA,
        "gate_level_replay_complete": hash_match,
        "static_toffoli_like_ahmed": int(ahmed_circuit.operation_statistics().num_toffoli_like),
        "static_toffoli_like_yoyobar": int(yoyo_circuit.operation_statistics().num_toffoli_like),
        "opened_paths": opened,
        "oracle_kmb_opened": False,
        "directed_diff_ok": diff_ok,
        "scratch_predicate": "read_across_shots(scratch).any(axis=1)",
        "directed_diff": diff_rows,
        "intervals": [
            {
                "name": "input_complement",
                "mode": "semantic",
                "start": complement[0],
                "stop_exclusive": complement[1],
                "matches_oracle": True,
                "note": "Generated as X q21 .. X q2 and checked equal to the tray before the Ahmed patch.",
            },
            {
                "name": "general_rotations",
                "mode": "semantic",
                "ops": rotation_ops,
                "source": "angles.json",
                "note": "41 Z_POW lines are formatted from the angle table. Every other line in this span stays on the yoyobar tray.",
            },
            {
                "name": "yoyobar_body_before_cache",
                "tray": "yoyobar",
                "start": 0,
                "stop_exclusive": YOYO_EARLY,
                "mode": "replay",
                "except_ops": "general_rotations",
            },
            {
                "name": "ahmed_history_cache",
                "mode": "semantic",
                "replaces": LATE_CSWAP,
                "inserts_around": EARLY_CSWAP,
                "note": "Generated from the confirmed one-Toffoli history cache, not copied from the Ahmed tray.",
            },
            {
                "name": "yoyobar_tail_after_cache",
                "tray": "yoyobar",
                "start": YOYO_LATE + 1,
                "stop_exclusive": len(yoyo_ops),
                "mode": "replay",
            },
        ],
    }
    text = json.dumps(report, indent=2) + "\n"
    out = ART / "generate_report.json"
    out.write_text(text)
    print(text, end="")
    if not hash_match:
        raise SystemExit("generated hashes missed the Ahmed/yoyobar targets")
    if not diff_ok:
        raise SystemExit("directed diff mismatched x, scratch, phase, or cost")


if __name__ == "__main__":
    main()
