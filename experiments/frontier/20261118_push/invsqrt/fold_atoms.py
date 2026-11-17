"""Exact phase-fold search with hash-consed product atoms (no simulation).

A product atom is the AND a&b, keyed by the canonical pair of operand supports, so two
CCX gates create the *same* atom exactly when their operands hold the same values.
A fold site is a CCX(a,b,t) at i and a later CCX at j that removes the same atom from t,
with every read of t in between being a phase read (Z(t) / CZ(c,t)) only.

  CCX(a,b,t) ... CZ(c,t) ... CCX(a,b,t)   ->   CCZ(a,b,c) + CZ(c,t)
  CCX(a,b,t) ... Z(t)   ... CCX(a,b,t)    ->   CZ(a,b)   + Z(t)

Both identities are exact on every basis state, for any initial value of t.
Saving in Toffolis = 2 - (number of phase reads of t in the window).
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261117_deep/invsqrt")))
from parse_kmx import parse  # noqa: E402

CONST = -1
DIAG = {}
ONE = frozenset({CONST})


def main():
    kmx = pathlib.Path(sys.argv[1])
    ops, meta = parse(kmx)
    nq = 44
    support = [frozenset({-(i + 2)}) for i in range(22)] + [frozenset() for _ in range(nq - 22)]
    key2atom = {}
    atom_key = {}

    def atom_for(key):
        a = key2atom.get(key)
        if a is None:
            a = len(key2atom) + 1
            key2atom[key] = a
            atom_key[a] = key
        return a

    # per-wire write log: (op_index, kind, atom, cond_depth)
    writes = collections.defaultdict(list)
    reads = collections.defaultdict(list)  # wire -> (idx, kind, other)
    depth = 0
    live = {}  # (wire) -> current set of atoms (only for reporting)
    for op in ops:
        n = op.name
        if n == "PUSH_CONDITION":
            depth += 1
            continue
        if n == "POP_CONDITION":
            depth -= 1
            continue
        q = op.qubits
        if n in ("Z", "Z_POW"):
            reads[q[0]].append((op.index, n, None, depth))
            continue
        if n == "CZ":
            reads[q[0]].append((op.index, n, q[1], depth))
            reads[q[1]].append((op.index, n, q[0], depth))
            continue
        if n == "CCZ":
            for w in q:
                reads[w].append((op.index, n, tuple(x for x in q if x != w), depth))
            continue
        if n == "NEG" or n.startswith("BIT_") or n.startswith("INFO"):
            continue
        if n == "X":
            w = q[0]
            a = atom_for(("x1", op.index)) if depth else CONST
            writes[w].append((op.index, "X", a, depth))
            support[w] ^= frozenset({a})
            continue
        if n == "HMR":
            w = q[0]
            a = atom_for(("m", op.index))
            writes[w].append((op.index, "HMR", a, depth))
            support[w] = frozenset()
            continue
        if n == "SWAP":
            a, b = q
            support[a], support[b] = support[b], support[a]
            writes[a].append((op.index, "SWAP", None, depth))
            writes[b].append((op.index, "SWAP", None, depth))
            continue
        if n == "CX":
            a, b = q
            reads[a].append((op.index, "CX-ctrl", b, depth))
            if depth:
                atom = atom_for(("c", op.index))
                writes[b].append((op.index, "CXc", atom, depth))
                support[b] ^= frozenset({atom})
            else:
                writes[b].append((op.index, "CX", None, depth))
                support[b] ^= support[a]
            continue
        if n == "CCX":
            a, b, t = q
            sa, sb = support[a], support[b]
            reads[a].append((op.index, "CCX-ctrl", t, depth))
            reads[b].append((op.index, "CCX-ctrl", t, depth))
            if not sa or not sb:
                writes[t].append((op.index, "CCX0", None, depth))  # AND is identically 0
                print("DEAD CCX (zero operand)", op.index, q)
                continue
            if sa == sb:
                writes[t].append((op.index, "CCXid", None, depth))
                print("CCX with equal controls (degradable)", op.index, q)
                continue
            key = ("and", tuple(sorted((sa, sb), key=lambda s: tuple(sorted(s)))))
            atom = atom_for(key) if not depth else atom_for(("cand", op.index))
            writes[t].append((op.index, "CCX", atom, depth))
            support[t] ^= frozenset({atom})
            continue

    print("atoms", len(key2atom), "wires", nq)

    # ---- fold search: consecutive writes to the same target
    sites = []
    for w, wr in writes.items():
        for a, b in zip(wr, wr[1:]):
            i, ki, ai, di = a
            j, kj, aj, dj = b
            if ki != "CCX" or kj != "CCX" or ai != aj:
                continue
            if ai is None:
                continue
            DIAG.setdefault("same_atom", 0)
            DIAG["same_atom"] += 1
            # reads of w strictly between i and j
            between = [r for r in reads[w] if i < r[0] < j]
            kinds = collections.Counter(r[1] for r in between)
            DIAG.setdefault(str(sorted(kinds)), 0)
            DIAG[str(sorted(kinds))] += 1
            if any(k not in ("Z", "CZ") for k in kinds):
                continue
            nphase = sum(kinds.values())
            if nphase > 1:
                continue
            sites.append((i, j, w, nphase, dict(kinds), atom_key[ai]))
    print("DIAG", DIAG)
    sites.sort()
    print(f"fold sites: {len(sites)}  (saving = sum(2 - k))")
    tot = 0
    for (i, j, w, k, kinds, key) in sites:
        save = 2 - k
        tot += save
        (_, sa), (_, sb) = key
        print(f"  ops {i}..{j} t=q{w} reads={kinds} save={save} operands={sorted(sa)}x{sorted(sb)}")
    print("total Toffoli saving:", tot)


if __name__ == "__main__":
    main()
