"""s4_stable.py: control-stability screen for the 147 small-gap structural pairs.

For each pair (Li,Lj,gap) from dirtyk2 a_smallgap.json:
- fetch exact Li/Lj lines (expect unconditional CCX),
- determine literal controls (a1,b1)/(a2,b2), targets t1/t2,
- check structural-vs-literal relation,
- check NO writes to {a1,b1} (compute literals) in (Li, Lj+1] (mid lines only,
  Lj itself only reads a/b as controls),
- check Li/Lj unconditional, mid lines: record any touching a1/b1/t1/t2.

Writes artifacts/20261109_dqi_decoder_struct/s4_stable.json
"""
from __future__ import annotations
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
SMALLGAP = Path("artifacts/20261109_dqi_dirtyk2/a_smallgap.json")
OUT = Path("artifacts/20261109_dqi_decoder_struct/s4_stable.json")

Q = lambda n: f"q{n}"


def load_window(lines_needed):
    """Load only needed lines by index (0-based)."""
    want = set(lines_needed)
    got = {}
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            if idx in want:
                got[idx] = raw.strip()
                if len(got) == len(want):
                    break
    return got


def written_wires(op, args):
    if op == "CCX":
        return args[2:3]
    if op == "CX":
        return args[1:2]
    if op in ("X", "HMR", "R"):
        return args[0:1]
    if op == "SWAP":
        return args[0:2]
    if op == "CSWAP":
        return args[1:3]
    return []


def main() -> None:
    sg = json.loads(SMALLGAP.read_text())
    pairs = sg["pairs"]
    need = set()
    for p in pairs:
        for i in range(p["Li"], p["Lj"] + 1):
            need.add(i)
    print(f"loading {len(need)} lines...", flush=True)
    txt = load_window(need)
    feas = []
    for p in pairs:
        Li, Lj = p["Li"], p["Lj"]
        l1, l2 = txt[Li], txt[Lj]
        rec = {"Li": Li, "Lj": Lj, "gap": p["gap"], "wires": p["wires"],
               "L1": l1[:70], "L2": l2[:70]}
        p1, p2 = l1.split(), l2.split()
        ok1 = (p1[0] == "CCX" and not ("if" in p1))
        ok2 = (p2[0] == "CCX" and not ("if" in p2))
        rec["both_uncond_ccx"] = bool(ok1 and ok2)
        if not (ok1 and ok2):
            rec["feasible"] = False
            rec["reason"] = "not both unconditional CCX"
            feas.append(rec)
            continue
        a1, b1, t1 = p1[1], p1[2], p1[3]
        a2, b2, t2 = p2[1], p2[2], p2[3]
        rec.update({"a1": a1, "b1": b1, "t1": t1, "a2": a2, "b2": b2, "t2": t2,
                    "same_literal": {a1, b1} == {a2, b2}})
        # stability of compute literals {a1,b1} over (Li, Lj]
        bad = []
        mid_ops = []
        for i in range(Li + 1, Lj + 1):
            s = txt[i]
            mid_ops.append(s[:70])
            q = s.split()
            o = q[0]
            if o in ("PUSH_CONDITION", "POP_CONDITION", "INFO_TAG"):
                bad.append((i, s[:60], "cond-boundary"))
                continue
            if len(q) >= 3 and q[-2] == "if":
                args = q[1:-2]
                cond_write = True
            else:
                args = q[1:]
                cond_write = False
            for w in written_wires(o, args):
                if w in (a1, b1):
                    bad.append((i, s[:60], "conditional" if cond_write else "unconditional"))
        rec["mid_ops"] = mid_ops
        rec["control_hits"] = bad
        rec["feasible"] = (len(bad) == 0)
        feas.append(rec)
    n_f = sum(1 for r in feas if r["feasible"])
    n_same = sum(1 for r in feas if r.get("same_literal") and r["feasible"])
    out = {"n_pairs": len(feas), "n_feasible": n_f,
           "n_feasible_same_literal": n_same,
           "n_feasible_struct_only": n_f - n_same,
           "pairs": feas}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"feasible: {n_f}/{len(feas)} (same-literal: {n_same})")
    for r in feas:
        if r["feasible"]:
            print(f'  Li={r["Li"]} Lj={r["Lj"]} gap={r["gap"]} {r["a1"]},{r["b1"]}->{r["t1"]} / {r["a2"]},{r["b2"]}->{r["t2"]} same={r["same_literal"]}')
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
