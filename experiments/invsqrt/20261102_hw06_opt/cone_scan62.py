"""Experiment 1: local Boolean resynthesis on baseline_hw06.kmb.

Searches CCX-centred cones with 2 (pair merge) or 3 (Ehan 3-to-2) nonlinear
products, prioritising B-segment delayed carry, inverse_B and curvature
recovery zones. Every candidate must pass:

  * Boolean proof: the abstract identity is a tautology (checked once via
    booleq62: distinct value-ids, truth table -> EQUIVALENT), plus
    machine-checked side conditions on the real circuit (shared-control and
    other-control value-id equality, same condition environment, target
    untouched between the two CCXs, no HMR/R in the window, no phase gate
    reading the target inside the window);
  * end-to-end re-interpretation: the rewritten op list yields identical
    wire value-ids at the window end;
  * cost: verifier slice (limited --max-x/--shots-per-x, fixed seed) on the
    rewritten circuit vs the baseline slice.

Temporary-AND, HMR cleanup, Ahmed cache and Ehan merges already in the
baseline are NOT re-counted: candidates overlapping the R1-R6 zones are
flagged and only genuinely new merges count.

Usage:
  uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/cone_scan62.py
"""

from __future__ import annotations

import difflib
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
AHMED = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt/ahmed.kmb"
OUT = ROOT / "experiments/invsqrt/20261102_hw06_opt/cone_scan62.json"
GAP_LIMIT = 500

# Macro segment boundaries in ahmed (a-coords) coordinates, from REPORT.md.
A_ZONES = [
    ("Hphase", 15244, 16127),
    ("A", 16127, 20738),
    ("B", 20738, 25630),
    ("Lphase", 25630, 28726),
    ("inverse_B", 28726, 32226),
    ("inverse_A", 32226, 43870),
    ("unlookup", 43870, 46706),
    ("tail", 46706, 47201),
]

PHASE_OPS = ("Z", "CZ", "CCZ", "Z_POW")


def load_ops(path):
    import kickmix

    circuit = kickmix.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def qn(token):
    return int(token[1:])


def build_a_to_b(A, B):
    """Piecewise a->b map from the difflib alignment (equal blocks only)."""
    sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
    table = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                table[i1 + d] = j1 + d
    return table


def zone_of_b(b, b_zones):
    for name, lo, hi in b_zones:
        if lo <= b < hi:
            return name
    return "unknown"


def main():
    A = load_ops(AHMED)
    B = load_ops(BASELINE)
    print(f"ahmed ops={len(A)} baseline ops={len(B)}", flush=True)
    a2b = build_a_to_b(A, B)
    b_zones = []
    for name, lo, hi in A_ZONES:
        assert lo in a2b and (hi in a2b or hi == len(A)), f"boundary {name} not aligned"
        b_zones.append((name, a2b[lo], a2b.get(hi, len(B))))
    print("b-coord zones:", b_zones, flush=True)

    # Abstract identity proof, done once: t^a&b^a&c == t^a&(b^c).
    v = retain62.Values()
    ta = v.vid(frozenset([100]))
    aa = v.vid(frozenset([101]))
    ba = v.vid(frozenset([102]))
    ca = v.vid(frozenset([103]))
    old = v.xor(v.xor(ta, v.and_(aa, ba)), v.and_(aa, ca))
    new = v.xor(ta, v.and_(aa, v.xor(ba, ca)))
    assert old != new
    proof = booleq62.equiv(v, old, new)
    print("pair-merge identity:", proof, flush=True)
    assert proof["verdict"] == "equivalent"

    # Full-circuit interpret with snapshots around every CCX.
    need = set()
    ccx_idx = [i for i, l in enumerate(B) if l.split()[0] == "CCX"]
    for i in ccx_idx:
        need.add(i - 1)
        need.add(i)
    values, _wire, snap, _sig, extra = retain62.interpret(B, capture_at=need)
    cond_at = extra["cond_at"]
    history_note = f"interpreted {len(B)} ops, {len(ccx_idx)} CCX"

    recs = []
    for i in ccx_idx:
        p = B[i].split()
        a, b, t = qn(p[1]), qn(p[2]), qn(p[3])
        inl = p[p.index("if") + 1] if "if" in p else None
        before = snap[i - 1]
        recs.append({"op": i, "a": a, "b": b, "t": t,
                     "va": before[a], "vb": before[b], "vt": before[t],
                     "cond": tuple(cond_at[i - 1]), "inline": inl})

    # Mentions per op for the no-touch screen.
    def mentions(i):
        p = B[i].split()
        qs = set()
        for tok in p[1:]:
            if tok.startswith("q") and tok[1:].isdigit():
                qs.add(int(tok[1:]))
        return p[0], qs

    pair_cands = []
    by_t = {}
    for r in recs:
        by_t.setdefault(r["t"], []).append(r)
    for t, rs in by_t.items():
        for k in range(len(rs)):
            for j in range(k + 1, len(rs)):
                r1, r2 = rs[k], rs[j]
                if r2["op"] - r1["op"] > GAP_LIMIT:
                    break
                # Shared control: same wire + same value; others value-equal.
                shared = None
                other1 = other2 = None
                if r1["a"] == r2["a"] and r1["va"] == r2["va"] and r1["b"] != r2["b"]:
                    shared, other1, other2 = "a", "b", "b"
                elif r1["a"] == r2["b"] and r1["va"] == r2["vb"] and r1["b"] != r2["a"]:
                    shared, other1, other2 = "a", "b", "a"
                elif r1["b"] == r2["a"] and r1["vb"] == r2["va"] and r1["a"] != r2["b"]:
                    shared, other1, other2 = "b", "b", "a"
                elif r1["b"] == r2["b"] and r1["vb"] == r2["vb"] and r1["a"] != r2["a"]:
                    shared, other1, other2 = "b", "a", "a"
                else:
                    continue
                w_shared = r1[shared]
                w_o1 = r1[other1]
                w_o2 = r2[other2]
                if len({w_shared, w_o1, w_o2, t}) != 4:
                    continue
                if r1["vb" if other1 == "b" else "va"] != r2["vb" if other2 == "b" else "va"]:
                    continue
                if r1["cond"] != r2["cond"] or r1["inline"] != r2["inline"]:
                    continue
                i1, i2 = r1["op"], r2["op"]
                # Window screens.
                bad = None
                for m in range(i1 + 1, i2):
                    kind, qs = mentions(m)
                    if t in qs:
                        bad = f"target-touched@{m}:{B[m]}"
                        break
                    if kind in ("HMR", "R"):
                        bad = f"measurement-in-window@{m}:{B[m]}"
                        break
                    if kind in PHASE_OPS and t in qs:
                        bad = f"phase-on-target@{m}:{B[m]}"
                        break
                if bad is not None:
                    continue
                for m in (i1, i2):
                    kind, _ = mentions(m)
                    if kind in ("HMR", "R"):
                        bad = "endpoint-measurement"
                        break
                if bad is not None:
                    continue
                pair_cands.append({
                    "i1": i1, "i2": i2, "gap": i2 - i1, "target": t,
                    "shared_wire": w_shared, "o1_wire": w_o1, "o2_wire": w_o2,
                    "shared_pos": shared,
                    "line1": B[i1], "line2": B[i2],
                    "cond": list(r1["cond"]), "inline": r1["inline"],
                    "zone": zone_of_b(i1, b_zones),
                }

...[truncated 7373 chars]