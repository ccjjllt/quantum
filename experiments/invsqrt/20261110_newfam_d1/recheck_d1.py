"""Direction D1 landing recheck on gengsr 25.2268 invsqrt (26ebf39d).

Read-only re-execution of Task 1 (Hosen census, verbatim port of the
20261108 frontier-audit `unread_ccx_before_hmr` rule + frame-depth fix from
20261110_hosen_sens) and Task 2 static bounds (A3 ladder angles vs verifier
min tolerance). The full 21x24 Simulator grid + the single official-verifier
arbitration already exist in 20261110_hosen_sens and are cited, not rerun.
"""
from __future__ import annotations

import io
import json
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

HERE = Path(__file__).parent
WORK = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt")
MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"

S1 = (8893, 16329)
A3 = (16329, 16499)
S2 = (16499, 36427)

DIAG = ("Z", "Z_POW", "CZ", "CCZ")
CLIFF_DIAG = ("Z", "CZ", "CCZ")
FRAME = ("PUSH_CONDITION", "POP_CONDITION")

A3LEVELS = [16337, 16347, 16355, 16363, 16371, 16378, 16386, 16394, 16402,
            16410, 16417, 16424, 16431, 16438, 16446, 16454, 16462, 16470,
            16478, 16486, 16493]

sys.path.insert(0, str(WORK / "data/competition/verifiers/invsqrt"))
import verify_submission_invsqrt as V  # noqa: E402


def parse_ops() -> list[str]:
    c = km.Circuit.from_file(str(NEW_KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def scan_site(ops: list[str], idx: int) -> dict:
    p = ops[idx].split()
    q = p[1]
    depth = 0
    saw_zpow = saw_cliff = False
    for j in range(idx - 1, -1, -1):
        p2 = ops[j].split()
        op2 = p2[0]
        if op2 == "POP_CONDITION":
            depth += 1
            continue
        if op2 == "PUSH_CONDITION":
            depth -= 1
            continue
        if q not in p2:
            continue
        if op2 in DIAG:
            saw_zpow = saw_zpow or (op2 == "Z_POW")
            saw_cliff = saw_cliff or (op2 in CLIFF_DIAG)
            continue
        if op2 == "CCX" and p2[3] == q:
            cond = (" if " in ops[j]) or (depth > 0)
            if cond:
                return {"class": "ccx_conditional", "ccx_idx": j,
                        "ccx_line": ops[j], "depth": depth,
                        "saw_cliff_diag": saw_cliff}
            if saw_zpow or saw_cliff:
                return {"class": "guarded", "ccx_idx": j,
                        "ccx_line": ops[j], "depth": depth}
            return {"class": "candidate", "ccx_idx": j,
                    "ccx_line": ops[j], "depth": depth}
        return {"class": "blocked", "block_op": op2, "block_idx": j}
    return {"class": "no_touch"}


def main() -> None:
    ops = parse_ops()
    assert len(ops) == 36686, len(ops)

    def cnt(reg, op):
        lo, hi = reg
        return sum(1 for i in range(lo, hi) if ops[i].split()[0] == op)

    s1_ccx = cnt(S1, "CCX")
    a3_ccx, a3_zpow = cnt(A3, "CCX"), cnt(A3, "Z_POW")
    a3_cswap, a3_hmr = cnt(A3, "CSWAP"), cnt(A3, "HMR")
    s2_ccx = cnt(S2, "CCX")
    assert s1_ccx == 365, s1_ccx
    assert (a3_ccx, a3_zpow, a3_cswap, a3_hmr) == (7, 21, 70, 24), \
        (a3_ccx, a3_zpow, a3_cswap, a3_hmr)
    assert s2_ccx == 499, s2_ccx
    assert all(ops[i].startswith("Z_POW q28 ") for i in A3LEVELS)

    # audit-compatible recount (exact 20261108 rule, no frame tracking)
    unread = guarded = 0
    for idx, l in enumerate(ops):
        parts = l.split()
        if parts[0] not in ("HMR", "R"):
            continue
        q = parts[1]
        saw = False
        for j in range(idx - 1, -1, -1):
            p2 = ops[j].split()
            if p2[0] in FRAME:
                continue
            if q not in p2:
                continue
            if p2[0] in DIAG:
                saw = True
                continue
            if p2[0] == "CCX" and p2[3] == q and (" if " not in ops[j]):
                if saw:
                    guarded += 1
                else:
                    unread += 1
            break

    # frame-corrected full census (20261110_hosen_sens rule)
    totals: dict[str, int] = {}
    by_region: dict[str, dict[str, int]] = {}
    detail = []
    for idx, l in enumerate(ops):
        if l.split()[0] not in ("HMR", "R"):
            continue
        r = scan_site(ops, idx)
        totals[r["class"]] = totals.get(r["class"], 0) + 1
        reg = ("S1" if S1[0] <= idx < S1[1]
               else "A3" if A3[0] <= idx < A3[1]
               else "S2" if S2[0] <= idx < S2[1] else "other")
        d = by_region.setdefault(reg, {})
        d[r["class"]] = d.get(r["class"], 0) + 1
        if reg in ("S1", "S2") and r["class"] in (
                "candidate", "guarded", "ccx_conditional"):
            detail.append({"hmr_idx": idx, "hmr_line": l, "region": reg, **r})

    # Task 2 static bounds: deletion shift <= ang/2 turns vs min tol
    import numpy as np

    spec = V.ProblemSpecInvSqrt.for_n_p(10)
    xs = np.array([1, 2, 3, 5, 64, 161, 1000, 3133452], dtype=np.uint64)
    _, tol = V.reference_values(spec, xs)
    min_tol = int(tol.min())
    static_rows = []
    for i in A3LEVELS:
        ang = Fraction(ops[i].split()[2])
        maxd = (int(ang.numerator) << 64) // (2 * int(ang.denominator))
        static_rows.append({"drop_idx": i,
                            "angle_turns": float(ang) / 2,
                            "max_shift_units": maxd,
                            "static_safe_all_x": bool(maxd < min_tol)})
    static_rows.sort(key=lambda r: r["angle_turns"])

    out = {
        "nops": len(ops),
        "region_gate_check": {
            "S1_CCX": s1_ccx, "A3_CCX": a3_ccx, "A3_Z_POW": a3_zpow,
            "A3_CSWAP": a3_cswap, "A3_HMR": a3_hmr, "S2_CCX": s2_ccx},
        "audit_compat_recount": {"unread": unread, "guarded": guarded},
        "frame_corrected_totals": totals,
        "by_region": by_region,
        "S1_S2_sites_of_interest": [
            {"hmr_idx": r["hmr_idx"], "hmr_line": r["hmr_line"],
             "region": r["region"], "class": r["class"],
             "ccx_idx": r.get("ccx_idx"), "ccx_line": r.get("ccx_line")}
            for r in detail],
        "n_candidates": sum(1 for r in detail if r["class"] == "candidate"),
        "expected_dscore_500_1500_reached": False,
        "A3_static_bound": {"min_tol_units": min_tol,
                            "rows_ascending": static_rows},
        "refs": {
            "full_grid": "experiments/invsqrt/20261110_hosen_sens/sens_check.json",
            "verifier_fail": "experiments/invsqrt/20261110_hosen_sens/verifier_drop16337.log"},
    }
    (HERE / "evidence.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("region_gate_check",
                                         "audit_compat_recount",
                                         "frame_corrected_totals",
                                         "by_region",
                                         "n_candidates")}, indent=1))
    print("static_two_smallest:",
          json.dumps(static_rows[:2], indent=1))


if __name__ == "__main__":
    main()
