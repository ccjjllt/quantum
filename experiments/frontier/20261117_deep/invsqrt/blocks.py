"""Segmentation / block profile of the 0af21cb8 circuit (static)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
WATCH = ['CCX', 'CCZ', 'CX', 'CZ', 'Z', 'X', 'Z_POW', 'HMR', 'NEG', 'SWAP', 'BIT_INVERT',
         'BIT_STORE0', 'PUSH_CONDITION']


def main() -> None:
    ops, meta = parse(KMX)
    n = len(ops)
    block = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    print(f'{"range":>13s} ' + ' '.join(f'{w[:6]:>6s}' for w in WATCH))
    for start in range(0, n, block):
        chunk = ops[start:start + block]
        counts = {w: 0 for w in WATCH}
        for o in chunk:
            counts[o.name] = counts.get(o.name, 0) + 1
        print(f'{start:6d}-{start+len(chunk)-1:<6d} ' + ' '.join(f'{counts[w]:6d}' for w in WATCH))


if __name__ == '__main__':
    main()
