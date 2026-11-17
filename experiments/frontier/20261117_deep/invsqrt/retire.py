"""Which scratch lines must be retired for a lower Q? (static token analysis)

For each scratch line, delete its tokens and recompute the token-count peak.  A line
whose removal lowers the peak is a *necessary* retirement; the minimum number of
retirements needed to reach a peak of 42/40 is also computed (greedy + exact-ish).
"""

from __future__ import annotations

import bisect
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
WRITES = ('X', 'CX', 'CCX', 'SWAP', 'HMR')


def build():
    ops, meta = parse(KMX)
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    n = len(ops)

    def target(op):
        if op.name in ('X', 'HMR'):
            return op.qubits[0]
        if op.name in ('CX', 'CZ', 'SWAP'):
            return op.qubits[1]
        if op.name in ('CCX', 'CCZ'):
            return op.qubits[2]
        return None

    val: list[int | None] = [None] * nq
    pre: dict[int, int | None] = {}
    reads: list[tuple[int, int]] = []
    depth = 0
    for op in ops:
        if op.name == 'PUSH_CONDITION':
            depth += 1
            continue
        if op.name == 'POP_CONDITION':
            depth -= 1
            continue
        t = target(op)
        for q in op.qubits:
            if q != t or op.name == 'SWAP':
                reads.append((op.index, q))
        if depth > 0 and op.name in WRITES:
            pre[op.index] = None
            for q in op.qubits:
                val[q] = None
            continue
        if op.name == 'X':
            pre[op.index] = val[op.qubits[0]]
            val[op.qubits[0]] = None if val[op.qubits[0]] is None else 1 - val[op.qubits[0]]
        elif op.name == 'CX':
            a, b = op.qubits
            pre[op.index] = val[b]
            val[b] = 1 - val[a] if (val[a] is not None and val[b] is not None) else None
        elif op.name == 'CCX':
            pre[op.index] = val[op.qubits[2]]
            val[op.qubits[2]] = None
        elif op.name == 'HMR':
            pre[op.index] = val[op.qubits[0]]
            val[op.qubits[0]] = 0
        elif op.name == 'SWAP':
            a, b = op.qubits
            pre[op.index] = None
            val[a] = val[b] = None

    lastread: dict[int, list[int]] = {q: [] for q in range(nq)}
    for i, q in reads:
        lastread[q].append(i)
    defs: dict[int, list[int]] = {q: [] for q in range(nq)}
    for idx in pre:
        defs[target(ops[idx])].append(idx)

    tokens = []
    for q in range(nq):
        ds = sorted(defs[q])
        rd = lastread[q]
        for k, d in enumerate(ds):
            nxt = ds[k + 1] if k + 1 < len(ds) else None
            nxt_known = nxt is not None and pre.get(nxt) is not None
            hi = bisect.bisect_left(rd, nxt) if nxt is not None else len(rd)
            lo = bisect.bisect_left(rd, d)
            last_read = rd[hi - 1] if hi > lo else None
            if last_read is None and (nxt is None or nxt_known):
                continue
            end = last_read + 1 if last_read is not None else d + 1
            if nxt is not None and not nxt_known:
                end = max(end, nxt)
            tokens.append((d, end, q, len(range(lo, hi))))
    return ops, nq, n, tokens


def peak_of(tokens, n, drop=()):
    delta = [0] * (n + 2)
    for a, b, q, _ in tokens:
        if q in drop:
            continue
        delta[a] += 1
        delta[b] -= 1
    cur = best = 0
    at = 0
    for i in range(n):
        cur += delta[i]
        if cur > best:
            best, at = cur, i
    return best, at


def main() -> None:
    ops, nq, n, tokens = build()
    base, at = peak_of(tokens, n)
    print(f'tokens {len(tokens)}; peak {base} at op {at} ({ops[at].raw})')

    scratch = list(range(22, nq))
    xreg = list(range(22))
    print('\n## single-line retirement effect (peak after dropping that line)')
    for q in scratch:
        p, a = peak_of(tokens, n, drop={q})
        print(f'  drop scratch q{q:2d} -> peak {p}')
    for q in xreg:
        p, a = peak_of(tokens, n, drop={q})
        print(f'  drop x       q{q:2d} -> peak {p}')

    # greedy: retire the line that helps most, repeat
    print('\n## greedy retirement (min lines to reach peak <= 42 / 40)')
    cur_drop: set[int] = set()
    for step in range(1, 9):
        best = None
        for q in scratch:
            if q in cur_drop:
                continue
            p, _ = peak_of(tokens, n, drop=cur_drop | {q})
            if best is None or p < best[1]:
                best = (q, p)
        cur_drop.add(best[0])
        print(f'  step {step}: retire q{best[0]} -> peak {best[1]}  (set {sorted(cur_drop)})')

    # how many op positions sit at each high concurrency
    prof = collections.Counter()
    delta = [0] * (n + 2)
    for a, b, q, _ in tokens:
        delta[a] += 1
        delta[b] -= 1
    cur = 0
    for i in range(n):
        cur += delta[i]
        prof[cur] += 1
    print('\n## concurrency profile (>=40)')
    for k in sorted(k for k in prof if k >= 40):
        print(f'  {k}: {prof[k]} op positions')


if __name__ == '__main__':
    main()
