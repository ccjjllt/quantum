"""Structural budget numbers: Toffoli pool by block, per-iteration CCX, peak liveness."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kmx_parse import load_ops  # noqa: E402

TOFF = {"CCX", "CCZ", "CSWAP"}
READ_KINDS = {"CX", "CCX", "CZ", "CCZ", "CSWAP", "SWAP", "Z", "Z_POW", "NEG"}


def main() -> None:
    ops, nq, regs = load_ops(Path(sys.argv[1]))
    print(f"qubits={nq} ops={len(ops)}")
    print("toffoli-like by kind:", Counter(o.kind for o in ops if o.kind in TOFF))
    print("toffoli-like by condition depth:",
          Counter(len(o.cond) for o in ops if o.kind in TOFF))

    # per-iteration CCX counts delimited by Z_POW
    zpos = [o.index for o in ops if o.kind == "Z_POW"]
    bounds = [-1] + zpos + [len(ops)]
    print(f"\n{len(zpos)} Z_POW delimiters; CCX between consecutive Z_POW:")
    rows = []
    for a, b in zip(bounds, bounds[1:]):
        seg = ops[a + 1:b]
        ccx = sum(1 for o in seg if o.kind == "CCX")
        ccz = sum(1 for o in seg if o.kind == "CCZ")
        csw = sum(1 for o in seg if o.kind == "CSWAP")
        hmr = sum(1 for o in seg if o.kind == "HMR")
        rows.append((b, b - a - 1, ccx, ccz, csw, hmr))
    for r in rows:
        print(f"  upto {r[0]:6d} len={r[1]:5d} CCX={r[2]:3d} CCZ={r[3]:2d} CSWAP={r[4]:2d} HMR={r[5]:3d}")
    print("total in delimited segments:", sum(r[2] for r in rows), "CCX")

    # peak value liveness: a qubit's current value is live from its last write
    # to its next read.
    last_write = {}
    next_read = {}
    # iterate backwards to know next read
    seq_reads = []
    for op in ops:
        qs = op.qubits
        seq_reads.append(qs)
    # forward pass with a running set of "value live" qubits
    written = set()
    live = set()
    peak = 0
    peak_at = None
    pending_reads = {}  # qubit -> last index at which it is read after i
    # compute last read index per qubit
    last_read = {}
    for op in ops:
        for q in op.qubits:
            last_read[q] = op.index
    live = set()
    for op in ops:
        qs = op.qubits
        # targets are written (last operand for controlled gates)
        is_write = op.kind in ("X", "CX", "CCX", "SWAP", "CSWAP", "Z_POW", "HMR", "Z", "CZ", "CCZ", "NEG")
        if op.kind == "HMR":
            tgt = qs[-1] if qs else None
            if tgt is not None and tgt in live:
                live.discard(tgt)
            continue
        if op.kind in ("X", "CX", "CCX", "SWAP", "CSWAP"):
            tgt = qs[-1]
            # control uses then write
            for q in qs[:-1]:
                pass
            if tgt in live:
                live.discard(tgt)
            if last_read.get(tgt, -1) > op.index:
                live.add(tgt)
        elif op.kind in ("Z", "CZ", "CCZ", "Z_POW"):
            for q in qs:
                if last_read.get(q, -1) > op.index:
                    live.add(q)
        if len(live) > peak:
            peak = len(live)
            peak_at = op.index
    print(f"\npeak value-liveness (written value read again later): {peak} at op {peak_at}")
    # crude bound: count qubits first touched before peak and last touched after
    print("qubit usage spans:")
    first = {}
    last = {}
    for op in ops:
        for q in op.qubits:
            first.setdefault(q, op.index)
            last[q] = op.index
    spans = sorted(((last[q] - first[q], q, first[q], last[q]) for q in first), reverse=True)
    for s in spans[:12]:
        print(f"  q{s[1]}: span {s[0]} from {s[2]} to {s[3]}")
    if peak_at is not None:
        active = [q for q in first if first[q] <= peak_at <= last[q]]
        print(f"  qubits touched before and after peak op {peak_at}: {len(active)} -> {sorted(active)}")


if __name__ == "__main__":
    main()
