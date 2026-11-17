"""Assemble the final chemistry leg from fetched emitter-kernel outputs.

Usage
-----
    python3 assemble_final.py --orig  DIR  --kernels DIR1 [DIR2 ...] --out STAGE \
        [--npz PATH_TO_RATNACHAND_or_OURS]

`--orig` is a directory holding the shipped `dfthcsos/` (npz + 15 loaders).
Each `--kernels DIR` is a fetched kernel output containing `run/dfthcsos/angle_k_N.kmb`
(possibly nested); the cheapest loader for each index wins.

The chemistry cost is `lambda_eff * T * Q` with `Q = 427` fixed by the shape and
`T = 2 * sum(loader Toffoli) + ...`; this script only assembles and reports the
loader Toffoli table and the implied T delta, so the official verifier remains the
authority on PASS/FAIL and on the final cost.

Nothing is submitted and nothing is run here.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil

SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]
LAM = 46.92171681802858
Q = 427


def find_loaders(root: pathlib.Path) -> dict[int, pathlib.Path]:
    """index -> path, preferring the shallowest / first hit."""
    out: dict[int, pathlib.Path] = {}
    for p in sorted(root.rglob('angle_k_*.kmb')):
        try:
            idx = int(p.stem.split('_')[-1])
        except ValueError:
            continue
        out.setdefault(idx, p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', required=True, help='dir containing dfthcsos/ with the shipped members')
    ap.add_argument('--kernels', nargs='+', default=[], help='fetched kernel output dirs')
    ap.add_argument('--out', required=True)
    ap.add_argument('--npz', default=None, help='replacement submission.npz (default: keep shipped)')
    a = ap.parse_args()

    orig = pathlib.Path(a.orig)
    src = orig / 'dfthcsos' if (orig / 'dfthcsos').is_dir() else orig
    npz = src / 'submission.npz'
    if not npz.is_file():
        raise SystemExit(f'missing {npz}')

    out = pathlib.Path(a.out)
    dfth = out / 'dfthcsos'
    dfth.mkdir(parents=True, exist_ok=True)

    shipped = find_loaders(src)
    if len(shipped) != 15:
        raise SystemExit(f'expected 15 shipped loaders, found {len(shipped)}: {sorted(shipped)}')

    best = dict(shipped)
    for kd in a.kernels:
        for idx, p in find_loaders(pathlib.Path(kd)).items():
            if idx not in best:
                continue
            if p.stat().st_size == best[idx].stat().st_size and p.read_bytes() == best[idx].read_bytes():
                continue
            # a cheaper loader is smaller on disk for this format family; keep the smallest,
            # and report both so the caller can cross-check the kernel's own Toffoli count.
            if p.stat().st_size < best[idx].stat().st_size:
                best[idx] = p

    if a.npz:
        shutil.copyfile(a.npz, dfth / 'submission.npz')
    else:
        shutil.copyfile(npz, dfth / 'submission.npz')
    for idx in sorted(best):
        shutil.copyfile(best[idx], dfth / f'angle_k_{idx}.kmb')

    total = sum(SHIPPED)
    print(f"{'idx':>3} {'shipped':>8} {'chosen':>7} {'bytes':>9}  source")
    chosen_total = 0
    for idx in sorted(best):
        n = best[idx].stat().st_size
        tag = 'shipped' if best[idx] == shipped[idx] else 'NEW'
        # Toffoli is not readable from size; the kernel's own log is authoritative.
        print(f'{idx:>3} {SHIPPED[idx]:>8} {tag:>7} {n:>9}  {best[idx]}')
        chosen_total += SHIPPED[idx]
    print(f'\nshipped loader Toffoli total {total}; T_angles = 2*{total} = {2*total}')
    print('To confirm the real delta: the official verifier report carries the exact cost;')
    print(f'expected chem cost = lambda * T * Q with lambda={LAM}, Q={Q}.')
    print(f'members written: {len(list(dfth.iterdir()))} files in {dfth}')


if __name__ == '__main__':
    main()
