# QCC invsqrt: validate a re-searched first-loader certificate on the v12 generator.
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
SRC = WORK / 'src'
if SRC.exists(): shutil.rmtree(SRC)
with zipfile.ZipFile(zp) as z: z.extractall(SRC)
TREE = SRC / 'invsqrt_source'
for _p in TREE.rglob('*'):
    if _p.is_file(): _p.chmod(0o755 if _p.suffix in ('.bin', '.sh') else 0o644)
PY = '/usr/bin/python3.13' if Path('/usr/bin/python3.13').exists() else sys.executable
LOADER = TREE / 'src/work/c10/narrow/research/joint_loader'
SEARCH = LOADER / 'search'; SEARCH.mkdir(parents=True, exist_ok=True)
print('python', subprocess.run([PY, '-c', 'import platform;print(platform.python_version())'],
                               capture_output=True, text=True).stdout.strip(), flush=True)


def search(cap, seed, seconds=20, tag=None):
    name = tag or f'v5_first_cap{cap}_s{seed}'
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
    else:
        row['err'] = (out.stderr or '')[-200:]
    return row, p


good = {}
for cap in (19, 17, 16):
    for seed in (0, 1, 2):
        row, p = search(cap, seed, seconds=25)
        print('SEARCH', json.dumps(row), flush=True)
        if row.get('status') == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
            if cap not in good or row['Toffolis'] < good[cap][0]['Toffolis']:
                good[cap] = (row, p)
    if cap in good:
        print(f'*** cap {cap}: Toffolis {good[cap][0]["Toffolis"]} peak {good[cap][0]["work_peak"]} '
              f'sha {good[cap][0]["sha"]}', flush=True)


def prepare_tree(dst: Path, relax_loader_cap=True) -> Path:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(TREE / 'src', dst)
    for p in dst.rglob('*'):
        if p.is_file(): p.chmod(0o755 if p.suffix in ('.bin', '.sh') else 0o644)
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
            p = Path(d) / f; b = p.read_bytes()
            if tok in b: p.write_bytes(b.replace(tok, str(dst).encode()))
    if relax_loader_cap:
        p = dst / 'patches/patch_ld_first20_56b8.py'
        t = p.read_text()
        old = "    assert data['work_cap'] == data['work_peak'] == 20"
        new = "    assert data['work_cap'] == data['work_peak'] and 14 <= data['work_cap'] <= 20"
        assert old in t
        p.write_text(t.replace(old, new))
    return dst


# ---- (b) end-to-end validation: unchanged build.sh + LD_FIRST_JSON, exact full-domain proof
if 19 in good:
    tree = prepare_tree(WORK / 'tree_val19')
    env = dict(os.environ, PY=PY, WORK=str(WORK / 'gw'), LD_FIRST_JSON=str(good[19][1]))
    out = subprocess.run(['bash', str(tree / 'build.sh'), str(KSO.parent), str(VER), str(WORK / 'out19')],
                         capture_output=True, text=True, env=env)
    print('=' * 24, f'validation build (cap 19 loader): rc={out.returncode}', flush=True)
    print(out.stdout[-2500:], flush=True)
    print('STDERR TAIL', out.stderr[-800:], flush=True)
    s19 = (WORK / 'out19/invsqrt.kmb')
    if s19.exists():
        print('emitted sha256', hashlib.sha256(s19.read_bytes()).hexdigest(), s19.stat().st_size, flush=True)
Path(OUT / 'report.json').write_text(json.dumps({str(k): v[0] for k, v in good.items()}, indent=1))
print('DONE')
