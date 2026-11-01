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

# Exact widths. Candidates come from contiguous variation-class runs, not sliced fanouts.
T_WIDTH = 19
C2_WIDTH = 8


def shr(value, exponent):
    if exponent >= 0:
        return value >> exponent
    return value << -exponent


def horner_t(c1, c2, delta, ft=T_WIDTH, f2=C2_WIDTH):
    """T = C1 - sum_{i<12} b_i (C2 >> e_i) + (1-b_12) (C2 >> e_12), e_i = 21+F2-FT-i."""
    acc = c1
    for i in range(13):
        exponent = 21 + f2 - ft - i
        term = shr(c2, exponent)
        bit = (delta >> i) & 1
        if i == 12:
            acc += (1 - bit) * term
        else:
            acc -= bit * term
    return acc


def pack(column, wires):
    word = 0
    for index, qubit in enumerate(wires):
        word |= int(column[qubit]) << index
    return word


def high_window_holds(bits, shift):
    """15 high-control constraint for s<=7. None means the window does not fit."""
    if shift > 7 or shift + 7 >= len(bits):
        return None
    if int(bits[shift + 7]) != 1:
        return False
    if shift and any(int(bit) for bit in bits[:shift]):
        return False
    if shift + 8 < len(bits) and any(int(bit) for bit in bits[shift + 8:]):
        return False
    return True


def load_kmx(path):
    import io
    circuit = kickmix.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    return circuit, header, ops


def compile_prefix(header, ops, start, stop):
    import io
    text = "\n".join(header + ops[start:stop]) + "\n"
    return kickmix.Circuit.from_file(io.StringIO(text), format="kmx")


def read_wires(sim, n):
    probes = kickmix.array([kickmix.q(i) for i in range(62)])
    mat = np.asarray(sim.read_across_shots(probes))
    if mat.shape[0] != 62:
        mat = mat.T
    return mat[:, :n].astype(np.uint8)


def decompose_one(x):
    t = 21 - (int(x).bit_length() - 1)
    xn = int(x) << t
    return {
        "t": t,
        "s": t >> 1,
        "p": t & 1,
        "address": ((t & 1) << 7) | ((xn >> 13) & 127),
        "delta": xn & ((1 << 13) - 1),
    }


def stamp_counterexamples(enumeration, local, domain):
    """Put the directed-sample and all-x result on every width-8 or width-19 candidate."""
    failures = {}
    for item in local.get("bit_failures") or []:
        failures.setdefault((item["cut"], tuple(item["wires"]), item["role"]), []).append(item)
    domain_first = domain.get("first_counterexample") or {}
    for row in enumeration["candidates"]:
        key = (row["cut"], tuple(row["wires"]), row["role"])
        if row["role"] == "C2":
            if domain_first.get("cut") == row["cut"] and domain_first.get("wires") == row["wires"]:
                row["counterexample"] = domain_first
            elif key in failures:
                row["counterexample"] = failures[key][0]
            elif row["counterexample"] is None:
                row["counterexample"] = {
                    "mechanism": "No directed-sample or all-x counterexample was recorded for this C2 candidate.",
                }
        elif row["role"] == "delta_slice":
            if domain.get("delta_slice_mismatches") == 0 and not failures.get(key):
                row["counterexample"] = {
                    "mechanism": (
                        "The delta-bit reading matched every legal x at seed 101. "
                        "This run is not T: its width is 8. It is not C2: varies_with_delta is true."
                    ),
                }
            else:
                row["counterexample"] = (failures.get(key) or [domain_first])[0]
        elif row["role"] == "T" and row["counterexample"] is None:
            row["counterexample"] = (failures.get(key) or [{
                "mechanism": "Width-19 candidate did not match the Horner recurrence.",
            }])[0]
    if enumeration["width_19_count"] != 0:
        return
    for key in (
        "width_19_physical_variation_class",
        "width_19_physical_variation_class_and_value_origin",
        "width_19_logical_variation_class",
    ):
        if enumeration[key]:
            raise SystemExit(f"{key} is not an explicit empty list")


def load_register_enumeration(doc):
    """Recompute candidates with the shipped extractor. Do not slice fanouts."""
    import extract62
    fresh = extract62.enumerate_integer_registers(doc["cuts"])
    stored = doc.get("integer_registers")
    if stored is None:
        raise SystemExit("horner_cuts.json has no integer_registers enumeration")
    if stored["width_19_count"] != fresh["width_19_count"]:
        raise SystemExit("stored width-19 count does not match the shipped enumerator")
    if stored["width_8_count"] != fresh["width_8_count"]:
        raise SystemExit("stored width-8 count does not match the shipped enumerator")
    tested = []
    seen = set()
    for row in fresh["candidates"]:
        if row["role"] not in ("C2", "T", "delta_slice"):
            continue
        if not row["value_origin_uniform"]:
            continue
        key = (row["cut"], row["role"], tuple(row["wires"]))
        if key in seen:
            continue
        seen.add(key)
        tested.append(row)
    return fresh, tested


def candidate_failure(row, column, parts):
    """Compare one snapshot column with the candidate's integer reading."""
    wires = row["wires"]
    if row["role"] == "C2":
        return None
    if row["role"] == "delta_slice":
        for qubit in wires:
            expected = (parts["delta"] >> qubit) & 1
            if int(column[qubit]) != expected:
                return {
                    "x": parts["x"],
                    "cut": row["cut"],
                    "role": row["role"],
                    "wires": wires,
                    "observed": pack(column, wires),
                    "expected_delta_bits": sum(((parts["delta"] >> q) & 1) << i for i, q in enumerate(wires)),
                    "mechanism": (
                        f"At cut {row['cut']}, wires {wires} are a width-8 delta-varying value-origin run. "
                        "The integer reading says wire q holds delta bit q. The snapshot disagrees."
                    ),
                }
        return None
    if row["role"] == "T":
        observed = pack(column, wires)
        predicted = horner_t(0, 0, parts["delta"]) & ((1 << T_WIDTH) - 1)
        if observed != predicted:
            return {
                "x": parts["x"],
                "cut": row["cut"],
                "role": "T",
                "wires": wires,
                "observed_t": observed,
                "predicted_t": predicted,
                "mechanism": "Width-19 T candidate disagrees with Horner(C1=0, C2=0).",
            }
    return None


def c2_word(row, column):
    return pack(column, row["wires"])


def run_horner(header, ops):
    doc = json.loads((ART / "horner_cuts.json").read_text())
    enumeration, tested = load_register_enumeration(doc)
    if any(row["width"] != len(row["wires"]) for row in enumeration["candidates"]):
        raise SystemExit("candidate width does not match its wire list")
    angles = json.loads((ART / "angles.json").read_text())["angles"]
    high = [(row["op"], int(row["wire"][1:])) for row in angles if row["phase_block"] == "Hphase"]
    low = [(row["op"], int(row["wire"][1:])) for row in angles if row["phase_block"] == "Lphase"]
    if len(high) + len(low) != 41:
        raise SystemExit(f"expected 41 rotations, found {len(high) + len(low)}")
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = kickmix.Circuit.from_file(CIRCUIT_PATH)
    x_reg, _scratch = official.validate_registers(circuit, spec)
    cut_ops = {row["cut"] for row in tested}
    points = sorted({op for op, _wire in high} | cut_ops)
    pieces = []
    prev = 0
    for op in points:
        pieces.append((op, compile_prefix(header, ops, prev, op)))
        prev = op

    def drive(xs, seed):
        sim = kickmix.Simulator(batch_size=256, seed=seed)
        buf = np.zeros(256, dtype=np.uint64)
        buf[: len(xs)] = np.asarray(xs, dtype=np.uint64)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(buf, 22))
        high_bits = []
        mats = {}
        for op, stage in pieces:
            sim.do(stage)
            if any(hop == op for hop, _wire in high):
                wire = next(w for hop, w in high if hop == op)
                probe = np.asarray(sim.read_across_shots(kickmix.array([kickmix.q(wire)]))).reshape(-1)
                high_bits.append(probe[: len(xs)].astype(np.uint8))
            if op in cut_ops:
                mats[op] = read_wires(sim, len(xs))
        return np.stack(high_bits, axis=0), mats

    samples = doc["samples"]
    local_xs = [row["x"] for row in samples]
    high_bits, mats = drive(local_xs, 101)
    local_bad = []
    c2_by_address = {id(row): {} for row in tested if row["role"] == "C2"}
    for index, sample in enumerate(samples):
        parts = dict(sample)
        for row in tested:
            column = mats[row["cut"]][:, index]
            if row["role"] == "C2":
                word = c2_word(row, column)
                seen = c2_by_address[id(row)]
                previous = seen.get(parts["address"])
                if previous is None:
                    seen[parts["address"]] = word
                elif previous != word:
                    local_bad.append({
                        "x": parts["x"],
                        "cut": row["cut"],
                        "role": "C2",
                        "wires": row["wires"],
                        "address": parts["address"],
                        "observed": word,
                        "previous": previous,
                        "mechanism": (
                            f"C2 candidate at cut {row['cut']} on wires {row['wires']} "
                            "changed inside one address."
                        ),
                    })
            else:
                failed = candidate_failure(row, column, parts)
                if failed is not None:
                    local_bad.append(failed)
    for row in tested:
        if row["role"] != "C2":
            continue
        words = set(c2_by_address[id(row)].values())
        if len(words) < 2:
            local_bad.append({
                "x": samples[0]["x"],
                "cut": row["cut"],
                "role": "C2",
                "wires": row["wires"],
                "mechanism": "Address-only candidate did not change across the sample addresses.",
            })
    h_local_bad = []
    for index, row in enumerate(samples):
        held = high_window_holds(high_bits[:, index], row["s"])
        if held is False:
            h_local_bad.append({"x": row["x"], "s": row["s"], "high_bits": [int(b) for b in high_bits[:, index]]})
    t_rows = [row for row in enumeration["candidates"] if row["width"] == 19]
    c2_rows = [row for row in tested if row["role"] == "C2"]
    local = {
        "status": "unconfirmed",
        "official_pass": False,
        "LB18": "rejected",
        "selection": "contiguous variation class and value origin; fanouts are not sliced",
        "width_8_count": enumeration["width_8_count"],
        "width_19_count": enumeration["width_19_count"],
        "width_19_physical_variation_class": enumeration["width_19_physical_variation_class"],
        "width_19_physical_variation_class_and_value_origin": enumeration["width_19_physical_variation_class_and_value_origin"],
        "width_19_logical_variation_class": enumeration["width_19_logical_variation_class"],
        "width_8_value_origin": enumeration["width_8_value_origin"],
        "tested_candidates": tested,
        "T_width_19": "unconfirmed" if not t_rows else "pending",
        "C2_width_8": "unconfirmed" if not c2_rows else "pending_domain",
        "horner_recurrence_applied": False,
        "horner_recurrence_reason": "No width-19 T candidate exists, so the Horner recurrence is not applied to a sliced fanout.",
        "sample_count": len(samples),
        "bit_mismatches": len(local_bad),
        "bit_failures": local_bad,
        "first_counterexample": None if not local_bad else local_bad[0],
        "high_window_failures_on_samples": h_local_bad,
        "controls_41_rebuilt": False,
        "controls_41_reason": "T width 19 has no contiguous candidate, so the 41 controls are not rebuilt. LB=18 is not used.",
        "high_rotation_count": len(high),
        "low_rotation_count": len(low),
    }
    if t_rows and c2_rows and not local_bad and not h_local_bad:
        local["status"] = "local_match_pending_domain"
        local["horner_recurrence_applied"] = True
    return local, enumeration, tested, drive


def domain_horner(enumeration, tested, drive):
    mismatches = 0
    first = None
    h_fail = 0
    h_outside = 0
    h_ok = 0
    c2_conflicts = 0
    delta_failures = 0
    seen = {id(row): {} for row in tested if row["role"] == "C2"}
    batch = 256
    for start in range(1, MAX_X + 1, batch):
        xs = np.arange(start, min(start + batch, MAX_X + 1), dtype=np.uint64)
        high_bits, mats = drive(xs, 101)
        for index, x in enumerate(xs.tolist()):
            parts = decompose_one(x)
            parts["x"] = int(x)
            shift = parts["s"]
            held = high_window_holds(high_bits[:, index], shift)
            if held is None:
                h_outside += 1
            elif held:
                h_ok += 1
            else:
                h_fail += 1
                mismatches += 1
                if first is None:
                    first = {"x": int(x), "s": shift, "mechanism": "High-phase window constraint failed."}
            for row in tested:
                column = mats[row["cut"]][:, index]
                if row["role"] == "C2":
                    word = c2_word(row, column)
                    previous = seen[id(row)].get(parts["address"])
                    if previous is None:
                        seen[id(row)][parts["address"]] = word
                    elif previous != word:
                        c2_conflicts += 1
                        mismatches += 1
                        if first is None:
                            first = {
                                "x": int(x),
                                "address": parts["address"],
                                "cut": row["cut"],
                                "wires": row["wires"],
                                "observed": word,
                                "previous": previous,
                                "mechanism": "Address-only C2 candidate changed inside one address.",
                            }
                elif row["role"] == "delta_slice":
                    failed = candidate_failure(row, column, parts)
                    if failed is not None:
                        delta_failures += 1
                        mismatches += 1
                        if first is None:
                            first = failed
                elif row["role"] == "T":
                    failed = candidate_failure(row, column, parts)
                    if failed is not None:
                        mismatches += 1
                        if first is None:
                            first = failed
    t_empty = enumeration["width_19_count"] == 0
    if first is None and t_empty:
        first = {
            "x": None,
            "mechanism": (
                "No contiguous variation-class or value-origin run has width 19, "
                "on physical qubits or on unconditional-SWAP logical labels. "
                "T is unconfirmed. The 41 rotation controls are not rebuilt. LB=18 is not used."
            ),
        }
    c2_stable = c2_conflicts == 0 and any(row["role"] == "C2" for row in tested)
    confirmed = (
        enumeration["width_19_count"] > 0
        and c2_stable
        and mismatches == 0
        and h_fail == 0
    )
    return {
        "domain_size": MAX_X,
        "seed": 101,
        "shots_per_x": 1,
        "official_pass": False,
        "layout_status": "confirmed" if confirmed else "unconfirmed",
        "LB18": "rejected",
        "selection": "contiguous variation class and value origin; fanouts are not sliced",
        "width_19_count": enumeration["width_19_count"],
        "width_19_physical_variation_class_and_value_origin": enumeration["width_19_physical_variation_class_and_value_origin"],
        "width_8_value_origin_count": len(enumeration["width_8_value_origin"]),
        "tested_candidate_count": len(tested),
        "mismatch_count": mismatches,
        "c2_address_conflicts": c2_conflicts,
        "delta_slice_mismatches": delta_failures,
        "high_window_mismatches": h_fail,
        "high_window_holds": h_ok,
        "high_window_outside_s_le_7": h_outside,
        "c2_address_stable": c2_stable,
        "horner_recurrence_applied": False,
        "controls_41_rebuilt": False,
        "first_counterexample": first,
        "note": "One computational-basis shot per legal x at seed 101. Not an official PASS.",
    }


def main():
    _circuit, header, ops = load_kmx(CIRCUIT_PATH)
    local, enumeration, tested, drive = run_horner(header, ops)
    domain = domain_horner(enumeration, tested, drive)
    if domain["layout_status"] == "confirmed" and domain["mismatch_count"] != 0:
        raise SystemExit("confirmed Horner layout disagrees with a snapshot")
    if domain["layout_status"] == "confirmed" and enumeration["width_19_count"] == 0:
        raise SystemExit("T width 19 was confirmed without a width-19 candidate")
    stamp_counterexamples(enumeration, local, domain)
    doc = json.loads((ART / "horner_cuts.json").read_text())
    doc["integer_registers"]["candidates"] = enumeration["candidates"]
    doc["integer_registers"]["width_8_value_origin"] = [
        row for row in enumeration["candidates"]
        if row["width"] == 8 and row["basis"] == "physical_variation_class_and_value_origin"
    ]
    (ART / "horner_cuts.json").write_text(json.dumps(doc, indent=2) + "\n")
    local["tested_candidates"] = tested
    local["candidates"] = enumeration["candidates"]
    (ART / "horner_local.json").write_text(json.dumps(local, indent=2) + "\n")
    (ART / "horner_domain.json").write_text(json.dumps(domain, indent=2) + "\n")
    recipe_path = ART / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["horner_integer"] = {
        "status": domain["layout_status"],
        "migrated_off_tray": False,
        "T_width": T_WIDTH,
        "C2_width": C2_WIDTH,
        "LB18": "rejected",
        "controls_41_rebuilt": False,
        "reason": "Width-19 variation-class runs are empty. Width-8 value-origin runs are recorded in horner_cuts.json and were compared on the directed samples and on every legal x.",
    }
    recipe_path.write_text(json.dumps(recipe, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"horner_local_mismatches": local["bit_mismatches"], "horner_domain": {
        "mismatch_count": domain["mismatch_count"],
        "layout_status": domain["layout_status"],
        "first_x": None if not domain["first_counterexample"] else domain["first_counterexample"]["x"],
    }}, indent=2))
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
        "integer_horner_layout": domain["layout_status"],
        "layout_hypothesis": {
            "F0": 28,
            "G0": 1,
            "S": 20,
            "LB": "rejected",
            "FT": "unconfirmed" if domain["layout_status"] != "confirmed" else 19,
            "F2": "unconfirmed" if domain["layout_status"] != "confirmed" else 8,
            "F0_G0_S_reading": "phase window: R0=F0-G0=27, nHf=F0-1-S=7, offH=S-G0=19; full-x review is horner_domain.json",
            "LB_rejected_hypothesis": 18,
        },
        "horner_domain_mismatch_count": domain["mismatch_count"],
        "horner_first_counterexample": domain["first_counterexample"],
    }
    text = json.dumps(report, indent=2) + "\n"
    (ART / "model_check.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
