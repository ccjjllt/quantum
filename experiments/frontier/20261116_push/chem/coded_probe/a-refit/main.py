"""Coded-quantizer probe (a2): full 352-weight refit floor of the coded words.

Input: jiyujia/qcc-chem-coded-814344-refined (fresh --coded "1-14" words at
(8,143,44), refined e2 21.216 mHa). Runs refit_weights.py (exact error_2 in w,
352 weights + offsets, L-BFGS + refine moves) to measure the fixed-words e2
floor: can the full w refit recover the 1.2 mHa over the gate, or is the coded
rounding penalty structural (cf. RESULT4 §2.3: 36-63 mHa floors for post-hoc
re-codes)? Gate/build/verify logic identical to probe (a): official verifier
only on a pass. Nothing submitted.
"""

import glob
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

WORK = Path('/kaggle/working')
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
hits = glob.glob('/kaggle/input/**/qcc-chem-coded-814344-refined/**/refined.npz', recursive=True)
if not hits:
    hits = glob.glob('/kaggle/input/**/refined.npz', recursive=True)
REFINED = Path(hits[0])
PIPE, POST = WORK / 'pipe', WORK / 'post'
shutil.rmtree(PIPE, ignore_errors=True)
shutil.copytree(SRC, PIPE)
shutil.rmtree(POST, ignore_errors=True)
POST.mkdir(parents=True)

import os
os.environ.setdefault('JAX_PLATFORMS', 'cpu')
os.environ.setdefault('JAX_ENABLE_X64', '1')
PY = sys.executable
T0 = time.time()
S = {'kernel': 'jiyujia/qcc-chem-coded-814344-refit', 'refined': str(REFINED),
     'post': {}, 'metrics': {}, 'verify': {}}


def el() -> float:
    return time.time() - T0


def log(*a):
    print(f'[{el() / 60:7.1f} min]', *a, flush=True)


def save_summary():
    (WORK / 'summary.json').write_text(json.dumps(S, indent=1))


def run(cmd, timeout, tag):
    log(f'$ {tag}: {" ".join(str(c) for c in cmd[1:])}')
    t = time.time()
    try:
        r = subprocess.run([str(c) for c in cmd], cwd=str(PIPE), capture_output=True, text=True,
                           timeout=max(timeout, 60))
    except subprocess.TimeoutExpired:
        log(f'$ {tag}: TIMEOUT after {timeout:.0f}s')
        return None, ''
    out = (r.stdout or '') + (r.stderr or '')
    log(f'$ {tag}: rc={r.returncode} {time.time() - t:.0f}s')
    for line in (r.stdout or '').splitlines()[-30:]:
        log('  |', line)
    if r.returncode:
        for line in (r.stderr or '').splitlines()[-20:]:
            log('  !', line)
    return r.returncode, out


def last_json(out):
    for line in reversed(out.splitlines()):
        j = line.find('{')
        if j >= 0:
            try:
                return json.loads(line[j:])
            except ValueError:
                continue
    return {}


final_npz = POST / 'final.npz'
rc4, out4 = run([PY, 'refit_weights.py', REFINED, final_npz, '--target', '19.95',
                 '--margin', '0.0005', '--rounds', '2', '--maxiter', '1000'],
                3.0 * 3600, 'refit weights (floor)')
src = final_npz if (rc4 == 0 and final_npz.is_file()) else REFINED
m = last_json(out4)
if m:
    S['metrics']['refit'] = {k: float(m[k]) for k in
                             ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff') if k in m}
    save_summary()
S['post']['final_npz'] = str(src.relative_to(WORK)) if isinstance(src, Path) else src

GAP_FLOOR = 3.914898
gate = S['metrics'].get('refit', {})
e1 = gate.get('error_1', 1.0) * 1e3
e2 = gate.get('error_2', 1.0) * 1e3
gap = gate.get('E_gap', 0.0)
log(f'GATE e1 {e1:.3f} e2 {e2:.3f} E_gap {gap:.9f} (limits 20 / 20 / {GAP_FLOOR})')
S['post']['gate'] = {'e1_mHa': e1, 'e2_mHa': e2, 'E_gap': gap,
                     'pass': bool(e1 <= 20 and e2 <= 20 and gap > GAP_FLOOR)}
save_summary()
if S['post']['gate']['pass']:
    d = POST / 'sub8_tensor'
    rc5, out5 = run([PY, 'build.py', src, d, '--brot', '8', '--tree', 'log_depth',
                     '--shots', '64', '--qrom', 'tensor', '--json', POST / 'result_tensor.json'],
                    2400, 'build+verify tensor (64 shots/address)')
    p = POST / 'result_tensor.json'
    if p.is_file():
        S['verify']['shots64_default'] = json.loads(p.read_text())
        save_summary()
    if rc5 == 0:
        sys.path.insert(0, str(PIPE))
        from paths import DATA  # noqa: E402
        sys.path.insert(0, str(DATA / 'verifiers'))
        from dfthcsos.verify import verify as official_verify  # noqa: E402
        for salt in ('dfthcsos-coded-a', 'dfthcsos-coded-b'):
            r = official_verify(d, shots_per_address=64, salt=salt)
            S['verify'][f'shots64_{salt}'] = {'status': r['status'], 'score': r['score'],
                                             'lambda_eff': r['lambda_eff'],
                                             'toffoli': r['toffoli_count'],
                                             'qubits': r['num_qubits'],
                                             'error_1_mHa': r['metrics']['error_1'] * 1e3,
                                             'error_2_mHa': r['metrics']['error_2'] * 1e3}
            log('salt', salt, S['verify'][f'shots64_{salt}'])
        save_summary()
else:
    log('gate not passed: no build, no official verify')

S['elapsed_hours'] = round(el() / 3600, 2)
save_summary()
log('done')
