"""File-wide CCX/CSWAP/CCZ-pair peephole with exact commutation guards.

Pair (two identical self-inverse gates) cancels iff every op between the
two occurrences commutes with it. Per-op kill rule for live triple K with
read-sensitive set S (CCX:{t}, CSWAP:{b,t}, CCZ:{}):
  CCX(c,d,e): kill iff e in K or S cap {c,d} nonempty
  CX(c,d):    kill iff d in K or c in S
  X/HMR(w):   kill iff w in K
  SWAP:       kill iff intersects K
  CZ/Z/Z_POW: kill iff S cap mentioned nonempty (diagonal conjugation)
  CCZ:        kill iff S cap mentioned nonempty (diagonal commutes w/ diagonal)
  R/other q-op: kill iff K cap mentioned nonempty (conservative)
  BIT/PUSH/POP/NEG/INFO/APPEND/REGISTER: ignore (classical/structural;
    coin identity follows because any pair-dependence of a coin flows
    through a triple-wire touch, which kills first)
Key normalization: CCX controls sorted, CCZ fully sorted (symmetric);
CSWAP kept ordered (swap-target matters).
Read-only scan; no mutation; no verifier run.
"""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("artifacts/peephole_all.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

CLASSICAL = {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
             "PUSH_CONDITION", "POP_CONDITION"}


def parse_q(tok):
    if tok.startswith("q"):
        try:
            return int(tok[1:])
        except ValueError:
            return None
    return None


live = {}        # key -> line number
by_wire = {}     # wire -> set of keys containing it
by_swap = {}     # wire -> set of keys whose S contains it
cancelable = []
n_scanned = {"CCX": 0, "CSWAP": 0, "CCZ": 0}
dirty_kills = 0


def swap_set(kind, triple):
    if kind == "CCX":
        return {triple[2]}
    if kind == "CSWAP":
        return {triple[1], triple[2]}
    return set()


def _drop(key):
    if key in live:
        del live[key]
        for w in set(key[1]):
            s = by_wire.get(w)
            if s is not None:
                s.discard(key)
        for w in swap_set(*key):
            s = by_swap.get(w)
            if s is not None:
                s.discard(key)
        return True
    return False


def kill_keys(keys):
    global dirty_kills
    n = 0
    for k in list(keys):
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
        if o == "CCX" and len(p) >= 4:
            qs = [parse_q(t) for t in p[1:4]]
            if any(v is None for v in qs):
                continue
            n_scanned["CCX"] += 1
            a, b = sorted(qs[:2])
            t = qs[2]
            key = ("CCX", (a, b, t))
            if key in live:
                cancelable.append([live[key], ln, ["CCX", a, b, t]])
                _drop(key)
            dirty_kills += kill_keys(union_of([by_wire.get(t), by_swap.get(a), by_swap.get(b)]))
            if key not in live:
                live[key] = ln
                for w in {a, b, t}:
                    by_wire.setdefault(w, set()).add(key)
                by_swap.setdefault(t, set()).add(key)
        elif o == "CSWAP" and len(p) >= 4:
            qs = [parse_q(t) for t in p[1:4]]
            if any(v is None for v in qs):
                continue
            n_scanned["CSWAP"] += 1
            a, b, t = qs
            key = ("CSWAP", (a, b, t))
            if key in live:
                cancelable.append([live[key], ln, ["CSWAP", a, b, t]])
                _drop(key)
            dirty_kills += kill_keys(union_of([by_wire.get(t), by_swap.get(a), by_swap.get(b)]))
            if key not in live:
                live[key] = ln
                for w in {a, b, t}:
                    by_wire.setdefault(w, set()).add(key)
                for w in {b, t}:
                    by_swap.setdefault(w, set()).add(key)
        elif o == "CCZ" and len(p) >= 4:
            qs = [parse_q(t) for t in p[1:4]]
            if any(v is None for v in qs):
                continue
            n_scanned["CCZ"] += 1
            key = ("CCZ", tuple(sorted(qs)))
            if key in live:
                cancelable.append([live[key], ln, ["CCZ"] + list(key[1])])
                _drop(key)
            # diagonal pair: an intervening CCZ only matters if it moves a
            # wire the pair is sensitive to; use by_swap (CCZ keys are never
            # in by_swap, so diagonal-diagonal pairs always survive).
            dirty_kills += kill_keys(union_of([by_swap.get(q) for q in qs]))
            if key not in live:
                live[key] = ln
                for w in set(qs):
                    by_wire.setdefault(w, set()).add(key)
                # NOT added to by_swap: diagonal intervening ops never kill CCZ pairs.
        elif o == "CX" and len(p) >= 3:
            c = parse_q(p[1])
            d = parse_q(p[2])
            if c is None or d is None:
                continue
            dirty_kills += kill_keys(union_of([by_wire.get(d), by_swap.get(c)]))
        elif o in ("X", "HMR") and len(p) >= 2:
            w = parse_q(p[1])
            if w is not None:
                dirty_kills += kill_keys(union_of([by_wire.get(w)]))
        elif o == "SWAP" and len(p) >= 3:
            ws = [parse_q(t) for t in p[1:3] if parse_q(t) is not None]
            dirty_kills += kill_keys(union_of([by_wire.get(w) for w in ws]))
        elif o in ("CZ", "Z", "Z_POW"):
            ws = []
            for t in p[1:]:
                v = parse_q(t)
                if v is not None:
                    ws.append(v)
            dirty_kills += kill_keys(union_of([by_swap.get(w) for w in ws]))
        elif o == "CCZ":
            # handled above (exact branch); reachable only for malformed lines
            ws = []
            for t in p[1:]:
                v = parse_q(t)
                if v is not None:
                    ws.append(v)
            dirty_kills += kill_keys(union_of([by_swap.get(w) for w in ws]))
        else:
            ws = []
            for t in p[1:]:
                v = parse_q(t)
                if v is not None:
                    ws.append(v)
            if ws:
                dirty_kills += kill_keys(union_of([by_wire.get(w) for w in ws]))

out = {"n_scanned": n_scanned, "n_cancelable_pairs": len(cancelable),
       "dirty_kills": dirty_kills, "cancelable_pairs": cancelable,
       "scope": "syntactic self-inverse pair cancellation with exact commutation guards; read-only; no verifier"}
OUT.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"n_scanned": n_scanned, "n_cancelable": len(cancelable),
                  "dirty_kills": dirty_kills}))
