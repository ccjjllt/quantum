"""Manual, independent resource/boundary audit of the pinned joint candidate.

No generator import, simulator or official verifier.  This audits the actual KMB
bytes, affine classical activation probabilities and clean helper boundaries.
The 63-input phase identities and legal-prefix proof are separate artifacts.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import platform
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
CAND = ART / "phase_joint_selector.kmb"
DOC = ART / "phase_joint_selector.json"
BASE_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
CAND_SHA = "7e2e2843bae6bc0b44063a9d2c4bedee63b4aca8031d78ce626606b91824057e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    c = km.Circuit.from_file(path)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return c, [l for l in lines if l.startswith(("APPEND", "REGISTER"))], [
        l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def affine_rank(rows):
    """Return rank of A for A*x=b, or None for an inconsistent system."""
    basis = {}
    for mask, rhs in rows:
        while mask:
            pivot = mask.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = mask, rhs
                break
            other, value = basis[pivot]
            mask ^= other
            rhs ^= value
        if not mask and rhs:
            return None
    return len(basis)


def probability(rows):
    rank = affine_rank(rows)
    return Fraction(0) if rank is None else Fraction(1, 2**rank)


def classical_cost(lines, initial, nvars):
    """Read actual instructions; each charged gate gets its full PUSH mask.

    Classical assignments here occur outside PUSH conditions. HMR results are
    used only by their own free CZ correction, never by a later charged gate.
    Store these as fresh symbols and assert that they do not enter cost masks.
    """
    bits, stack, charges = dict(initial), [], []
    for i, line in enumerate(lines):
        p = line.split()
        kind = p[0]
        cond = bits[int(p[-1][1:])] if "if" in p else (0, 1)
        if kind == "PUSH_CONDITION":
            stack.append(cond)
        elif kind == "POP_CONDITION":
            stack.pop()
        elif kind.startswith("BIT_"):
            assert not stack, (i, line, stack)
            target = int(p[1][1:])
            if kind == "BIT_INVERT":
                old = bits.get(target, (0, 0))
                bits[target] = old[0] ^ cond[0], old[1] ^ cond[1]
            else:
                assert "if" not in p
                bits[target] = 0, int(kind == "BIT_STORE1")
        elif kind == "HMR":
            target = int(p[2][1:])
            assert target not in bits
            bits[target] = 1 << nvars, 0
            nvars += 1
        elif kind in ("CCX", "CCZ"):
            forms = stack + ([cond] if "if" in p else [])
            rows = [(mask, 1 ^ const) for mask, const in forms]
            assert all(mask < (1 << 29) for mask, _ in rows)
            prob = probability(rows)
            charges.append({"offset": i, "instruction": line,
                            "affine_equations": rows, "rank": affine_rank(rows),
                            "probability": str(prob)})
        else:
            assert kind in ("CX", "CZ", "X", "Z"), (i, line)
    assert not stack
    return bits, charges, sum((Fraction(c["probability"]) for c in charges), Fraction(0))


def main():
    assert sha(BASE) == BASE_SHA and sha(CAND) == CAND_SHA
    doc = json.loads(DOC.read_text())
    base, header, ops = load(BASE)
    cand, new_header, new_ops = load(CAND)
    replacement = doc["replacement"]
    assert header == new_header
    assert new_ops[:27775] == ops[:27775]
    assert new_ops[27775:27775 + len(replacement)] == replacement
    assert new_ops[27775 + len(replacement):] == ops[28783:]
    assert base.num_qubits == cand.num_qubits == 62
    assert [l for l in ops if l.startswith("Z_POW")] == [l for l in new_ops if l.startswith("Z_POW")]

    writers, last_qwrite, stack = {}, {}, []
    for i, line in enumerate(ops[:27775]):
        p = line.split()
        kind = p[0]
        if kind == "PUSH_CONDITION":
            stack.append(p[-1])
            continue
        if kind == "POP_CONDITION":
            stack.pop()
            continue
        rec = {"op_index": i, "instruction": line, "push_stack": list(stack)}
        if kind == "HMR":
            writers[int(p[2][1:])] = rec
        elif kind.startswith("BIT_"):
            writers[int(p[1][1:])] = rec
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        if kind in ("X", "R", "HMR"):
            targets = qs[:1]
        elif kind in ("CX", "CCX"):
            targets = qs[-1:]
        elif kind in ("SWAP", "CSWAP"):
            targets = qs[-2:]
        else:
            assert kind in ("Z", "CZ", "CCZ", "NEG", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT")
            targets = []
        for q in targets:
            last_qwrite[q] = rec
    assert not stack
    source_writers = {b: writers[b] for b in doc["source_bits"]}
    assert len(source_writers) == 29
    assert len({v["op_index"] for v in source_writers.values()}) == 29
    assert all(v["instruction"].startswith("HMR ") and " if " not in v["instruction"] and not v["push_stack"] for v in source_writers.values())
    helpers = {q: last_qwrite[q] for q in (28, 40)}
    assert all(v["instruction"].startswith("HMR ") and " if " not in v["instruction"] and not v["push_stack"] for v in helpers.values())
    assert not [(i, l) for i, l in enumerate(ops[27775:28783], 27775) if any(f"q{q}" in l.split() for q in helpers)]

    written = set()
    for line in ops[27775:28783]:
        p = line.split()
        if p[0].startswith("BIT_"):
            written.add(int(p[1][1:]))
        elif p[0] == "HMR":
            written.add(int(p[2][1:]))
    later_reads = [(i, l) for i, l in enumerate(ops[28783:], 28783)
                   if "if" in l.split() and int(l.split()[-1][1:]) in written]
    assert not later_reads
    assert not [(i, l) for i, l in enumerate(ops) if any(t.startswith("b") and t[1:].isdigit() and 42000 <= int(t[1:]) <= 42022 for t in l.split())]

    initial = {b: (1 << j, 0) for j, b in enumerate(doc["source_bits"])}
    initial, _, _ = classical_cost(ops[27643:27775], initial, 29)
    old_bits, old_charges, old_cost = classical_cost(ops[27775:28783], initial, 29)
    new_bits, new_charges, new_cost = classical_cost(replacement, initial, 29)
    masks = [[old_bits[start + j][0] for j in range(19)] for start in (24256, 24320)]
    assert masks == doc["original_masks"]
    assert all(old_bits[start + j][1] == 0 for start in (24256, 24320) for j in range(19))
    failures = [new_bits[42000 + j][0] for j in range(3)]
    assert failures == [b["failure_mask"] for b in doc["branches"]]
    assert all(new_bits[42000 + j][1] == 0 for j in range(3))
    rank = affine_rank([(m, 0) for m in failures])
    assert rank == 3
    zero_rows = [[(m, 1) for m in failures] + [(m, 0) for m in group] for group in masks]
    zero_ranks = [affine_rank(rows) for rows in zero_rows]
    assert zero_ranks == [None, None]
    assert [affine_rank([(m, 0) for m in group]) for group in masks] == [19, 19]
    assert old_cost == 2 - Fraction(1, 2**18)
    assert new_cost == Fraction(9, 8)

    report = {
        "status": "PASS: actual bytes, full classical activation cost, borrowed-wire boundary and classical liveness",
        "scope": "No simulator or official verifier. Phase equivalence/legal-prefix semantics audited separately.",
        "command": "uv run python experiments/invsqrt/20261103_one_ccx/audit_joint_resources.py",
        "environment": {"python": sys.version, "platform": platform.platform(), "kickmix": importlib.metadata.version("kickmix")},
        "source_sha256": sha(Path(__file__)), "generator_sha256": sha(Path(__file__).with_name("phase_cache.py")),
        "uv_lock_sha256": sha(ROOT / "uv.lock"), "baseline_sha256": sha(BASE), "candidate_sha256": sha(CAND),
        "candidate_manifest_sha256": sha(DOC), "window": [27775, 28783], "Q": 62,
        "actual_prefix_replacement_suffix_match": True, "Z_POW_sequence_identical": True,
        "source_writers": source_writers, "borrowed_wire_last_writes": helpers,
        "borrowed_wires_mentions_in_original_window": [], "old_window_written_bits": sorted(written),
        "old_written_bits_downstream_reads": later_reads, "new_classical_bit_collision": False,
        "cleanup_identity": "q28=u; q40=q21*u. Diagonal core leaves data. HMR q40 contributes m*q21*u; CZ q21 q28 if m cancels exactly; reversed CX clears q28.",
        "old_actual_charged_gate_activations": old_charges,
        "new_actual_charged_gate_activations": new_charges,
        "failure_masks": failures, "failure_rank": rank, "original_group_ranks": [19, 19],
        "fallback_and_group_zero_equations": zero_rows,
        "fallback_and_group_zero_results": ["inconsistent", "inconsistent"],
        "expected_old_cost": str(old_cost), "expected_new_cost": str(new_cost),
        "expected_saving": str(old_cost-new_cost), "expected_saving_decimal": float(old_cost-new_cost),
        "expected_with_tail3_saving": str(old_cost-new_cost+Fraction(3,16)),
        "expected_with_tail3_saving_decimal": float(old_cost-new_cost+Fraction(3,16)),
    }
    output = ART / "phase_joint_resource_audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(output), "status": report["status"], "old": str(old_cost), "new": str(new_cost), "saving": str(old_cost-new_cost), "with_tail3": str(old_cost-new_cost+Fraction(3,16))}, indent=2))


if __name__ == "__main__":
    main()
