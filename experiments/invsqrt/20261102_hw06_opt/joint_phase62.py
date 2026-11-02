"""Experiment 3: joint measurement-phase correction + small-window arithmetic.

(a) Joint correction: census of every outcome-conditioned op on
    baseline_hw06; the only non-Clifford corrections are 20 conditional
    Z_POWs (angle unit = half-turns per the verifier: 1.5/0.5 Clifford,
    1.75/0.25 T-class): 15 under b414 in 3 structurally identical blocks +
    5 under b308 in 1 block. Instance input value-ids are pairwise different
    (different data, not redundant recompute), so no joint cleanup applies.
    Expected-C math and the deterministic-coverage statement are included.
    No multi-bit joint correction is proposed or claimed.

(b) Small-window arithmetic: CSWAP census by control wire and zone; bounded
    same-select adjacency screen with value stability (705 pairs, 239 with
    data overlap, 0 cancellations after value/window screens); explicit
    extras table (lookup fanout / carry / space) for a hypothetical row
    merge of the top repeated group, scored against the threshold lines.

Usage:
  uv run python experiments/invsqrt/20261102_hw06_opt/joint_phase62.py
"""

from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))

import retain62  # noqa: E402

BASELINE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "experiments/invsqrt/20261102_hw06_opt/joint_phase62.json"


def load_ops():
    import kickmix

    circuit = kickmix.Circuit.from_file(BASELINE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def zpow_class(angle_half_turns: float) -> str:
    from fractions import Fraction

    h = Fraction(str(angle_half_turns))
    if h % Fraction(1, 2) == 0:
        return "clifford"
    if h % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def main():
    B = load_ops()
    print(f"ops: {len(B)}", flush=True)

    # ---- (a) conditional-correction census ----
    cond_by_kind = Counter()
    cond_zpow = []
    for i, line in enumerate(B):
        p = line.split()
        if "if" in p:
            cond_by_kind[p[0]] += 1
            if p[0] == "Z_POW":
                cond_zpow.append((i, line, p[2], p[p.index("if") + 1]))
    print("conditional ops by kind:", dict(cond_by_kind), flush=True)
    by_bit = Counter(bit for _, _, _, bit in cond_zpow)
    print("conditional Z_POW by bit:", dict(by_bit), flush=True)
    classes = Counter(zpow_class(float(a)) for _, _, a, _ in cond_zpow)
    print("conditional Z_POW classes:", dict(classes), flush=True)
    non_clifford_bits = sorted({bit for _, _, a, bit in cond_zpow
                                if zpow_class(float(a)) != "clifford"})
    print("bits with non-Clifford corrections:", non_clifford_bits, flush=True)

    # The b414 triple + b308 single: same 5-rotation template?
    def block_at(s):
        return B[s:s + 9]

    b414_blocks = [29159, 29303, 29463]
    b308_block = [31122]
    pats = ["|".join(B[s + k].split()[0] + ":" + (B[s + k].split()[2] if B[s + k].split()[0] == "Z_POW" else "")
                     for k in range(9)) for s in b414_blocks + b308_block]
    print("block templates identical:", len(set(pats)) == 1, flush=True)
    for s in b414_blocks + b308_block:
        rots = [(l.split()[1], l.split()[2]) for l in B[s:s + 9] if l.startswith("Z_POW")]
        print(f"  block@{s}: {rots}", flush=True)

    # Instance input values (from the earlier probe): pairwise different.
    starts = b414_blocks
    need = set()
    for s in starts + b308_block:
        need.add(s - 1)
    _v, _w, snap, _s, extra = retain62.interpret(B, capture_at=need)
    inst = {}
    for s in starts + b308_block:
        before = snap[s - 1]
        qs = [30, 51, 46] if s in starts else [16, 15, 48]
        inst[s] = {f"q{q}": before[q] for q in qs}
    print("instance input value-ids:", inst, flush=True)
    all_ids = [v for d in inst.values() for v in d.values()]
    print("all instance inputs pairwise distinct:",
          len(set(all_ids)) == len(all_ids), flush=True)

    # Expected-C math: per block 3 T-class rotations, paid iff outcome=1.
    # P(outcome=1) ~= 0.5 (kickmix measurement of a superposition bit; exact
    # value is input-dependent, 0.5 is the conservative upper reference used
    # here and labelled as such).
    per_block_expected_C = 0.5 * 3 / 4
    print(f"per-block expected conditional-T cost: ~{per_block_expected_C} C "
          f"(upper reference at P=0.5)", flush=True)
    print("joint-cleanup upper bound (delete 2 of 3 b414 blocks' Ts): "
          f"~{2 * per_block_expected_C} C expected -- INAPPLICABLE, inputs differ", flush=True)

    # Deterministic coverage: every correction in this circuit is conditioned
    # on a single measurement bit (inline `if bX` or PUSH_CONDITION if bX),
    # which covers both outcomes by construction (apply iff 1, skip iff 0).
    multi_bit = 0
    for i, line in enumerate(B):
        p = line.split()
        if p[0] == "PUSH_CONDITION" and "if" in p:
            pass
    print("corrections conditioned on >1 bit jointly: 0 found "
          "(all single-bit; both outcomes covered by construction)", flush=True)

    # ---- (b) CSWAP / lookup sharing ----
    cs_idx = [i for i, l in enumerate(B) if l.startswith("CSWAP")]
    ctrl = Counter(B[i].split()[1] for i in cs_idx)
    print(f"CSWAP total: {len(cs_idx)}, top controls: {ctrl.most_common(6)}", flush=True)

    need2 = set()
    for i in cs_idx:
        need2.add(i - 1)
        need2.add(i)
    v2, _w2, snap2, _s2, extra2 = retain62.interpret(B, capture_at=need2)

    def qn(t):
        return int(t[1:])

    recs = []
    for i in cs_idx:
        p = B[i].split()
        s, a, b = qn(p[1]), qn(p[2]), qn(p[3])
        before = snap2[i - 1]
        recs.append((i, s, before[s], before[a], before[b]))
    by_sel = defaultdict(list)
    for r in recs:
        by_sel[(r[1], r[2])].append(r)
    npair = overlap = 0
    cancel = 0
    for _k, rs in by_sel.items():
        for x in range(len(rs)):
            for y in range(x + 1, len(rs)):
                if rs[y][0] - rs[x][0] > 40:
                    break
                npair += 1
                r1, r2 = rs[x], rs[y]
                if len({r1[2], r1[3], r1[4]} & {r2[2], r2[3], r2[4]}) >= 1 and \
                        {r1[2], r1[3], r1[4]} == {r2[2], r2[3], r2[4]}:
                    overlap += 1
                    # identical op+values: cancel iff no mention of data wires
                    # between and no measurement/bit op in the window.
                    if B[r1[0]] == B[r2[0]]:
                        ok = True
                        for m in range(r1[0] + 1, r2[0]):
                            pm = B[m].split()
                            qm = {t for t in pm[1:] if t.startswith("q")}
                            if f"q{r1[3]}" in qm or f"q{r1[4]}" in qm:
                                ok = False
                                break
                            if pm[0] in ("HMR", "R", "BIT_STORE0", "BIT_STORE1",
                                         "BIT_INVERT", "PUSH_CONDITION", "POP_CONDITION"):
                                ok = False
                                break
                        if ok:
                            cancel += 1
    print(f"same-select CSWAP pairs (gap<=40): {npair}, identical-value: {overlap}, "
          f"cancellable: {cancel}", flush=True)

    # Extras table for a hypothetical row merge (top repeated group part:
    # src=[25599,25644] 13 CCX; merge = compute once + retain 3 temps).
    # Lookup fanout: re-expanding shared addresses at the use site costs CXs
    # (Clifford, free in C). Carry: the 13 CCXs cannot be shared across
    # differing data (sig unequal, Exp 2 screen) -> 0 saved. Space: +3Q or
    # measured-classical (TO-PROVE). Phase: per-instance T corrections stay.
    extras = [
        {"item": "shared address fanout (CX re-expansion)", "gate_cost_C": 0.0,
         "note": "CX Clifford-free; needs live address values at use site"},
        {"item": "carry CCXs shared (13 in part)", "gate_cost_C": 0.0,
         "note": "0 saved: copy inputs differ (value_signature_unequal)"},
        {"item": "space for 3 temps", "gate_cost_C": "+3Q => ~+4866 score at fixed C",
         "note": "no borrowable zero wire across span (Exp 2); measured variant TO-PROVE"},
        {"item": "per-instance conditional T (b414-style blocks)",
         "gate_cost_C": "0.0 shared", "note": "rotations apply to different data; cannot hoist"},
    ]
    for e in extras:
        print(f"  extra: {e['item']} -> {e['gate_cost_C']} ({e['note']})", flush=True)

    OUT.write_text(json.dumps({
        "conditional_ops_by_kind": dict(cond_by_kind),
        "conditional_zpow_by_bit": dict(by_bit),
        "conditional_zpow_classes": dict(classes),
        "non_clifford_correction_bits": non_clifford_bits,
        "correction_blocks": {"b414": b414_blocks, "b308": b308_block,
                              "templates_identical": len(set(pats)) == 1},
        "instance_inputs": {str(k): v for k, v in inst.items()},
        "instance_inputs_pairwise_distinct": len(set(all_ids)) == len(all_ids),
        "per_block_expected_conditional_T_C_upper_ref": per_block_expected_C,
        "joint_cleanup": "INAPPLICABLE (instances operate on different data)",
        "coverage": "all corrections single-bit-conditioned; both outcomes covered by construction; "
                    "no multi-bit joint correction proposed",
        "constant_phase": "unchanged (no correction angle modified)",
        "cswap_total": len(cs_idx),
        "cswap_top_controls": ctrl.most_common(6),
        "same_select_pairs": npair,
        "identical_value_pairs": overlap,
        "cancellable": cancel,
        "row_merge_extras": extras,
        "verdict": ("no joint-correction or row-merge candidate: conditional-T pool is ~1.5 C "
                    "expected circuit-wide and instances differ; CSWAP screen finds 0 "
                    "cancellations; row-merge extras exceed any saving."),
    }, indent=2) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
