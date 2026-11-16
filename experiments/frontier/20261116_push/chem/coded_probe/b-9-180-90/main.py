"""Coded-quantizer probe (b): merged (9,180,90) seed, fresh --coded rounding.

Input: jiyujia/qcc-chem-r9-merged-180x90 (the seg0 pre-fit checkpoint of the
r9 probe: continuous e2 19.838 -> 14.820, i.e. within the 20 mHa gate
pre-shrink). Fresh quantize.py --coded "0-14" at brot 8 (all 75 word columns:
no shipped batches to preserve at this shape), then refine.py, then
refit_weights.py — the exact public coded path, all fits on Kaggle CPU.

Question: does coded rounding AT THE MERGED SIZE preserve e2 <= 20 mHa, and
what forced-cut census does it carry (per-word bit0 affine + delta/XOR codes)?
Plain passed here in the continuous sense (14.820), so --coded is eligible per
RESULT6 §5. No loader port exists at 1,696 rows, so per-loader T is reported as
a model (products from Σcuts at the shipped cache) and the shape is priced
exactly (T_heur/Q) for the cost verdict. build.py + the unchanged official
verifier (64 shots/address, default + 2 salts) run ONLY on a passing gate.

Nothing is submitted. Output: /kaggle/working/{post,census}/** + summary.json.
"""

import glob
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------ config
CODED = "0-14"
BROT = 8
FREE9 = '0.7,0.5,0.32,0.2,0.12,0.07,0.04,0.02,0.0'
Q_STAGE, Q_FIN = 400, 1000
# ------------------------------------------------------------------

WORK = Path('/kaggle/working')
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
hits = glob.glob('/kaggle/input/**/9x180x90.npz', recursive=True)
assert hits, 'merged checkpoint 9x180x90.npz not found in /kaggle/input'
STRUCT = Path(hits[0])
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
WALL = float(os.environ.get('WALL_HOURS', '9.0')) * 3600.0
S = {'kernel': 'jiyujia/qcc-chem-coded-r9merged', 'coded': CODED, 'brot': BROT,
     'structure': str(STRUCT), 'wall_hours': WALL / 3600,
     'segments': [], 'post': {}, 'metrics': {}, 'census': {}, 'verify': {}}


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


METRIC_KEYS = ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')


def record(tag, metrics):
    S['metrics'][tag] = {k: float(metrics[k]) for k in METRIC_KEYS if k in metrics}
    save_summary()


# ------------------------------------------------------------- quantize
rounded, refined, final_npz = (POST / n for n in ('rounded.npz', 'refined.npz', 'final.npz'))
rc, out = run([PY, 'quantize.py', STRUCT, rounded, '--brot', str(BROT), '--x64',
               '--stage-steps', Q_STAGE, '--final-steps', Q_FIN, '--fit-steps', Q_STAGE,
               '--kappa', '5e-5', '--free', FREE9, '--lbfgs-until', '0',
               '--coded', CODED],
              min(max(WALL - el() - 3600, 600), 4.0 * 3600), 'round 8-bit coded ' + CODED)
S['segments'].append({'step': 'quantize-coded-' + CODED, 'rc': rc,
                      'e2_pairs': re.findall(r'error_2\s+([\d.]+)\s+->\s+([\d.]+)\s+mHa', out or '')[-6:]})
save_summary()
src = rounded

# ------------------------------------------------------------- refine
if rc == 0 and src.is_file():
    rc3, out3 = run([PY, 'refine.py', src, refined, '--brot', str(BROT), '--rounds', '3',
                     '--maxiter', '1000', '--margin', '0.0005'],
                    min(2400, max(WALL - el() - 1800, 300)), 'refine')
    if rc3 == 0 and refined.is_file():
        src = refined
        m = last_json(out3)
        if m:
            record('refined', m)
save_summary()

# ------------------------------------------------------------- weight refit (gate 19.95, as in fresh-shape probes)
ref_e2 = S['metrics'].get('refined', {}).get('error_2', 1.0)
if src == refined and ref_e2 * 1e3 < 19.95 and WALL - el() > 3600:
    rc4, out4 = run([PY, 'refit_weights.py', refined, final_npz, '--target', '19.95',
                     '--margin', '0.0005', '--rounds', '2', '--maxiter', '1000'],
                    min(1800, max(WALL - el() - 1500, 300)), 'refit weights')
    if rc4 == 0 and final_npz.is_file():
        src = final_npz
        m = last_json(out4)
        if m:
            record('refit', m)
        save_summary()
S['post']['final_npz'] = str(src.relative_to(WORK))

# ------------------------------------------------------------- census (numpy only)
NOUT_C = 35
M35 = (1 << NOUT_C) - 1
NL1 = [m for m in range(1, 16) if bin(m).count('1') >= 2]   # 11 nonlinear low masks
CUB1 = [m for m in NL1 if bin(m).count('1') >= 3]            # 5 cubic masks
RELS = [('lsb0', 1 << 0), ('lsb1', 1 << 7), ('lsb2', 1 << 14), ('lsb3', 1 << 21),
        ('lsb4', 1 << 28),
        ('xor_b1', sum(1 << (7 * z + 1) for z in range(5))),
        ('xor_b2', sum(1 << (7 * z + 2) for z in range(5)))]


def complete_words(words, rows):
    nfull = -(-rows // 16)
    nbits = max(1, (nfull - 1).bit_length())
    a = np.zeros((nfull * 16, words.shape[1]), dtype=np.uint8)
    a[:rows] = (words[:rows] & 255).astype(np.uint8)
    f = a.reshape(nfull, 16, -1)
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(nbits):
        for h in range(nfull):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    if rows % 16:
        f[-1, rows % 16:] = 0
    for b in range(nbits):
        for h in range(nfull):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    return a, nfull, nbits


def slice_vecs(Wc, k, nfull, nbits):
    delta = Wc[:, 5 * k:5 * k + 5].astype(np.int64).copy()
    if k:
        delta ^= Wc[:, 5 * k - 5:5 * k]
    packed = np.zeros(nfull * 16, dtype=np.uint64)
    for j in range(5):
        packed |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(nfull, 16).copy()
    for b in range(4):
        for lo in range(16):
            if lo & (1 << b):
                f[:, lo] ^= f[:, lo ^ (1 << b)]
    for b in range(nbits):
        for hi in range(nfull):
            if hi & (1 << b):
                f[hi] ^= f[hi ^ (1 << b)]
    return [sum(int(f[h, l]) << ((l - 1) * NOUT_C) for l in range(1, 16)) for h in range(nfull)]


def affine_pat(bits16):
    for a in range(16):
        c = int(bits16[0])
        if all(int(bits16[t]) == (c ^ (bin(a & t).count('1') & 1)) for t in range(16)):
            return (a, c)
    return None


def census(words, rows, nlouders=15):
    Wc, nfull, nbits = complete_words(words, rows)
    nreal = (rows - 1) // 16 + 1
    per_loader, tot_cuts = [], 0
    for k in range(nlouders):
        t = slice_vecs(Wc, k, nfull, nbits)
        hold = {}
        for name, rel in RELS:
            got = []
            for m in range(15):
                if all(bin((((x >> (NOUT_C * m)) & M35) & rel)).count('1') % 2 == 0
                       for x in t[1:nreal]):
                    got.append(m + 1)
            hold[name] = got
        lsb = sum(len(set(v) & set(NL1)) for n, v in hold.items() if n.startswith('lsb'))
        xb1 = len(set(hold['xor_b1']) & set(NL1))
        xb2 = len(set(hold['xor_b2']) & set(CUB1))
        sc = lsb + xb1 + xb2
        per_loader.append({'k': k, 'lsb_nonlin': lsb, 'xor_b1_nonlin': xb1,
                           'xor_b2_cubic': xb2, 'sum_cuts': sc,
                           'products_model': (525 - sc) / 2,
                           'T_model_shipped_cache': (525 - sc) / 2 + 69 + 6})
        tot_cuts += sc
    return {'per_loader': per_loader, 'total_cuts': tot_cuts, 'nfull': nfull, 'nbits': nbits,
            'nreal': nreal}


def bitaffine_summary(words, rows):
    nblk = rows // 16  # floor blocks; tail rows (<16) ignored, as in inspect2/recode
    out = {}
    for b in (0, 1, 2):
        bad = 0
        per_col = []
        for zz in range(words.shape[1]):
            c = 0
            for h in range(nblk):
                bits = [(int(words[16 * h + t, zz]) >> b) & 1 for t in range(16)]
                if affine_pat(bits) is None:
                    c += 1
            per_col.append(c)
            bad += c
        out[f'bit{b}'] = {'nonaffine_blockcols': bad, 'nonaffine_cols': sum(1 for c in per_col if c)}
    return out


zc = np.load(src)
new_words = np.asarray(zc['angle_words'], np.int64)
rows = int(new_words.shape[0])
assert rows == 1696, new_words.shape
S['census']['new'] = census(new_words, rows)
S['census']['new']['bitaffine'] = bitaffine_summary(new_words, rows)
ccols = [int(c) for c in zc['coded']] if 'coded' in zc.files else []
S['census']['coded_cols'] = ccols
log('CENSUS total_cuts', S['census']['new']['total_cuts'])
log('CENSUS bitaffine', json.dumps(S['census']['new']['bitaffine']))
log('CENSUS per-loader', json.dumps([(d['k'], d['sum_cuts']) for d in S['census']['new']['per_loader']]))
save_summary()

# ------------------------------------------------------------- gate + official verify only on pass
GAP_FLOOR = 3.914898
gate = S['metrics'].get('refit', S['metrics'].get('refined', {}))
e1 = gate.get('error_1', 1.0) * 1e3
e2 = gate.get('error_2', 1.0) * 1e3
gap = gate.get('E_gap', 0.0)
log(f'GATE e1 {e1:.3f} e2 {e2:.3f} E_gap {gap:.9f} (limits 20 / 20 / {GAP_FLOOR})')
S['post']['gate'] = {'e1_mHa': e1, 'e2_mHa': e2, 'E_gap': gap,
                     'pass': bool(e1 <= 20 and e2 <= 20 and gap > GAP_FLOOR)}
save_summary()
if S['post']['gate']['pass'] and WALL - el() > 2400:
    d = POST / 'sub8_tensor'
    rc5, out5 = run([PY, 'build.py', src, d, '--brot', str(BROT), '--tree', 'log_depth',
                     '--shots', '64', '--qrom', 'tensor', '--json', POST / 'result_tensor.json'],
                    min(2400, WALL - el() - 300), 'build+verify tensor (64 shots/address)')
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
    log('gate not passed (or no time left): no build, no official verify')

S['elapsed_hours'] = round(el() / 3600, 2)
save_summary()
log('done')
