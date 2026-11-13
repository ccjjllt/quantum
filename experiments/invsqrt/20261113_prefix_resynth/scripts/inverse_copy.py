"""Search the circuit for an exact inverse copy of a block (compute/uncompute pair).

Read-only.  Takes the op range [lo:hi), forms its reversed inverse op stream
(X/CX/CCX/SWAP/CSWAP are self-inverse; Z-family ops are not, so a block that
contains them is reported separately) and searches the whole op list for a
matching window.  A match would mean the block is pure compute+uncompute and is
replaceable by measurement-based uncomputation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "20261112_newfamily_census" / "scripts"))
from kmx_parse import load_ops  # noqa: E402

SELF_INV = {"X", "CX", "CCX", "SWAP", "CSWAP"}


def main() -> None:
    path = Path(sys.argv[1])
    lo = int(sys.argv[2])
    hi = int(sys.argv[3])
    ops, nq, _ = load_ops(path)
    block = ops[lo:hi]
    bad = [o.kind for o in block if o.kind not in SELF_INV]
    print(f"block [{lo}:{hi}) = {len(block)} ops; non-self-inverse kinds: {sorted(set(bad))}")
    if bad:
        print("  (block contains phase/measurement ops; inverse-copy search is not applicable)")
        return
    inv = [o.raw for o in reversed(block)]
    allraw = [o.raw for o in ops]
    hits = []
    w = 24
    # index the circuit by 24-op windows
    idx = {}
    for i in range(len(allraw) - w + 1):
        idx.setdefault(tuple(allraw[i:i + w]), []).append(i)
    i = 0
    while i <= len(inv) - w:
        key = tuple(inv[i:i + w])
        found = False
        for start in idx.get(key, []):
            j = 0
            while i + j < len(inv) and start + j < len(allraw) and inv[i + j] == allraw[start + j]:
                j += 1
            if j >= w:
                hits.append((i, start, j))
                i += j
                found = True
                break
        if not found:
            i += 1
    print(f"inverse-copy windows found: {len(hits)}")
    for h in hits[:10]:
        print("  inv-block offset", h[0], "-> circuit op", h[1], "length", h[2])


if __name__ == "__main__":
    main()
