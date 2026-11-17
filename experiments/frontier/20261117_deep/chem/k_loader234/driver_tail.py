
# ============================== driver =====================================
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


root = Path('/tmp/work')
root.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ZIP_B64))) as z:
    z.extractall(root)
CODE2 = root / 'code2'
log(f'code2 extracted: {len(list(CODE2.rglob("*.py")))} py files')

COMP = 'google-verifiable-quantum-circuit-compilation'
DATA = next(p for p in (Path('/kaggle/input/competitions') / COMP, Path('/kaggle/input') / COMP)
            if (p / 'verifiers').is_dir())
for p in (DATA / 'kickmix', DATA / 'verifiers'):
    if p.is_dir():
        sys.path.insert(0, str(p))
sys.path.insert(0, str(CODE2 / 'compiler'))
sys.path.insert(0, str(CODE2))
os.environ.setdefault('LS_SECONDS', '200')

import compile_basis as C            # noqa: E402
from planner import complete_words, cross_tensor   # noqa: E402
from dfthcsos.scoreinfra import circuits as KC     # noqa: E402

C.STOP_AT = int(os.environ.get('STOP_AT', '147'))
C.prove_one = lambda *a, **kw: {'toffoli_count': None, 'source_sha256': 'n/a'}
log(f'STOP_AT {C.STOP_AT}  LS_SECONDS {os.environ["LS_SECONDS"]}')

# ---- find the shipped chem family (npz + 15 .kmb) -------------------------
cands = []
for npz in glob.glob('/kaggle/input/**/submission.npz', recursive=True):
    d = Path(npz).parent
    if (d / 'angle_k_0.kmb').is_file() and (d / 'angle_k_14.kmb').is_file():
        cands.append(d)
for npz in glob.glob('/kaggle/input/**/dfthcsos__submission.npz', recursive=True):
    cands.append(Path(npz).parent)
log(f'chemical candidate dirs: {[str(c) for c in cands]}')

best = None
for d in cands:
    kmbs = sorted(d.glob('angle_k_*.kmb'))
    if len(kmbs) < 15:
        continue
    circuits = [KC.read_circuit(p, format='kmb') for p in kmbs[:15]]
    costs = KC.circuit_costs(circuits)
    tot = sum(c['max_magic'] for c in costs)
    log(f'  {d}: 15 loaders, static max_magic sum {tot}  per-k '
        f'{[c["max_magic"] for c in costs[:5]]}...')
    if best is None or abs(tot - 4022) < abs(best[1] - 4022):
        best = (d, tot, kmbs, circuits)
SHIP, SHIP_TOT, KMBS, CIRCUITS = best
log(f'shipped family: {SHIP}  static sum {SHIP_TOT}')
z = np.load(SHIP / 'submission.npz')
TREE = np.asarray(z['tree_edges'], dtype=np.int64)
log(f'npz keys {z.files}')
W_npz = np.asarray(z['angle_words'], dtype=np.int64)
W_rec, layout, ang_tof = None, None, None
for tag, sd in (('official', KC.initial_seed(KC.submission_sha256(CIRCUITS, SHIP / 'submission.npz', TREE), '')),
                ('zero', 0)):
    try:
        W_r, layout, ang_tof = KC.recover_words_from_circuits(
            CIRCUITS, num_vectors=76 + 8 * 143, num_angles=75, seed=sd)
        log(f'words recovered with seed {tag}  match_npz='
            f'{bool(W_r.shape == W_npz.shape and np.array_equal(W_r, W_npz))}')
        W_rec = W_r
        break
    except Exception as exc:
        log(f'seed {tag} failed: {type(exc).__name__}: {exc}')
if W_rec is None:
    log('recovery failed -> planning on the npz angle_words (the final verify re-derives '
        'the words from the circuits and rejects a mismatch loudly)')
    W_rec = W_npz
    layout = None
    ang_tof = None
log(f'planning words {W_rec.shape}  brot '
    f'{None if layout is None else layout.word_width}  angles_toffoli {ang_tof}')
np.save('/kaggle/working/words_maoxin.npy', W_rec)
np.save('/kaggle/working/words_npz.npy', np.asarray(z['angle_words']))

OUT = Path('/kaggle/working/build')
OUT.mkdir(parents=True, exist_ok=True)
summary = {'shipped_dir': str(SHIP), 'static_sum': SHIP_TOT, 'angles_toffoli': ang_tof,
           'recovered_shape': list(W_rec.shape), 'loaders': [int(c['max_magic']) for c in KC.circuit_costs(CIRCUITS)]}
log('summary so far: ' + json.dumps(summary))

for k in (2, 3):
    t0 = time.time()
    res = C.compile_one(np.asarray(W_rec, dtype=np.int64), k, OUT, seeds=(7, 8, 9), trials=40)
    log(f'k{k} compile_one -> {res}  [{time.time()-t0:.0f}s]')
    if res is None:
        summary[f'k{k}'] = None
        continue
    kmx = OUT / f'angle_k_{k}.kmx'
    circ = KC.read_circuit(kmx, format='kmx')
    st = circ.operation_statistics()
    kmb = OUT / f'angle_k_{k}.kmb'
    circ.to_file(kmb, format='kmb')
    per = {'products': res['products'], 'toffoli_emitter': res['toffoli'],
           'max_magic_static': int(st.num_toffoli_like), 'qubits': int(circ.num_qubits),
           'sum_cuts': res['sum_cuts']}
    summary[f'k{k}'] = per
    log(f'k{k}: {per}')
    (Path('/kaggle/working') / 'summary.json').write_text(json.dumps(summary, indent=1))

(Path('/kaggle/working') / 'summary.json').write_text(json.dumps(summary, indent=1))
log('plan/emit phase done; summary.json written')
print(json.dumps(summary, indent=1))

# ---- assemble the candidate package and run the official verifier ----------
def assemble_and_verify():
    import hashlib
    import shutil
    pkg = Path('/kaggle/working/pkg/dfthcsos')
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    # shipped submission.npz verbatim
    shutil.copy2(SHIP / 'submission.npz', pkg / 'submission.npz')
    replaced = []
    for k in range(15):
        src = SHIP / f'angle_k_{k}.kmb'
        if not src.is_file():
            src = SHIP / f'angle_k_{k}.kmx'          # syed-style names handled below
        dst = pkg / f'angle_k_{k}.kmb'
        new = OUT / f'angle_k_{k}.kmb'
        if new.is_file():
            shutil.copy2(new, dst)
            replaced.append(k)
        else:
            shutil.copy2(src, dst)
    log(f'assembled {pkg}  replaced {replaced}')
    per = []
    for k in range(15):
        c = KC.read_circuit(pkg / f'angle_k_{k}.kmb', format='kmb')
        per.append(int(c.operation_statistics().num_toffoli_like))
    log(f'per-k static Toffoli {per}  sum {sum(per)}')
    shas = {}
    for p in sorted(pkg.iterdir()):
        shas[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    vpy = DATA / 'verifiers' / 'dfthcsos' / 'verify.py'
    cmd = [sys.executable, str(vpy), str(pkg / 'submission.npz'), str(pkg),
           '--tree-edges', str(pkg / 'submission.npz')]
    log('running official verifier: ' + ' '.join(cmd))
    env = dict(os.environ, PYTHONPATH=str(DATA / 'verifiers'))
    r = subprocess.run(cmd, capture_output=True, text=True, env=env,
                       cwd=str(DATA / 'verifiers'))
    out = (r.stdout or '')[-4000:]
    log(f'verify rc={r.returncode}\nSTDOUT:\n{out}\nSTDERR tail:\n{(r.stderr or "")[-1500:]}')
    return dict(per_k=per, sum=sum(per), sha256=shas, rc=r.returncode,
                stdout=out, stderr=(r.stderr or '')[-1500:])


if all((OUT / f'angle_k_{k}.kmb').is_file() for k in (2, 3)):
    summary['verify'] = assemble_and_verify()
else:
    log('k2/k3 .kmb missing -> no package, no verifier')
(Path('/kaggle/working') / 'summary.json').write_text(json.dumps(summary, indent=1))
log('DONE')
print(json.dumps({k: v for k, v in summary.items() if k != 'verify'}, indent=1))
