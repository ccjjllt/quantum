"""Hosen erasure census on gengsr 25.2268 invsqrt (26ebf39d), S1 + S2.

Reuses the 20261108 frontier-audit `unread_ccx_before_hmr` rule:
for each HMR/R on line q, scan back to the nearest op touching q
(skipping PUSH/POP_CONDITION frame lines and diagonal Z/Z_POW/CZ/CCZ,
noting any Z_POW seen); if that nearest touch is an unconditional CCX
with target q -> candidate (unread), or guarded if a Z_POW was skipped.

Improvement vs the audit version: track PUSH_CONDITION frame depth so a
CCX inside a conditional frame is not misclassified as unconditional.

Hosen rewrite economics per site (unconditional, executed once/shot):
  CCX (1 Toffoli-like) -> HMR + conditional CZ (both free)
  => net -1 Toffoli-like executed per shot => dScore = -62 at Q=62.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import kickmix as km

MAIN = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
NEW_KMB = MAIN / "artifacts/20261110_gengsr_252268/release/invsqrt.kmb"
OUT = Path(__file__).parent / "hosen_census.json"

S1 = (8893, 16329)
A3 = (16329, 16499)
S2 = (16499, 36427)

DIAG = ("Z", "Z_POW", "CZ", "CCZ")
CLIFF_DIAG = ("Z", "CZ", "CCZ")  # audit guard rule: any diagonal touch guards
FRAME = ("PUSH_CONDITION", "POP_CONDITION")


def parse_ops(kmb_path: Path) -> list[str]:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def in_region(idx: int, reg: tuple[int, int]) -> bool:
    return reg[0] <= idx < reg[1]


def scan_site(ops: list[str], idx: int) -> dict:
    """Backward scan from HMR/R at idx. Returns classification dict."""
    p = ops[idx].split()
    q = p[1]
    hmr_cond = (" if " in ops[idx])
    saw_zpow = False
    saw_cliff = False
    guard_angles: list[str] = []
    depth = 0  # conditional-frame depth (POP seen while scanning back)
    for j in range(idx - 1, -1, -1):
        l = ops[j]
        p2 = l.split()
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
            if op2 == "Z_POW":
                guard_angles.append(p2[2] if len(p2) > 2 else "?")
            continue
        if op2 == "CCX" and p2[3] == q:
            cond = (" if " in l) or (depth > 0)
            if cond:
                return {"class": "ccx_conditional", "ccx_idx": j,
                        "ccx_line": l, "hmr_cond": hmr_cond,
                        "saw_zpow": saw_zpow, "saw_cliff_diag": saw_cliff,
                        "guard_angles": guard_angles, "depth": depth}
            if saw_zpow or saw_cliff:
                return {"class": "guarded", "ccx_idx": j,
                        "ccx_line": l, "hmr_cond": hmr_cond,
                        "saw_zpow": saw_zpow, "saw_cliff_diag": saw_cliff,
                        "guard_angles": guard_angles, "depth": depth,
                        "guard_kind": ("zpow" if saw_zpow else "cliff_diag")}
            return {"class": "candidate", "ccx_idx": j,
                    "ccx_line": l, "hmr_cond": hmr_cond,
                    "saw_zpow": False, "guard_angles": [],
                    "depth": depth}
        return {"class": "blocked", "block_idx": j, "block_line": l,
                "block_op": op2, "hmr_cond": hmr_cond,
                "saw_zpow": saw_zpow, "guard_angles": guard_angles,
                "depth": depth}
    return {"class": "no_touch", "hmr_cond": hmr_cond,
            "saw_zpow": saw_zpow, "guard_angles": guard_angles}


def main() -> None:
    ops = parse_ops(NEW_KMB)
    assert len(ops) == 36686, len(ops)
    sites = []
    for idx, l in enumerate(ops):
        if l.split()[0] not in ("HMR", "R"):
            continue
        r = scan_site(ops, idx)
        r["hmr_idx"] = idx
        r["hmr_line"] = l
        r["region"] = ("S1" if in_region(idx, S1)
                       else "A3" if in_region(idx, A3)
                       else "S2" if in_region(idx, S2) else "other")
        sites.append(r)

    # audit-compatible recount (no frame tracking): replicate exact audit fn
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

    # S1 unconditional-CCX exclusion breakdown (forward scan from each CCX)
    s1_ccx, s1_cond_ccx = 0, 0
    fwd: dict[str, int] = {}
    for i in range(*S1):
        p = ops[i].split()
        if p[0] != "CCX":
            continue
        if " if " in ops[i]:
            s1_cond_ccx += 1
            fwd["conditional_inline"] = fwd.get("conditional_inline", 0) + 1
            continue
        s1_ccx += 1
        q = p[3]
        fate = "no_later_touch"
        seen_zpow = seen_cliff = False
        for j in range(i + 1, len(ops)):
            l2 = ops[j]
            p2 = l2.split()
            if p2[0] in FRAME or q not in p2:
                continue
            if p2[0] in DIAG:
                seen_zpow = seen_zpow or (p2[0] == "Z_POW")
                seen_cliff = seen_cliff or (p2[0] in CLIFF_DIAG)
                continue
            if p2[0] in ("HMR", "R"):
                # first non-diagonal touch is the measurement: candidate
                # iff no diagonal phase was imprinted in between
                if seen_zpow:
                    fate = "hmr_guarded_zpow"
                elif seen_cliff:
                    fate = "hmr_guarded_cliff_diag"
                else:
                    fate = "hmr_unread_candidate"
                break
            fate = f"blocked_by_{p2[0]}"
            break
        fwd[fate] = fwd.get(fate, 0) + 1

    by_region: dict[str, dict[str, int]] = {}
    for r in sites:
        d = by_region.setdefault(r["region"], {})
        d[r["class"]] = d.get(r["class"], 0) + 1

    detail = [r for r in sites if r["region"] in ("S1", "S2")
              and r["class"] in ("candidate", "guarded", "ccx_conditional")]
    cands = [r for r in sites if r["class"] == "candidate"]
    per_site_net_toffoli = -1
    per_site_score = -62  # Q=62, unconditional single execution
    total = len(cands) * per_site_score

    out = {
        "nops": len(ops),
        "audit_compat_recount": {"unread": unread, "guarded": guarded},
        "frame_corrected_totals": {
            c: sum(1 for r in sites if r["class"] == c)
            for c in ("candidate", "guarded", "ccx_conditional",
                      "blocked", "no_touch")},
        "by_region": by_region,
        "S1_ccx_breakdown": {"unconditional": s1_ccx,
                             "conditional_inline": s1_cond_ccx,
                             "forward_fate": fwd},
        "S1_S2_sites_of_interest": detail,
        "all_candidates": cands,
        "economics": {"per_site_net_toffoli_like": per_site_net_toffoli,
                      "per_site_dscore_Q62": per_site_score,
                      "n_candidates": len(cands),
                      "total_expected_dscore": total,
                      "band_500_1500_reached": bool(500 <= -total <= 1500)},
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in
                      ("audit_compat_recount", "frame_corrected_totals",
                       "by_region", "S1_ccx_breakdown", "economics")}, indent=1))
    print("detail_sites:", len(detail))


if __name__ == "__main__":
    main()
