"""Backup R=5 chemistry fit: B10c54 (10,120,54) --merge 2--> (5,240,108) --shrink--> (5,143,75).

Independent backup of qingyu1232/qcc-chem-merge-shrink-full-budget with a deliberately
different, more conservative schedule: one extra cut point (155x78), longer fades, and a
3,400-iteration final fit at the target shape instead of 1,800.

Segmented on purpose.  Every cut step is its own shrink.py call seeded with the previous
checkpoint (--merged), so (a) a session that hits the wall clock loses at most one segment,
(b) the remaining budget is rescaled from the *measured* iteration rate after each segment,
and (c) every intermediate shape is written to disk.  The fit phase must end 2.4 h before
the session limit; the post chain (round -> polish -> refine -> refit -> build -> official
verify at the default 64 shots/address) runs in that window.

Nothing is submitted.  Output: /kaggle/working/{fit,post}/** and summary.json.
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

WORK = Path('/kaggle/working')
SMOKE = Path(__file__).with_name('smoke.flag').is_file()   # tiny-budget plumbing test, same code path
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
SEED = SRC.parent / 'B10c54.npz'
PIPE, FIT, POST = WORK / 'pipe', WORK / 'fit', WORK / 'post'
shutil.rmtree(PIPE, ignore_errors=True)
shutil.copytree(SRC, PIPE)
for d in (FIT, POST):
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)

os.environ.setdefault('JAX_PLATFORMS', 'cpu')
os.environ.setdefault('JAX_ENABLE_X64', '1')
PY = sys.executable
T0 = time.time()
WALL = float(os.environ.get('WALL_HOURS', '11.0')) * 3600.0
FIT_BUDGET = WALL - 2.4 * 3600.0
S = {'kernel': 'jiyujia/qcc-chem-r5-backup-b11c', 'seed': str(SEED), 'wall_hours': WALL / 3600,
     'fit_budget_hours': FIT_BUDGET / 3600, 'segments': [], 'post': {}, 'metrics': {},
     'verify': {}}
if SMOKE:                       # plumbing test only: every stage runs, every budget is tiny
    WALL, FIT_BUDGET = 0.7 * 3600.0, 0.5 * 3600.0
    S.update(smoke=True, wall_hours=WALL / 3600, fit_budget_hours=FIT_BUDGET / 3600)

def el() -> float:
    return time.time() - T0


def log(*a):
    print(f'[{el() / 60:7.1f} min]', *a, flush=True)


def save_summary():
    (WORK / 'summary.json').write_text(json.dumps(S, indent=1))


def run(cmd, timeout, tag):
    """Run one pipeline command; return (rc, stdout+stderr).  A timeout is rc=None."""
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
    for line in (r.stdout or '').splitlines()[-50:]:
        log('  |', line)
    if r.returncode:
        for line in (r.stderr or '').splitlines()[-25:]:
            log('  !', line)
    return r.returncode, out


# --------------------------------------------------------------------------- fit phase
# (step, pre, fade, final): pre is one fit at the incoming shape; 2*fade is spent fading the
# parts that the cut removes (x0.5 then x0.2); final is the fit after the drop.  Only the merge
# segment needs a pre-fit (the merged seed has not been optimised at (5,240,108) yet).
SEGS = [dict(step='240x100', pre=400, fade=300, final=1000),
        dict(step='200x90', pre=0, fade=350, final=1400),
        dict(step='170x82', pre=0, fade=350, final=1600),
        dict(step='155x78', pre=0, fade=400, final=1600),
        dict(step='143x75', pre=0, fade=450, final=3400)]
MIN_FADE, MIN_FINAL = 250, 900
if SMOKE:
    SEGS = [dict(seg['step'], pre=8, fade=4, final=10) for seg in SEGS]
    MIN_FADE, MIN_FINAL = 2, 4
TARGET_E2 = re.compile(r'error_2\s+([\d.]+)\s+->\s+([\d.]+)\s+mHa')


def iters(seg):
    return seg['pre'] + 2 * seg['fade'] + seg['final']


rate = 1.6          # s per iteration, tracked from the measured segments
prev = SEED         # seed npz for the next segment
merged = False
for i, seg in enumerate(SEGS):
    last = i == len(SEGS) - 1
    remaining = FIT_BUDGET - el()
    # keep the final segment's planned time out of the budget of the earlier ones
    reserve = 0.0 if last else iters(SEGS[-1]) * rate
    planned = sum(iters(s) for s in SEGS[i:])
    k = 1.0
    if last:
        k = max(0.3, min(1.0, remaining / max(iters(seg) * rate, 1.0)))
    else:
        k = max(0.5, min(1.0, (remaining - reserve) / max(planned * rate, 1.0)))
    pre = int(seg['pre'] * k)
    fade = max(MIN_FADE, int(seg['fade'] * k))
    final = max(MIN_FINAL, int(seg['final'] * k))
    if last:
        # never buy the final fit with a broken fade: shrink the fit instead
        pre, fade = seg['pre'], max(seg['fade'], MIN_FADE)
        final = max(MIN_FINAL, min(seg['final'], int(remaining / rate - pre - 2 * fade)))
    outdir = FIT / f'seg{i}'
    outdir.mkdir(exist_ok=True)
    cmd = [PY, 'experiments/shrink.py', prev, outdir]
    cmd += ['--merged'] if merged else ['--merge', '2']
    cmd += ['--device', '--pre', pre, '--fade', fade, '--fit', 1, '--final', final,
            '--save', seg['step'], seg['step']]
    log(f'seg{i} {seg["step"]} k={k:.2f}: pre {pre} fade {fade} final {final} '
        f'(remaining {remaining / 3600:.2f} h, rate {rate:.2f} s/it)')
    t = time.time()
    rc, out = run(cmd, min(remaining - 300, 5.5 * 3600), f'shrink {seg["step"]}')
    dt = time.time() - t
    got = outdir / f'5x{seg["step"]}.npz'
    e2 = TARGET_E2.findall(out)
    S['segments'].append(dict(seg=seg['step'], pre=pre, fade=fade, final=final, k=round(k, 3),
                              seconds=round(dt), rc=rc, e2_pairs=e2[-3:],
                              file=str(got.relative_to(WORK)) if got.is_file() else None))
    save_summary()
    if not got.is_file():
        log(f'seg{i}: no {got.name}, abandoning the fit phase')
        break
    used = pre + 2 * fade + final
    if rc == 0 and used > 200 and dt > 0:
        rate = max(0.4, min(6.0, dt / used * 1.1))     # 10 % margin on the measured rate
    prev, merged = got, True

CONTP = prev
log(f'continuous checkpoint {CONTP} ({CONTP.name})')

# --------------------------------------------------------------------------- post chain
FREE9 = '0.7,0.5,0.32,0.2,0.12,0.07,0.04,0.02,0.0'   # 9 rounding stages + the final w-only stage
if SMOKE:
    FREE9 = '0.5,0.25,0.0'
rounded, polished, refined, final_npz = (POST / n for n in
                                         ('rounded.npz', 'polished.npz', 'refined.npz', 'final.npz'))
METRIC_KEYS = ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')


def record(tag, metrics):
    S['metrics'][tag] = {k: float(metrics[k]) for k in METRIC_KEYS if k in metrics}
    save_summary()


def last_json(out):
    """The last JSON object printed on its own line (refine/refit print 'RESULT {...}')."""
    for line in reversed(out.splitlines()):
        i = line.find('{')
        if i >= 0:
            try:
                return json.loads(line[i:])
            except ValueError:
                continue
    return {}


avail = max(900.0 if SMOKE else 1500.0, WALL - el() - (900.0 if SMOKE else 3000.0))
stage, fin = (40, 60) if SMOKE else (700, 1800)
est = (9 * stage + fin) * 0.75 + 300   # ~0.75 s/Adam step at (5,143,75) on 4 vCPU
sc = max(0.3, min(1.0, avail / est))
stage, fin = int(stage * sc), int(fin * sc)
if SMOKE:
    stage, fin = 40, 60
S['post']['round_steps'] = dict(stage=stage, final=fin, scale=round(sc, 3))
rc = 1
if CONTP != SEED:
    rc, _ = run([PY, 'quantize.py', CONTP, rounded, '--brot', '8', '--x64',
                 '--stage-steps', stage, '--final-steps', fin, '--fit-steps', stage,
                 '--kappa', '5e-5', '--free', FREE9, '--lbfgs-until', '0'],
                min(avail, est * 1.7 + 600), 'round 8-bit')
src = rounded

if rc == 0 and src.is_file() and not SMOKE and WALL - el() > 5400:
    rc2, out2 = run([PY, 'polish_words.py', src, polished, '--brot', '8', '--sweeps', '2'],
                    min(1800, WALL - el() - 4200), 'polish')
    S['post']['polish'] = [ln for ln in out2.splitlines() if 'sweep' in ln][-2:]
    if rc2 == 0 and polished.is_file():
        src = polished

# refine is mandatory for a build (it is what writes U, W, H2_I and the one-body rows)
rounds = 1 if SMOKE else (4 if WALL - el() > 7200 else 2)
rc3, out3 = run([PY, 'refine.py', src, refined, '--brot', '8', '--rounds', rounds,
                 '--maxiter', 200 if SMOKE else 1500, '--margin', '0.0005'],
                min(3000 if not SMOKE else 1200, WALL - el() - 2400 if not SMOKE else WALL - el() - 600),
                'refine')
if rc3 == 0 and refined.is_file():
    src = refined
    m = last_json(out3)
    if m:
        record('refined', m)
save_summary()

# refit_weights spends whatever e2 headroom is left on lambda_eff
e2_limit = 500.0 if SMOKE else 19.95          # mHa
if src == refined and S['metrics'].get('refined', {}).get('error_2', 1.0) * 1e3 < e2_limit \
        and WALL - el() > (1800 if SMOKE else 4200):
    rc4, out4 = run([PY, 'refit_weights.py', refined, final_npz, '--target', str(e2_limit),
                     '--margin', '0.0005', '--rounds', '1' if SMOKE else '2',
                     '--maxiter', 200 if SMOKE else 1500],
                    min(600 if SMOKE else 2400, WALL - el() - (600 if SMOKE else 1800)),
                    'refit weights')
    if rc4 == 0 and final_npz.is_file():
        src = final_npz
        m = last_json(out4)
        if m:
            record('refit', m)
        save_summary()
S['post']['final_npz'] = str(src.relative_to(WORK))

# --------------------------------------------------------------------------- build + verify
for qrom in ('reference', 'tensor'):
    d = POST / f'sub8_{qrom}'
    rc5, out5 = run([PY, 'build.py', src, d, '--brot', '8', '--tree', 'log_depth',
                     '--shots', '64', '--qrom', qrom, '--json', POST / f'result_{qrom}.json'],
                    min(2400, WALL - el() - 300), f'build+verify {qrom} (64 shots/address)')
    p = POST / f'result_{qrom}.json'
    if p.is_file():
        S['verify'][qrom] = json.loads(p.read_text())
        save_summary()
    elif rc5 != 0:
        S['verify'][qrom] = {'error': (out5 or '')[-600:]}
        save_summary()

# two extra salts on the primary build, to show the words are salt invariant
prim = POST / 'sub8_reference'
if prim.is_dir() and WALL - el() > 900:
    code = ('import json,sys; sys.path.insert(0,"/kaggle/working/pipe");'
            'from dfthcsos.verify import verify;'
            'r=verify(sys.argv[1], salt=sys.argv[2]);'
            'print("SALT", json.dumps({k: r[k] for k in ("status","score","lambda_eff",'
            '"toffoli_count","num_qubits","verified_shots","submission_sha256")}))')
    for salt in ('r5backup-a', 'r5backup-b'):
        rc6, out6 = run([PY, '-c', code, prim, salt], 900, f'verify salt {salt}')
        for line in out6.splitlines():
            if line.startswith('SALT '):
                S['verify'][f'salt:{salt}'] = json.loads(line[5:])
        save_summary()

S['elapsed_hours'] = round(el() / 3600, 2)
save_summary()
log('summary', json.dumps({k: S[k] for k in ('segments', 'post', 'metrics', 'verify')})[:4000])
log('done')
