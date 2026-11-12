"""Dump kickmix circuits to .kmx text for structural inspection (local only, no verification)."""
from __future__ import annotations

import sys
from pathlib import Path

import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
OUT = ROOT / '.worktree/dfthcsos/artifacts/20261112_loader_re'


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.glob('angle_k_*.kmb')):
        c = km.Circuit.from_file(p, format='auto')
        c.to_file(dst / (p.stem + '.kmx'), format='kmx')
        print(p.name, c.num_qubits, len(c), c.operation_statistics().num_toffoli_like, flush=True)


if __name__ == '__main__':
    main()
