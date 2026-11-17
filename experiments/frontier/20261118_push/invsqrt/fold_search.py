"""Exact phase-fold search on an invsqrt tape.

Pattern (deterministic, phase map unchanged):
    CCX(a,b,t) ... CZ(c,t) ... CCX(a,b,t)
  ->  CCZ(a,b,c) at the CZ position, both CCX deleted
     (2 Toffolis -> 1; identical action on every basis state)

Generalised: a mirror CCX pair whose target t is read in between ONLY by Z(t) / CZ(c,t)
phase gates is foldable at 1 Toffoli per read (2 Toffolis -> k Toffolis).
Reads that use t as a *value* control (CX/CCX/CSWAP/Z_POW/CCZ) block the fold.
"""
import collections
import pathlib
import re
import sys

OPS = ("APPEND_TO_REGISTER", "REGISTER")


def load(path):
    ops = []
    cond = []
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        if name == "PUSH_CONDITION":
            cond.append(" ".join(parts[1:]))
            ops.append(("PUSH", parts[1:], tuple(cond)))
        elif name == "POP_CONDITION":
            ops.append(("POP", [], tuple(cond)))
            cond.pop()
        elif name in OPS:
            continue
        else:
            ops.append((name, parts[1:], tuple(cond)))
    return ops


def qidx(tok):
    return int(tok[1:]) if tok.startswith("q") else None


def main():
    path = sys.argv[1]
    ops = load(path)
    n = len(ops)
    print("body ops", n)

    def writes(name, args, w):
        """does this op write qubit w (as a value target)?"""
        if name in ("X", "Z", "HMR", "R"):
            return qidx(args[0]) == w
        if name == "CX":
            return qidx(args[1]) == w
        if name == "CCX":
            return qidx(args[2]) == w
        if name in ("CSWAP",):
            return qidx(args[1]) == w or qidx(args[2]) == w
        if name == "SWAP":
            return qidx(args[0]) == w or qidx(args[1]) == w
        if name == "Z_POW":
            return False
        return False

    def read_kind(name, args, w):
        """how t is read: 'phase-Z', 'phase-CZ:<c>', 'value', 'phase-CCZ', 'zpow', None"""
        if name == "Z":
            return ("phase-Z", None) if qidx(args[0]) == w else None
        if name == "CZ":
            a, b = qidx(args[0]), qidx(args[1])
            if b == w:
                return ("phase-CZ", a)
            if a == w:
                return ("phase-CZ", b)
            return None
        if name == "CX":
            if qidx(args[0]) == w:
                return ("value", None)
            return None
        if name == "CCX":
            if qidx(args[0]) == w or qidx(args[1]) == w:
                return ("value", None)
            return None
        if name == "CCZ":
            if w in (qidx(args[0]), qidx(args[1]), qidx(args[2])):
                return ("phase-CCZ", None)
            return None
        if name == "Z_POW":
            return ("zpow", None) if qidx(args[0]) == w else None
        if name == "CSWAP":
            if qidx(args[0]) == w:
                return ("value", None)
            return None
        if name == "SWAP":
            return ("value", None) if w in (qidx(args[0]), qidx(args[1])) else None
        return None

    ccx = [(i, qidx(a[0]), qidx(a[1]), qidx(a[2]), c)
           for i, (nm, a, c) in enumerate(ops) if nm == "CCX"]
    print("CCX", len(ccx))

    pairs = []
    for (i, a, b, t, ci) in ccx:
        # scan forward for the first write to t
        for j in range(i + 1, n):
            nm, ar, cj = ops[j]
            if writes(nm, ar, t):
                if nm == "CCX" and qidx(ar[0]) == a and qidx(ar[1]) == b and qidx(ar[2]) == t:
                    # mirror pair; classify reads in (i, j)
                    kinds = []
                    for k in range(i + 1, j):
                        rk = read_kind(ops[k][0], ops[k][1], t)
                        if rk is not None:
                            kinds.append((k, rk[0], rk[1], ops[k][2]))
                    pairs.append((i, j, a, b, t, ci, kinds))
                break

    print("mirror pairs (first-write match):", len(pairs))
    hist = collections.Counter()
    foldable = []
    for (i, j, a, b, t, ci, kinds) in pairs:
        sig = tuple(sorted(k[1] for k in kinds))
        hist[sig] += 1
        conds = {k[3] for k in kinds} | {ci}
        same_cond = len(conds) == 1
        only_phase = all(k[1] in ("phase-Z", "phase-CZ") for k in kinds)
        if only_phase and same_cond and len(kinds) <= 2:
            foldable.append((i, j, a, b, t, kinds))
    print("read-signature histogram of mirror pairs:")
    for sig, cnt in hist.most_common():
        print("   ", sig, cnt)
    print("foldable (phase-only, <=2 reads, single condition context):", len(foldable))
    for (i, j, a, b, t, kinds) in foldable:
        print(f"  pair ops {i}..{j}  CCX q{a} q{b} q{t}  reads={[(k[0], k[1], k[2]) for k in kinds]}")


if __name__ == "__main__":
    main()
