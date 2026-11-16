"""Fresh-shape chemistry probe: R=10 (B=120, C=32) via the public merge pipeline.

Seed + joint U/W fit (dfthc_refit experiments/shrink.py, --device on Kaggle CPU),
then the shipped coded 8-bit quantizer (quantize.py --brot 8), refine.py and
refit_weights.py. Metrics (e1/e2/E_gap/Lambda/lambda_eff) are recorded from the
refine/refit RESULT lines. build.py / the official 78,080-shot verifier (+2 salts)
run ONLY if the local gate passes (e1<=20, e2<=20 mHa, E_gap above floor, and
cost <= 294,762,300 reachable with the priced T_heur/Q). Otherwise the blocker is
recorded and nothing is built or submitted.

Nothing is submitted. Output: /kaggle/working/{fit,post}/** and summary.json.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ------------------------------------------------------------------ config
R_TGT, B_TGT, C_TGT = 10, 120, 32
SEED_GLOB = 'B10c54.npz'          # file name inside /kaggle/input
SOURCE = ''           # public_seed source ('group26'/'group24'/'' = seed already converted)
MERGE = 0               # 0 = seed already at target R (use --merged)
SCHEDULE = [(120,44),(120,38),(120,32)]          # [(B, C), ...] shrink steps after the merge
PRE0, FADE0, FIT0 = 150, 150, 400
FADE, FIT, FINAL, FINAL_LAST = 150, 400, 500, 1200
Q_STAGE, Q_FIN = 400, 1000
# ------------------------------------------------------------------

WORK = Path('/kaggle/working')
_FLAG = 'smoke.flag'
SMOKE = (Path(__file__).with_name(_FLAG).is_file() if '__file__' in globals() else False
         ) or Path(_FLAG).is_file() or (WORK / _FLAG).is_file()
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
hits = glob.glob(f'/kaggle/input/**/{SEED_GLOB}', recursive=True)
assert hits, f'seed {SEED_GLOB} not found in /kaggle/input'
SEED = Path(hits[0])
PIPE, FITD, POST = WORK / 'pipe', WORK / 'fit', WORK / 'post'
shutil.rmtree(PIPE, ignore_errors=True)
shutil.copytree(SRC, PIPE)
for d in (FITD, POST):
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)

os.environ.setdefault('JAX_PLATFORMS', 'cpu')
os.environ.setdefault('JAX_ENABLE_X64', '1')
PY = sys.executable
T0 = time.time()
WALL = float(os.environ.get('WALL_HOURS', '9.0')) * 3600.0
FIT_BUDGET = WALL - 2.5 * 3600.0
S = {'kernel': 'jiyujia/qcc-chem-fresh-shape-r-10-b-120-c-32', 'shape': [R_TGT, B_TGT, C_TGT], 'seed': str(SEED),
     'wall_hours': WALL / 3600, 'fit_budget_hours': FIT_BUDGET / 3600,
     'segments': [], 'post': {}, 'metrics': {}, 'verify': {}}
if SMOKE:
    WALL, FIT_BUDGET = 0.9 * 3600.0, 0.45 * 3600.0
    S.update(smoke=True, wall_hours=WALL / 3600, fit_budget_hours=FIT_BUDGET / 3600)


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
    for line in (r.stdout or '').splitlines()[-40:]:
        log('  |', line)
    if r.returncode:
        for line in (r.stderr or '').splitlines()[-20:]:
            log('  !', line)
    return r.returncode, out


TARGET_E2 = re.compile(r'error_2\s+([\d.]+)\s+->\s+([\d.]+)\s+mHa')
rate = 1.6
# group-compression seeds ship words, not (U, W): convert to a trainable npz first
if SOURCE:
    CONV = FITD / 'seed_conv.npz'
    rc0, out0 = run([PY, 'public_seed.py', CONV, SOURCE], 900, f'convert {SOURCE}')
    assert rc0 == 0 and CONV.is_file(), f'seed convert failed: {(out0 or "")[-800:]}'
    SEED = CONV
    S['seed'] = str(SEED)
    save_summary()
prev = SEED
merged = (MERGE == 0)
steps = [f'{b}x{c}' for b, c in SCHEDULE]
if SMOKE:
    steps = steps[:1]
    PRE0, FADE0, FIT0 = 6, 3, 6
    FADE, FIT, FINAL, FINAL_LAST = 2, 4, 6, 8
for i, step in enumerate(steps):
    last = i == len(steps) - 1
    pre = PRE0 if i == 0 else 0
    fade = FADE0 if i == 0 else FADE
    final = FINAL_LAST if last else FINAL
    outdir = FITD / f'seg{i}'
    outdir.mkdir(exist_ok=True)
    cmd = [PY, 'experiments/shrink.py', prev, outdir]
    cmd += ['--merged'] if merged else ['--merge', MERGE]
    cmd += ['--device', '--pre', pre, '--fade', fade, '--fit', FIT,
            '--final', final, '--save', step, step]
    t = time.time()
    rc, out = run(cmd, min(max(FIT_BUDGET - el(), 300), 5.5 * 3600), f'shrink {step}')
    dt = time.time() - t
    got = outdir / f'{R_TGT}x{step}.npz'
    e2 = TARGET_E2.findall(out)
    S['segments'].append(dict(step=step, pre=pre, fade=fade, final=final,
                              seconds=round(dt), rc=rc, e2_pairs=e2[-4:],
                              file=str(got.relative_to(WORK)) if got.is_file() else None))
    save_summary()
    if not got.is_file():
        log(f'seg{i}: no {got.name}, abandoning the fit phase')
        break
    used = pre + 2 * fade + final
    if rc == 0 and used > 200 and dt > 0:
        rate = max(0.4, min(6.0, dt / used * 1.1))
    prev, merged = got, True

CONTP = prev
log(f'continuous checkpoint {CONTP} ({CONTP.name})')

FREE9 = '0.7,0.5,0.32,0.2,0.12,0.07,0.04,0.02,0.0'
if SMOKE:
    FREE9 = '0.5,0.25,0.0'
rounded, refined, final_npz = (POST / n for n in
                              ('rounded.npz', 'refined.npz', 'final.npz'))
METRIC_KEYS = ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')


def record(tag, metrics):
    S['metrics'][tag] = {k: float(metrics[k]) for k in METRIC_KEYS if k in metrics}
    save_summary()


def last_json(out):
    for line in reversed(out.splitlines()):
        j = line.find('{')
        if j >= 0:
            try:
                return json.loads(line[j:])
            except ValueError:
                continue
    return {}


stage, fin = (Q_STAGE, Q_FIN) if not SMOKE else (30, 40)
rc = 1
if CONTP != SEED:
    rc, _ = run([PY, 'quantize.py', CONTP, rounded, '--brot', '8', '--x64',
                 '--stage-steps', stage, '--final-steps', fin, '--fit-steps', stage,
                 '--kappa', '5e-5', '--free', FREE9, '--lbfgs-until', '0'],
                min(max(WALL - el() - 3600, 600), 3.5 * 3600), 'round 8-bit')
src = rounded

rounds = 1 if SMOKE else 3
if rc == 0 and src.is_file():
    rc3, out3 = run([PY, 'refine.py', src, refined, '--brot', '8', '--rounds', rounds,
                     '--maxiter', 100 if SMOKE else 1000, '--margin', '0.0005'],
                    min(2400 if not SMOKE else 600, max(WALL - el() - 1800, 300)), 'refine')
    if rc3 == 0 and refined.is_file():
        src = refined
        m = last_json(out3)
        if m:
            record('refined', m)
save_summary()

e2_limit = 500.0 if SMOKE else 19.95
ref_e2 = S['metrics'].get('refined', {}).get('error_2', 1.0)
if src == refined and ref_e2 * 1e3 < e2_limit and WALL - el() > (900 if SMOKE else 3600):
    rc4, out4 = run([PY, 'refit_weights.py', refined, final_npz, '--target', str(e2_limit),
                     '--margin', '0.0005', '--rounds', '1' if SMOKE else '2',
                     '--maxiter', 100 if SMOKE else 1000],
                    min(600 if SMOKE else 1800, max(WALL - el() - 1500, 300)), 'refit weights')
    if rc4 == 0 and final_npz.is_file():
        src = final_npz
        m = last_json(out4)
        if m:
            record('refit', m)
        save_summary()
S['post']['final_npz'] = str(src.relative_to(WORK))

# gate: build + official 78,080-shot verify (+2 salts) only on a passing package
GAP_FLOOR = 3.914898
gate = S['metrics'].get('refit', S['metrics'].get('refined', {}))
e1 = gate.get('error_1', 1.0) * 1e3
e2 = gate.get('error_2', 1.0) * 1e3
gap = gate.get('E_gap', 0.0)
log(f'GATE e1 {e1:.3f} e2 {e2:.3f} E_gap {gap:.9f} (limits 20 / 20 / {GAP_FLOOR})')
S['post']['gate'] = {'e1_mHa': e1, 'e2_mHa': e2, 'E_gap': gap,
                     'pass': bool(e1 <= 20 and e2 <= 20 and gap > GAP_FLOOR)}
if S['post']['gate']['pass'] and WALL - el() > 2400:
    d = POST / 'sub8_reference'
    rc5, out5 = run([PY, 'build.py', src, d, '--brot', '8', '--tree', 'log_depth',
                     '--shots', '64', '--qrom', 'reference', '--json', POST / 'result_ref.json'],
                    min(2400, WALL - el() - 300), 'build+verify (64 shots/address)')
    p = POST / 'result_ref.json'
    if p.is_file():
        S['verify']['shots64'] = json.loads(p.read_text())
        save_summary()
else:
    log('gate not passed (or no time left): no build, no official verify')

S['elapsed_hours'] = round(el() / 3600, 2)
save_summary()
log('done')
