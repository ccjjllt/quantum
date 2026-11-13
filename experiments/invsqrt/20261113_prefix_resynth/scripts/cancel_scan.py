"""Exactly-sound peephole scan: self-inverse gate pairs that cancel.

A pair of identical unconditioned self-inverse gates on the same qubits cancels
exactly when no op strictly between them touches any of those qubits.  This is a
syntactic identity (no simulation, no domain assumption), so every hit is a free
deletion.  Only unconditioned gates are tracked, so classical-bit bookkeeping is
irrelevant: an unconditioned gate is unaffected by any bit write.

Usage: cancel_scan.py CIRCUIT.kmb [LO HI]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "20261112_newfamily_census" / "scripts"))
from kmx_parse import load_ops  # noqa: E402

INVOL = {"X", "CX", "CCX", "SWAP", "CSWAP", "Z", "CZ", "CCZ"}


def scan(ops, lo: int, hi: int):
    alive: dict[tuple, int] = {}
    hits: list[tuple[int, int, str]] = []
    for op in ops[lo:hi]:
        if op.kind in INVOL and not op.cond:
            key = (op.kind, op.qubits)
            if key in alive:
                hits.append((alive[key], op.index, op.raw))
                del alive[key]
                continue
        qs = set(op.qubits)
        for key in [k for k in alive if set(k[1]) & qs]:
            del alive[key]
        if op.kind in INVOL and not op.cond:
            alive[(op.kind, op.qubits)] = op.index
    return hits


def main() -> None:
    path = Path(sys.argv[1])
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    ops, nq, _ = load_ops(path)
    hits = scan(ops, lo, hi)
    print(f"range [{lo}:{min(hi, len(ops))}] exact cancelling pairs: {len(hits)}")
    for a, b, raw in hits[:60]:
        print(f"  {a:>6} .. {b:>6}  {raw}")
    if len(hits) > 60:
        print(f"  ... {len(hits) - 60} more")
    print(f"static Toffoli saved if all applied: {sum(1 for a, b, r in hits if r.split()[0] in ('CSWAP', 'CCZ', 'CCX'))}")


if __name__ == "__main__":
    main()
