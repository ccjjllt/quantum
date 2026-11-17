"""Are products recomputed (i.e. is the second half an inverse pass)? Exact atom accounting."""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261117_deep/invsqrt")))
from parse_kmx import parse  # noqa: E402

CONST = -1


def main():
    ops, _ = parse(pathlib.Path(sys.argv[1]))
    nq = 44
    support = [frozenset({-(i + 2)}) for i in range(22)] + [frozenset() for _ in range(nq - 22)]
    key2atom, atom_key = {}, {}

    def atom_for(key):
        a = key2atom.get(key)
        if a is None:
            a = len(key2atom) + 1
            key2atom[key] = a
            atom_key[a] = key
        return a

    created = collections.defaultdict(list)   # atom -> [op indices]
    removed = collections.defaultdict(list)
    depth = 0
    halves = (7500,)
    for op in ops:
        n = op.name
        if n == "PUSH_CONDITION":
            depth += 1
            continue
        if n == "POP_CONDITION":
            depth -= 1
            continue
        q = op.qubits
        if n in ("Z", "CZ", "CCZ", "Z_POW", "NEG") or n.startswith("BIT_") or n.startswith("INFO"):
            continue
        if n == "X":
            a = atom_for(("x1", op.index)) if depth else CONST
            support[q[0]] ^= frozenset({a})
            continue
        if n == "HMR":
            support[q[0]] = frozenset()
            continue
        if n == "SWAP":
            support[q[0]], support[q[1]] = support[q[1]], support[q[0]]
            continue
        if n == "CX":
            a, b = q
            if depth:
                support[b] ^= frozenset({atom_for(("c", op.index))})
            else:
                support[b] ^= support[a]
            continue
        if n == "CCX":
            a, b, t = q
            sa, sb = support[a], support[b]
            if not sa or not sb:
                print("DEAD CCX", op.index)
                continue
            if sa == sb:
                print("ID CCX", op.index)
                continue
            key = ("and", tuple(sorted((sa, sb), key=lambda s: tuple(sorted(s)))))
            atom = atom_for(key)
            if atom in support[t]:
                removed[atom].append(op.index)
            else:
                created[atom].append(op.index)
            support[t] ^= frozenset({atom})
            continue

    multi = {a: v for a, v in created.items() if len(v) > 1}
    print("product atoms created:", len(created), " recreated at least once:", len(multi))
    span = collections.Counter()
    for a, v in multi.items():
        lo, hi = min(v), max(v)
        span["both halves" if lo < 7500 <= hi else "same half"] += 1
    print("  repeats:", dict(span))
    print("total creation events:", sum(len(v) for v in created.values()))
    print("removed events (CCX uncompute):", sum(len(v) for v in removed.values()))
    # how many atoms are never removed by a CCX and never HMR'd?  (informational)
    print("atoms with no CCX removal:", len(created) - len(removed))
    # distribution of creation indices per region
    reg = collections.Counter()
    for a, v in created.items():
        for i in v:
            reg[i // 2500 * 2500] += 1
    print("creation events by 2500-op block:", dict(sorted(reg.items())))


if __name__ == "__main__":
    main()
