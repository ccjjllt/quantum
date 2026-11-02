"""Experiment 4: retain-vs-recompute on the largest exact-repeat chain (baseline_hw06).

Chain: src=[25599,25644] (B tail, last 88 ops of B) -> copy=[28838,28883]
(inverse_B head). 46 ops, exact op-text repeat, 13 CCX in the copy -- the
largest copy_toffoli_like of any exact repeat with sep>=500 on this baseline
(scan over the full 47258-op circuit; the Exp-2 chain had only 3 CCX).
Scope note: this chain does NOT overlap the R1-R6 rewrite zones (R6 ends at
b-coord 25534 < 25599), so none of its 13 CCX is an already-counted
Ahmed-cache / Ehan-merge / temporary-AND saving.

Result (triple lock, all machine-checked):
  value:  FAIL -- CCX value signatures differ at the FIRST CCX
          (controls 13619/12846 vs 18173/18146: different data, B-tail vs
          inverse_B-head operating on different inputs, same structural
          reason as joint_phase62); 2 of 3 frontier outputs (q40,q57) are
          nonzero before the copy; all 3 lifetime checks fail.
  phase/measurement: FAIL -- copy contains 2x HMR (q21/q41 -> b341),
          3x conditional CZ (if b341), an unbalanced leading POP_CONDITION,
          and unconditional NEG/Z/CZ acting on wires whose values differ
          from src time; condition env differs (src [b457] vs copy [b458]).
          No deterministic correction covering all outcomes is proposed
          (only deterministic fixes allowed), so no rewrite is claimable.
  cost:   FAIL -- even the fantasy upper bound (delete all 13 CCX, zero
          cleanup, 62Q) gives dC=-13 -> dscore=-806, ~6.2x short of the
          62Q 5% line (81.10 C -> -5028.2 score). Coherent keep is net
          positive (per-slice saving is 1 CCX vs +1Q ~ +1622 score).

Cost model: verifier units C = executed Toffoli-like + T/4, score = Q*C;
CX/X/CZ/NEG Clifford-free; unconditional CCX = 1 C.
Threshold lines (README authoritative): 62Q 81.10, 63Q 105.56, 64Q 129.26 C.

Usage:
  uv run python experiments/invsqrt/20261102_hw06_opt/retain_chain2_62.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_hw06_opt"))
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))

import retain62  # noqa: E402
import booleq62  # noqa: E402

BASELINE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "experiments/invsqrt/20261102_hw06_opt/retain_chain2_62.json"

SRC = (25599, 25644)
COPY = (28838, 28883)
R6_B = (25511, 25534)  # b-coord rewrite zone R6; must not overlap SRC

C_OFFICIAL = 100568.4992 / 62.0
LINES = {"62Q": 81.10, "63Q": 105.56, "64Q": 129.26}


def load_ops():
    import kickmix

    circuit = kickmix.Circuit.from_file(BASELINE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def op_kind(line):
    return line.split()[0]


def main():
    B = load_ops()
    assert len(B) == 47258, len(B)
    src_ops = B[SRC[0]:SRC[1] + 1]
    copy_ops = B[COPY[0]:COPY[1] + 1]
    assert len(src_ops) == 46 and len(copy_ops) == 46
    exact = src_ops == copy_ops
    print(f"chain: 46 ops, exact text repeat: {exact}", flush=True)
    assert exact
    assert SRC[0] > R6_B[1], "chain must not overlap R1-R6 rewrite zones"
    print(f"R-zone overlap: none (R6 ends {R6_B[1]} < src {SRC[0]})", flush=True)

    # Copy cost + inventory.
    toff = 0
    cond_toff = []
    hmr_in_copy = []
    cond_phase_in_copy = []
    uncond_phase_in_copy = []
    for i in range(COPY[0], COPY[1] + 1):
        p = B[i].split()
        k = p[0]
        if k in ("CCX", "CCZ", "CSWAP"):
            toff += 1
            if "if" in p:
                cond_toff.append((i, B[i]))
        if k in ("HMR", "R"):
            hmr_in_copy.append((i, B[i]))
        if k in ("CZ", "Z", "CCZ", "Z_POW", "NEG") and "if" in p:
            cond_phase_in_copy.append((i, B[i]))
        if k in ("CZ", "Z", "NEG") and "if" not in p:
            uncond_phase_in_copy.append((i, B[i]))
    print(f"copy Toffoli-like: {toff}, conditional among them: {len(cond_toff)}", flush=True)
    print(f"HMR/R in copy: {len(hmr_in_copy)} {hmr_in_copy}", flush=True)
    print(f"conditional phase in copy: {len(cond_phase_in_copy)}", flush=True)
    for i, l in cond_phase_in_copy:
        print(f"  {i}: {l}", flush=True)
    print(f"unconditional phase (NEG/Z/CZ) in copy: {len(uncond_phase_in_copy)}", flush=True)

    # Condition-stack walk inside the copy.
    depth = 0
    min_depth = 0
    pushpop = []
    for i in range(COPY[0], COPY[1] + 1):
        k = op_kind(B[i])
        if k == "PUSH_CONDITION":
            depth += 1
            pushpop.append((i, B[i]))
        elif k == "POP_CONDITION":
            depth -= 1
            min_depth = min(min_depth, depth)
            pushpop.append((i, B[i]))
    print(f"copy stack: pushes/pops={pushpop}, net={depth}, min_depth={min_depth}", flush=True)
    stack_balanced_empty = (depth == 0 and min_depth >= 0)
    print(f"copy condition-stack balanced & empty: {stack_balanced_empty}", flush=True)

    # Full-circuit interpret: frontier, signatures, zero rows, cond env.
    need = {SRC[0] - 1, SRC[1], COPY[0] - 1, COPY[1]}
    ccxset = set(i for i in list(range(SRC[0], SRC[1] + 1))
                 + list(range(COPY[0], COPY[1] + 1)) if B[i].startswith("CCX"))
    v, _wire, snap, sig, extra = retain62.interpret(B, ccxset, need)
    sb, se = snap[SRC[0] - 1], snap[SRC[1]]
    cb, ce = snap[COPY[0] - 1], snap[COPY[1]]
    outs = [q for q in range(62) if se[q] == ce[q] and se[q] != cb[q]
            and se[q] != v.zero and se[q] != sb[q]]
    print(f"frontier outs: {outs}", flush=True)
    ss = [(i, retain62.signature_key(sig[i])) for i in range(SRC[0], SRC[1] + 1) if i in sig]
    cs = [(j, retain62.signature_key(sig[j])) for j in range(COPY[0], COPY[1] + 1) if j in sig]
    print(f"CCX sig rows src/copy: {len(ss)}/{len(cs)}", flush=True)
    sig_equal = [k for _, k in ss] == [k for _, k in cs]
    print(f"value_signature_equal: {sig_equal}", flush=True)
    first_diff = None
    if not sig_equal:
        for (i, a), (j, b_) in zip(ss, cs):
            if a != b_:
                first_diff = {"src_op": i, "src_line": B[i], "copy_op": j,
                              "copy_line": B[j], "src_key": a, "copy_key": b_}
                print(f"first sig diff: src@{i} {B[i]} key={a}", flush=True)
                print(f"                cpy@{j} {B[j]} key={b_}", flush=True)
                break
    zero_rows = [{"qubit": q, "copy_before": cb[q], "is_zero": cb[q] == v.zero}
                 for q in outs]
    print("zero-before-copy:", {q: (cb[q] == v.zero) for q in outs}, flush=True)
    zero_holds = bool(outs) and all(r["is_zero"] for r in zero_rows)
    cond_env = {"src_before": extra["cond_at"][SRC[0] - 1],
                "src_after": extra["cond_at"][SRC[1]],
                "copy_before": extra["cond_at"][COPY[0] - 1],
                "copy_after": extra["cond_at"][COPY[1]]}
    print(f"cond env: {cond_env}", flush=True)
    cond_same = (cond_env["src_before"] == cond_env["copy_before"]
                 and cond_env["src_after"] == cond_env["copy_after"])
    print(f"cond_env src==copy: {cond_same}", flush=True)

    # Lifetime evidence per frontier output.
    lives = {}
    for q in outs:
        le = retain62.lifetime_evidence(q, se[q], v.zero, SRC[1], COPY[0], COPY[1],
                                        extra["history"])
        lives[q] = {"unoverwritten": le["unoverwritten"], "reasons": le["reasons"]}
        print(f"lifetime q{q}: {le['unoverwritten']} {le['reasons']}", flush=True)

    # Barriers: span total + inside copy.
    span_barriers = [r["op"] for r in extra["barriers"] if SRC[1] < r["op"] < COPY[0]]
    print(f"HMR/R strictly inside span ({SRC[1]},{COPY[0]}): {len(span_barriers)}", flush=True)

    # Value proof probe: first-differing control pair via booleq62.
    # Same id is sufficient for equivalent; here ids differ, so count free
    # vars and only run a truth table when small (deterministic, no Z3 hang).
    proof_probe = {}
    if first_diff is not None:
        a_ctrls, _t1, _c1, _ac1 = first_diff["src_key"]
        b_ctrls, _t2, _c2, _ac2 = first_diff["copy_key"]
        # signature_key = (controls, target, condition, active_condition)
        pair = (a_ctrls[0], b_ctrls[0])
        fvars = booleq62.free_variables(v, *pair)
        proof_probe = {"compared": "src_ctrl0 vs copy_ctrl0",
                       "free_vars": len(fvars)}
        if len(fvars) <= booleq62.SMALL_CONE_LIMIT:
            res = booleq62.truth_table_equiv(v, *pair)
            proof_probe.update(res)
        else:
            proof_probe.update({"method": "truth-table", "verdict": "deferred",
                                "reason": f"{len(fvars)} free vars: unproven, no rewrite"})
        print(f"value proof probe: {proof_probe}", flush=True)

    # Backward slices inside the copy per frontier output.
    def reads_writes(line):
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q") and t[1:].isdigit()]
        if k == "X":
            return set(qs), set(qs)
        if k == "CX":
            return {qs[0]}, {qs[1]}
        if k == "CCX":
            return {qs[0], qs[1]}, {qs[2]}
        if k in ("HMR", "R"):
            return set(), {qs[0]}
        return set(), set()

    slices = {}
    for q in outs:
        needw = {q}
        used = []
        for i in range(COPY[1], COPY[0] - 1, -1):
            rd, wr = reads_writes(B[i])
            if needw & wr:
                used.append(i)
                needw = (needw - wr) | rd
        used.sort()
        slices[q] = {"ops": used, "n_ops": len(used),
                     "ccx": sum(1 for i in used if op_kind(B[i]) == "CCX"),
                     "lines": [B[i] for i in used]}
        print(f"slice q{q}: {slices[q]['n_ops']} ops, {slices[q]['ccx']} CCX: {used}",
              flush=True)

    # Borrowable zero wires across the span.
    span_mentions = set()
    for i in range(SRC[1] + 1, COPY[0]):
        for t in B[i].split()[1:]:
            if t.startswith("q") and t[1:].isdigit():
                span_mentions.add(int(t[1:]))
    quiet = [q for q in range(62) if q not in span_mentions]
    start = snap[SRC[1]]
    borrowable = [q for q in quiet if start[q] == v.zero]
    print(f"quiet wires: {len(quiet)}, borrowable zero: {borrowable}", flush=True)

    # --- Cost table (all non-baseline rows hypothetical: value+phase FAILED) ---
    C = C_OFFICIAL
    base_score = 62 * C
    fantasy_dC = float(-toff)  # delete all 13 CCX, zero cleanup: upper bound
    fantasy_dscore = round(62 * (C + fantasy_dC) - base_score, 2)
    need5pct_score = round(62 * C - 95540.0742, 2)
    rows = [
        {"retained": 0, "mode": "pay-copy", "delta_C": 0.0, "Q": 62,
         "delta_score": 0.0, "proof": "baseline"},
        {"retained": "all", "mode": "fantasy-delete-13",
         "delta_C": fantasy_dC, "Q": 62, "delta_score": fantasy_dscore,
         "cleanup": "zero (unrealistic upper bound)",
         "proof": "INAPPLICABLE(value-signature-unequal,nonzero-before-copy,"
                  "hmr-in-copy,cond-env-differ)"},
        {"retained": 1, "mode": "coherent-per-slice",
         "delta_C": -1.0, "Q": 63,
         "delta_score": round(63 * (C - 1.0) - base_score, 2),
         "cleanup": "bennett-uncompute",
         "proof": "INAPPLICABLE(same value failures; shown for scale only)"},
        {"retained": 1, "mode": "measured-per-slice",
         "delta_C": -1.0, "Q": 62,
         "delta_score": round(62 * (C - 1.0) - base_score, 2),
         "cleanup": "HMR+classical+clifford-corrections",
         "proof": "TO-PROVE(correction-coverage)+INAPPLICABLE(value failures)"},
    ]
    for r in rows:
        print(f"  {r['mode']:22s} dC={r['delta_C']:+.1f} "
              f"Q={r['Q']} dscore={r['delta_score']:+.2f} [{r['proof']}]", flush=True)
    print(f"5%-line needs dscore<={-need5pct_score:+.2f} at 62Q "
          f"(fantasy {fantasy_dscore:+.2f} is {need5pct_score/abs(fantasy_dscore):.1f}x short)",
          flush=True)

    OUT.write_text(json.dumps({
        "chain": {"src": list(SRC), "copy": list(COPY), "exact_text_repeat": exact,
                  "length_ops": 46, "copy_toffoli_like": toff,
                  "copy_conditional_toffoli": cond_toff,
                  "hmr_in_copy": [list(x) for x in hmr_in_copy],
                  "conditional_phase_in_copy": [list(x) for x in cond_phase_in_copy],
                  "unconditional_phase_in_copy": [list(x) for x in uncond_phase_in_copy],
                  "copy_stack_pushpop": pushpop, "copy_stack_net": depth,
                  "copy_stack_min_depth": min_depth,
                  "copy_stack_balanced_empty": bool(stack_balanced_empty),
                  "span_ops": COPY[0] - SRC[1] - 1,
                  "span_hmr_r": len(span_barriers),
                  "frontier": outs,
                  "value_signature_equal": sig_equal,
                  "first_signature_diff": first_diff,
                  "value_proof_probe": proof_probe,
                  "zero_before_copy": zero_rows,
                  "zero_holds": bool(zero_holds),
                  "cond_env": cond_env, "cond_env_same": bool(cond_same),
                  "lifetime": {str(q): lives[q] for q in outs},
                  "r_zone_overlap": False,
                  "wires_never_mentioned_in_span": quiet,
                  "borrowable_zero_wires": borrowable},
        "slices": {str(q): slices[q] for q in outs},
        "C_official": C,
        "threshold_lines_readme_C_units": LINES,
        "cost_table": rows,
        "fantasy_gross_C": fantasy_dC,
        "needed_5pct_dscore_62Q": -need5pct_score,
        "verdict": ("VETO on this chain (largest exact repeat, 13 CCX): value FAIL "
                    "(signature unequal at first CCX; q40/q57 nonzero before copy; "
                    "all lifetimes fail); phase/measurement FAIL (2x HMR + 3x "
                    "conditional CZ + unbalanced POP in copy; cond env b457 vs b458); "
                    "cost FAIL (fantasy -13 C = -806 score, ~6.2x short of 62Q 5% line). "
                    "No rewrite proposed; no saving claimed."),
    }, indent=2) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
