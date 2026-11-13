"""Anchor-diff the child circuit against each parent with fixed 24-op windows.

Read-only.  Prints the child's segments that are copied verbatim from a parent
(or from neither), which is what "splice" means here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "20261112_newfamily_census" / "scripts"))
from kmx_parse import load_ops  # noqa: E402

W = 24


def windows(ops, w=W):
    d = {}
    for i in range(len(ops) - w + 1):
        d.setdefault(tuple(ops[i:i + w]), []).append(i)
    return d


def main() -> None:
    child, _, _ = load_ops(Path(sys.argv[1]))
    c = [o.raw for o in child]
    parents = {}
    for p in sys.argv[2:]:
        o, _, _ = load_ops(Path(p))
        parents[Path(p).stem] = ([x.raw for x in o], windows([x.raw for x in o]))

    # walk child, at each position mark which parent has a 24-op window match
    label = ["----"] * len(c)
    for name, (rp, wd) in parents.items():
        i = 0
        while i <= len(c) - W:
            if tuple(c[i:i + W]) in wd:
                # extend
                j = i + W
                while j < len(c) and j - i < len(rp) and c[j] == rp[(wd[tuple(c[i:i + W])][0]) + (j - i)]:
                    j += 1
                for k in range(i, j):
                    label[k] = name[:4]
                i = j
            else:
                i += 1

    # compress runs
    print(f"child {len(c)} ops")
    runs = []
    cur = label[0]
    start = 0
    for i in range(1, len(c) + 1):
        if i == len(c) or label[i] != cur:
            runs.append((start, i, cur))
            if i < len(c):
                cur = label[i]
                start = i
    for a, b, lab in runs:
        if b - a >= 8 or lab != "----":
            print(f"{a:>6}-{b:<6} {b - a:>6} ops  {lab}")


if __name__ == "__main__":
    main()
