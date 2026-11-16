"""Generate the Kaggle kernel: (A) run the body at Q=45/44/42 past the width guard to find the
first real over-budget block with its live set; (B) per-block 46-peak live sets for the Q=46 body.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
ZIP = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/invsqrt_source_zip')
RAW = ZIP.read_bytes()

PATCH = r'''
# census-only patch: never shipped.
#  - relaxes patch_w47_body's `max_qubits in (46,47,48)` guard so the body really runs at any Q
#  - logs every allocation with its enclosing block label
import atexit
import json
import os
import sys

Q = 46
LABEL = ['init']
LOG = []
ENFORCE = int(os.environ.get('ENFORCE_Q', '0') or 0)

if os.environ.get('CENSUS_PACK') == '1':
    _m = sys.modules.get('variant_patch_patch_w47_body')
    if _m is not None:
        _m.PACK = True
        print('census: PACK forced on before apply()', flush=True)


def _dump():
    p = os.environ.get('CENSUS_OUT')
    if p:
        with open(p, 'w') as f:
            json.dump({'log': LOG, 'enforce': ENFORCE}, f)


atexit.register(_dump)


def apply(ctx):
    km = ctx.km
    base = km.CircuitBuilder

    class Counting(base):
        def set_max_qubits(self, limit):
            LOG.append(['set_max_qubits', int(limit), 0])
            super().set_max_qubits(ENFORCE if ENFORCE else int(limit))

        @property
        def max_qubits(self):
            # the emit_body guard asserts membership in (46, 47, 48); report 46 so the body runs
            return 46

        def alloc_qubits(self, n):
            LOG.append([LABEL[0], int(super().num_allocated_qubits), int(n)])
            return super().alloc_qubits(n)

        def create_quantum_register(self, n):
            LOG.append([LABEL[0], int(super().num_allocated_qubits), int(n)])
            return super().create_quantum_register(n)

    km.CircuitBuilder = Counting

    def wrap(obj, name, label):
        fn = getattr(obj, name, None)
        if fn is None:
            return

        def inner(*a, **k):
            old = LABEL[0]
            LABEL[0] = label
            try:
                return fn(*a, **k)
            finally:
                LABEL[0] = old
        setattr(obj, name, inner)

    comp = ctx.components
    bl = comp['lifecycle'].baseline
    for nm in ('forward', 'inverse'):
        wrap(comp['normalization'], nm, 'normalization.' + nm)
        wrap(comp['root'], nm, 'root.' + nm)
    for nm in ('prepare_H3_initial', 'prepare_H4', 'prepare_H3_current', 'coefficient_forward',
               'seed_forward', 'product_forward', 'coefficient_inverse', 'product_inverse',
               'seed_cleanup', 'root_R_frame', 'erase_high_H', 'merge_coefficient_transcripts'):
        wrap(bl, nm, nm)
    wrap(ctx.tables, 'load_joint16', 'load_joint16')
    wrap(ctx.old.divider, 'compute_phase_cleanup', 'divider_cleanup')
'''

ANALYSIS = r'''
# ---- live-profile analysis of an emitted invsqrt kmx (static, no simulation) ----
def parse_ops(text):
    ops = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith('#'):
            continue
        kind = parts[0]
        q = [int(t[1:]) for t in parts[1:] if t.startswith('q')]
        ops.append((kind, q))
    return ops


def effects(kind, q):
    if kind == 'CX':
        return [q[0]], [q[1]]
    if kind == 'CCX':
        return [q[0], q[1]], [q[2]]
    if kind in ('CZ', 'CCZ', 'Z', 'Z_POW'):
        return list(q), []
    if kind in ('X', 'R'):
        return [], list(q)
    if kind in ('HMR', 'SWAP'):
        return list(q), list(q)
    return [], []


def profile(ops, nq, xw=22):
    live_mask = [0] * len(ops)
    live = set()
    reads = [[] for _ in range(nq)]
    writes = [[] for _ in range(nq)]
    for i in range(len(ops) - 1, -1, -1):
        kind, q = ops[i]
        rd, wr = effects(kind, q)
        live = (live - set(wr)) | set(rd)
        live_mask[i] = sum(1 << w for w in live)
    for i, (kind, q) in enumerate(ops):
        rd, wr = effects(kind, q)
        for w in set(rd):
            reads[w].append(i)
        for w in set(wr):
            writes[w].append(i)
    # dirty intervals
    clean = [w >= xw for w in range(nq)]
    start = [0 if w < xw else None for w in range(nq)]
    iv = [[] for _ in range(nq)]
    for i, (kind, q) in enumerate(ops):
        for w in q:
            if clean[w]:
                clean[w] = False
                start[w] = i
        if kind == 'HMR':
            w = q[0]
            if start[w] is not None:
                iv[w].append((start[w], i))
                start[w] = None
            clean[w] = True
    for w in range(nq):
        if start[w] is not None:
            iv[w].append((start[w], len(ops) - 1))
    occ = [0] * len(ops)
    for w in range(nq):
        for (a, b) in iv[w]:
            for i in range(max(0, a), min(len(ops), b + 1)):
                occ[i] |= 1 << w
    for i in range(len(ops)):
        occ[i] |= live_mask[i]
    cnt = [bin(x).count('1') for x in occ]
    return cnt, live_mask, occ, reads, writes, iv
'''

TEMPLATE = r'''# QCC invsqrt: v12 body at Q=42/44/45 (first real over-budget block) + per-block 46-peak live sets.
import base64, hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

WORK = Path('/tmp/v12')
OUT = Path('/kaggle/working')
INPUT = Path('/kaggle/input')
WORK.mkdir(parents=True, exist_ok=True)


def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]


KSO = _walk('kickmix.so')[0]
VER = next(p for p in _walk('verify_submission_invsqrt.py') if 'verifiers' in str(p)).parents[1]
SRCZIP = next(iter(_walk('invsqrt_source_zip')), None)
assert SRCZIP is not None
zp = WORK / 'src.zip'
zp.write_bytes(SRCZIP.read_bytes())
print('source zip sha256', hashlib.sha256(zp.read_bytes()).hexdigest(), flush=True)
SRC = WORK / 'src'
if SRC.exists():
    shutil.rmtree(SRC)
with zipfile.ZipFile(zp) as z:
    z.extractall(SRC)
TREE = SRC / 'invsqrt_source'
PY = '/usr/bin/python3.13' if Path('/usr/bin/python3.13').exists() else sys.executable
PYV = subprocess.run([PY, '-c', 'import platform;print(platform.python_version())'], capture_output=True, text=True).stdout.strip()
print('python', PYV, flush=True)

PATCH = """__PATCH__"""
ANALYSIS = """__ANALYSIS__"""


def prepare_tree(dst: Path) -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(TREE / 'src', dst)
    for p in dst.rglob('*'):
        if p.is_file():
            p.chmod(0o644)
    off = dst / 'work/c10/narrow/base/official'
    (off / 'kickmix').mkdir(parents=True, exist_ok=True)
    (off / 'verifier_invsqrt').mkdir(parents=True, exist_ok=True)
    shutil.copy(KSO, off / 'kickmix/kickmix.so')
    shutil.copy(VER / 'invsqrt/verify_submission_invsqrt.py', off / 'verifier_invsqrt/verify_submission_invsqrt.py')
    tok = b'@FG_ROOT@'
    base = dst / 'work/c10'
    for d, subdirs, files in os.walk(dst):
        if os.path.abspath(d) == os.path.abspath(base):
            subdirs[:] = []
            continue
        for f in files:
            p = Path(d) / f
            b = p.read_bytes()
            if tok in b:
                p.write_bytes(b.replace(tok, str(dst).encode()))
    (dst / 'patches/patch_census.py').write_text(PATCH)
    return dst


def run(cmd, env=None):
    e = dict(os.environ)
    for k in ('DIVIDER_FORCE_CAP', 'DIVIDER_PLACEHOLDER', 'DIVIDER_RETIRE', 'LD_FIRST_JSON',
              'LEAD_SECOND_JSON', 'TK46_SECOND_JSON', 'W2_E_HOLD', 'W2_F_HOLD', 'W2_R2', 'W2_V10_G1',
              'W2_V9_FORM', 'W2_V9_PLACEHOLDER', 'FG', 'NARROW'):
        e.pop(k, None)
    if env:
        e.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=e)


PATCHES = [l.split()[1] for l in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines()
           if l.split() and l.split()[0] == 'patch']


def build_body(tag, enforce_q, pack, pipe=False):
    tree = prepare_tree(WORK / f'tree_{tag}')
    cpath = WORK / f'{tag}.census.json'
    name = tag
    args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
            '--out', str(tree / 'build'), '--name', name, '--Q', '46']
    for p in PATCHES:
        args += ['--patch', str(tree / 'patches' / p)]
    args += ['--patch', str(tree / 'patches/patch_census.py')]
    out = run(args, env={'CENSUS_PACK': '1' if pack else '0', 'ENFORCE_Q': str(enforce_q),
                         'CENSUS_OUT': str(cpath), 'PY': PY})
    print('=' * 24, f'{tag}: Q={enforce_q} PACK={pack} rc={out.returncode}', flush=True)
    if out.returncode != 0:
        tail = (out.stdout + out.stderr).strip().splitlines()
        for l in tail[-8:]:
            print('   ', l)
    best = {}
    rows = []
    if cpath.exists():
        d = json.loads(cpath.read_text())
        rows = d['log']
        for label, cur, n in rows:
            best[label] = max(best.get(label, 0), cur + n)
        print('   per-block peak demand:', sorted(best.items(), key=lambda kv: -kv[1])[:8], flush=True)
        print('   last 3 allocation events:', rows[-3:], flush=True)
    kmx = tree / 'build' / (name + '.kmx')
    bjson = tree / 'build' / (name + '.build.json')
    return out, tree, kmx, bjson


# ---------------- A. push the body below 46
res = {}
for q in (45, 44, 42):
    out, tree, kmx, bjson = build_body(f'q{q}', q, True)
    res[q] = dict(rc=out.returncode, kmx_exists=kmx.exists())

# ---------------- B. the shipped 46Q body: per-block 46-peaks and their live sets
out, tree, kmx, bjson = build_body('q46raw', 0, False)
print('raw build rc', out.returncode, 'kmx', kmx.exists(), flush=True)
if kmx.exists():
    text = kmx.read_text()
    exec(compile(ANALYSIS, '<analysis>', 'exec'), globals())
    ops = parse_ops(text)
    nq = max(max(q) for _, q in ops if q) + 1
    cnt, live_mask, occ, reads, writes, iv = profile(ops, nq)
    print(f'parsed ops {len(ops)} qubits {nq} peak occupied {max(cnt)} peak live {max(bin(m).count("1") for m in live_mask)}', flush=True)
    cuts = json.loads(bjson.read_text())['cuts'] if bjson.exists() else []
    print('cuts:', [(c['name'], c['instruction_cut'], c['live_qubits']) for c in cuts], flush=True)
    # cluster the peak ops
    peak = max(cnt)
    runs = []
    st = None
    for i, c in enumerate(cnt):
        if c == peak and st is None:
            st = i
        elif c != peak and st is not None:
            runs.append((st, i - 1))
            st = None
    if st is not None:
        runs.append((st, len(cnt) - 1))
    print(f'peak {peak}: {len(runs)} runs, total {sum(b - a + 1 for a, b in runs)} ops', flush=True)
    # name runs by the enclosing cut interval, and report held (live but unread) wires
    bounds = [(c['name'], c['instruction_cut']) for c in cuts]
    def name_of(i):
        nm = 'pre'
        for name, idx in bounds:
            if i >= idx:
                nm = name
        return nm
    by_block = {}
    for (a, b) in runs:
        nm = name_of(a)
        ent = by_block.setdefault(nm, dict(n=0, runs=0, first=a, last=b, peak=0))
        ent['n'] += b - a + 1
        ent['runs'] += 1
        ent['last'] = b
        ent['peak'] = max(ent['peak'], max(cnt[a:b + 1]))
    print('peak-run census by enclosing cut name:', flush=True)
    for nm, e in sorted(by_block.items(), key=lambda kv: -kv[1]['n']):
        print(f'   {nm:30s} ops_at_peak {e["n"]:5d} runs {e["runs"]:3d} span [{e["first"]},{e["last"]}]', flush=True)
    # for the longest run of each block, list live wires and which are never read inside
    seen = set()
    detailed = 0
    for (a, b) in sorted(runs, key=lambda t: -(t[1] - t[0]))[:40]:
        nm = name_of(a)
        if nm in seen or detailed >= 8:
            continue
        seen.add(nm)
        detailed += 1
        lv = [w for w in range(nq) if live_mask[a] >> w & 1]
        held = [w for w in lv if not [i for i in reads[w] if a <= i <= b]]
        touched = [w for w in lv if w not in held]
        print(f'--- block {nm}: run [{a},{b}] len {b-a+1} live {len(lv)}', flush=True)
        print(f'    live   {lv}', flush=True)
        print(f'    read-in {touched}', flush=True)
        print(f'    HELD (live, never read inside) {held}', flush=True)
Path(OUT / 'report.json').write_text(json.dumps(res, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__PATCH__', PATCH).replace('__ANALYSIS__', ANALYSIS)
d = ROOT / 'kaggle' / 'v12blocks'
d.mkdir(parents=True, exist_ok=True)
(d / 'v12blocks.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-v12-block-ledger",
    "title": "qcc v12 block ledger",
    "code_file": "v12blocks.py",
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
print('wrote', d / 'v12blocks.py', len(code), 'bytes; zip sha', hashlib.sha256(RAW).hexdigest())
