"""Scan dmitriigluzdov/vqcc-femoco-public-factorization for a cheaper chemistry shape.

Read-only. Pure arithmetic on small npz metadata plus the official cost model.
No circuit is emitted, nothing is simulated, nothing is submitted.

Questions answered:
  1. what factorizations (U, W, H2_I shapes) does the public package actually ship?
  2. for each, what are rows = N + R*B, Q, T_h under the official cost model?
  3. is `circuit_sources/chemistry_r5.py` a reusable *fitter* (builds U/W from the
     FCIDUMP) or only an emitter?  Its source is printed for off-line reading.
"""
import math
import sys
from pathlib import Path

import numpy as np

N_ORB = 76
LAM = 46.921716818          # measured lambda_eff of the shipped factorization
LOADER_T_PER_ROW = 8044.0 / 1220.0   # shipped loader density (8,044 T over 1,220 rows)
SHIPPED_COST = 294_643_137.73

COMP = 'google-verifiable-quantum-circuit-compilation'
DATA = next(
    (p for p in (Path('/kaggle/input/competitions') / COMP, Path('/kaggle/input') / COMP)
     if (p / 'verifiers').is_dir()),
    None,
)
print('competition dir:', DATA, flush=True)
if DATA is not None:
    for p in (DATA / 'kickmix', DATA / 'verifiers'):
        if p.is_dir():
            sys.path.insert(0, str(p))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'cp', str(DATA / 'verifiers' / 'dfthcsos' / 'scoreinfra' / 'costs_prepare.py'))
CP = importlib.util.module_from_spec(spec)
sys.modules['cp'] = CP
spec.loader.exec_module(CP)
MODEL = CP.SpinFreeData_V1


def cost_of(R, B, C, beta=8, J=5):
    """Q and T_h from the official model; loader T at the shipped density."""
    m = MODEL(R=R, B=B, C=C, N=N_ORB, chi=10, beta=beta)
    inner = m.inner_state_prep_qubit_cost()['temporary']
    outer = m.outer_state_prep_qubit_cost()['temporary']
    ang = J * beta + 37          # reproduces 77 at the shipped point
    Q = 84 + J * beta + max(outer, inner, ang)
    T_h = m.outer_state_prep() + m.inner_state_prep() + m.givens_rotations()
    rows = N_ORB + R * B
    T = LOADER_T_PER_ROW * rows + T_h
    return dict(R=R, B=B, C=C, rows=rows, inner=inner, outer=outer, Q=Q, T_h=T_h,
                T=T, cost=LAM * T * Q)


# ---- locate the mounted dataset -------------------------------------------------
# Kaggle mounts dataset sources at /kaggle/input/datasets/<owner>/<slug> on this image,
# so search the whole tree rather than only the top level.
root = None
cands = []
for top in (Path('/kaggle/input/datasets'), Path('/kaggle/input')):
    if not top.is_dir():
        continue
    for cand in top.rglob('*'):
        if cand.is_dir() and 'femoco' in cand.name.lower():
            cands.append(cand)
    if cands:
        break
print('candidate dataset dirs:', cands, flush=True)
root = cands[0] if cands else None
print('dataset root:', root, flush=True)

print('\n== files ==', flush=True)
if root is not None:
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.suffix.in_({'.npz', '.csv', '.py', '.kmb', '.xz'}):
            print(f'{p.stat().st_size:>10d}  {p.relative_to(root)}', flush=True)

# ---- every npz: shape -> cost --------------------------------------------------
print('\n== npz inventory ==', flush=True)
if root is not None:
    for npz in sorted(root.rglob('*.npz')):
        print(f'\n-- {npz.relative_to(root)} ({npz.stat().st_size} B)', flush=True)
        try:
            with np.load(npz, allow_pickle=False) as z:
                keys = list(z.keys())
                shapes = {k: (z[k].shape, str(z[k].dtype)) for k in keys}
                print('   keys:', keys, flush=True)
                for k, v in shapes.items():
                    print(f'     {k}: {v[0]} {v[1]}', flush=True)
                if 'U' not in keys:
                    continue
                U = z['U']
                R, B, N = U.shape
                C = z['W'].shape[2] if 'W' in keys else None
                if N != N_ORB or C is None:
                    print(f'   skip: N={N} C={C}', flush=True)
                    continue
                d = cost_of(R, B, C)
                print(f'   shape (R,B,C)=({R},{B},{C})  rows={d["rows"]}  Q={d["Q"]}  '
                      f'T_h={d["T_h"]}  T~{d["T"]:.0f}  cost~{d["cost"] / 1e6:.2f}M  '
                      f'({100 * (d["cost"] / SHIPPED_COST - 1):+.2f}% vs shipped)', flush=True)
                if 'angle_words' in keys:
                    aw = z['angle_words']
                    print(f'   angle_words {aw.shape} (expect ({d["rows"]}, {N_ORB - 1}))',
                          flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f'   ERROR {type(exc).__name__}: {exc}', flush=True)

# ---- is the R=5 source a fitter or an emitter? ---------------------------------
print('\n== circuit_sources/chemistry_r5.py ==', flush=True)
if root is not None:
    src = root / 'circuit_sources' / 'chemistry_r5.py'
    if src.is_file():
        print(src.read_text(errors='replace'), flush=True)
    else:
        print('missing', flush=True)

print('\n== shipped reference point ==', flush=True)
print(cost_of(8, 143, 44), flush=True)
print(f'shipped cost {SHIPPED_COST / 1e6:.2f}M', flush=True)
print('DONE', flush=True)
