"""Generate the Kaggle AND-search kernel: flag values as XOR of <=k products of wire pairs.

For each (cut, target) pair, search
    V_t = XOR_{i<=k} (a_i & b_i)  XOR  affine(non-flag wires)
with a_i,b_i drawn from the non-flag wires. k = 1, 2, 3 (3 via meet-in-the-middle).
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

CUTS = [430, 6610, 7305, 7350, 20500]
TARGETS = [22, 23, 24, 25]
FLAGS = [22, 23, 24, 25]

TEMPLATE = r'''# QCC invsqrt f2cdab0b: search flag values as XOR of <=k pairwise ANDs + affine part.
import base64, hashlib, json, os, sys, itertools
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
    raw = np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(Q)])), dtype=np.uint8)
    assert raw.shape == (Q, len(xs)), raw.shape
    return raw.T


def to_int(bits):
    return int.from_bytes(np.packbits(np.asarray(bits, dtype=np.uint8), bitorder='little').tobytes(), 'little')


class Span:
    def __init__(self, vecs, names):
        self.basis = {}
        self.names = names
        for name, v in zip(names, vecs):
            combo = 1 << name
            while v:
                p = v.bit_length() - 1
                hit = self.basis.get(p)
                if hit is None:
                    self.basis[p] = (v, combo)
                    break
                v ^= hit[0]
                combo ^= hit[1]

    def reduce(self, v):
        while v:
            hit = self.basis.get(v.bit_length() - 1)
            if hit is None:
                return v
            v ^= hit[0]
        return 0

    def solve(self, v):
        combo = 0
        while v:
            hit = self.basis.get(v.bit_length() - 1)
            if hit is None:
                return None
            v ^= hit[0]
            combo ^= hit[1]
        return [self.names[k] for k in range(max(self.names) + 1) if combo >> k & 1]


rng = np.random.default_rng(7)
probe_xs = np.unique(np.concatenate([
    rng.integers(1, MAX_X + 1, 1500, dtype=np.uint64),
    np.array([1, 2, 3, 5, 8, 17, 1024, 4096, 65536, 1048576, MAX_X], dtype=np.uint64),
])).astype(np.uint64)
print('probe xs', len(probe_xs))

CUTS = __CUTS__
TARGETS = __TARGETS__
FLAGS = __FLAGS__

results = []
for cut0 in CUTS:
    cut = snap(cut0)
    v = read_all(cut, probe_xs, seed=11)
    vecs = {w: to_int(v[:, w]) for w in range(Q)}
    for t in TARGETS:
        allowed = [w for w in range(Q) if w not in FLAGS and w != t]
        sp = Span([vecs[w] for w in allowed], allowed)
        target = sp.reduce(vecs[t])
        entry = {'cut': cut0, 'target': t, 'affine': target == 0, 'k': None, 'and': None, 'aff': None}
        if target == 0:
            entry['aff'] = sp.solve(vecs[t])
            entry['k'] = 0
            print(f'cut {cut0} q{t}: k=0 affine {entry["aff"]}')
            results.append(entry)
            continue
        pairs = [(a, b) for i, a in enumerate(allowed) for b in allowed[i + 1:]]
        prod = {}
        for (a, b) in pairs:
            prod[(a, b)] = sp.reduce(vecs[a] & vecs[b])
        hit = None
        for (a, b), c in prod.items():
            if c == target:
                hit = ([(a, b)], None)
                break
        k = 1
        if hit is None:
            k = 2
            # target ^ canon(ab) == canon(cd)
            want = {}
            for (c, d), val in prod.items():
                want.setdefault(val, (c, d))
            for (a, b), val in prod.items():
                need = target ^ val
                if need in want:
                    hit = ([(a, b), want[need]], None)
                    break
        if hit is None:
            k = 3
            two = {}
            for (a, b), v1 in prod.items():
                for (c, d), v2 in prod.items():
                    two.setdefault(v1 ^ v2, ((a, b), (c, d)))
            for (e, f), val in prod.items():
                need = target ^ val
                if need in two:
                    hit = (list(two[need]) + [(e, f)], None)
                    break
        if hit is not None:
            entry['k'] = k
            entry['and'] = hit[0]
            resid = vecs[t]
            for (a, b) in hit[0]:
                resid ^= (vecs[a] & vecs[b])
            entry['aff'] = sp.solve(resid)
            print(f'cut {cut0} q{t}: k={k} ANDs {hit[0]} affine {entry["aff"]}')
        else:
            print(f'cut {cut0} q{t}: none up to k=3')
        results.append(entry)

Path('/kaggle/working/and_result.json').write_text(json.dumps(results, indent=1))
print('DONE')
'''

code = (TEMPLATE.replace('__B64__', B64)
        .replace('__CUTS__', repr(CUTS))
        .replace('__TARGETS__', repr(TARGETS))
        .replace('__FLAGS__', repr(FLAGS)))
d = ROOT / 'kaggle' / 'andsearch'
d.mkdir(parents=True, exist_ok=True)
(d / 'andsearch.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-andsearch",
    "title": "qcc invsqrt44q andsearch",
    "code_file": "andsearch.py",
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
print('wrote', d / 'andsearch.py', len(code), 'bytes')
