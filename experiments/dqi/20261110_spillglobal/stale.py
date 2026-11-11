"""Victim stale-|0> check for clean-shape candidates.

For full-window replay, the rewritten victim keeps its PRE-window value S
(the R/HMR kill moves to the borrow). Sound downstream iff S = |0|, i.e. the
victim's last VALUE-affecting op before b is its R/HMR birth (only
control/phase reads since). Role-aware tracking (same roles as
spillmulti/search.py): X/CX-t/CCX-t/SWAP/CSWAP-all/R/HMR write; CX-t...;
CZ/Z/CCZ phase-only.

Single forward pass to max candidate b. Snapshots last value-affect at each b.
Writes artifacts/20261110_spillglobal/stale.json (candidate -> victim liveness).
"""
from __future__ import annotations

import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillglobal")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
N_Q = 892


def writers(op, qs):
    if op == "X":
        return [qs[0]]
    if op == "CX":
        return [qs[1]]
    if op in ("CCX", "CCX_CARRY"):
        return [qs[2]]
    if op in ("SWAP", "CSWAP"):
        return list(qs)
    if op in ("R", "HMR"):
        return [qs[0]]
    return []


def main():
    scan = json.load(open(ART / "scan.json"))
    cands = [o for o in scan if o["k"] is not None and o["n_cond_in_win"] == 0
             and o["n_hmr_in_win"] == 1 and o["n_borrow_hmr"] > 0]
    by_b = {o["b"]: o for o in cands}
    maxb = max(o["b"] for o in cands)
    last_aff_op = [""] * N_Q
    last_aff_idx = [-1] * N_Q
    snap = {}
    op_idx = -1
    with open(KMX, errors="replace") as f:
        for raw in f:
            l = raw.rstrip("\n")
            if not l or l.startswith(SKIP):
                continue
            op_idx += 1
            if op_idx > maxb:
                break
            if op_idx in by_b:
                o = by_b[op_idx]
                v = int(o["victim"][1:])
                snap[o["block"]] = [last_aff_op[v], last_aff_idx[v]]
            parts = l.split()
            op = parts[0]
            if op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                      "PUSH_CONDITION", "POP_CONDITION"):
                continue
            toks = [t for t in parts[1:] if t.startswith("q") and t[1:].isdigit()]
            qs = [int(t[1:]) for t in toks if 0 <= int(t[1:]) < N_Q]
            if not qs:
                continue
            if op in ("X", "R", "HMR", "CX", "CCX", "CCX_CARRY", "SWAP", "CSWAP"):
                ws = writers(op, [f"q{q}" for q in qs])
                for w in ws:
                    qi = int(w[1:])
                    last_aff_op[qi] = op
                    last_aff_idx[qi] = op_idx
            elif op in ("CZ", "Z", "CCZ"):
                pass
            else:
                for q in qs:
                    last_aff_op[q] = op
                    last_aff_idx[q] = op_idx
    out = {}
    for o in cands:
        aff, idx = snap[o["block"]]
        out[str(o["block"])] = {"L": o["L"], "victim": o["victim"],
                                 "last_value_affect_op": aff,
                                 "last_value_affect_idx": idx,
                                 "stale_zero": aff in ("R", "HMR")}
    (ART / "stale.json").write_text(json.dumps(out, indent=1) + "\n")
    n0 = sum(1 for v in out.values() if v["stale_zero"])
    print(f"stale-|0> victims: {n0}/{len(out)}")
    for b, v in out.items():
        if v["stale_zero"]:
            print(f"  blk{b} L={v['L']} v={v['victim']} lastaff={v['last_value_affect_op']}@{v['last_value_affect_idx']}")


if __name__ == "__main__":
    main()
