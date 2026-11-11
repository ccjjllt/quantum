"""spillglobal scan: victim-window census for all 238 long blocks.

For each long block [L,R] (op coords, from longblocks.json): victim R is at
op L-1 (verified: 238/238 are `R qV`). Find kill = first `HMR qV` after b=L-1.
At b snapshot last-ANY-touch per qubit; borrow candidates = qubits untouched
in [b..k] whose last touch before b is an R/HMR birth (strict q20: gap clean by
construction). HMR-born borrows preferred (task requirement).

Also records: victim touch roles, paid count, HMR count, conditionals in
window, full window touch set (file coords, for interference census), kill
bit, and the NEXT touch of victim after kill (must be R/HMR rebirth for the
full-window-replay shape to be sound downstream).

Single forward pass to EOF. Writes artifacts/20261110_spillglobal/scan.json.
Read-only w.r.t. inputs.
"""
from __future__ import annotations

import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillglobal")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}
N_Q = 892


def qtoks(parts):
    out = []
    for p in parts[1:]:
        if p == "if":
            break
        if p.startswith("q") and p[1:].isdigit():
            out.append(p)
    return out


def main():
    ART.mkdir(parents=True, exist_ok=True)
    lb = json.load(open("artifacts/20261110_exactlive/longblocks.json"))
    rows = lb["rows"]
    # state per block index
    st = []
    for r in rows:
        st.append({"L": r["L"], "R": r["R"], "span": r["span"],
                   "b": r["L"] - 1, "victim": None, "F_B": None,
                   "phase": 0, "snap_op": None, "snap_kind": None,
                   "win_touch": set(), "victim_hits": [],
                   "victim_roles": {}, "paid": 0, "hmrs": [],
                   "conds": 0, "k": None, "F_K": None, "kill_bit": None,
                   "next_touch": None})
    by_b = {s["b"]: i for i, s in enumerate(st)}
    victim_of = {}  # qnum -> block idx currently in window (phase 1)

    last_op = [""] * N_Q       # last ANY-touch op kind per qubit
    last_idx = [-1] * N_Q      # its op index

    op_idx = -1
    file_idx = -1
    active = set()
    retired = 0
    with open(KMX, errors="replace") as f:
        for raw in f:
            file_idx += 1
            l = raw.rstrip("\n")
            if not l or l.startswith(SKIP):
                continue
            op_idx += 1
            parts = l.split()
            op = parts[0]
            if op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                      "PUSH_CONDITION", "POP_CONDITION"):
                continue
            toks = qtoks(parts)
            qs = [int(t[1:]) for t in toks if 0 <= int(t[1:]) < N_Q]

            # block starts at its b
            if op_idx in by_b:
                i = by_b[op_idx]
                s = st[i]
                assert op == "R", (i, op_idx, l[:60])
                assert len(qs) == 1, (i, l[:60])
                s["victim"] = qs[0]
                s["F_B"] = file_idx
                s["snap_op"] = list(last_op)
                s["snap_kind"] = list(last_idx)
                s["phase"] = 1
                active.add(i)
                victim_of[qs[0]] = i

            # in-window accounting
            done = []
            for i in list(active):
                s = st[i]
                if op_idx < s["b"]:
                    continue
                if s["phase"] == 1:
                    for q in qs:
                        s["win_touch"].add(q)
                    if s["victim"] in qs:
                        s["victim_hits"].append(op_idx)
                        s["victim_roles"][op] = s["victim_roles"].get(op, 0) + 1
                    if op in PAID:
                        s["paid"] += 1
                    if op == "HMR":
                        for q in qs:
                            if q == s["victim"]:
                                s["hmrs"].append(op_idx)
                    if " if " in l:
                        s["conds"] += 1
                    # kill = first HMR of victim after b (excludes b itself: b is R)
                    if op == "HMR" and s["victim"] in qs and op_idx > s["b"]:
                        s["k"] = op_idx
                        s["F_K"] = file_idx
                        s["kill_bit"] = parts[2] if len(parts) > 2 else "?"
                        s["phase"] = 2
                        victim_of.pop(s["victim"], None)
                elif s["phase"] == 2 and s["next_touch"] is None:
                    if s["victim"] in qs:
                        s["next_touch"] = [op_idx, file_idx, l[:80]]
                        s["phase"] = 3
                        retired += 1
            if active and retired == len(st):
                break
            # drop fully retired from active
            for i in list(active):
                if st[i]["phase"] == 3:
                    active.discard(i)

            for q in qs:
                last_op[q] = op
                last_idx[q] = op_idx

    out = []
    for i, s in enumerate(st):
        cands = []
        if s["k"] is not None:
            snap_op, snap_idx = s["snap_op"], s["snap_kind"]
            for q in range(N_Q):
                if q in s["win_touch"]:
                    continue
                if snap_op[q] in ("R", "HMR"):
                    cands.append({"q": f"q{q}", "birth_kind": snap_op[q],
                                  "birth_op": snap_idx[q],
                                  "gap_ops": s["b"] - snap_idx[q]})
        hmr_c = [c for c in cands if c["birth_kind"] == "HMR"]
        hmr_c.sort(key=lambda c: c["gap_ops"])
        out.append({"block": i, "L": s["L"], "R": s["R"], "span": s["span"],
                    "victim": f"q{s['victim']}" if s["victim"] is not None else None,
                    "b": s["b"], "k": s["k"], "F_B": s["F_B"], "F_K": s["F_K"],
                    "win_len_ops": (s["k"] - s["b"]) if s["k"] is not None else None,
                    "kill_bit": s["kill_bit"],
                    "n_victim_hits": len(s["victim_hits"]),
                    "victim_roles": s["victim_roles"],
                    "paid_in_win": s["paid"], "n_hmr_in_win": len(s["hmrs"]),
                    "n_cond_in_win": s["conds"],
                    "n_win_touch_qubits": len(s["win_touch"]),
                    "n_borrow_strict": len(cands),
                    "n_borrow_hmr": len(hmr_c),
                    "borrows_hmr": hmr_c[:12],
                    "next_victim_touch": s["next_touch"]})
    # window touch sets saved separately (file-coord sets not JSON-friendly as sets)
    (ART / "scan.json").write_text(json.dumps(out, indent=1) + "\n")

    good = [o for o in out if o["k"] is not None and o["n_cond_in_win"] == 0
            and o["n_hmr_in_win"] == 1 and o["n_borrow_hmr"] > 0
            and o["next_victim_touch"] is not None
            and o["next_victim_touch"][2].split()[0] in ("R", "HMR")]
    print(f"blocks with clean full-window shape + HMR borrow + dead-after victim: "
          f"{len(good)}/{len(out)}")
    for o in good:
        print(f"  blk{o['block']} L={o['L']} span={o['span']} v={o['victim']} "
              f"winops={o['win_len_ops']} roles={o['victim_roles']} paid={o['paid_in_win']} "
              f"kill={o['kill_bit']} hmr_borrows={o['n_borrow_hmr']} "
              f"next={o['next_victim_touch'][2][:40]} F=[{o['F_B']}..{o['F_K']}]")
    bad_next = [o for o in out if o["k"] is not None and o["next_victim_touch"] is not None
                and o["next_victim_touch"][2].split()[0] not in ("R", "HMR")]
    print(f"victim NOT dead-after (next touch not R/HMR): {len(bad_next)}")
    for o in bad_next[:10]:
        print(f"  blk{o['block']} v={o['victim']} next={o['next_victim_touch'][2][:60]}")


if __name__ == "__main__":
    main()
