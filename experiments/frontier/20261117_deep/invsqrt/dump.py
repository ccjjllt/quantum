"""Dump a range of parsed operations."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402


def main() -> None:
    lo = int(sys.argv[1])
    hi = int(sys.argv[2])
    ops, _ = parse('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
    for op in ops[lo:hi]:
        print(f'{op.index:6d} {op.raw}')


if __name__ == '__main__':
    main()
