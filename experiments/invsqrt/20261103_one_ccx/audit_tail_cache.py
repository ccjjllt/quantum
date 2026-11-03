"""Independent manual audit of the two/three-AND tail-cache KMB artifacts.

Reads the ACTUAL baseline and candidate KMBs. Does not import the generator or
either earlier symbolic prover. Original HMR events align by unique output-bit
name; added events are fresh. Exact Boolean parity represents all local phases
because this window contains only pi-phase operations, not general rotations.

Run manually (never invokes the official verifier):
  uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/audit_tail_cache.py --candidate both
"""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import importlib.metadata
import io
import json
import platform
import shlex
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import kickmix as km
import z3

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
BASE_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
EXPECTED = {
    "two_and": "d155f0c8a1ef65e4cf85eb45ab06bdf016e63299b98e205df301c9b7b86ca89a",
    "three_and": "c2c255036961fcddbbabca84c231d4101ae928cbf34ae9a3da75926b7b665a0f",
}
LO, HI = 47113, 47186


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    raw = path.read_bytes()
    circuit = km.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    header, ops = [], []
    for line in buf.getvalue().splitlines():
        (header if line.startswith(("APPEND", "REGISTER")) else ops).append(line)
    canonical = io.BytesIO()
    circuit.to_file(canonical, format="kmb")
    return circuit, header, ops, digest(raw), digest(canonical.getvalue())


def qubit_writes(line):
    p = line.split(); k = p[0]
    qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
    if k in ("X", "CX", "CCX", "HMR", "R"):
        return qs[-1:]
    if k in ("SWAP", "CSWAP"):
        return qs[-2:]
    return []


def bit_write(line):
    p = line.split()
    if p[0] == "HMR":
        return p[2]
    if p[0].startswith("BIT_"):
        return p[1]
    return None


def lexical_stack(ops, stop):
    stack = []
    for index, line in enumerate(ops[:stop]):
        p = line.split()
        if p[0] == "PUSH_CONDITION":
            stack.append((p[-1], index))
        elif p[0] == "POP_CONDITION":
            assert stack, (index, "stack underflow")
            stack.pop()
    return stack


def initial_bit(name):
    return z3.Bool("entry_" + name)


def run(lines, initial_q, initial_stack=()):
    """Independent exact interpreter; HMR events keyed by output bit names."""
    q = list(initial_q)
    bits = {}
    stack = list(initial_stack)
    phase = z3.BoolVal(False)
    cost = z3.IntVal(0)
    events = {}
    event_versions = collections.Counter()
    reset_serial = 0

    def bit(name):
        return bits.setdefault(name, initial_bit(name))

    for line in lines:
        p = line.split(); kind = p[0]
        if kind == "PUSH_CONDITION":
            stack.append(bit(p[-1])); continue
        if kind == "POP_CONDITION":
            assert stack, "stack underflow"
            stack.pop(); continue
        guards = list(stack)
        if "if" in p:
            guards.append(bit(p[p.index("if") + 1]))
        active = z3.And(guards)
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        if kind == "X":
            q[qs[0]] = z3.If(active, z3.Not(q[qs[0]]), q[qs[0]])
        elif kind == "CX":
            q[qs[1]] = z3.Xor(q[qs[1]], z3.And(active, q[qs[0]]))
        elif kind == "CCX":
            q[qs[2]] = z3.Xor(q[qs[2]], z3.And(active, q[qs[0]], q[qs[1]]))
            cost += z3.If(active, 1, 0)
        elif kind in ("SWAP", "CSWAP"):
            a, b = qs[-2:]
            ctl = active if kind == "SWAP" else z3.And(active, q[qs[0]])
            olda, oldb = q[a], q[b]
            q[a], q[b] = z3.If(ctl, oldb, olda), z3.If(ctl, olda, oldb)
            if kind == "CSWAP":
                cost += z3.If(active, 1, 0)
        elif kind in ("Z", "CZ", "CCZ", "NEG"):
            phase = z3.Xor(phase, z3.And([active] + [q[j] for j in qs]))
            if kind == "CCZ":
                cost += z3.If(active, 1, 0)
        elif kind in ("HMR", "R"):
            if kind == "HMR":
                name = p[2]
                version = event_versions[name]
                event_versions[name] += 1
                event_name = name if version == 0 else f"{name}_v{version}"
                outcome = z3.Bool("out_" + event_name)
                events[event_name] = active
            else:
                outcome = z3.Bool(f"anonymous_reset_{reset_serial}")
                reset_serial += 1
            phase = z3.Xor(phase, z3.And(active, q[qs[0]], outcome))
            q[qs[0]] = z3.If(active, z3.BoolVal(False), q[qs[0]])
            if kind == "HMR":
                bits[name] = z3.If(active, outcome, bit(name))
        elif kind in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            old = bit(p[1])
            new = z3.Not(old) if kind == "BIT_INVERT" else z3.BoolVal(kind == "BIT_STORE1")
            bits[p[1]] = z3.If(active, new, old)
        else:
            raise ValueError("Unsupported local opcode: " + line)
    return q, bits, stack, phase, cost, events


def prove_unsat(expression, label):
    solver = z3.Solver()
    solver.set(timeout=60_000)
    solver.add(expression)
    verdict = solver.check()
    result = {"label": label, "result": str(verdict)}
    if verdict == z3.unknown:
        result["reason"] = solver.reason_unknown()
    if verdict == z3.sat:
        result["counterexample"] = str(solver.model())
    return result


def prove_clean_entries(base, clean):
    """Find actual unconditional resets; prove the remaining short tail suffix."""
    sites = {}
    stack = []
    for index, line in enumerate(base[:LO]):
        p = line.split()
        if p[0] == "PUSH_CONDITION":
            stack.append(p[-1])
        elif p[0] == "POP_CONDITION":
            stack.pop()
        elif p[0] == "HMR" and not stack and "if" not in p:
            wire = int(p[1][1:])
            if wire in clean:
                sites[wire] = index
    assert set(sites) == set(clean)
    boundary = max(sites.values()) + 1
    assert not lexical_stack(base, boundary)
    records = {}
    for wire, site in sites.items():
        assert all(wire not in qubit_writes(line) for line in base[site + 1:boundary])
        entry = [z3.Bool(f"clean_{wire}_q{j}") for j in range(62)]
        entry[wire] = z3.BoolVal(False)
        q, *_ = run(base[boundary:LO], entry)
        proof = prove_unsat(q[wire], f"q{wire} zero at local entry")
        records[str(wire)] = {"unconditional_HMR": site,
                              "no_write_through": boundary - 1,
                              "suffix": [boundary, LO], **proof}
    return records


def expectation_sources(base):
    """Check the concrete independent random events underlying the 1/16 guard."""
    wanted = {"b318": 46869, "b319": 46994, "b320": 47112, "b322": 47148}
    expected_guards = {"b318": [], "b319": ["b8045"],
                       "b320": ["b8045", "b8046"], "b322": ["b8045", "b8046"]}
    records = {}
    for bit, index in wanted.items():
        p = base[index].split()
        assert p[0] == "HMR" and p[2] == bit and "if" not in p
        guards = [name for name, _ in lexical_stack(base, index)]
        assert guards == expected_guards[bit], (bit, guards)
        records[bit] = {"HMR_index": index, "guards": guards}
    assert base[46870:46872] == ["BIT_STORE1 b8045", "BIT_INVERT b8045 if b318"]
    assert base[46995:46997] == ["BIT_STORE1 b8046", "BIT_INVERT b8046 if b319"]
    assert all(bit_write(line) != "b8045" for line in base[46872:HI])
    assert all(bit_write(line) != "b8046" for line in base[46997:HI])
    return {"events": records, "outer_conditions": ["b8045 = not b318", "b8046 = not b319"],
            "guard_probability": "1/2 * 1/2 * 1/2 * 1/2 = 1/16",
            "assumption": "kickmix HMR outcomes are independent unbiased random bits when executed"}


def audit(variant):
    path = ART / f"tail_cache_{variant}.kmb"
    bc, bh, base, bsha, bcanonical = load(BASE)
    cc, ch, cand, csha, ccanonical = load(path)
    assert bsha == bcanonical == BASE_SHA
    assert csha == ccanonical == EXPECTED[variant]
    assert bc.num_qubits == cc.num_qubits == 62 and bh == ch
    cut = len(cand) - (len(base) - HI)
    assert base[:LO] == cand[:LO] and base[HI:] == cand[cut:]
    old, new = base[LO:HI], cand[LO:cut]
    assert not any(line.startswith(("R ", "Z_POW ")) for line in old + new)
    zpow_equal = [l for l in base if l.startswith("Z_POW ")] == [l for l in cand if l.startswith("Z_POW ")]
    assert zpow_equal
    baseline_bits = {t for line in base for t in line.split() if t.startswith("b") and t[1:].isdigit()}
    candidate_bits = {t for line in cand for t in line.split() if t.startswith("b") and t[1:].isdigit()}
    fresh_bits = sorted(candidate_bits - baseline_bits)
    clean = [19, 32, 34, 35] + ([36] if variant == "three_and" else [])
    clean_proofs = prove_clean_entries(base, clean)
    stack = lexical_stack(base, LO)
    assert [name for name, _ in stack] == ["b8045", "b8046"]
    for name, pushed in stack:
        assert all(bit_write(line) != name for line in base[pushed + 1:LO])
    entry_q = [z3.Bool(f"entry_q{j}") if j not in clean else z3.BoolVal(False) for j in range(62)]
    entry_stack = [initial_bit(name) for name, _ in stack]
    qo, bo, so, po, co, eo = run(old, entry_q, entry_stack)
    qn, bn, sn, pn, cn, en = run(new, entry_q, entry_stack)
    assert len(so) == len(sn)
    assert set(eo) <= set(en)
    existing_bits = (set(bo) | set(bn)) & baseline_bits
    differences = [z3.Xor(a, b) for a, b in zip(qo, qn)] + [z3.Xor(po, pn)]
    differences += [z3.Xor(bo.get(k, initial_bit(k)), bn.get(k, initial_bit(k))) for k in existing_bits]
    differences += [z3.Xor(a, b) for a, b in zip(so, sn)]
    differences += [z3.Xor(active, en[name]) for name, active in eo.items()]
    equivalence = prove_unsat(z3.Or(differences), "all qubits, old bits, saved stack, phase, old event execution conditions")
    saving = 3 if variant == "three_and" else 2
    guard = z3.And(initial_bit("b8045"), initial_bit("b8046"), initial_bit("b320"), z3.Bool("out_b322"))
    cost = prove_unsat(co - cn != z3.If(guard, saving, 0), "exact per-branch Toffoli-like execution delta")
    diff = []
    for tag, i, j, k, l in difflib.SequenceMatcher(a=base, b=cand, autojunk=False).get_opcodes():
        if tag != "equal":
            diff.append({"tag": tag, "baseline_range": [i, j], "candidate_range": [k, l],
                         "old": base[i:j], "new": cand[k:l]})
    bcounts = collections.Counter(l.split()[0] for l in base)
    ccounts = collections.Counter(l.split()[0] for l in cand)
    passed = equivalence["result"] == cost["result"] == "unsat" and all(p["result"] == "unsat" for p in clean_proofs.values())
    return {"status": "PASS" if passed else "NOT_PROVEN", "scope": "independent local all-branch proof; not official full-domain verification",
            "variant": variant, "baseline": str(BASE), "candidate": str(path),
            "baseline_sha256": bsha, "candidate_sha256": csha, "canonical_hashes_match_raw": True,
            "qubits": 62, "extra_qubits": 0, "all_zpow_instructions_identical": zpow_equal,
            "baseline_window": [LO, HI], "candidate_window": [LO, cut], "actual_file_diff": diff,
            "static_opcode_delta": {k: ccounts[k] - bcounts[k] for k in sorted(set(bcounts) | set(ccounts)) if ccounts[k] != bcounts[k]},
            "fresh_classical_bits": fresh_bits, "event_alignment": "unique HMR output-bit names, independently parsed from actual KMBs",
            "clean_entry_proofs": clean_proofs, "equivalence": equivalence, "cost_proof": cost,
            "cost_saving_branch": f"{saving} iff b8045 AND b8046 AND entry_b320 AND outcome_b322; 0 otherwise",
            "expected_equivalent_saving": saving / 16, "expectation_evidence": expectation_sources(base),
            "added_HMR_events": sorted(set(en) - set(eo)),
            "general_rotations_added": 0, "official_verifier_shots_in_this_audit": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", choices=("two_and", "three_and", "both"), default="both")
    args = ap.parse_args()
    command = "uv run --offline --with z3-solver python " + shlex.join([str(Path(__file__).relative_to(ROOT)), "--candidate", args.candidate])
    meta = {"date_time": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "python": platform.python_version(), "kickmix": importlib.metadata.version("kickmix"),
            "z3": z3.get_version_string(), "command": command, "cwd": str(ROOT),
            "argv": sys.argv, "audit_script_sha256": digest(Path(__file__).read_bytes())}
    variants = ("two_and", "three_and") if args.candidate == "both" else (args.candidate,)
    ok = True
    for variant in variants:
        result = audit(variant)
        result["metadata"] = meta
        ART.mkdir(parents=True, exist_ok=True)
        dest = ART / f"audit_tail_cache_{variant}.json"
        dest.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"variant": variant, "status": result["status"], "candidate_sha256": result["candidate_sha256"],
                          "expected_equivalent_saving": result["expected_equivalent_saving"], "proof": str(dest)}))
        ok &= result["status"] == "PASS"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
