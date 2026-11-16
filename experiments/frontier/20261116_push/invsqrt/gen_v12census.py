"""Generate the Kaggle kernel: v12 generator build gate + width census (dataset-attached source)."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
ZIP = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/invsqrt_source_zip')
RAW = ZIP.read_bytes()

CENSUS_PATCH = r'''
# census-only patch: never shipped.  Records every qubit allocation with its block label and
# serves over-budget allocations from a hidden reserve, so one build reports *every* block
# that would exceed the nominal width (not just the first failure).
import atexit
import json
import os
import sys

Q = 46
LABEL = ['init']
LOG = []
OVER = []
RESERVE = int(os.environ.get('CENSUS_RESERVE', '0'))
ENFORCE = int(os.environ.get('ENFORCE_Q', '0') or 0)

# must happen at import time: patch_w47_body.apply() returns early unless PACK is already on
if os.environ.get('CENSUS_PACK') == '1':
    _m = sys.modules.get('variant_patch_patch_w47_body')
    if _m is not None:
        _m.PACK = True
        print('census: PACK forced on before apply()', flush=True)


def _dump():
    p = os.environ.get('CENSUS_OUT')
    if p:
        with open(p, 'w') as f:
            json.dump({'log': LOG, 'over': OVER, 'reserve': RESERVE, 'enforce': ENFORCE}, f)


atexit.register(_dump)


def apply(ctx):
    km = ctx.km
    base = km.CircuitBuilder

    class Counting(base):
        def __init__(self):
            super().__init__()
            self._reserve = []
            if RESERVE:
                self._reserve = list(super().alloc_qubits(RESERVE))
                LOG.append(['__reserve__', 0, RESERVE])

        def set_max_qubits(self, limit):
            LOG.append(['set_max_qubits', int(limit), 0])
            super().set_max_qubits((ENFORCE if ENFORCE else int(limit)) + RESERVE)

        @property
        def max_qubits(self):
            return 46 if RESERVE else super().max_qubits

        @property
        def num_allocated_qubits(self):
            n = int(super().num_allocated_qubits)
            return n - RESERVE if RESERVE else n

        @property
        def num_free_qubits(self):
            n = int(super().num_free_qubits)
            return n - len(self._reserve) if RESERVE else n

        def alloc_qubits(self, n):
            cur = int(self.num_allocated_qubits)
            LOG.append([LABEL[0], cur, int(n)])
            try:
                return super().alloc_qubits(n)
            except ValueError:
                if len(self._reserve) < n:
                    raise
                got = [self._reserve.pop(0) for _ in range(n)]
                OVER.append([LABEL[0], cur, int(n)])
                return km.array(got)

        def create_quantum_register(self, n):
            LOG.append([LABEL[0], int(self.num_allocated_qubits), int(n)])
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
    wrap(comp['normalization'], 'forward', 'normalization.forward')
    wrap(comp['normalization'], 'inverse', 'normalization.inverse')
    wrap(comp['root'], 'forward', 'root.forward')
    wrap(comp['root'], 'inverse', 'root.inverse')
    for nm in ('prepare_H3_initial', 'prepare_H4', 'prepare_H3_current', 'coefficient_forward',
               'seed_forward', 'product_forward', 'coefficient_inverse', 'product_inverse',
               'seed_cleanup', 'root_R_frame', 'erase_high_H', 'merge_coefficient_transcripts'):
        wrap(bl, nm, nm)
    wrap(ctx.tables, 'load_joint16', 'load_joint16')
    wrap(ctx.old.divider, 'compute_phase_cleanup', 'divider_cleanup')
'''

TEMPLATE = r'''# QCC invsqrt: v12 generator build gate + width census (Kaggle CPU, no internet).
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
print('kickmix.so', KSO, '\nverifiers dir', VER, flush=True)
print('verifier listing', sorted(p.name for p in VER.rglob('*') if p.is_file())[:8], flush=True)

SRCZIP = next(iter(_walk('invsqrt_source_zip')), None)
assert SRCZIP is not None, 'invsqrt_source_zip not mounted'
zp = WORK / 'invsqrt_source.zip'
zp.write_bytes(SRCZIP.read_bytes())
print('source zip sha256', hashlib.sha256(zp.read_bytes()).hexdigest(), 'bytes', zp.stat().st_size, flush=True)
SRC = WORK / 'src'
if SRC.exists():
    shutil.rmtree(SRC)
with zipfile.ZipFile(zp) as z:
    z.extractall(SRC)
TREE = SRC / 'invsqrt_source'
print('tree', TREE, 'files', sum(1 for _ in TREE.rglob('*') if _.is_file()), flush=True)

PY = '/usr/bin/python3.13' if Path('/usr/bin/python3.13').exists() else sys.executable
print('python', subprocess.run([PY, '-c', 'import sys,platform;print(platform.python_version(),sys.version_info[:2])'],
                               capture_output=True, text=True).stdout.strip(), flush=True)
print(subprocess.run([PY, '-c', 'import numpy;print("numpy",numpy.__version__)'], capture_output=True, text=True).stdout.strip(), flush=True)

CENSUS = """__CENSUS__"""


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
    for f in ('verify_submission_invsqrt.py',):
        shutil.copy(VER / 'invsqrt' / f, off / 'verifier_invsqrt' / f)
    tok = b'@FG_ROOT@'
    n = 0
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
                n += 1
    (dst / 'patches/patch_census.py').write_text(CENSUS)
    print(f'prepared {dst} (relocated {n} files)', flush=True)
    return dst


def run(cmd, env=None, timeout=None):
    e = dict(os.environ)
    for k in ('DIVIDER_FORCE_CAP', 'DIVIDER_PLACEHOLDER', 'DIVIDER_RETIRE', 'LD_FIRST_JSON',
              'LEAD_SECOND_JSON', 'TK46_SECOND_JSON', 'W2_E_HOLD', 'W2_F_HOLD', 'W2_R2', 'W2_V10_G1',
              'W2_V9_FORM', 'W2_V9_PLACEHOLDER', 'FG', 'NARROW'):
        e.pop(k, None)
    if env:
        e.update(env)
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=timeout)
    return out, time.time() - t0


# ---------------- 1. toolchain gate
print('=' * 26, 'gate: build.sh at Q=46', flush=True)
out, secs = run(['bash', str(TREE / 'build.sh'), str(KSO.parent), str(VER), str(WORK / 'gate')],
                env={'PY': PY, 'WORK': str(WORK / 'gatework')})
print(f'gate rc={out.returncode} in {secs:.0f}s')
print(out.stdout[-3000:])
if out.returncode != 0:
    print('GATE STDERR/TAIL', out.stderr[-2000:])
gate_ok = 'BUILT invsqrt.kmb 321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177' in out.stdout
print('GATE_PASS', gate_ok, flush=True)

# ---------------- 2. census
PATCHES = []
for line in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines():
    parts = line.split()
    if parts and parts[0] == 'patch':
        PATCHES.append(parts[1])
print('patch args:', len(PATCHES), flush=True)


def summarise(path):
    d = json.loads(Path(path).read_text())
    rows, over = d['log'], d['over']
    best = {}
    for label, cur, n in rows:
        best[label] = max(best.get(label, 0), cur + n)
    order = sorted(best.items(), key=lambda kv: -kv[1])
    print('   per-block peak demand:')
    for label, v in order:
        print(f'     {v:3d}  {label}')
    if over:
        byb = {}
        for label, cur, n in over:
            byb[label] = max(byb.get(label, 0), cur + n)
        print('   OVER-budget allocations (block -> demand):',
              sorted(byb.items(), key=lambda kv: -kv[1]))
    else:
        print('   no over-budget allocation: the body fits')
    return best, rows


def census(tag, enforce_q, pack):
    tree = prepare_tree(WORK / f'tree_{tag}')
    cpath = WORK / f'{tag}.census.json'
    args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
            '--out', str(tree / 'build'), '--name', tag, '--Q', '46']
    for p in PATCHES:
        args += ['--patch', str(tree / 'patches' / p)]
    args += ['--patch', str(tree / 'patches/patch_census.py')]
    out, secs = run(args, env={'CENSUS_PACK': '1' if pack else '0', 'ENFORCE_Q': str(enforce_q),
                               'CENSUS_OUT': str(cpath), 'PY': PY})
    print('=' * 26, f'census {tag}: enforce Q={enforce_q} PACK={pack} rc={out.returncode} {secs:.0f}s', flush=True)
    body = (out.stdout or '').strip().splitlines()
    print('   stdout tail:', body[-3:] if body else '(empty)')
    if out.returncode != 0:
        tail = (out.stdout + out.stderr).strip().splitlines()
        print('   FAILURE TAIL:')
        for l in tail[-10:]:
            print('     ', l)
    if cpath.exists():
        best, rows = summarise(cpath)
        print('   last 6 allocation events:', rows[-6:])
        return out, best
    print('   (no census log)')
    return out, {}


out46, best46 = census('census46', 0, False)
for p in (WORK / 'tree_census46' / 'build').glob('*.build.json'):
    d = json.loads(p.read_text())
    print('BUILD', p.name, 'Q', d['Q'], flush=True)
    print('cost_model', json.dumps(d['cost_model']), flush=True)
    print('exact_native_expectation', json.dumps(d.get('exact_native_expectation', {}).get('static', {}))[:400], flush=True)
    print('cuts raw:', json.dumps(d['cuts'])[:1200], flush=True)

out45, best45 = census('census45', 45, True)
out44, best44 = census('census44', 44, True)
out42, best42 = census('census42', 42, True)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'report.json').write_text(json.dumps({'gate_pass': gate_ok, 'census46': best46,
                                             'census45': best45, 'census44': best44,
                                             'census42': best42}, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__CENSUS__', CENSUS_PATCH)
d = ROOT / 'kaggle' / 'v12census'
d.mkdir(parents=True, exist_ok=True)
(d / 'v12census.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-v12-width-census",
    "title": "qcc v12 width census",
    "code_file": "v12census.py",
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
print('wrote', d / 'v12census.py', len(code), 'bytes; zip sha', hashlib.sha256(RAW).hexdigest())
