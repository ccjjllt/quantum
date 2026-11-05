"""Reproduce SomeJoint's two cross-HMR 3->2 merges on our nofallback parent.

Source: somejoint/quantum-circuits-24-53-local-gm-window-merges, downloaded
2026-11-04, version 32; source notebook SHA is recorded in the output. Apache-2.0 lineage
and the algebraic identity are attributed to SomeJoint's window splice.
This script performs a local exhaustive value/phase check and writes a KMB.
It does not invoke the official verifier or submit to Kaggle.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb"
BASE_SHA = "5541151cdeea9bd0729c1e09715af3737c4d7d1c95da913b3b976485e766ff38"
ART = ROOT / "artifacts/20261104_reaudit/cross_hmr"
SOURCE = ROOT / "artifacts/20261104_submission_refresh/somejoint/quantum-circuits-24-53-local-gm-window-merges.ipynb"
SOURCE_URL = "https://www.kaggle.com/code/somejoint/quantum-circuits-24-53-local-gm-window-merges"


def load(path):
    c = km.Circuit.from_file(path)
    out = io.StringIO(); c.to_file(out, format="kmx")
    lines = out.getvalue().splitlines()
    return c, [l for l in lines if l.startswith(("APPEND", "REGISTER"))], [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def local_check(old, new):
    wires = sorted({int(t[1:]) for line in old + new for t in line.split()[1:] if t.startswith("q")})
    hmr = [l.split() for l in old if l.startswith("HMR ")]
    assert len(hmr) == 1
    outcome = hmr[0][2]
    n = len(wires)
    cases = 1 << (n + 1)
    one = (1 << cases) - 1
    initial = {w: sum(((v >> j) & 1) << v for v in range(cases)) for j, w in enumerate(wires)}
    measurement = sum(((v >> n) & 1) << v for v in range(cases))

    def execute(lines):
        q, bits, phase, seen = dict(initial), {}, 0, 0
        for line in lines:
            p = line.split(); k = p[0]
            qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
            active = bits[p[-1]] if "if" in p else one
            if k in ("X", "CX", "CCX"):
                value = active
                for w in qs[:-1]: value &= q[w]
                q[qs[-1]] ^= value
            elif k == "HMR":
                assert "if" not in p and p[2] == outcome
                phase ^= q[qs[0]] & measurement
                q[qs[0]] = 0; bits[p[2]] = measurement; seen += 1
            elif k in ("Z", "CZ"):
                value = active
                for w in qs: value &= q[w]
                phase ^= value
            else: raise ValueError(line)
        assert seen == 1
        return q, phase

    expected = execute(old)
    actual = execute(new)
    assert actual == expected, "value/phase local mismatch"
    # The final copy supplies c*(u+v); dropping it must be caught.
    assert execute(new[:-1]) != expected
    return {"status": "PASS", "dirty_wires": wires, "wire_count": n,
            "measurement_outcomes": 2, "exhaustive_cases": cases,
            "all_output_values_equal": True, "phase_equal": True,
            "negative_control_drop_final_copy": "REJECTED"}


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    c, hdr, ops = load(BASE)
    assert c.num_qubits == 62
    specs = [(21488, 14, 53, 19, 18, 9, 8), (25503, 21, 29, 40, 28, 1, 0)]
    patches = []
    for lo, a, m, t, ctl, u, v in specs:
        old = ops[lo:lo + 19]
        first = [f"CCX q{a} q{m} q{t}", f"CX q{u} q{m}",
                 f"CX q{a} q{m}", f"CX q{v} q{m}", f"CCX q{ctl} q{m} q{t}",
                 f"CX q{v} q{m}", f"CX q{ctl} q{m}"]
        assert old[:7] == first
        assert old[7].startswith(f"HMR q{a} ")
        bit = old[7].split()[2]
        assert all(l.startswith(("Z ", "CZ ")) and l.endswith(f"if {bit}") for l in old[8:17])
        assert old[17:] == [f"CX q{u} q{v}", f"CCX q{ctl} q{v} q{a}"]
        depth = sum(l.startswith("PUSH_CONDITION") - l.startswith("POP_CONDITION") for l in ops[:lo])
        assert depth == 0
        new = [f"CX q{ctl} q{a}", f"CX q{ctl} q{m}", f"CCX q{a} q{m} q{t}",
               f"CX q{ctl} q{m}", f"CX q{ctl} q{a}", f"CX q{ctl} q{t}",
               f"CX q{u} q{m}", f"CX q{a} q{m}", f"CX q{ctl} q{m}",
               *old[7:], f"CX q{a} q{t}"]
        proof = local_check(old, new)
        assert sum(l.startswith("CCX ") for l in old) == 3
        assert sum(l.startswith("CCX ") for l in new) == 2
        patches.append({"window": [lo, lo + 19], "old": old, "new": new,
                        "proof": proof, "executed_C_saved_per_shot": 1})
    out, cursor = [], 0
    for p in patches:
        lo, hi = p["window"]
        out += ops[cursor:lo] + p["new"]
        cursor = hi
    out += ops[cursor:]
    assert [l for l in out if l.startswith("HMR ")] == [l for l in ops if l.startswith("HMR ")]
    assert [l for l in out if l.startswith("Z_POW ")] == [l for l in ops if l.startswith("Z_POW ")]
    candidate = km.Circuit.from_file(io.StringIO("\n".join(hdr + out) + "\n"), format="kmx")
    assert candidate.num_qubits == 62
    ART.mkdir(parents=True, exist_ok=True)
    target = ART / "public62_nofallback_cross_hmr.kmb"
    candidate.to_file(target, format="kmb")
    _, hdr2, readback = load(target)
    assert hdr2 == hdr and readback == out
    report = {"scope": "exact local exhaustive equivalence and real circuit generation; official validation is recorded separately",
              "baseline_sha256": BASE_SHA, "candidate_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "source_url": SOURCE_URL, "source_notebook_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "source_notebook_version": 32,
              "qubits": 62, "operations_before": len(ops), "operations_after": len(out),
              "exact_C_saving_vs_local_parent": 2, "exact_cost_saving": 124,
              "measurement_sequence_unchanged": True, "Z_POW_sequence_unchanged": True, "patches": patches}
    (ART / "cross_hmr_proof.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "patches"}, indent=2))


if __name__ == "__main__":
    main()
