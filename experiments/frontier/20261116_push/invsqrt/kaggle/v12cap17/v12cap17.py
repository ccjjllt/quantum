# QCC invsqrt: cap-17 first-loader certificate -> exact proof + Q=42 census.
import hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

WORK = Path('/tmp/v12'); OUT = Path('/kaggle/working'); INPUT = Path('/kaggle/input')
WORK.mkdir(parents=True, exist_ok=True)


def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]


KSO = _walk('kickmix.so')[0]
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
print('python', subprocess.run([PY, '-c', 'import platform;print(platform.python_version())'],
                               capture_output=True, text=True).stdout.strip(), flush=True)


def search(cap, seed, seconds=22, tag=None):
    name = tag or f'v6_first_cap{cap}_s{seed}'
    cmd = [PY, '-u', str(LOADER / 'adaptive_loader_v2.py'), '--name', name, '--mode', 'first_raw',
           '--work-cap', str(cap), '--seed', str(seed), '--seconds', str(seconds), '--rounds', '8',
           '--factor-seconds', '0.5', '--tail-seconds', '2']
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONPATH=str(LOADER / 'inputs')))
    p = SEARCH / f'{name}.json'
    row = dict(cap=cap, seed=seed, secs=round(time.time() - t0, 1), rc=out.returncode)
    if p.exists():
        d = json.loads(p.read_text())
        row.update(status=d['status'], Toffolis=d['Toffolis'], work_peak=d['work_peak'],
                   loaded=len(d['loaded_output_masks']), sha=hashlib.sha256(p.read_bytes()).hexdigest())
    return row, p


best = None
for seed in (0, 1, 2):
    row, p = search(17, seed)
    print('SEARCH', json.dumps(row), flush=True)
    if row.get('status') == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
        if best is None or row['Toffolis'] < best[0]['Toffolis']:
            best = (row, p)
        if row['Toffolis'] <= 78:
            break
assert best is not None, 'cap 17 search did not complete'
cert = best[1]
print(f'*** using cap-17 certificate {cert.name} Toffolis {best[0]["Toffolis"]} sha {best[0]["sha"]}', flush=True)

# relax the certificate's cap assert in the source tree (a patch-layer file)
p = TREE / 'src/patches/patch_ld_first20_56b8.py'
t = p.read_text()
old = "    assert data['work_cap'] == data['work_peak'] == 20"
new = "    assert data['work_cap'] == data['work_peak'] and 14 <= data['work_cap'] <= 20"
assert old in t
p.write_text(t.replace(old, new))
print('relaxed the loader cap assert (patch layer only)', flush=True)

# ---- (a) unchanged build.sh + LD_FIRST_JSON: the exact full-domain proof decides
env = dict(os.environ, PY=PY, WORK=str(WORK / 'gw'), LD_FIRST_JSON=str(cert))
out = subprocess.run(['bash', str(TREE / 'build.sh'), str(KSO.parent), str(VER), str(WORK / 'out17')],
                     capture_output=True, text=True, env=env)
print('=' * 24, f'validation build (cap-17 loader): rc={out.returncode}', flush=True)
print(out.stdout[-2500:], flush=True)
if out.returncode != 0:
    print('STDERR TAIL', out.stderr[-1200:], flush=True)
for cand in (WORK / 'out17/invsqrt.kmb',):
    if cand.exists():
        print('emitted', hashlib.sha256(cand.read_bytes()).hexdigest(), cand.stat().st_size, flush=True)

# ---- (b) census at Q=42 with the cap-17 loader: which block blocks next
CENSUS = """
import atexit, json, os, sys
Q = 46
LABEL = ['init']
LOG = []
ENFORCE = int(os.environ.get('ENFORCE_Q', '0') or 0)
if os.environ.get('CENSUS_PACK') == '1':
    _m = sys.modules.get('variant_patch_patch_w47_body')
    if _m is not None:
        _m.PACK = True
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
            old = LABEL[0]; LABEL[0] = label
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
"""


def prepare_tree(dst: Path) -> Path:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(TREE / 'src', dst)
    for pp in dst.rglob('*'):
        if pp.is_file(): pp.chmod(0o644)
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
    (dst / 'patches/patch_census.py').write_text(CENSUS)
    return dst


PATCHES = [l.split()[1] for l in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines()
           if l.split() and l.split()[0] == 'patch']


def census(tag, q):
    tree = prepare_tree(WORK / f'tree_{tag}')
    cpath = WORK / f'{tag}.json'
    args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
            '--out', str(tree / 'build'), '--name', tag, '--Q', '46']
    for pp in PATCHES:
        args += ['--patch', str(tree / 'patches' / pp)]
    args += ['--patch', str(tree / 'patches/patch_census.py')]
    e = dict(os.environ, CENSUS_PACK='1', ENFORCE_Q=str(q), CENSUS_OUT=str(cpath), PY=PY,
             LD_FIRST_JSON=str(cert))
    o = subprocess.run(args, capture_output=True, text=True, env=e)
    print('=' * 24, f'census {tag} Q={q}: rc={o.returncode}', flush=True)
    if o.returncode != 0:
        for l in (o.stdout + o.stderr).strip().splitlines()[-6:]:
            print('   ', l)
    if cpath.exists():
        rows = json.loads(cpath.read_text())['log']
        bestd = {}
        for label, cur, n in rows:
            bestd[label] = max(bestd.get(label, 0), cur + n)
        print('   demand:', sorted(bestd.items(), key=lambda kv: -kv[1])[:9], flush=True)
        print('   last events:', rows[-3:], flush=True)


census('cap17_q42', 42)
Path(OUT / 'report17.json').write_text(json.dumps(best[0], indent=1))
print('DONE')
