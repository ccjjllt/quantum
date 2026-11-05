"""File-wide CCX-pair peephole with exact commutation guard.

P=CCX(a,b,t) target t. intervening op M: pair cancels iff [P,M]=0.
Rules (sound, no false positives; controls-reads allowed):
  CCX(c,d,e): kill K iff e in K or t_K in {c,d}
  CX(c,d):    kill K iff d in K or t_K == c
  X(w),HMR(w): kill K iff w in K
  SWAP:       kill K iff K intersects swapped wires
  CZ/Z:       kill K iff t_K mentioned (diagonal conjugation)
  R/others with q ops: kill K iff K intersects mentioned wires (conservative)
  BIT/PUSH/POP/INFO/APPEND/REGISTER/NEG-classical: ignore
Read-only scan; no mutation; no verifier run.
"""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("artifacts/20261106_eeakernel_rewrite/peephole.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

CLASSICAL = {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
             "PUSH_CONDITION", "POP_CONDITION"}

live = {}        # triple -> line
by_wire = {}     # wire -> set of triples
by_target = {}   # wire -> set of triples with target == wire
cancelable = []
n_ccx = 0
dirty_kills = 0


def _drop(key):
    if key in live:
        del live[key]
        for w in set(key):
            s = by_wire.get(w)
            if s is not None:
                s.discard(key)
        s = by_target.get(key[2])
        if s is not None:
            s.discard(key)
        return True
    return False


def kill_many(key_iter):
    n = 0
    for k in list(key_iter):
        if _drop(k):
            n += 1
    return n


def union_of(sets):
    out = set()
    for s in sets:
        if s:
            out |= s
    return out


with open(KMX) as f:
    for ln, line in enumerate(f, 1):
        if line.startswith(("INFO_TAG", "APPEND", "REGISTER")):
            continue
        p = line.split()
        if not p:
            continue
        o = p[0]
        if o in CLASSICAL:
            continue
        if o == "CCX" and len(p) >= 4 and p[1].startswith("q") and p[2].startswith("q") and p[3].startswith("q"):
            n_ccx += 1
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            key = (a, b, t)
            if key in live:
                cancelable.append([live[key], ln, [a, b, t]])
                _drop(key)
            # current op kills other live triples per commutation rule
            dirty_kills += kill_many(union_of([by_wire.get(t), by_target.get(a), by_target.get(b)]))
            if key not in live:
                live[key] = ln
                for w in {a, b, t}:
                    by_wire.setdefault(w, set()).add(key)
                by_target.setdefault(t, set()).add(key)
        elif o == "CX" and len(p) >= 3 and p[1].startswith("q") and p[2].startswith("q"):
            cc, d = int(p[1][1:]), int(p[2][1:])
            dirty_kills += kill_many(union_of([by_wire.get(d), by_target.get(cc)]))
        elif o == "X" and len(p) >= 2 and p[1].startswith("q"):
            dirty_kills += kill_many(union_of([by_wire.get(int(p[1][1:]))]))
        elif o == "HMR" and len(p) >= 2 and p[1].startswith("q"):
            dirty_kills += kill_many(union_of([by_wire.get(int(p[1][1:]))]))
        elif o == "SWAP" and len(p) >= 3:
            ws = [int(x[1:]) for x in p[1:3] if x.startswith("q")]
            dirty_kills += kill_many(union_of([by_wire.get(w) for w in ws]))
        elif o in ("CZ", "Z", "Z_POW"):
            ws = []
            for x in p[1:]:
                if x.startswith("q"):
                    try:
                        ws.append(int(x[1:]))
                    except ValueError:
                        pass
            dirty_kills += kill_many(union_of([by_target.get(w) for w in ws]))
        else:
            ws = []
            for x in p[1:]:
                if x.startswith("q"):
                    try:
                        ws.append(int(x[1:]))
                    except ValueError:
                        pass
            if ws:
                dirty_kills += kill_many(union_of([by_wire.get(w) for w in ws]))

out = {"n_ccx_scanned": n_ccx, "n_cancelable_pairs": len(cancelable),
       "dirty_kills": dirty_kills, "cancelable_pairs": cancelable,
       "scope": "syntactic CCX^2=I with exact commutation guard; no mutation, no verifier"}
OUT.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"n_ccx_scanned": n_ccx, "n_cancelable": len(cancelable),
                  "dirty_kills": dirty_kills}))
