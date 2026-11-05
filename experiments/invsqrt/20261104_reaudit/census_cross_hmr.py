"""Read-only, bounded geometric census; no synthesis or gain claim.

Reports consecutive three-Toffoli-like spans containing exactly one HMR,
at most ten wires and a fixed condition stack. Already absorbed rewrite
regions are excluded. At most 32 nonoverlapping windows are detailed.
"""
from __future__ import annotations
import bisect
import collections
import hashlib
import io
import json
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261104_reaudit/cross_hmr"
BASE = ART / "public62_nofallback_cross_hmr.kmb"
SHA = "aac6ce1048f55ec961329f44082d88f4afa11d013ca13f062f5cac23b4c861c3"


def topology(lines):
    roles, out = {}, []
    for line in lines:
        p = line.split()
        if p[0] not in ("CCX", "CCZ", "CSWAP", "HMR"): continue
        qs = [t for t in p[1:] if t.startswith("q")]
        out.append([p[0], [roles.setdefault(t, len(roles)) for t in qs]])
    return json.dumps(out, separators=(",", ":"))


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    c = km.Circuit.from_file(BASE); buf = io.StringIO(); c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [l.split() for l in ops]
    paid = [i for i, p in enumerate(gates) if p[0] in ("CCX", "CCZ", "CSWAP")]
    st, stacks = [], []
    for p in gates:
        stacks.append(tuple(st))
        if p[0] == "PUSH_CONDITION": st.append(p[-1])
        elif p[0] == "POP_CONDITION": st.pop()
    assert not st
    absorbed = []
    old_topologies = set()
    previous = json.loads((ART / "cross_hmr_proof.json").read_text())
    for p in previous["patches"]:
        old_topologies.add(topology(p["old"]))
        n = p["new"]
        matches = [i for i in range(len(ops) - len(n) + 1) if ops[i:i+len(n)] == n]
        assert len(matches) == 1
        absorbed.append({"kind": "cross_HMR_2C_already_counted", "window": [matches[0], matches[0] + len(n)]})
    templates = json.loads((ROOT / "experiments/invsqrt/20261104_public62_optimization/routeA_templates.json").read_text())
    for e in templates["kirill_identity"] + templates["syed_conditional"]:
        n = e["new"]
        matches = [i for i in range(len(ops) - len(n) + 1) if ops[i:i+len(n)] == n]
        assert len(matches) == 1
        absorbed.append({"kind": "previous_public_identity_already_counted", "window": [matches[0], matches[0] + len(n)]})
    rows, rejected, overlap = [], collections.Counter(), []
    raw_qualified = 0
    for a, b, d in zip(paid, paid[1:], paid[2:]):
        win = gates[a:d+1]
        if sum(p[0] == "HMR" for p in win) != 1:
            rejected["HMR_count_not_one"] += 1; continue
        if any(p[0] in ("Z_POW", "R", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "PUSH_CONDITION", "POP_CONDITION") for p in win):
            rejected["rotation_or_reset_or_classical_write_or_stack_boundary"] += 1; continue
        if any(s != stacks[a] for s in stacks[a:d+1]):
            rejected["stack_changed"] += 1; continue
        wires = sorted({int(t[1:]) for p in win for t in p[1:] if t.startswith("q")})
        if len(wires) > 10:
            rejected["more_than_ten_wires"] += 1; continue
        raw_qualified += 1
        conflicts = [r for r in absorbed if a < r["window"][1] and r["window"][0] < d+1]
        if conflicts:
            overlap.append({"window": [a, d+1], "absorbed_regions": conflicts}); continue
        sig = topology(ops[a:d+1])
        unconditional = not stacks[a] and all("if" not in gates[j] for j in (a, b, d))
        rows.append({"window": [a, d+1], "paid_indices": [a, b, d],
                     "paid_types": [gates[j][0] for j in (a, b, d)],
                     "wire_count": len(wires), "wires": wires, "span_ops": d+1-a,
                     "condition_stack": list(stacks[a]), "unconditional_paid_window": unconditional,
                     "topology": json.loads(sig), "matches_old_absorbed_cross_HMR_topology": sig in old_topologies,
                     "hmr_index": next(a+i for i, p in enumerate(win) if p[0] == "HMR"),
                     "template_3_to_2_C_saving_upper_bound": 1,
                     "upper_bound_note": "one per shot only IF an equivalent 3->2 circuit exists; guarded activation probability only bounded by <=1",
                     "instructions": ops[a:d+1]})
    # Unit-weight interval DP gives the largest nonoverlapping research cohort;
    # among ties prefer unconditional paid windows. No assumption of solvability.
    rows.sort(key=lambda r: (r["window"][1], r["window"][0]))
    ends = [r["window"][1] for r in rows]
    dp = [(0, 0, [])]
    for i, row in enumerate(rows):
        prev = bisect.bisect_right(ends, row["window"][0], 0, i)
        old = dp[prev]
        take = (old[0] + 1, old[1] + int(row["unconditional_paid_window"]), old[2] + [i])
        skip = dp[-1]
        dp.append(take if take[:2] > skip[:2] else skip)
    selected = [rows[i] for i in dp[-1][2]][:32]
    histogram = collections.Counter(tuple(r["paid_types"]) for r in rows)
    out = {"scope": "read-only geometry census, no resynthesis, no new candidate and no demonstrated gain",
           "baseline_sha256": SHA, "qubits": c.num_qubits, "paid_gate_count": len(paid),
           "all_consecutive_three_paid_spans": len(paid)-2, "geometrically_qualified_spans": raw_qualified,
           "rejection_counts": dict(rejected), "excluded_absorbed_overlap_count": len(overlap),
           "excluded_absorbed_overlaps": overlap, "fresh_geometric_spans_before_overlap_resolution": len(rows),
           "fresh_exact_paid_HMR_topology_count": len({json.dumps(r["topology"]) for r in rows}),
           "fresh_spans_matching_already_absorbed_cross_HMR_topology": sum(r["matches_old_absorbed_cross_HMR_topology"] for r in rows),
           "paid_type_histogram": {"/".join(k): v for k, v in histogram.items()},
           "maximum_nonoverlapping_geometric_spans": dp[-1][0],
           "selected_unconditional_paid_windows": sum(r["unconditional_paid_window"] for r in selected),
           "selected_guarded_windows": sum(not r["unconditional_paid_window"] for r in selected),
           "selected_windows": selected,
           "research_template_3_to_2_C_saving_upper_bound": len(selected),
           "research_template_3_to_2_cost_saving_upper_bound": 62 * len(selected),
           "whole_window_erasure_trivial_C_upper_bound": 3 * len(selected),
           "demonstrated_new_gain_C": 0,
           "upper_bound_warning": "These are static bounds for the selected disjoint research cohort, not achieved savings, not proof that any window can be reduced, and not a global circuit bound."}
    (ART / "remaining_cross_hmr_census.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("selected_windows", "excluded_absorbed_overlaps")}, indent=2))


if __name__ == "__main__":
    main()
