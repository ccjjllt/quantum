"""Generate the Kaggle 'plan' kernel: relation requests with exact retired-source exclusions,
plus value-continuity checks between each zero site and its rebuild site.
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

IDLE10 = [10, 11, 12, 13, 14, 15, 16, 17, 19, 43]
FLAGS = [22, 23, 24, 25]

# (cut, retired set, targets) in execution order
SITES = [
    # Phase A: zero the four flags at 430 (window 1 start)
    (430, [], [22]),
    (430, [22], [23]),
    (430, [22, 23], [24]),
    (430, [22, 23, 24], [25]),
    # Phase B at 6610: rebuild the flags, then zero the ten idle wires
    (6610, [23, 24, 25], [22]),
    (6610, [24, 25], [23]),
    (6610, [25], [24]),
    (6610, [], [25]),
    (6610, [], [10]),
    (6610, [10], [11]),
    (6610, [10, 11], [12]),
    (6610, [10, 11, 12], [13]),
    (6610, [10, 11, 12, 13], [14]),
    (6610, [10, 11, 12, 13, 14], [15]),
    (6610, [10, 11, 12, 13, 14, 15], [16]),
    (6610, [10, 11, 12, 13, 14, 15, 16], [17]),
    (6610, [10, 11, 12, 13, 14, 15, 16, 17], [19]),
    (6610, [10, 11, 12, 13, 14, 15, 16, 17, 19], [43]),
    # Phase C at 7347: rebuild the ten idle wires (reverse order), flags still live except q22
    (7347, [22, 10, 11, 12, 13, 14, 15, 16, 17, 19], [43]),
    (7347, [22, 10, 11, 12, 13, 14, 15, 16, 17], [19]),
    (7347, [22, 10, 11, 12, 13, 14, 15, 16], [17]),
    (7347, [22, 10, 11, 12, 13, 14, 15], [16]),
    (7347, [22, 10, 11, 12, 13, 14], [15]),
    (7347, [22, 10, 11, 12, 13], [14]),
    (7347, [22, 10, 11, 12], [13]),
    (7347, [22, 10, 11], [12]),
    (7347, [22, 10], [11]),
    (7347, [22], [10]),
    # Phase C2 at 7350: zero q23, q24, q25 (window 2 start)
    (7350, [], [23]),
    (7350, [23], [24]),
    (7350, [23, 24], [25]),
    # Phase D at 20500: rebuild q22 (zeroed at 7305), q23, q24, q25
    (20500, [23, 24, 25], [22]),
    (20500, [24, 25], [23]),
    (20500, [25], [24]),
    (20500, [], [25]),
]

# continuity pairs: (wire, cut_a, cut_b) values must be identical
CONTINUITY = [
    (22, 430, 6610), (23, 430, 6610), (24, 430, 6610), (25, 430, 6610),
    (22, 7305, 20500), (23, 7350, 20500), (24, 7350, 20500), (25, 7350, 20500),
] + [(w, 6610, 7347) for w in IDLE10]

CUTS = sorted({c for (c, _, _) in SITES} | {c for (_, a, b) in CONTINUITY for c in (a, b)})

TEMPLATE = r'''# QCC invsqrt f2cdab0b: relation requests with retired-source exclusion + continuity checks.
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
print('sha', hashlib.sha256(raw).hexdigest(), 'Q', circuit.num_qubits, 'lines', len(lines))

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
    if raw.shape != (Q, len(xs)):
        raise AssertionError(f'unexpected read shape {raw.shape}, expected {(Q, len(xs))}')
    return raw.T


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
    rng.integers(1, MAX_X + 1, 2500, dtype=np.uint64),
    np.array([1, 2, 3, 4, 5, 7, 8, 15, 16, 17, 1023, 1024, 1025, 4095, 4096,
              65535, 65536, 1048575, 1048576, 2097151, 2097152, MAX_X - 1, MAX_X], dtype=np.uint64),
])).astype(np.uint64)
print('probe xs', len(probe_xs))

CUTS = [0] + __CUTS__
SITES = __SITES__
CONTINUITY = __CONT__

vals = {}
for cut0 in CUTS:
    cut = snap(cut0)
    v0 = read_all(cut, probe_xs, seed=11)
    v1 = read_all(cut, probe_xs, seed=12)
    nondet = [w for w in range(Q) if not np.array_equal(v0[:, w], v1[:, w])]
    vals[cut0] = (cut, v0, [to_int(v0[:, w]) for w in range(Q)], nondet)
    print(f'CUT {cut0}->{cut} nondet {nondet}')

# sanity: empty prefix must reproduce the input register
c0, v0c, i0c, nd0 = vals[0]
if not np.array_equal(v0c[:, :WIDTH], to_bits(probe_xs, WIDTH).T):
    raise AssertionError('cut-0 sanity failed: x register mismatch')
print('cut-0 sanity OK (shape', v0c.shape, ')')

print('--- continuity ---')
cont_ok = {}
for (w, a, b) in CONTINUITY:
    ca, va, ia, _ = vals[a]
    cb, vb, ib, _ = vals[b]
    same = np.array_equal(va[:, w], vb[:, w])
    cont_ok[f'{w}:{a}:{b}'] = bool(same)
    print(f'  q{w} at {a}=={b}: {same}')

print('--- relations ---')
out = []
for (cut0, retired, targets) in SITES:
    cut, v0, vecs, nondet = vals[cut0]
    allowed = [u for u in range(Q) if u not in retired]
    for t in targets:
        basis_wires = [u for u in allowed if u != t]
        if t in nondet:
            print(f'  cut {cut0} target q{t}: NONDETERMINISTIC')
            out.append({'cut': cut0, 'retired': retired, 'target': t, 'src': None, 'const': None})
            continue
        combo = solve_span([vecs[u] for u in basis_wires], vecs[t])
        if combo is None:
            print(f'  cut {cut0} target q{t} retired {retired}: NO RELATION')
            out.append({'cut': cut0, 'retired': retired, 'target': t, 'src': None, 'const': None})
        else:
            src = [basis_wires[k] for k in range(len(basis_wires)) if combo >> k & 1]
            const = (combo >> len(basis_wires)) & 1
            print(f'  cut {cut0} target q{t} retired {retired}: = XOR{src} + {const}')
            out.append({'cut': cut0, 'retired': retired, 'target': t, 'src': src, 'const': const})

Path('/kaggle/working/plan_result.json').write_text(json.dumps({'sites': out, 'continuity': cont_ok}, indent=1))
print('DONE')
'''

code = (TEMPLATE.replace('__B64__', B64)
        .replace('__CUTS__', repr(CUTS))
        .replace('__SITES__', repr(SITES))
        .replace('__CONT__', repr(CONTINUITY)))
d = ROOT / 'kaggle' / 'plan'
d.mkdir(parents=True, exist_ok=True)
(d / 'plan.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-plan",
    "title": "qcc invsqrt44q plan",
    "code_file": "plan.py",
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
print('wrote', d / 'plan.py', len(code), 'bytes; cuts', CUTS)
