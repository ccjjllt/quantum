"""DQI dirty-borrow study B: deep dive on 6 small-gap pairs.

Second sweep over the frontier .kmx. For each target pair (Li,Lj):
 - raw window disassembly [Li-3, Lj+3]
 - for every ancilla wire (840..891): last touch (idx, op, cond) before Li,
   first touch (idx, op, cond) after Lj  (liveness / dead-wire evidence)
 - idle-in-window ancilla set + clean subset (pristine / uncond HMR,R)
Writes artifacts/20261109_dqi_dirtyk2/b_windows.json
"""
from __future__ import annotations
import bisect
import json
from pathlib import Path

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
ART = Path("artifacts/20261109_dqi_dirtyk2")

TARGETS = [
    (52710777, 52710779),
    (53303309, 53303311),
    (52710776, 52710780),
    (52710931, 52710941),
    (56083964, 56083998),
    (57526924, 57526958),
]

VAL_OPS = ("X", "CX", "SWAP", "HMR", "R", "CCX", "CCZ", "CSWAP", "CZ")


def main():
    tset = {li for li, _ in TARGETS} | {lj for _, lj in TARGETS}
    lo_all = min(li for li, _ in TARGETS) - 3
    hi_all = max(lj for _, lj in TARGETS) + 3
    by_li = {li: lj for li, lj in TARGETS}
    wins: dict[int, list] = {li: [] for li, _ in TARGETS}
    last = {w: None for w in range(840, 892)}  # w -> [idx, op, cond]
    snap: dict[int, dict] = {}
    nxt: dict[int, dict] = {li: {} for li, _ in TARGETS}
    done_next: dict[int, set] = {li: set() for li, _ in TARGETS}
    stage = "header"
    stack: list[str] = []
    depth = 0
    with open(KMX) as f:
        for idx, raw in enumerate(f):
            if idx > hi_all and all(len(done_next[li]) >= 52 for li in by_li):
                break
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                    stage = stack[0]
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    stage = stack[0] if stack else "header"
                continue
            if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                continue
            if l.startswith("PUSH_CONDITION"):
                depth += 1
                continue
            if l.startswith("POP_CONDITION"):
                depth -= 1
                continue
            parts = l.split()
            op = parts[0]
            if len(parts) >= 3 and parts[-2] == "if":
                inline = parts[-1]
                args = parts[1:-2]
            else:
                inline = None
                args = parts[1:]
            cond = (depth > 0) or (inline is not None)
            for li, lj in TARGETS:
                if li - 3 <= idx <= lj + 3:
                    wins[li].append([idx, l])
            if op in VAL_OPS:
                touched = set()
                for tok in args:
                    if tok and tok[0] == "q":
                        try:
                            q = int(tok[1:])
                        except ValueError:
                            continue
                        if 840 <= q <= 891:
                            touched.add(q)
                for q in touched:
                    last[q] = [idx, op, cond]
                for li, lj in TARGETS:
                    if idx > lj:
                        for q in touched:
                            if q not in done_next[li]:
                                done_next[li].add(q)
                                nxt[li][q] = [idx, op, cond]
            for li in by_li:
                if idx == li and li not in snap:
                    snap[li] = {w: (list(last[w]) if last[w] else None)
                                for w in range(840, 892)}
    out = []
    for li, lj in TARGETS:
        gap = lj - li
        # member wires from window CCX lines
        mw = set()
        for idx_, l in wins[li]:
            if idx_ in (li, lj) and l.startswith("CCX"):
                p = l.split()
                a_ = [t for t in p[1:] if t[0] == "q"]
                mw.update(int(t[1:]) for t in a_)
        idle = []
        for w in range(840, 892):
            if w in mw:
                continue
            # untouched in [li,lj]? check via wins lines mentioning q{w}
            hit = any(li <= _ <= lj and
                      any(t == f"q{w}" for t in ln.split()[1:])
                      for _, ln in wins[li])
            if not hit:
                idle.append(w)
        rows = []
        for w in idle:
            lt = snap[li][w]
            nt = nxt[li].get(w)
            if lt is None:
                cls = "pristine"
            elif not lt[2] and lt[1] in ("HMR", "R"):
                cls = "hmr-zero"
            else:
                cls = f"dirty(last {lt[1]}{' cond' if lt[2] else ''}@{lt[0]})"
            rows.append({"w": w, "class": cls, "last": lt, "next": nt})
        out.append({"Li": li, "Lj": lj, "gap": gap, "members": sorted(mw),
                    "n_idleA": len(idle),
                    "n_clean": sum(1 for r in rows if r["class"] in ("pristine", "hmr-zero")),
                    "idle_detail": rows,
                    "window": wins[li]})
        print(f"Li={li} gap={gap} members={sorted(mw)} idle={len(idle)} "
              f"clean={sum(1 for r in rows if r['class'] in ('pristine','hmr-zero'))}", flush=True)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "b_windows.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote b_windows.json", flush=True)


if __name__ == "__main__":
    main()
