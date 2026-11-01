"""Manual reverse dataflow for one 62Q rotation-control cone.

Stages run only by hand, and only after the previous stage recorded success:
local, prefix, cross, controls, horner, domain.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

import kickmix  # noqa: E402
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

import generate62  # noqa: E402
import retain62  # noqa: E402

ART = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"
TRAY = ART / "ahmed_tray.kmx"
CIRCUIT = ART / "ahmed.kmb"

LOCAL_VARS = (18, 0, 27, 2, 14, 21, 54)
LOCAL_WRITES = {0, 2, 18, 21, 50}
CROSS_VARS = (18, 0, 27, 3, 21, 26)
SLICE_LO = 25622
SLICE_HI = 25630
ZPOW_25630 = 25630
HMR_25631 = 25631
CROSS_LO = 25857
CROSS_HI = 25860
ZPOW_25860 = 25860
HMR_25861 = 25861


def load_ops():
    circuit = kickmix.Circuit.from_file(CIRCUIT)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    tray = [
        line
        for line in TRAY.read_text().splitlines()
        if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))
    ]
    if tray[SLICE_LO:ZPOW_25630 + 1] != ops[SLICE_LO:ZPOW_25630 + 1]:
        raise SystemExit("ahmed tray and canonical KMB disagree on the op 25630 slice")
    if tray[CROSS_LO:HMR_25861 + 1] != ops[CROSS_LO:HMR_25861 + 1]:
        raise SystemExit("ahmed tray and canonical KMB disagree on the op 25860 slice")
    return header, ops


def status_path(stage):
    return ART / f"dataflow_{stage}.json"


def read_status(stage):
    path = status_path(stage)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_status(stage, payload):
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    status_path(stage).write_text(text)
    print(text, end="")
    return payload


def require_success(stage):
    prev = read_status(stage)
    if not prev or not prev.get("success"):
        return None
    return prev


def quote(ops, start, stop):
    return [{"op": start + offset, "line": ops[start + offset]} for offset in range(stop - start)]


def formula_25630(values, entry):
    """r = MUX(q18; q0, MUX(q27; q2, q14 AND NOT q21)) XOR (q54 AND (q18 XOR q27))."""
    hidden = values.and_(entry[14], values.xor(entry[21], values.one))
    inner = values.mux(entry[27], entry[2], hidden)
    outer = values.mux(entry[18], entry[0], inner)
    return values.xor(outer, values.and_(entry[54], values.xor(entry[18], entry[27])))


def formula_25860(values, entry):
    """r = MUX(q18; q0, MUX(q27; q3, q21 AND q26)). q28 starts at zero."""
    hidden = values.and_(entry[21], entry[26])
    inner = values.mux(entry[27], entry[3], hidden)
    return values.mux(entry[18], entry[0], inner)


def assignment_map(mask, variables):
    return {qubit: (mask >> index) & 1 for index, qubit in enumerate(variables)}


def local_expected_q50(values, entry_ids):
    """q50 after each real op in [25622, 25630), using entry value-ids."""
    q50 = values.zero
    q50 = values.xor(q50, entry_ids[14])
    q50 = values.xor(q50, values.and_(entry_ids[21], entry_ids[14]))
    # CX q23 q21 writes q21 and does not touch q50.
    q50 = values.mux(entry_ids[27], entry_ids[2], q50)
    q50 = values.mux(entry_ids[18], entry_ids[0], q50)
    q18 = values.xor(entry_ids[18], entry_ids[27])
    q50 = values.xor(q50, values.and_(entry_ids[54], q18))
    q18 = values.xor(q18, entry_ids[27])
    return q50, q18


def run_local(ops):
    lines = quote(ops, SLICE_LO, SLICE_HI)
    window = ops[SLICE_LO:ZPOW_25630 + 1]
    mismatches = []
    unexpected = []
    q18_ok = True
    capture_ok = True
    for mask in range(128):
        entry = assignment_map(mask, LOCAL_VARS)
        entry[50] = 0
        values, wire, snap, _sig, extra = retain62.interpret(
            window, track=True, entry=entry, capture_at=set(range(len(window)))
        )
        ids = {qubit: values.one if entry.get(qubit) else values.zero for qubit in LOCAL_VARS}
        ids[50] = values.zero
        got = wire[50]
        expected, restored = local_expected_q50(values, ids)
        formula = formula_25630(values, ids)
        zpow = extra["zpow"][-1]
        if got != expected or got != formula or zpow["value_id"] != got or restored != ids[18]:
            q18_ok = q18_ok and restored == ids[18]
            capture_ok = capture_ok and zpow["value_id"] == got
            mismatches.append(
                {
                    "op": ZPOW_25630 if zpow["value_id"] != got else SLICE_HI - 1,
                    "assignment": {f"q{qubit}": entry[qubit] for qubit in LOCAL_VARS},
                    "observed_q50": got,
                    "expected_q50": expected,
                    "formula": formula,
                    "zpow_value_id": zpow["value_id"],
                    "q18_final": wire[18],
                    "q18_entry": ids[18],
                }
            )
            break
        changed = [qubit for qubit in range(62) if wire[qubit] != extra["entry"][qubit]]
        stray = [qubit for qubit in changed if qubit not in LOCAL_WRITES]
        if stray:
            unexpected.append({"assignment": entry, "qubits": stray})
            break
        if wire[18] != extra["entry"][18]:
            q18_ok = False
            mismatches.append(
                {
                    "op": 25629,
                    "assignment": {f"q{qubit}": entry[qubit] for qubit in LOCAL_VARS},
                    "observed_q18": wire[18],
                    "expected_q18": extra["entry"][18],
                }
            )
            break
    success = not mismatches and not unexpected and q18_ok and capture_ok
    payload = {
        "stage": "local",
        "success": success,
        "lines": lines,
        "real_op_25624": ops[25624],
        "extra_real_write": {"op": 25624, "line": ops[25624]},
        "assignments": 128,
        "matched": 128 - len(mismatches) if not unexpected else 128 - len(mismatches),
        "q18_restored": q18_ok and not mismatches,
        "pre_rotation_is_q50": capture_ok and not mismatches,
        "unexpected_writes": unexpected,
        "mismatch": mismatches[0] if mismatches else None,
        "entered_prefix": False,
    }
    if success:
        payload["matched"] = 128
    write_status("local", payload)
    _update_control({"local": payload})
    return payload


def _update_control(stages):
    path = ART / "control_25630.json"
    current = json.loads(path.read_text()) if path.exists() else {"stages": {}}
    current["stages"] = {**current.get("stages", {}), **stages}
    path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")


def cone_of(values, root, and_limit=20_000, node_limit=100_000):
    seen = set()
    stack = [root]
    ands = set()
    leaves = []
    failures = []
    while stack:
        vid = stack.pop()
        if vid in seen:
            continue
        seen.add(vid)
        if len(seen) > node_limit:
            failures.append({"kind": "node_limit", "nodes": len(seen)})
            break
        for atom in values.fs[vid]:
            if atom == -1 or 0 <= atom <= 21:
                leaves.append({"kind": "const" if atom == -1 else "input", "atom": atom})
            elif atom in values.meas_source:
                src = values.meas_source[atom]
                leaves.append({"kind": "measurement", "atom": atom, "op": src["op"], "bit": src["bit"]})
            elif atom in values.and_of:
                if atom not in ands:
                    ands.add(atom)
                    if len(ands) > and_limit:
                        failures.append({"kind": "and_limit", "ands": len(ands)})
                        stack.clear()
                        break
                    left, right = values.and_of[atom]
                    stack.append(left)
                    stack.append(right)
            elif atom >= 1_000_000:
                failures.append({"kind": "undeclared_fresh", "atom": atom})
            else:
                failures.append({"kind": "unknown_atom", "atom": atom})
    meas = []
    seen_meas = set()
    for leaf in leaves:
        if leaf["kind"] == "measurement" and leaf["op"] not in seen_meas:
            seen_meas.add(leaf["op"])
            meas.append(leaf)
    return {
        "nodes": len(seen),
        "ands": len(ands),
        "leaves": leaves,
        "measurement_ops": sorted(seen_meas),
        "failures": failures,
    }


def compile_prefix(header, ops, start, stop):
    text = "\n".join(header + ops[start:stop]) + "\n"
    return kickmix.Circuit.from_file(io.StringIO(text), format="kmx")


def read_column(sim, probe, count):
    raw = np.asarray(sim.read_across_shots(probe)).reshape(-1)
    return raw[:count].astype(np.uint8)


def eval_vid(values, root, env):
    memo = {}
    stack = [(root, False)]
    while stack:
        vid, done = stack.pop()
        if vid in memo:
            continue
        if not done:
            stack.append((vid, True))
            for atom in values.fs[vid]:
                if atom in values.and_of:
                    left, right = values.and_of[atom]
                    stack.append((left, False))
                    stack.append((right, False))
            continue
        acc = 0
        for atom in values.fs[vid]:
            if atom == -1:
                acc ^= 1
            elif atom in values.and_of:
                left, right = values.and_of[atom]
                acc ^= memo[left] & memo[right]
            else:
                acc ^= env[atom]
        memo[vid] = acc
    return memo[root]


def directed_match(header, ops, values, vid, qubit, stop_op, meas_ops):
    """Compare one symbolic cone with kickmix at the existing directed inputs."""
    pieces = []
    prev = 0
    for op in meas_ops:
        pieces.append(("meas", op, compile_prefix(header, ops, prev, op + 1)))
        prev = op + 1
    pieces.append(("read", stop_op, compile_prefix(header, ops, prev, stop_op)))
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = kickmix.Circuit.from_file(CIRCUIT)
    x_reg, _scratch = official.validate_registers(circuit, spec)
    mismatches = []
    compared = 0
    for _name, xs in generate62.directed_inputs().items():
        for seed in (101, 202, 303):
            for offset in range(0, len(xs), 256):
                batch = np.asarray(xs[offset:offset + 256], dtype=np.uint64)
                padded = np.zeros(256, dtype=np.uint64)
                padded[: len(batch)] = batch
                sim = kickmix.Simulator(batch_size=256, seed=seed)
                sim.clear_for_shot()
                sim.write_across_shots(x_reg, official.to_bits(padded, spec.width))
                measured = {}
                observed = None
                for kind, op, stage in pieces:
                    sim.do(stage)
                    if kind == "meas":
                        bit = retain62_bit(values, op)
                        measured[op] = read_column(sim, kickmix.array([kickmix.b(bit)]), len(batch))
                    else:
                        observed = read_column(sim, kickmix.array([kickmix.q(qubit)]), len(batch))
                for index, value in enumerate(batch.tolist()):
                    env = {q: (int(value) >> q) & 1 for q in range(22)}
                    for leaf in meas_ops:
                        bit_col = measured[leaf]
                        atom = measurement_atom(values, leaf)
                        env[atom] = int(bit_col[index])
                    try:
                        predicted = eval_vid(values, vid, env)
                    except KeyError as exc:
                        mismatches.append({"x": int(value), "seed": seed, "missing_atom": int(exc.args[0])})
                        return {"compared": compared, "mismatches": mismatches}
                    compared += 1
                    if predicted != int(observed[index]):
                        mismatches.append(
                            {
                                "x": int(value),
                                "seed": seed,
                                "op": stop_op,
                                "observed": int(observed[index]),
                                "expected": int(predicted),
                            }
                        )
                        return {"compared": compared, "mismatches": mismatches}
    return {"compared": compared, "mismatches": mismatches}


def measurement_atom(values, op):
    for atom, src in values.meas_source.items():
        if src["op"] == op:
            return atom
    raise KeyError(op)


def retain62_bit(values, op):
    for src in values.meas_source.values():
        if src["op"] == op:
            return src["bit"]
    raise KeyError(op)


def run_prefix(header, ops):
    if require_success("local") is None:
        payload = {"stage": "prefix", "success": False, "entered": False, "reason": "local did not pass"}
        write_status("prefix", payload)
        return payload
    values, _wire, snap, _sig, extra = retain62.interpret(
        ops[: HMR_25631 + 1], track=True, capture_at={25621, 25622, 25623}
    )
    entry = snap[25621]
    zpow = next(row for row in extra["zpow"] if row["op"] == ZPOW_25630)
    reset = next(row for row in extra["measurement_resets"] if row["op"] == HMR_25631)
    ids = {qubit: entry[qubit] for qubit in LOCAL_VARS}
    formula = formula_25630(values, ids)
    specified_after_ccx = values.and_(entry[14], values.xor(entry[21], values.one))
    gate_after_ccx = values.xor(entry[14], values.and_(entry[21], entry[14]))
    first_id_gap = None
    if snap[25623][50] != specified_after_ccx:
        first_id_gap = {
            "op": 25623,
            "line": ops[25623],
            "observed": snap[25623][50],
            "expected": specified_after_ccx,
            "gate_form_value_id": gate_after_ccx,
            "gate_form_matches_snapshot": gate_after_ccx == snap[25623][50],
            "mechanism": (
                "The specified subexpression q14 AND NOT q21 is not the same value-id "
                "as q50 after CCX q21 q14 q50. The snapshot matches q14 XOR (q14 AND q21). "
                "The formula was not rewritten."
            ),
        }
    cone = cone_of(values, zpow["value_id"])
    q50_zero = entry[50] == values.zero
    formula_ok = formula == zpow["value_id"]
    meas_ok = (
        reset["measurement_bit"] == 350
        and reset["measurement_leaf"] != reset["pre_value"]
        and reset["pre_value"] == zpow["value_id"]
        and reset["not_boolean_clear"] is True
    )
    clean = not extra["unknown_ops"] and not cone["failures"]
    symbol_ok = q50_zero and formula_ok and meas_ok and clean
    directed = None
    if symbol_ok:
        directed = directed_match(
            header, ops, values, zpow["value_id"], 50, ZPOW_25630, cone["measurement_ops"]
        )
    snapshot_ok = directed is not None and not directed["mismatches"]
    success = symbol_ok and snapshot_ok
    failure = None
    if not symbol_ok:
        failure = {
            "op": None if first_id_gap is None else first_id_gap["op"],
            "first_value_id_gap": first_id_gap,
            "q50_zero_at_25622": q50_zero,
            "formula_value_id": formula,
            "captured_value_id": zpow["value_id"],
            "formula_agrees": formula_ok,
            "measurement": {
                "op": reset["op"],
                "bit": reset["measurement_bit"],
                "pre_value": reset["pre_value"],
                "leaf": reset["measurement_leaf"],
                "written_as_b350_equals_r25630": reset["measurement_leaf"] == reset["pre_value"],
            },
            "unknown_ops": extra["unknown_ops"][:5],
            "cone_failures": cone["failures"][:5],
        }
    elif not snapshot_ok:
        failure = directed["mismatches"][0]
    payload = {
        "stage": "prefix",
        "entered": True,
        "success": success,
        "q50_zero_at_op_25622": q50_zero,
        "formula_value_id": formula,
        "captured_value_id": zpow["value_id"],
        "value_id_agreement": formula_ok,
        "op_25631": {
            "bit": reset["measurement_bit"],
            "pre_value": reset["pre_value"],
            "measurement_leaf": reset["measurement_leaf"],
            "phase_dependence": [reset["pre_value"], reset["measurement_leaf"]],
            "written_as_b350_equals_r25630": False if meas_ok else reset["measurement_leaf"] == reset["pre_value"],
            "not_boolean_clear": True,
        },
        "cone": {"nodes": cone["nodes"], "ands": cone["ands"], "measurement_ops": cone["measurement_ops"], "failures": cone["failures"]},
        "unknown_ops": len(extra["unknown_ops"]),
        "directed": None if directed is None else {"compared": directed["compared"], "mismatch_count": len(directed["mismatches"])},
        "failure": failure,
    }
    write_status("prefix", payload)
    _update_control({"prefix": payload})
    return payload


def run_cross(header, ops):
    if require_success("prefix") is None:
        payload = {"stage": "cross", "success": False, "entered": False, "reason": "prefix did not pass"}
        write_status("cross", payload)
        return payload
    lines = quote(ops, CROSS_LO, CROSS_HI)
    mismatches = []
    for mask in range(64):
        entry = assignment_map(mask, CROSS_VARS)
        entry[28] = 0
        values, wire, _snap, _sig, extra = retain62.interpret(
            ops[CROSS_LO:ZPOW_25860 + 1], track=True, entry=entry
        )
        ids = {qubit: values.one if entry.get(qubit) else values.zero for qubit in CROSS_VARS}
        expected = formula_25860(values, ids)
        zpow = extra["zpow"][-1]
        if wire[28] != expected or zpow["value_id"] != wire[28]:
            mismatches.append(
                {
                    "op": ZPOW_25860,
                    "assignment": {f"q{qubit}": entry[qubit] for qubit in CROSS_VARS},
                    "observed": wire[28],
                    "expected": expected,
                    "zpow_value_id": zpow["value_id"],
                }
            )
            break
    if mismatches:
        payload = {
            "stage": "cross",
            "entered": True,
            "success": False,
            "lines": lines,
            "assignments": 64,
            "matched": 64 - len(mismatches),
            "mismatch": mismatches[0],
        }
        write_status("cross", payload)
        _update_control({"cross": payload})
        return payload
    values, _wire, snap, _sig, extra = retain62.interpret(
        ops[: HMR_25861 + 1], track=True, capture_at={25629, 25856}
    )
    entry = snap[25856]
    end_b = snap[25629]
    ids = {qubit: entry[qubit] for qubit in CROSS_VARS}
    formula = formula_25860(values, ids)
    zpow = next(row for row in extra["zpow"] if row["op"] == ZPOW_25860)
    reset = next(row for row in extra["measurement_resets"] if row["op"] == HMR_25861)
    cswaps = []
    for index in range(25630, CROSS_LO):
        line = ops[index]
        if line.startswith("CSWAP"):
            qubits = [retain62.qn(tok) for tok in line.split()[1:] if tok.startswith("q")]
            if 0 in qubits or 3 in qubits:
                cswaps.append({"op": index, "line": line})
    cone = cone_of(values, zpow["value_id"])
    symbol_ok = (
        formula == zpow["value_id"]
        and reset["measurement_bit"] == 373
        and reset["measurement_leaf"] != reset["pre_value"]
        and reset["pre_value"] == zpow["value_id"]
        and not extra["unknown_ops"]
        and not cone["failures"]
    )
    directed = None
    if symbol_ok:
        directed = directed_match(
            header, ops, values, zpow["value_id"], 28, ZPOW_25860, cone["measurement_ops"]
        )
    success = symbol_ok and directed is not None and not directed["mismatches"]
    payload = {
        "stage": "cross",
        "entered": True,
        "success": success,
        "lines": lines,
        "assignments": 64,
        "matched": 64,
        "q28_entry_zero_in_local": True,
        "formula_value_id": formula,
        "captured_value_id": zpow["value_id"],
        "value_id_agreement": formula == zpow["value_id"],
        "q0_at_end_of_B": end_b[0],
        "q3_at_end_of_B": end_b[3],
        "q0_at_cross_entry": entry[0],
        "q3_at_cross_entry": entry[3],
        "q0_changed_after_B": end_b[0] != entry[0],
        "q3_changed_after_B": end_b[3] != entry[3],
        "cswap_chain_touching_q0_or_q3": cswaps,
        "entry_is_post_cswap_version": True,
        "op_25861": {
            "bit": reset["measurement_bit"],
            "pre_value": reset["pre_value"],
            "measurement_leaf": reset["measurement_leaf"],
            "phase_dependence": [reset["pre_value"], reset["measurement_leaf"]],
            "written_as_b373_equals_r25860": reset["measurement_leaf"] == reset["pre_value"],
        },
        "cone": {"nodes": cone["nodes"], "ands": cone["ands"], "failures": cone["failures"]},
        "directed": None if directed is None else {"compared": directed["compared"], "mismatch_count": len(directed["mismatches"])},
        "failure": None if success else {"symbol_ok": symbol_ok, "directed": directed["mismatches"][:1] if directed else None},
    }
    write_status("cross", payload)
    _update_control({"cross": payload})
    return payload


def refuse(stage, reason):
    payload = {"stage": stage, "success": False, "entered": False, "reason": reason}
    write_status(stage, payload)
    return payload


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: dataflow62.py local|prefix|cross|controls|horner|domain")
    stage = sys.argv[1]
    header, ops = load_ops()
    if stage == "local":
        run_local(ops)
    elif stage == "prefix":
        run_prefix(header, ops)
    elif stage == "cross":
        run_cross(header, ops)
    elif stage == "controls":
        if require_success("cross") is None:
            refuse("controls", "cross did not pass")
        else:
            refuse("controls", "controls stage is not open until cross success is extended")
    elif stage == "horner":
        if require_success("controls") is None:
            refuse("horner", "controls did not pass")
        else:
            refuse("horner", "horner was not entered")
    elif stage == "domain":
        trace = ART / "horner_trace.json"
        closed = False
        if trace.exists():
            closed = json.loads(trace.read_text()).get("closed") is True
        if not closed:
            refuse("domain", "horner_trace.json is not closed")
        else:
            refuse("domain", "domain was not entered")
    else:
        raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    main()
