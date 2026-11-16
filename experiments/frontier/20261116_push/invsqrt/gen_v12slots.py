"""Kernel: bounded Q42 test.  For each blocking block's peak run, list the wires that are
allocated-but-dead across the whole run, and check on the FULL DOMAIN (all 3,133,452 inputs,
2 simulator seeds) whether each is identically 0.  An identically-0 wire can be freed with no
gate at all (it already is |0>), so the slot costs 0 Toffolis.

Also reports, for every non-zero slot, the first failing input.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

TEMPLATE = r'''# QCC invsqrt: Q42 slot test -- is the dead wire at each blocking block identically |0>?
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path
import numpy as np

WORK = Path('/tmp/v12'); OUT = Path('/kaggle/working'); INPUT = Path('/kaggle/input')
WORK.mkdir(parents=True, exist_ok=True)


def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]


KSO = _walk('kickmix.so')[0]
sys.path.insert(0, str(KSO.parent))
_spec = importlib.util.spec_from_file_location('kickmix', str(KSO))
km = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(km)
sys.modules['kickmix'] = km
print('kickmix loaded from the competition host file', flush=True)
VER = next(p for p in _walk('verify_submission_invsqrt.py') if 'verifiers' in str(p)).parents[1]
SRCZIP = next(iter(_walk('invsqrt_source_zip')), None)
zp = WORK / 'src.zip'; zp.write_bytes(SRCZIP.read_bytes())
if (WORK / 'src').exists(): shutil.rmtree(WORK / 'src')
with zipfile.ZipFile(zp) as z: z.extractall(WORK / 'src')
TREE = WORK / 'src/invsqrt_source'
for _p in TREE.rglob('*'):
    if _p.is_file(): _p.chmod(0o755 if _p.suffix in ('.bin', '.sh') else 0o644)
PY = '/usr/bin/python3.13' if Path('/usr/bin/python3.13').exists() else sys.executable
LOADER = TREE / 'src/work/c10/narrow/research/joint_loader'
SEARCH = LOADER / 'search'; SEARCH.mkdir(parents=True, exist_ok=True)
MAX_X = 3133452
WIDTH = 22
print('python', subprocess.run([PY, '-c', 'import platform;print(platform.python_version())'],
                               capture_output=True, text=True).stdout.strip(), flush=True)

# ---- cap-17 first-loader certificate (the proven one; any seed with work_peak 17 works)
def search(cap, seed, seconds=25, tag=None):
    name = tag or f'v8_first_cap{cap}_s{seed}'
    cmd = [PY, '-u', str(LOADER / 'adaptive_loader_v2.py'), '--name', name, '--mode', 'first_raw',
           '--work-cap', str(cap), '--seed', str(seed), '--seconds', str(seconds), '--rounds', '8',
           '--factor-seconds', '0.5', '--tail-seconds', '2']
    subprocess.run(cmd, capture_output=True, text=True,
                   env=dict(os.environ, PYTHONPATH=str(LOADER / 'inputs')))
    p = SEARCH / f'{name}.json'
    d = json.loads(p.read_text())
    return dict(cap=cap, seed=seed, status=d['status'], Toffolis=d['Toffolis'],
                work_peak=d['work_peak'], enrolled=len(d['loaded_output_masks'])), p


cert = None
for seed in (0, 1, 2):
    row, p = search(17, seed)
    print('SEARCH', json.dumps(row), flush=True)
    if row['status'] == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
        cert = p; break
assert cert is not None


def prepare_tree(dst: Path) -> Path:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(TREE / 'src', dst)
    for pp in dst.rglob('*'):
        if pp.is_file(): pp.chmod(0o755 if pp.suffix in ('.bin', '.sh') else 0o644)
    off = dst / 'work/c10/narrow/base/official'
    (off / 'kickmix').mkdir(parents=True, exist_ok=True)
    (off / 'verifier_invsqrt').mkdir(parents=True, exist_ok=True)
    shutil.copy(KSO, off / 'kickmix/kickmix.so')
    shutil.copy(VER / 'invsqrt/verify_submission_invsqrt.py', off / 'verifier_invsqrt/verify_submission_invsqrt.py')
    tok = b'@FG_ROOT@'; base = dst / 'work/c10'
    for d, subdirs, files in os.walk(dst):
        if os.path.abspath(d) == os.path.abspath(base):
            subdirs[:] = []; continue
        for f in files:
            q = Path(d) / f; b = q.read_bytes()
            if tok in b: q.write_bytes(b.replace(tok, str(dst).encode()))
    p = dst / 'patches/patch_ld_first20_56b8.py'
    t = p.read_text()
    old = "    assert data['work_cap'] == data['work_peak'] == 20"
    new = "    assert data['work_cap'] == data['work_peak'] and 14 <= data['work_cap'] <= 20"
    assert old in t
    p.write_text(t.replace(old, new))
    return dst


tree = prepare_tree(WORK / 'tree_slot')
PATCHES = [l.split()[1] for l in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines()
           if l.split() and l.split()[0] == 'patch']
env = dict(os.environ, PY=PY, LD_FIRST_JSON=str(cert), MG='')
for k in ('DIVIDER_FORCE_CAP','DIVIDER_PLACEHOLDER','DIVIDER_RETIRE','LEAD_SECOND_JSON','TK46_SECOND_JSON',
          'W2_E_HOLD','W2_F_HOLD','W2_R2','W2_V10_G1','W2_V9_FORM','W2_V9_PLACEHOLDER','FG','NARROW'):
    env.pop(k, None)
args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
        '--out', str(tree / 'build'), '--name', 'slotraw', '--Q', '46']
for pp in PATCHES:
    args += ['--patch', str(tree / 'patches' / pp)]
o = subprocess.run(args, capture_output=True, text=True, env=env)
print('generator rc', o.returncode, flush=True)
if o.returncode != 0:
    print((o.stdout + o.stderr)[-1200:], flush=True); raise SystemExit
kmx = tree / 'build/slotraw.kmx'
text = kmx.read_text()
cuts = json.loads((tree / 'build/slotraw.build.json').read_text())['cuts']

# ---------------- static profile of the raw emitted text
ops = []
for line in text.splitlines():
    parts = line.split()
    if not parts or parts[0].startswith('#'):
        continue
    ops.append((parts[0], [int(t[1:]) for t in parts[1:] if t.startswith('q')]))
print('ops', len(ops), flush=True)
nq = max(max(q) for _, q in ops if q) + 1


def eff(kind, q):
    if kind == 'CX': return [q[0]], [q[1]]
    if kind == 'CCX': return [q[0], q[1]], [q[2]]
    if kind in ('CZ', 'CCZ', 'Z', 'Z_POW'): return list(q), []
    if kind in ('X', 'R'): return [], list(q)
    if kind in ('HMR', 'SWAP'): return list(q), list(q)
    return [], []


live_mask = [0] * len(ops); live = set()
for i in range(len(ops) - 1, -1, -1):
    rd, wr = eff(*ops[i]); live = (live - set(wr)) | set(rd); live_mask[i] = sum(1 << w for w in live)
clean = [w >= WIDTH for w in range(nq)]
start = [0 if w < WIDTH else None for w in range(nq)]
iv = [[] for _ in range(nq)]
for i, (kind, q) in enumerate(ops):
    for w in q:
        if clean[w]: clean[w] = False; start[w] = i
    if kind == 'HMR':
        w = q[0]
        if start[w] is not None: iv[w].append((start[w], i)); start[w] = None
        clean[w] = True
for w in range(nq):
    if start[w] is not None: iv[w].append((start[w], len(ops) - 1))
occ = [0] * len(ops)
for w in range(nq):
    for (a, b) in iv[w]:
        for i in range(max(0, a), min(len(ops), b + 1)): occ[i] |= 1 << w
for i in range(len(ops)): occ[i] |= live_mask[i]
cnt = [bin(x).count('1') for x in occ]
print('peak occupied', max(cnt), 'peak live', max(bin(m).count('1') for m in live_mask), flush=True)
bounds = [(c['name'], c['instruction_cut']) for c in cuts]
def name_of(i):
    nm = 'pre'
    for name, idx in bounds:
        if i >= idx: nm = name
    return nm

# peak runs, grouped by enclosing stage
peak = max(cnt)
runs = []; st = None
for i, c in enumerate(cnt):
    if c == peak and st is None: st = i
    elif c != peak and st is not None: runs.append((st, i - 1)); st = None
if st is not None: runs.append((st, len(cnt) - 1))
by = {}
for (a, b) in runs:
    nm = name_of(a)
    ent = by.setdefault(nm, dict(n=0, first=a, last=b, runs=0))
    ent['n'] += b - a + 1; ent['runs'] += 1; ent['last'] = b
print('peak-46 runs by stage:', [(k, v['n'], v['runs'], v['first'], v['last']) for k, v in
                                 sorted(by.items(), key=lambda kv: -kv[1]['n'])], flush=True)

# every stage that owns a peak-46 run gets one probe, longest run first
choice = {}
for nm, ent in sorted(by.items(), key=lambda kv: -kv[1]['n']):
    best = None
    for (a, b) in runs:
        if name_of(a) == nm and (best is None or b - a > best[1] - best[0]):
            best = (a, b)
    if best:
        choice[nm] = best
print('chosen peak runs:', choice, flush=True)

# slots = wires that are allocated (dirty) and dead at EVERY op of the run
slots = {}
for nm, (a, b) in choice.items():
    dead = None
    for i in range(a, b + 1):
        s = occ[i] & ~live_mask[i]
        dead = s if dead is None else (dead & s)
    ws = [w for w in range(nq) if dead >> w & 1]
    slots[nm] = ws[:10]
    print(f'block {nm}: run [{a},{b}] len {b-a+1} live(a) {bin(live_mask[a]).count("1")} '
          f'dead-throughout {len(ws)} -> testing {slots[nm]}', flush=True)

# ---------------- full-domain check of the candidate slots
def to_bits(values, width):
    return (values[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1 == 1


def full_domain_ones(nlines, wires, seed):
    """count ones over all official inputs for each wire; returns (counts, first_one_x)."""
    circ = km.Circuit('\n'.join(lines[:nlines]))
    qarr = km.array([km.q(i) for i in range(nq)])
    xarr = km.array([km.q(i) for i in range(WIDTH)])
    counts = {w: 0 for w in wires}
    firstx = {}
    CH = 65536
    for start in range(0, MAX_X, CH):
        n = min(CH, MAX_X - start)
        xs = (np.arange(start, start + n, dtype=np.uint64) % np.uint64(MAX_X)) + np.uint64(1)
        sim = km.Simulator(batch_size=n, debug_print=False, counting_operations=False, seed=seed)
        sim.clear_for_shot()
        sim.write_across_shots(xarr, to_bits(xs, WIDTH))
        sim.do(circ)
        v = np.asarray(sim.read_across_shots(qarr), dtype=np.uint8)
        for w in wires:
            hit = v[w].astype(bool)
            c = int(hit.sum())
            if c:
                counts[w] += c
                if w not in firstx:
                    firstx[w] = int(xs[int(np.argmax(hit))])
    return counts, firstx


lines = [l for l in text.splitlines() if l.strip()]

report = {}
for nm, (a, b) in choice.items():
    wires = slots[nm]
    if not wires:
        continue
    c1, f1 = full_domain_ones(a, wires, 1)
    zeros = [w for w in wires if c1[w] == 0]
    c2 = {w: 0 for w in wires}
    if zeros:
        cc, _ = full_domain_ones(a, zeros, 2)
        c2.update(cc)
    print(f'--- {nm} at op {a} (full domain, 2 seeds)', flush=True)
    for w in wires:
        verdict = 'IDENTICALLY ZERO -> free slot' if (c1[w] == 0 and c2[w] == 0) else 'NONZERO'
        print(f'    q{w}: ones {c1[w]}/{c2[w]}  first_x {f1.get(w)}  {verdict}', flush=True)
        report[f'{nm}:q{w}'] = dict(ones=c1[w], ones_seed2=c2[w], first_x=f1.get(w), verdict=verdict)
Path(OUT / 'slot_test.json').write_text(json.dumps(report, indent=1))
print('DONE')
'''

d = ROOT / 'kaggle' / 'v12slots'
d.mkdir(parents=True, exist_ok=True)
(d / 'v12slots.py').write_text(TEMPLATE)
meta = {
    "id": "jiyujia/qcc-v12-q42-slot-test",
    "title": "qcc v12 q42 slot test",
    "code_file": "v12slots.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": [],
    "dataset_sources": ["jiyujia/qcc-invsqrt-v12-generator-source"],
    "kernel_sources": [],
    "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
    "model_sources": [],
}
(d / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
print('wrote', d / 'v12slots.py', len(TEMPLATE), 'bytes')
