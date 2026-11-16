"""Kernel: prove the cap-17 first-loader certificate exact by driving the pipeline manually
(build_variant with LD_FIRST_JSON -> pipeline.sh -> exact full-domain proof).
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

TEMPLATE = r'''# QCC invsqrt: cap-17 first-loader certificate -> manual pipeline -> exact full-domain proof.
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


def search(cap, seed, seconds=22, tag=None):
    name = tag or f'v7_first_cap{cap}_s{seed}'
    cmd = [PY, '-u', str(LOADER / 'adaptive_loader_v2.py'), '--name', name, '--mode', 'first_raw',
           '--work-cap', str(cap), '--seed', str(seed), '--seconds', str(seconds), '--rounds', '8',
           '--factor-seconds', '0.5', '--tail-seconds', '2']
    out = subprocess.run(cmd, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONPATH=str(LOADER / 'inputs')))
    p = SEARCH / f'{name}.json'
    d = json.loads(p.read_text())
    return dict(cap=cap, seed=seed, status=d['status'], Toffolis=d['Toffolis'], work_peak=d['work_peak'],
                loaded=len(d['loaded_output_masks']), sha=hashlib.sha256(p.read_bytes()).hexdigest()), p


best = None
for seed in (0, 1, 2):
    row, p = search(17, seed)
    print('SEARCH', json.dumps(row), flush=True)
    if row['status'] == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE' and (best is None or row['Toffolis'] < best[0]['Toffolis']):
        best = (row, p)
    if best is not None and best[0]['Toffolis'] <= 78:
        break
assert best is not None
cert = best[1]
print(f'*** cap-17 certificate {cert.name} Toffolis {best[0]["Toffolis"]} sha {best[0]["sha"]}', flush=True)


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


def driven_build(tag, cert_path):
    tree = prepare_tree(WORK / f'tree_{tag}')
    PATCHES = [l.split()[1] for l in (TREE / 'src/patches/PATCH_ORDER.txt').read_text().splitlines()
               if l.split() and l.split()[0] == 'patch']
    env = dict(os.environ, PY=PY, LD_FIRST_JSON=str(cert_path), MG='',
               PYTHONPATH=str(tree / 'work/c10/narrow/research/joint_loader/inputs'))
    for k in ('DIVIDER_FORCE_CAP','DIVIDER_PLACEHOLDER','DIVIDER_RETIRE','LEAD_SECOND_JSON','TK46_SECOND_JSON',
              'W2_E_HOLD','W2_F_HOLD','W2_R2','W2_V10_G1','W2_V9_FORM','W2_V9_PLACEHOLDER','FG','NARROW'):
        env.pop(k, None)
    args = [PY, str(tree / 'tools/macrun.py'), str(tree / 'tools/build_variant.py'),
            '--out', str(tree / 'build'), '--name', tag + 'raw', '--Q', '46']
    for pp in PATCHES:
        args += ['--patch', str(tree / 'patches' / pp)]
    t0 = time.time()
    o = subprocess.run(args, capture_output=True, text=True, env=env)
    print(f'generator rc={o.returncode} {time.time()-t0:.0f}s', flush=True)
    if o.returncode != 0:
        print((o.stdout + o.stderr)[-1500:], flush=True)
        return None
    print(o.stdout[-900:], flush=True)
    o2 = subprocess.run(['bash', str(tree / 'tools/pipeline.sh'), str(tree / f'build/{tag}raw.kmx'),
                         str(tree / 'final'), tag, '46'], capture_output=True, text=True, env=env)
    print(f'pipeline rc={o2.returncode} {time.time()-t0:.0f}s', flush=True)
    print(o2.stdout[-1500:], flush=True)
    if o2.returncode != 0:
        print((o2.stdout + o2.stderr)[-1500:], flush=True)
        return None
    return tree


tree = driven_build('cap17', cert)
if tree is not None:
    kmb = tree / 'final/cap17.kmb'
    proof = tree / 'final/cap17.proof.json'
    if kmb.exists():
        print('EMITTED', hashlib.sha256(kmb.read_bytes()).hexdigest(), kmb.stat().st_size, flush=True)
    if proof.exists():
        d = json.loads(proof.read_text())
        print('PROOF', d.get('status'), d.get('proved_inputs'), d.get('circuit_sha256'), flush=True)
Path(OUT / 'cap17.json').write_text(json.dumps(best[0], indent=1))
print('DONE')
'''

d = ROOT / 'kaggle' / 'v12proof17'
d.mkdir(parents=True, exist_ok=True)
(d / 'v12proof17.py').write_text(TEMPLATE)
meta = {
    "id": "jiyujia/qcc-v12-cap17-proof",
    "title": "qcc v12 cap17 proof",
    "code_file": "v12proof17.py",
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
print('wrote', d / 'v12proof17.py', len(TEMPLATE), 'bytes')
