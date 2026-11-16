"""Generate a decisive Kaggle kernel: per-wire ones-count at many cuts, two seeds."""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

CUTS = [0, 257, 258, 300, 1000, 3000, 6000, 6610, 6650, 6700, 7300, 7350, 10000, 13350, 18500, 20500]
WATCH = [8, 10, 17, 22, 23, 24, 25, 41, 42, 43]

TEMPLATE = r'''# QCC invsqrt f2cdab0b: ones-count of watched wires at many cuts, two seeds.
import base64, hashlib, json, os, sys
from pathlib import Path
import numpy as np

INPUT = Path('/kaggle/input')


def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]


KSO = _walk('kickmix.so')[0]
sys.path.insert(0, str(KSO.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location('kickmix', str(KSO))
km = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(km)
sys.modules['kickmix'] = km

PAYLOAD = """__B64__"""
raw = base64.b64decode(PAYLOAD)
Path('/tmp/f2.kmb').write_bytes(raw)
circuit = km.Circuit.from_file('/tmp/f2.kmb', format='auto')
circuit.to_file('/tmp/f2.kmx')
lines = [l for l in Path('/tmp/f2.kmx').read_text().splitlines() if l.strip()]
Q = circuit.num_qubits
WIDTH = 22
MAX_X = 3133452

depth = []
d = 0
for l in lines:
    t = l.split()[0]
    if t == 'POP_CONDITION':
        d -= 1
    depth.append(d)
    if t == 'PUSH_CONDITION':
        d += 1


def snap(n):
    while n < len(lines) and depth[n] != 0:
        n += 1
    return n


def to_bits(values, width):
    return (values[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1 == 1


def read_all(nlines, xs, seed):
    nlines = snap(nlines)
    sim = km.Simulator(batch_size=len(xs), debug_print=False, counting_operations=False, seed=seed)
    sim.clear_for_shot()
    sim.write_across_shots(km.array([km.q(i) for i in range(WIDTH)]), to_bits(xs, WIDTH))
    sim.do(km.Circuit('\n'.join(lines[:nlines])))
    r = np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(Q)])), dtype=np.uint8)
    assert r.shape == (Q, len(xs)), r.shape
    return r.T


xs = np.unique(np.random.default_rng(99).integers(1, MAX_X + 1, 500, dtype=np.uint64)).astype(np.uint64)
xb = to_bits(xs, WIDTH)
v0 = read_all(0, xs, seed=1)
print('cut0 x-register equals input:', bool(np.array_equal(v0[:, :WIDTH], xb.T)))

WATCH = __WATCH__
report = {}
for cut in __CUTS__:
    a = read_all(cut, xs, seed=1)
    b = read_all(cut, xs, seed=2)
    ones = {w: int(a[:, w].sum()) for w in WATCH}
    same = bool(np.array_equal(a, b))
    print(f'CUT {cut:6d} seeds_equal {same} ones(/{len(xs)}) {ones}')
    report[cut] = {'ones': ones, 'same': same}
Path('/kaggle/working/ones.json').write_text(json.dumps(report, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__B64__', B64).replace('__CUTS__', repr(CUTS)).replace('__WATCH__', repr(WATCH))
d = ROOT / 'kaggle' / 'ones'
d.mkdir(parents=True, exist_ok=True)
(d / 'ones.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-ones",
    "title": "qcc invsqrt44q ones",
    "code_file": "ones.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": [],
    "dataset_sources": [],
    "kernel_sources": [],
    "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
    "model_sources": [],
}
(d / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
print('wrote', d / 'ones.py', len(code), 'bytes')
