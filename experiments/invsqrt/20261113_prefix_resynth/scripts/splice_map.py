"""Locate the splice between 9c708f7b and its two public parents.

Read-only: prints the longest common prefix/suffix of the flat op stream with
each parent, and which parent supplies each segment of the prefix region.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "20261112_newfamily_census" / "scripts"))
from kmx_parse import load_ops  # noqa: E402


def raw(ops):
    return [o.raw for o in ops]


def common_prefix(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def common_suffix(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[-1 - i] == b[-1 - i]:
        i += 1
    return i


def main() -> None:
    base = Path(sys.argv[1])
    parents = [Path(p) for p in sys.argv[2:]]
    child, nq, _ = load_ops(base)
    c = raw(child)
    print(f"child {base.name}: {len(c)} ops, {nq}q")
    for p in parents:
        par, nqp, _ = load_ops(p)
        q = raw(par)
        pre = common_prefix(c, q)
        suf = common_suffix(c, q)
        print(f"\nparent {p.name}: {len(q)} ops, {nqp}q")
        print(f"  common prefix = {pre} ops; common suffix = {suf} ops")
        print(f"  child  around prefix end: {c[max(0, pre - 2):pre + 4]}")
        print(f"  parent around prefix end: {q[max(0, pre - 2):pre + 4]}")


if __name__ == "__main__":
    main()
