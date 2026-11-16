"""Generate a Kaggle probe: for each cut, the full affine (GF(2)) relation table over all wires."""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

CUTS = [430, 6610, 6616, 6731, 6732, 6843, 6844, 6845, 6856, 6857, 6975, 6976, 6977, 7232, 7233,
        7305, 7347, 20500]

TEMPLATE = r'''# QCC invsqrt f2cdab0b: affine relation table at chosen cut points (all wires).
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
print('sha', hashlib.sha256(raw).hexdigest(), 'Q', circuit.num_qubits)
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
    return np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(Q)])), dtype=np.uint8)


def to_int(bits):
    return int.from_bytes(np.packbits(np.asarray(bits, dtype=np.uint8), bitorder='little').tobytes(), 'little')


def solve_span(vecs, target):
    basis = {}
    for i, v in enumerate(vecs):
        combo = 1 << i
        while v:
            p = v.bit_length() - 1
            hit = basis.get(p)
            if hit is None:
                basis[p] = (v, combo)
                break
            v ^= hit[0]
            combo ^= hit[1]
    v, combo = target, 0
    while v:
        hit = basis.get(v.bit_length() - 1)
        if hit is None:
            return None
        v ^= hit[0]
        combo ^= hit[1]
    return combo


rng = np.random.default_rng(7)
probe_xs = np.unique(np.concatenate([
    rng.integers(1, MAX_X + 1, 2200, dtype=np.uint64),
    np.array([1, 2, 3, 4, 5, 7, 8, 15, 16, 17, 1023, 1024, 1025, 4095, 4096,
              65535, 65536, 1048575, 1048576, 2097151, 2097152, MAX_X - 1, MAX_X], dtype=np.uint64),
])).astype(np.uint64)
print('probe xs', len(probe_xs))

CUTS = __CUTS__
report = {}
for cut0 in CUTS:
    cut = snap(cut0)
    try:
        v0 = read_all(cut, probe_xs, seed=11)
        v1 = read_all(cut, probe_xs, seed=12)
        nondet = [w for w in range(Q) if not np.array_equal(v0[:, w], v1[:, w])]
        vecs = [to_int(v0[:, w]) for w in range(Q)]
        rel = {}
        for w in range(Q):
            if w in nondet:
                continue
            others = [u for u in range(Q) if u != w]
            combo = solve_span([vecs[u] for u in others], vecs[w])
            if combo is not None:
                src = [others[k] for k in range(len(others)) if combo >> k & 1]
                rel[w] = [src, (combo >> len(others)) & 1]
        report[cut] = {'asked': cut0, 'nondet': nondet, 'rel': rel}
        print(f'CUT {cut} (asked {cut0}): nondet {nondet} n_rel {len(rel)}')
        for w in sorted(rel):
            src, const = rel[w]
            print(f'   q{w} = XOR{src} + {const}')
    except Exception as exc:
        print(f'CUT {cut0} FAILED: {exc!r}')

Path('/kaggle/working/relations.json').write_text(json.dumps(report, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__B64__', B64).replace('__CUTS__', repr(CUTS))
d = ROOT / 'kaggle' / 'relate'
d.mkdir(parents=True, exist_ok=True)
(d / 'relate.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-relate",
    "title": "qcc invsqrt44q relate",
    "code_file": "relate.py",
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
print('wrote', d / 'relate.py', len(code), 'bytes; sha', hashlib.sha256(RAW).hexdigest())
