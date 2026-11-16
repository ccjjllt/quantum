"""Generate the Kaggle kernel: (1) loader certificate re-search at work_cap 19/18,
(2) drop-in build at Q=44/42 with the new certificate, (3) census of the next blocker.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
ZIP = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/invsqrt_source_zip')
RAW = ZIP.read_bytes()

CENSUS_PATCH = r'''
# census-only patch; relaxes the body guard so the emitter runs at any Q.
import atexit, json, os, sys
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

TEMPLATE = r'''# QCC invsqrt: loader certificate re-search (cap 19/18) + drop-in build + next-block census.
import hashlib, json, os, shutil, subprocess, sys, time, zipfile
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
zp = WORK / 'src.zip'
zp.write_bytes(SRCZIP.read_bytes())
SRC = WORK / 'src'
if SRC.exists():
    shutil.rmtree(SRC)
with zipfile.ZipFile(zp) as z:
    z.extractall(SRC)
TREE = SRC / 'invsqrt_source'
# zip extraction drops the executable bit; the loader search spawns its own helper binary
for _p in TREE.rglob('*'):
    if _p.is_file():
        _p.chmod(0o755 if _p.suffix in ('.bin', '.sh') else 0o644)
print('chmod: helper binaries marked executable', flush=True)
PY = '/usr/bin/python3.13' if Path('/usr/bin/python3.13').exists() else sys.executable
print('python', subprocess.run([PY, '-c', 'import platform;print(platform.python_version())'],
                               capture_output=True, text=True).stdout.strip(), flush=True)
print('source tree', TREE, flush=True)

CENSUS = """__CENSUS__"""
LOADER = TREE / 'src/work/c10/narrow/research/joint_loader'
SEARCH = LOADER / 'search'
SEARCH.mkdir(parents=True, exist_ok=True)

# ---------------- 1. certificate re-search at lower work caps
def search(cap, seed, seconds=20, resume=None, tag=None):
    name = tag or f'v4_first_cap{cap}_s{seed}'
    cmd = [PY, '-u', str(LOADER / 'adaptive_loader_v2.py'), '--name', name,
           '--mode', 'first_raw', '--work-cap', str(cap), '--seed', str(seed),
           '--seconds', str(seconds), '--rounds', '8', '--factor-seconds', '0.5', '--tail-seconds', '2']
    if resume:
        cmd += ['--resume', str(resume)]
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONPATH=str(LOADER / 'inputs')))
    p = SEARCH / f'{name}.json'
    row = dict(cap=cap, seed=seed, tag=name, secs=round(time.time() - t0, 1), rc=out.returncode)
    if out.returncode != 0:
        err = (out.stderr or out.stdout or '').strip().splitlines()
        row['err'] = ' | '.join(err[-6:])[:600]
    if p.exists():
        d = json.loads(p.read_text())
        row.update(status=d['status'], Toffolis=d['Toffolis'], work_peak=d['work_peak'],
                   loaded=len(d['loaded_output_masks']), sha=hashlib.sha256(p.read_bytes()).hexdigest())
    else:
        row.update(status='NO_FILE', err=(out.stderr or '')[-300:])
    return row, p


CAND = {}
for cap in (20, 19, 18):
    best = None
    for seed in range(4):
        row, p = search(cap, seed)
        print('SEARCH', json.dumps(row), flush=True)
        if row.get('status') == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
            if best is None or row['Toffolis'] < best[0]['Toffolis']:
                best = (row, p)
        elif best is None and (not CAND.get(cap) or row.get('loaded', 0) > CAND[cap][0].get('loaded', -1)):
            CAND[cap] = (row, p)
    if best is None and cap in CAND:
        # resume the most-loaded partial two more times
        for k in range(3):
            row, p = search(cap, 100 + k, resume=CAND[cap][1], tag=f'v4_first_cap{cap}_res{k}')
            print('RESUME', json.dumps(row), flush=True)
            if row.get('status') == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
                best = (row, p)
                break
            if row.get('loaded', 0) > CAND[cap][0].get('loaded', -1):
                CAND[cap] = (row, p)
    if best is not None:
        print(f'*** cap {cap} COMPLETE: Toffolis {best[0]["Toffolis"]} peak {best[0]["work_peak"]} '
              f'sha {best[0]["sha"]}', flush=True)
        CAND[cap] = best
Path(OUT / 'search.json').write_text(json.dumps({str(k): v[0] for k, v in CAND.items()}, indent=1))

# ---------------- 2. patch the loader cap assert (tree copy only)
def relax_loader_assert(tree):
    p = tree / 'patches/patch_ld_first20_56b8.py'
    t = p.read_text()
    old = "    assert data['work_cap'] == data['work_peak'] == 20"
    new = "    assert data['work_cap'] == data['work_peak'] and 14 <= data['work_cap'] <= 20"
    assert old in t, 'cap assert not found'
    p.write_text(t.replace(old, new))


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
    (dst / 'patches/patch_census.py').write_text(CENSUS)
    relax_loader_assert(dst)
    return dst


PATCHES = [l.split()[1] for l in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines()
           if l.split() and l.split()[0] == 'patch']


def build(tag, enforce_q, pack, ld_first=None):
    tree = prepare_tree(WORK / f'tree_{tag}')
    cpath = WORK / f'{tag}.census.json'
    args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
            '--out', str(tree / 'build'), '--name', tag, '--Q', '46']
    for p in PATCHES:
        args += ['--patch', str(tree / 'patches' / p)]
    args += ['--patch', str(tree / 'patches/patch_census.py')]
    env = dict(os.environ, CENSUS_PACK='1' if pack else '0', ENFORCE_Q=str(enforce_q),
               CENSUS_OUT=str(cpath), PY=PY)
    if ld_first:
        env['LD_FIRST_JSON'] = str(ld_first)
    out = subprocess.run(args, capture_output=True, text=True, env=env)
    print('=' * 22, f'{tag}: Q={enforce_q} pack={pack} ld_first={bool(ld_first)} rc={out.returncode}', flush=True)
    if out.returncode != 0:
        for l in (out.stdout + out.stderr).strip().splitlines()[-8:]:
            print('   ', l)
    best = {}
    if cpath.exists():
        rows = json.loads(cpath.read_text())['log']
        for label, cur, n in rows:
            best[label] = max(best.get(label, 0), cur + n)
        print('   demand:', sorted(best.items(), key=lambda kv: -kv[1])[:9], flush=True)
        print('   last events:', rows[-4:], flush=True)
    kmx = tree / 'build' / (tag + '.kmx')
    kmb = tree / 'build' / (tag + '.kmb')
    return out, tree, kmx, kmb


# baseline census with the shipped cap-20 loader, PACK on
build('base44', 44, True)
# with the new certificate
winner = CAND.get(19) or CAND.get(18)
if winner:
    cert = winner[1]
    print('using certificate', cert, json.loads(cert.read_text())['work_peak'], flush=True)
    for q in (44, 43, 42):
        build(f'new{q}', q, True, ld_first=cert)
Path(OUT / 'report.json').write_text(json.dumps({str(k): v[0] for k, v in CAND.items()}, indent=1))
print('DONE')
'''

code = TEMPLATE.replace('__CENSUS__', CENSUS_PATCH)
d = ROOT / 'kaggle' / 'v12loader'
d.mkdir(parents=True, exist_ok=True)
(d / 'v12loader.py').write_text(code)
meta = {
    "id": "jiyujia/qcc-v12-loader-research",
    "title": "qcc v12 loader research",
    "code_file": "v12loader.py",
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
print('wrote', d / 'v12loader.py', len(code), 'bytes; zip sha', hashlib.sha256(RAW).hexdigest())
