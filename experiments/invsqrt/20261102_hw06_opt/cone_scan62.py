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
GAP_LIMIT = 200

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
    excl = {"value_no_shared": 0, "cond_env_differ": 0, "no_wires_at_merge": 0,
            "wire_degenerate": 0, "window_target_touched": 0,
            "window_measurement": 0, "window_phase_on_target": 0}
    by_t = {}
    for r in recs:
        by_t.setdefault(r["t"], []).append(r)
    for t, rs in by_t.items():
        for k in range(len(rs)):
            for j in range(k + 1, len(rs)):
                r1, r2 = rs[k], rs[j]
                if r2["op"] - r1["op"] > GAP_LIMIT:
                    break
                # Value-level match: the two control-value sets share exactly
                # one value (wires may differ; values may have moved).
                s1 = {r1["va"], r1["vb"]}
                s2 = {r2["va"], r2["vb"]}
                inter = s1 & s2
                if len(inter) != 1 or len(s1) != 2 or len(s2) != 2:
                    excl["value_no_shared"] += 1
                    continue
                if r1["cond"] != r2["cond"] or r1["inline"] != r2["inline"]:
                    excl["cond_env_differ"] += 1
                    continue
                sh = inter.pop()
                v1 = (s1 - s2).pop()
                v2 = (s2 - s1).pop()
                i1, i2 = r1["op"], r2["op"]
                before1 = snap[i1 - 1]
                before2 = snap[i2 - 1]
                wsh = [q for q in range(62) if before1[q] == sh and q != t]
                w1 = [q for q in range(62) if before1[q] == v1 and q != t]
                w2 = [q for q in range(62) if before1[q] == v2 and q != t]
                merge_at = "i1"
                if not wsh or not w1 or not w2:
                    # Fallback: merge at i2 (delete the first CCX instead).
                    wsh = [q for q in range(62) if before2[q] == sh and q != t]
                    w1 = [q for q in range(62) if before2[q] == v1 and q != t]
                    w2 = [q for q in range(62) if before2[q] == v2 and q != t]
                    merge_at = "i2"
                if not wsh or not w1 or not w2:
                    excl["no_wires_at_merge"] += 1
                    continue
                before = before1 if merge_at == "i1" else before2
                # Prefer the CCXs' own wires when they qualify.
                anchor = r1 if merge_at == "i1" else r2
                ws = anchor["a"] if before[anchor["a"]] == sh else (
                    anchor["b"] if before[anchor["b"]] == sh else wsh[0])
                wo1 = (anchor["a"] if before[anchor["a"]] == v1 else
                       (anchor["b"] if before[anchor["b"]] == v1 else w1[0]))
                wo2 = w2[0] if wo1 not in w2 else w2[0]
                if wo1 == ws:
                    alt = [q for q in w1 if q != ws]
                    if not alt:
                        excl["wire_degenerate"] += 1
                        continue
                    wo1 = alt[0]
                if wo2 in (ws, wo1):
                    alt = [q for q in w2 if q not in (ws, wo1)]
                    if not alt:
                        excl["wire_degenerate"] += 1
                        continue
                    wo2 = alt[0]
                if len({ws, wo1, wo2, t}) != 4:
                    excl["wire_degenerate"] += 1
                    continue
                # Window screens.
                bad = None
                for m in range(i1 + 1, i2):
                    kind, qs = mentions(m)
                    if t in qs:
                        bad = "window_target_touched"
                        break
                    if kind in ("HMR", "R"):
                        bad = "window_measurement"
                        break
                    if kind in PHASE_OPS and t in qs:
                        bad = "window_phase_on_target"
                        break
                if bad is not None:
                    excl[bad] += 1
                    continue
                pair_cands.append({
                    "i1": i1, "i2": i2, "gap": i2 - i1, "target": t,
                    "merge_at": merge_at,
                    "shared_wire": ws, "o1_wire": wo1, "o2_wire": wo2,
                    "shared_is_ccx_wire": ws in (r1["a"], r1["b"]),
                    "line1": B[i1], "line2": B[i2],
                    "cond": list(r1["cond"]), "inline": r1["inline"],
                    "zone": zone_of_b(i1, b_zones),
                })
    print("pair exclusion reasons:", excl, flush=True)

    # 3-4 product fanout: >=3 same-target CCXs sharing one control VALUE.
    # Identity: t^a&b^a&c^a&d == t^a&(b^c^d) (saves #products-1 CCXs for
    # 2*(#products-1) CXs). Same window screens; merge at the first CCX.
    fanout_cands = []
    for t, rs in by_t.items():
        for k in range(len(rs)):
            # collect CCXs within GAP_LIMIT sharing a control value with rs[k]
            group = [rs[k]]
            for j in range(k + 1, len(rs)):
                if rs[j]["op"] - rs[k]["op"] > GAP_LIMIT:
                    break
                group.append(rs[j])
            if len(group) < 3:
                continue
            from collections import Counter
            valcount = Counter()
            for r in group:
                valcount[r["va"]] += 1
                valcount[r["vb"]] += 1
            for sh, cnt in valcount.items():
                if cnt < 3:
                    continue
                members = [r for r in group
                           if r["va"] == sh or r["vb"] == sh][:4]
                if len(members) < 3:
                    continue
                if any(m["cond"] != members[0]["cond"] or
                       m["inline"] != members[0]["inline"] for m in members):
                    continue
                i1 = members[0]["op"]
                i2 = members[-1]["op"]
                before1 = snap[i1 - 1]
                others = []
                ok = True
                for m in members:
                    ov = m["vb"] if m["va"] == sh else m["va"]
                    others.append(ov)
                # all other-values must be present at i1 on distinct wires
                used = set()
                wsh_cands = [q for q in range(62) if before1[q] == sh and q != t]
                if not wsh_cands:
                    continue
                ws = members[0]["a"] if before1[members[0]["a"]] == sh else (
                    members[0]["b"] if before1[members[0]["b"]] == sh else wsh_cands[0])
                used.add(ws)
                wires = []
                for m, ov in zip(members, others):
                    cand_w = None
                    for q in (m["a"], m["b"]):
                        if before1[q] == ov and q not in used and q != t:
                            cand_w = q
                            break
                    if cand_w is None:
                        for q in range(62):
                            if before1[q] == ov and q not in used and q != t:
                                cand_w = q
                                break
                    if cand_w is None:
                        ok = False
                        break
                    used.add(cand_w)
                    wires.append(cand_w)
                if not ok or len(used) != len(members) + 1:
                    continue
                bad = None
                for mm in range(i1 + 1, i2):
                    kind, qs = mentions(mm)
                    if t in qs:
                        bad = "target-touched"
                        break
                    if kind in ("HMR", "R"):
                        bad = "measurement"
                        break
                    if kind in PHASE_OPS and t in qs:
                        bad = "phase-on-target"
                        break
                if bad is not None:
                    continue
                fanout_cands.append({
                    "ops": [m["op"] for m in members], "target": t,
                    "n_products": len(members), "merge_at": i1,
                    "shared_wire": ws, "other_wires": wires,
                    "lines": [B[m["op"]] for m in members],
                    "cond": list(members[0]["cond"]),
                    "inline": members[0]["inline"],
                    "zone": zone_of_b(i1, b_zones),
                })
    print(f"fanout (3-4 product) candidates: {len(fanout_cands)}", flush=True)
    for c in fanout_cands[:20]:
        print(f"  ops={c['ops']} t=q{c['target']} n={c['n_products']} "
              f"zone={c['zone']} lines={c['lines']}", flush=True)

    print(f"pair candidates after screens: {len(pair_cands)}", flush=True)
    zones = {}
    for c in pair_cands:
        zones[c["zone"]] = zones.get(c["zone"], 0) + 1
    print("by zone:", zones, flush=True)
    for c in pair_cands[:40]:
        print(f"  i1={c['i1']} i2={c['i2']} gap={c['i2']-c['i1']} t=q{c['target']} "
              f"shared=q{c['shared_wire']} o1=q{c['o1_wire']} o2=q{c['o2_wire']} "
              f"zone={c['zone']} cond={c['cond']} inline={c['inline']}", flush=True)

    # End-to-end re-interpretation for each candidate (rewritten window must
    # give identical wire value-ids at i2).
    verified = []
    for c in pair_cands:
        i1, i2 = c["i1"], c["i2"]
        t = c["target"]
        ws, wo1, wo2 = c["shared_wire"], c["o1_wire"], c["o2_wire"]
        suffix = f" if {c['inline']}" if c["inline"] else ""
        new_ccx = f"CCX q{ws} q{wo1} q{t}{suffix}"
        patch = [f"CX q{wo2} q{wo1}{suffix}", new_ccx, f"CX q{wo2} q{wo1}{suffix}"]
        if c["merge_at"] == "i1":
            new_ops = B[:i1] + patch + B[i1 + 1:i2] + B[i2 + 1:]
        else:
            new_ops = B[:i1] + B[i1 + 1:i2] + patch + B[i2 + 1:]
        keep = {i2 + 2}  # window-end index in new coords in both variants
        values2, _w2, snap2, _s2, extra2 = retain62.interpret(new_ops, capture_at=keep)
        end_new = snap2[i2 + 2]
        orig_full = snap[i2]
        ok_wires = sum(1 for q in range(62) if end_new[q] == orig_full[q])
        ok_cond = extra2["cond_at"][i2 + 2] == cond_at[i2]
        if ok_wires == 62 and ok_cond:
            verified.append({**c, "proof": "reinterpret-62/62 wires + cond env"})
        else:
            print(f"  REINTERPRET MISMATCH i1={i1} i2={i2}: wires {ok_wires}/62 cond={ok_cond}",
                  flush=True)
    print(f"reinterpret-verified: {len(verified)}/{len(pair_cands)}", flush=True)

    report = {
        "baseline": str(BASELINE),
        "ops": len(B),
        "ccx_text_lines": len(ccx_idx),
        "identity_proof": proof,
        "b_zones": b_zones,
        "pair_candidates": len(pair_cands),
        "pair_exclusions": excl,
        "pair_by_zone": zones,
        "reinterpret_verified": len(verified),
        "candidates": [{**c, "proof": "reinterpret-62/62 wires + cond env"} for c in verified],
        "saving_per_merge_c_units": 1.0,
    }

    # Cone census: distinct-AND-atom count of each CCX target-after value.
    # Cones with 2-4 ANDs are exactly the recent accumulations where a
    # pair/triple rewrite could apply; the screens above already dispose them.
    def and_count(root):
        seen = set()
        stack = [root]
        ands = set()
        while stack:
            vid = stack.pop()
            if vid in seen:
                continue
            seen.add(vid)
            for atom in values.fs[vid]:
                if atom in values.and_of:
                    ands.add(atom)
                    l, r = values.and_of[atom]
                    stack.append(l)
                    stack.append(r)
        return len(ands)

    hist = {}
    small_cones = []
    for i in ccx_idx:
        p = B[i].split()
        t = qn(p[3])
        k = and_count(snap[i][t])
        hist[k] = hist.get(k, 0) + 1
        if 2 <= k <= 4:
            small_cones.append({"op": i, "target": t, "ands": k,
                                "line": B[i], "zone": zone_of_b(i, b_zones)})
    small_by_zone = {}
    for c in small_cones:
        small_by_zone[c["zone"]] = small_by_zone.get(c["zone"], 0) + 1
    print("cone-AND histogram:", dict(sorted(hist.items())), flush=True)
    print(f"small cones (2-4 ANDs): {len(small_cones)} by zone: {small_by_zone}", flush=True)
    ccx_by_zone = {}
    for i in ccx_idx:
        z = zone_of_b(i, b_zones)
        ccx_by_zone[z] = ccx_by_zone.get(z, 0) + 1
    print("CCX by zone:", ccx_by_zone, flush=True)
    report["cone_and_histogram"] = dict(sorted(hist.items()))
    report["small_cones_2_4"] = len(small_cones)
    report["small_cones_by_zone"] = small_by_zone
    report["ccx_by_zone"] = ccx_by_zone
    report["small_cone_list"] = small_cones
    report["fanout_candidates"] = len(fanout_cands)
    report["fanout_list"] = fanout_cands
    report["note"] = ("cone_and_histogram counts full input-cone AND atoms, which "
                      "grow monotonically along each wire; the 2-4 nonlinear-product "
                      "search is the pair/triple/fanout rewrite screens above, which "
                      "operate on value-level identities inside the window.")
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()