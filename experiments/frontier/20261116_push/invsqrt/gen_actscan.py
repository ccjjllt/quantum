"""Generate a Kaggle kernel: per-Toffoli activation scan (no-op / always-on detection)
plus the full-shot official verification of the baseline file.

The activation scan asks, for every Toffoli-like op, whether its control-AND is ever 1
and ever 0 over a sample of inputs.  An op whose activation is identically 0 is an exact
no-op (delete it: -1 Toffoli); one whose activation is identically 1 becomes a CX/CZ
(-1 Toffoli).
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
KMB = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/f2cdab0b.kmb')
RAW = KMB.read_bytes()
B64 = base64.b64encode(RAW).decode()

TEMPLATE = r'''# QCC invsqrt f2cdab0b: Toffoli activation scan + official full verification.
import base64, hashlib, json, os, subprocess, sys
from pathlib import Path
import numpy as np

INPUT = Path('/kaggle/input')


def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]


KSO = _walk('kickmix.so')[0]
COMP = next(p for p in _walk('verify_submission_invsqrt.py') if 'verifiers' in str(p)).parents[2]
sys.path.insert(0, str(KSO.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location('kickmix', str(KSO))
km = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(km)
sys.modules['kickmix'] = km

PAYLOAD = """__B64__"""
raw = base64.b64decode(PAYLOAD)
cand = Path('/kaggle/working/f2cdab0b.kmb')
cand.write_bytes(raw)
print('sha256', hashlib.sha256(raw).hexdigest(), 'bytes', len(raw))
circuit = km.Circuit.from_file(cand, format='auto')
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

# locate Toffoli-like ops
tof = []
for i, l in enumerate(lines):
    parts = l.split()
    if parts[0] in ('CCX', 'CCZ', 'CSWAP'):
        q = [int(t[1:]) for t in parts[1:] if t.startswith('q')]
        tof.append((i, parts[0], q))
print('toffoli-like ops', len(tof))


def to_bits(values, width):
    return (values[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1 == 1


def prefix(n):
    n2 = n
    while n2 < len(lines) and depth[n2] != 0:
        n2 += 1
    return '\n'.join(lines[:n2])


rng = np.random.default_rng(3)
xs = np.unique(rng.integers(1, MAX_X + 1, 256, dtype=np.uint64)).astype(np.uint64)
xb = to_bits(xs, WIDTH)

never, always = [], []
for (i, kind, q) in tof:
    sim = km.Simulator(batch_size=len(xs), debug_print=False, counting_operations=False, seed=5)
    sim.clear_for_shot()
    sim.write_across_shots(km.array([km.q(w) for w in range(WIDTH)]), xb)
    sim.do(km.Circuit(prefix(i)))
    rawv = np.asarray(sim.read_across_shots(km.array([km.q(w) for w in range(Q)])), dtype=np.uint8)
    act = np.ones(len(xs), dtype=bool)
    for w in q[:-1] if kind != 'CSWAP' else q[1:]:
        act &= rawv[w].astype(bool)
    frac = float(act.mean())
    if frac == 0.0:
        never.append((i, kind, q))
    elif frac == 1.0:
        always.append((i, kind, q))
print('activation never 1 (exact no-op):', len(never))
for e in never:
    print('   NEVER', e, lines[e[0]])
print('activation always 1 (Toffoli -> Clifford):', len(always))
for e in always:
    print('   ALWAYS', e, lines[e[0]])
Path('/kaggle/working/activation_scan.json').write_text(json.dumps({'never': never, 'always': always}))

print('=' * 30, 'official verification, default salt, full shots')
env = dict(os.environ, PYTHONPATH=f'{KSO.parent}:{COMP / "verifiers"}')
out = subprocess.run([sys.executable, str(COMP / 'verifiers/invsqrt/verify_submission_invsqrt.py'), str(cand)],
                     capture_output=True, text=True, env=env)
text = out.stdout
try:
    rep = json.loads(text[text.index('{'):])
    print('STATUS', rep['status'], 'score', rep['score'], 'Q', rep['num_qubits'],
          'mean_toffolis', rep.get('mean_toffolis'), 'worst', rep.get('worst_error_over_tolerance'))
    print(json.dumps(rep, indent=1)[:2500])
except Exception as e:
    print('PARSE_FAIL', e, 'rc', out.returncode)
    print(text[-3000:])
    print(out.stderr[-3000:])
print('DONE')
'''

code = TEMPLATE.replace('__B64__', B64)
d = ROOT / 'kaggle' / 'actscan'
d.mkdir(parents=True, exist_ok=True)
(d / 'actscan.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt44q-actscan",
    "title": "qcc invsqrt44q actscan",
    "code_file": "actscan.py",
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
print('wrote', d / 'actscan.py', len(code), 'bytes')
