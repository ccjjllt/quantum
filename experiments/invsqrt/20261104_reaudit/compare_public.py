"""Manual exact comparison to the downloaded SomeJoint public inverse.

The local nofallback window is normalized back only in memory. All remaining
differences are checked as arbitrary-input value/phase identities, including
symbolic HMR outcomes. No official verification, no candidate is written.
"""
from __future__ import annotations
import collections
import difflib
import hashlib
import io
import json
from pathlib import Path
import time
import kickmix as km
import z3

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / "artifacts/20261104_submission_refresh/heliosli/public_invsqrt.kmb"
LOC = ROOT / "artifacts/20261104_reaudit/cross_hmr/public62_nofallback_cross_hmr.kmb"
KIR = ROOT / "artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb"
MIG = ROOT / "artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb"
ART = ROOT / "artifacts/20261104_reaudit/cross_hmr"


def load(path):
    c = km.Circuit.from_file(path); stream = io.StringIO(); c.to_file(stream, format="kmx")
    lines = stream.getvalue().splitlines()
    return c, [l for l in lines if l.startswith(("APPEND", "REGISTER"))], [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def execute(lines, entry, label):
    q, bits, phase = list(entry), {}, z3.BoolVal(False)
    versions = collections.Counter()
    for line in lines:
        p = line.split(); kind = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = bits.get(p[-1], z3.Bool(f"{label}_entry_{p[-1]}")) if "if" in p else z3.BoolVal(True)
        if kind in ("X", "CX", "CCX"):
            q[qs[-1]] = z3.Xor(q[qs[-1]], z3.And([active] + [q[w] for w in qs[:-1]]))
        elif kind == "HMR":
            assert "if" not in p
            bit = p[2]; version = versions[bit]; versions[bit] += 1
            outcome = z3.Bool(f"{label}_outcome_{bit}_{version}")
            phase = z3.Xor(phase, z3.And(q[qs[0]], outcome))
            bits[bit] = outcome; q[qs[0]] = z3.BoolVal(False)
        elif kind in ("Z", "CZ", "CCZ"):
            phase = z3.Xor(phase, z3.And([active] + [q[w] for w in qs]))
        else: raise ValueError(line)
    return q, bits, phase


def main():
    pc, ph, public = load(PUB); lc, lh, local = load(LOC)
    _, _, kirill = load(KIR); _, _, migration = load(MIG)
    assert pc.num_qubits == lc.num_qubits == 62 and ph == lh
    pub_sha = hashlib.sha256(PUB.read_bytes()).hexdigest()
    loc_sha = hashlib.sha256(LOC.read_bytes()).hexdigest()
    assert pub_sha == "15118bfa94a4084cd853c752100442ec41d8a80bae0f483af98a0cac2677e64c"
    assert loc_sha == "aac6ce1048f55ec961329f44082d88f4afa11d013ca13f062f5cac23b4c861c3"
    # Same original selector and same proven replacement, only preceding lengths differ.
    assert public[27755:28763] == kirill[27745:28753]
    assert local[27751:30575] == migration[27745:30569]
    normalized = local[:27751] + public[27755:28763] + local[30575:]
    assert [l for l in public if l.startswith("HMR ")] == [l for l in normalized if l.startswith("HMR ")]
    assert [l for l in public if l.startswith("Z_POW ")] == [l for l in local if l.startswith("Z_POW ")]
    rows = []
    for j, group in enumerate(difflib.SequenceMatcher(a=public, b=normalized, autojunk=False).get_grouped_opcodes(4)):
        a0, a1 = group[0][1], group[-1][2]
        b0, b1 = group[0][3], group[-1][4]
        old, new = public[a0:a1], normalized[b0:b1]
        assert sum(l.startswith("PUSH_CONDITION") - l.startswith("POP_CONDITION") for l in public[:a0]) == 0
        assert sum(l.startswith("PUSH_CONDITION") - l.startswith("POP_CONDITION") for l in normalized[:b0]) == 0
        assert [l for l in old if l.startswith("HMR ")] == [l for l in new if l.startswith("HMR ")]
        ccx_old = sum(l.startswith("CCX ") for l in old)
        ccx_new = sum(l.startswith("CCX ") for l in new)
        assert ccx_old == ccx_new
        assert all(" if " not in l for l in old + new if l.startswith("CCX "))
        assert not any(l.startswith("CCZ ") for l in old + new)
        entry = [z3.Bool(f"window{j}_q{w}") for w in range(62)]
        oq, ob, op = execute(old, entry, f"w{j}")
        nq, nb, np = execute(new, entry, f"w{j}")
        assert ob.keys() == nb.keys()
        fail = z3.Or([a != b for a, b in zip(oq, nq)] + [op != np] + [ob[b] != nb[b] for b in ob])
        solver = z3.Solver(); solver.set(timeout=60000); solver.add(fail)
        start = time.monotonic(); result = solver.check()
        row = {"public_window": [a0, a1], "normalized_local_window": [b0, b1],
               "result": str(result), "seconds": time.monotonic() - start,
               "unconditional_CCX_each": ccx_old, "HMR_events": len([l for l in old if l.startswith("HMR ")]),
               "public_ops": old, "normalized_local_ops": new}
        if result == z3.unknown: row["reason"] = solver.reason_unknown()
        rows.append(row)
        assert result == z3.unsat, row
    assert len(rows) == 5, len(rows)
    audit_path = ROOT / "artifacts/20261104_reaudit/migration/audit_migrated.json"
    audit = json.loads(audit_path.read_text())
    assert audit["status"] == "PASS"
    assert audit["candidate_sha256"] == hashlib.sha256(MIG.read_bytes()).hexdigest()
    assert audit["baseline_sha256"] == hashlib.sha256(KIR.read_bytes()).hexdigest()
    assert audit["billing"]["saving_C"] == "262143/262144"
    report = {"status": "PASS", "public_sha256": pub_sha, "candidate_sha256": loc_sha,
              "public_operations": len(public), "candidate_operations": len(local),
              "same_public_cross_HMR_method": True, "cross_HMR_implementations_identical_bytes": False,
              "normalized_local_method": "replace only local nofallback with the actual public original selector in memory",
              "normalized_local_equivalent_to_public_for_all_inputs_and_measurement_outcomes": True,
              "selector_bytes_match_prior_proved_inputs_and_output": True,
              "migration_audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
              "exact_extra_C_saving_vs_public": "262143/262144",
              "exact_extra_cost_saving_vs_public": 62 * 262143 / 262144,
              "comparison_patches": rows}
    (ART / "comparison_to_latest_public.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "comparison_patches"}, indent=2))


if __name__ == "__main__":
    main()
