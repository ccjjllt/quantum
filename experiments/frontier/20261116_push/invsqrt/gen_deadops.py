"""Generate a Kaggle kernel: full-domain (3,133,452 inputs) activation counts for the ops
that never fired in a 256-sample scan, plus full-domain wire popcounts for q22..q25.

An op whose control-AND is 0 for *every* official input is an exact no-op and can be
deleted (cost = -1 Toffoli each; -0.5 if inside a condition block).
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

CANDIDATES = [109, 123, 131, 145, 153, 167, 175, 189, 197, 211, 219, 234,
              6656, 6659, 6662, 6665, 6668, 6671, 6674, 6677, 6680, 6683, 6686, 6689,
              6986, 7105, 7150, 7151, 7182, 7190, 7194, 7205,
              7270, 7273, 7276, 7279, 7282, 7285, 7288, 7291, 7294, 7297, 7300, 7303]
CUTS = [1750, 3000, 6000, 13350, 18500, 20500]

TEMPLATE = r'''# QCC invsqrt f2cdab0b: full-domain activation counts + wire popcounts.
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


CHUNK = 65536


def count_ops(nlines, ops, wires_of_interest):
    """Full-domain pass: count activations of `ops` (each (index, controls)) and ones of
    each wire in wires_of_interest."""
    nlines = snap(nlines)
    circ = km.Circuit('\n'.join(lines[:nlines]))
    act = {i: 0 for (i, _) in ops}
    ones = {w: 0 for w in wires_of_interest}
    qarr = km.array([km.q(i) for i in range(Q)])
    xarr = km.array([km.q(i) for i in range(WIDTH)])
    for start in range(0, MAX_X, CHUNK):
        n = min(CHUNK, MAX_X - start)
        xs = (np.arange(start, start + n, dtype=np.uint64) % np.uint64(MAX_X)) + np.uint64(1)
        sim = km.Simulator(batch_size=n, debug_print=False, counting_operations=False, seed=9)
        sim.clear_for_shot()
        sim.write_across_shots(xarr, to_bits(xs, WIDTH))
        sim.do(circ)
        v = np.asarray(sim.read_across_shots(qarr), dtype=np.uint8)
        for (i, ctrls) in ops:
            m = np.ones(n, dtype=bool)
            for w in ctrls:
                m &= v[w].astype(bool)
            act[i] += int(m.sum())
        for w in wires_of_interest:
            ones[w] += int(v[w].sum())
    return act, ones


print('=' * 20, 'full-domain wire popcounts')
for cut in __CUTS__:
    act, ones = count_ops(cut, [], [8, 10, 17, 22, 23, 24, 25, 26, 41, 42, 43])
    print(f'CUT {cut}: ones {ones}', flush=True)

print('=' * 20, 'full-domain activation counts for 256-sample "never" ops')
cands = []
for i in __CANDS__:
    parts = lines[i].split()
    q = [int(t[1:]) for t in parts[1:] if t.startswith('q')]
    ctrls = q[:-1] if parts[0] != 'CSWAP' else q[1:]
    cands.append((i, ctrls))
print('n candidates', len(cands))
dead = []
for (i, ctrls) in cands:
    act, _ = count_ops(i, [(i, ctrls)], [])
    total = act[i]
    cond = depth[i] > 0
    print(f'op {i} {lines[i]!r} conditional={cond} activations={total}', flush=True)
    if total == 0:
        dead.append((i, lines[i], cond))
Path('/kaggle/working/dead_ops.json').write_text(json.dumps(dead, indent=1))
print('TRULY DEAD:', len(dead))
for e in dead:
    print('   ', e)
print('DONE')
'''

code = (TEMPLATE.replace('__B64__', B64)
        .replace('__CUTS__', repr(CUTS))
        .replace('__CANDS__', repr(CANDIDATES)))
d = ROOT / 'kaggle' / 'deadops'
d.mkdir(parents=True, exist_ok=True)
(d / 'deadops.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-deadops",
    "title": "qcc invsqrt44q deadops",
    "code_file": "deadops.py",
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
print('wrote', d / 'deadops.py', len(code), 'bytes')
