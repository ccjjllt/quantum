"""Generate a Kaggle kernel: at peak-occupancy ops, is any occupied wire identically 0/1?

A wire whose value is identically 0 across a whole peak region carries no information and
can be freed (R gate) at zero cost -> Q reduction.  Also reports identical-wire pairs.
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

CUTS = [1750, 2000, 2500, 3000, 4400, 5000, 6000, 13350, 14000, 18100, 18500, 18900, 19500]

TEMPLATE = r'''# QCC invsqrt f2cdab0b: constant-wire scan at peak ops.
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
    sim = km.Simulator(batch_size=len(xs), debug_print=False, counting_operations=False, seed=seed)
    sim.clear_for_shot()
    sim.write_across_shots(km.array([km.q(i) for i in range(WIDTH)]), to_bits(xs, WIDTH))
    sim.do(km.Circuit('\n'.join(lines[:nlines])))
    r = np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(Q)])), dtype=np.uint8)
    assert r.shape == (Q, len(xs)), r.shape
    return r.T


rng = np.random.default_rng(11)
xs = np.unique(rng.integers(1, MAX_X + 1, 1000, dtype=np.uint64)).astype(np.uint64)
print('samples', len(xs))

out = {}
for cut0 in __CUTS__:
    cut = snap(cut0)
    v = read_all(cut, xs, seed=21)
    const0 = [w for w in range(Q) if not v[:, w].any()]
    const1 = [w for w in range(Q) if v[:, w].all()]
    # identical pairs
    pairs = []
    for a in range(Q):
        for b in range(a + 1, Q):
            if np.array_equal(v[:, a], v[:, b]):
                pairs.append((a, b))
    # unequal pairs (complementary)
    comp = []
    for a in range(Q):
        for b in range(a + 1, Q):
            if np.array_equal(v[:, a], 1 - v[:, b]):
                comp.append((a, b))
    print(f'CUT {cut0}: identically0 {const0} identically1 {const1} identical_pairs {pairs} complementary {comp}')
    out[cut0] = {'zero': const0, 'one': const1, 'same': pairs, 'comp': comp}
Path('/kaggle/working/const_scan.json').write_text(json.dumps(out, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__B64__', B64).replace('__CUTS__', repr(CUTS))
d = ROOT / 'kaggle' / 'constscan'
d.mkdir(parents=True, exist_ok=True)
(d / 'constscan.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-constscan",
    "title": "qcc invsqrt44q constscan",
    "code_file": "constscan.py",
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
print('wrote', d / 'constscan.py', len(code), 'bytes')
