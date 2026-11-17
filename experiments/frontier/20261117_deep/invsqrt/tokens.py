"""Sound token model: what Q does this gate sequence really need?

A write target is XOR-accumulated into the wire's old value, so the old value is
*consumed* by every write whose pre-value is not a known constant.  The token that
carries a wire's value therefore runs from the write that created it to its last read
AND to the next write (if that next write has an unknown pre-value).

Tokens are what must live on distinct wires, so peak(token concurrency) is a sound
lower bound on num_qubits for this exact gate sequence.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402


def main() -> None:
    ops, meta = parse('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    n = len(ops)

    WRITES = ('X', 'CX', 'CCX', 'SWAP', 'HMR')

    def target(op):
        if op.name in ('X', 'HMR'):
            return op.qubits[0]
        if op.name in ('CX', 'CZ', 'SWAP'):
            return op.qubits[1]
        if op.name in ('CCX', 'CCZ'):
            return op.qubits[2]
        return None

    # --- known-pre-value analysis -----------------------------------------
    val: list[int | None] = [None] * nq
    pre: dict[int, int | None] = {}   # def index -> pre-value (None = unknown)
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
            if t is not None:
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
            a, b, t2 = op.qubits
            pre[op.index] = val[t2]
            val[t2] = None
        elif op.name == 'HMR':
            pre[op.index] = val[op.qubits[0]]
            val[op.qubits[0]] = 0
        elif op.name == 'SWAP':
            a, b = op.qubits
            pre[op.index] = None
            val[a] = val[b] = None

    # --- tokens -----------------------------------------------------------
    defs: dict[int, list[int]] = {q: [] for q in range(nq)}
    lastread: dict[int, list[int]] = {q: [] for q in range(nq)}
    for i, q in reads:
        lastread[q].append(i)
    for idx, v in pre.items():
        t = target(ops[idx])
        defs[t].append(idx)
    import bisect
    tokens = []
    for q in range(nq):
        ds = sorted(defs[q])
        rd = lastread[q]
        for k, d in enumerate(ds):
            nxt = ds[k + 1] if k + 1 < len(ds) else None
            nxt_known = (nxt is not None and pre.get(nxt) is not None)
            # last read in [d, nxt)
            hi = bisect.bisect_left(rd, nxt) if nxt is not None else len(rd)
            lo = bisect.bisect_left(rd, d)
            last_read = rd[hi - 1] if hi > lo else None
            if last_read is None and (nxt is None or nxt_known):
                continue          # value never read and not consumed -> dead write
            end = last_read + 1 if last_read is not None else d + 1
            if nxt is not None and not nxt_known:
                end = max(end, nxt)   # consumed by the next write: exclusive end
            tokens.append((d, end, q))
    delta = [0] * (n + 2)
    for a, b, _ in tokens:
        delta[a] += 1
        delta[b] -= 1
    cur = peak = 0
    peak_at = 0
    for i in range(n):
        cur += delta[i]
        if cur > peak:
            peak, peak_at = cur, i
    print(f'tokens: {len(tokens)}')
    print(f'sound token-count peak = {peak} at op {peak_at}')
    live = [q for a, b, q in tokens if a <= peak_at < b]
    print(f'  lines holding a token at op {peak_at}: {len(live)} -> {sorted(live)}')

    hist = {}
    for a, b, _ in tokens:
        for i in range(a, b):
            hist[i] = hist.get(i, 0) + 1
    from collections import Counter
    print('  concurrency histogram (top 8):', Counter(hist.values()).most_common(8))
    print('\ndead writes (never read, not consumed):',
          sum(1 for q in defs for d in defs[q]
              if pre.get(d) is not None and not lastread[q]))


if __name__ == '__main__':
    main()
