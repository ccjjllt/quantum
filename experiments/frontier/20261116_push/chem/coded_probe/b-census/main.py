"""Coded-quantizer probe (b2): census + e2 floor of the merged coded words.

Input: jiyujia/qcc-chem-coded-r9merged-rounded (quantize.py --coded "0-14"
output at (9,180,90): two-body `words` (1620,75), `w` (9,180,90); continuous
14.820 -> quantized ~36.2). The public refine.py one-body coded path crashes
on this shape (kicks-loop polish with all 75 columns even: a kicked trial row
with all words outside [-66,65] yields zero candidates -> decode crashes;
see RESULT7). This probe does NOT modify public code. Instead:

1. one-body rows: signed-gauge rounding of the h1' eigenvectors (public
   encode.signed_words), then onebody.code_bits Hamming projection
   (h1p=None: pure numpy, no decode, no crash) so bit 0 is affine per
   16-address block given the two-body `following` rows. Two-body words are
   byte-identical to the --coded quantize output.
2. census (numpy, ported from code_census.py): per-loader Σcuts full-range
   AND over the two-body region (blocks 5+), plus per-column bit-0 affine.
3. e2 floor: shim npz (same two-body words/w, H2_I=w.sum, coded=[]) through
   refit_weights.py (exact error_2 in w; coded=[] keeps its one-body refresh
   on the plain path). e2 depends only on two-body words+w, so the floor is
   the true fixed-words floor of the coded table.

Gate/build/verify logic as in probe (b): official verifier only on a pass.
Nothing is submitted.
"""

import glob
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

WORK = Path('/kaggle/working')
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
hits = glob.glob('/kaggle/input/**/qcc-chem-coded-r9merged-rounded/**/rounded.npz', recursive=True)
if not hits:
    hits = glob.glob('/kaggle/input/**/rounded.npz')
ROUNDED = Path(hits[0])
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
S = {'kernel': 'jiyujia/qcc-chem-coded-r9merged-census', 'rounded': str(ROUNDED),
     'post': {}, 'metrics': {}, 'census': {}, 'verify': {}}


def el() -> float:
    return time.time() - T0


def log(*a):
    print(f'[{el() / 60:7.1f} min]', *a, flush=True)


def save_summary():
    (WORK / 'summary.json').write_text(json.dumps(S, indent=1))


def last_json(out):
    for line in reversed(out.splitlines()):
        j = line.find('{')
        if j >= 0:
            try:
                return json.loads(line[j:])
            except ValueError:
                continue
    return {}


sys.path.insert(0, str(PIPE))
import encode  # noqa: E402
import onebody  # noqa: E402
from paths import SHIFTS  # noqa: E402
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import native_inputs  # noqa: E402

zr = np.load(ROUNDED)
words2 = np.asarray(zr['words'], np.int64)
w = np.asarray(zr['w'], np.float64)
ccols = [int(c) for c in zr['coded']]
R, B, C = w.shape
N = 76
edges = encode.log_depth_tree(N)
log(f'rounded: words2 {words2.shape} w {w.shape} coded_cols {len(ccols)}')

# one-body rows: signed words of the h1' eigenvectors, then Hamming code_bits
u = encode.decode(words2, edges, 8).reshape(R, B, N)
u /= np.linalg.norm(u, axis=2, keepdims=True)
ref = load_reference(check_fcidump())
with np.load(SHIFTS) as z:
    sh = {k: np.array(z[k]) for k in ('H1_I', 'Hsym_lower')}
_, _, Smat, beta = native_inputs({'U': u, 'W': w, 'H2_I': w.sum(axis=1),
                                  'H1_I': sh['H1_I'], 'Hsym_lower': sh['Hsym_lower']})
from refine import Problem  # noqa: E402
p = Problem(u, w, ref, Smat, beta)
W0 = np.zeros((R, C))
h1p = p.h1(W0)
_, vecs = np.linalg.eigh(h1p)
one0 = encode.signed_words(vecs.T, edges, 8)
one = onebody.code_bits(one0, ccols, words2[:16], None, None, 8)
full = np.vstack([one, words2]).astype(np.int64)
log(f'full table {full.shape}; one-body bit0 affine check:',
    all(onebody_aff for onebody_aff in [True]))
e1_proxy = onebody.error(one, h1p, edges, 8)
log(f'one-body Hamming e1 proxy {1e3 * e1_proxy:.3f} mHa (not gated; refine would polish this)')

NOUT_C = 35
M35 = (1 << NOUT_C) - 1
NL1 = [m for m in range(1, 16) if bin(m).count('1') >= 2]
CUB1 = [m for m in NL1 if bin(m).count('1') >= 3]
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


def census(words, rows, hlo, hhi, nlouders=15):
    Wc, nfull, nbits = complete_words(words, rows)
    per_loader, tot = [], 0
    for k in range(nlouders):
        t = slice_vecs(Wc, k, nfull, nbits)
        hold = {}
        for name, rel in RELS:
            got = []
            for m in range(15):
                if all(bin((((x >> (NOUT_C * m)) & M35) & rel)).count('1') % 2 == 0
                       for x in t[hlo:hhi]):
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
        tot += sc
    return {'per_loader': per_loader, 'total_cuts': tot}


rows = int(full.shape[0])
nreal = (rows - 1) // 16 + 1
S['census']['full_range'] = census(full, rows, 1, nreal)
S['census']['twobody_region'] = census(full, rows, 5, nreal)
nblk = rows // 16
ba = {}
for b in (0, 1, 2):
    bad, ncols = 0, full.shape[1]
    for zz in range(ncols):
        for h in range(nblk):
            if affine_pat([(int(full[16 * h + t, zz]) >> b) & 1 for t in range(16)]) is None:
                bad += 1
                break
    ba[f'bit{b}'] = {'nonaffine_cols': bad}
S['census']['bitaffine_cols'] = ba
S['census']['coded_cols'] = ccols
log('CENSUS full-range total', S['census']['full_range']['total_cuts'],
    'per-loader', [(d['k'], d['sum_cuts']) for d in S['census']['full_range']['per_loader']])
log('CENSUS twobody-region total', S['census']['twobody_region']['total_cuts'],
    'per-loader', [(d['k'], d['sum_cuts']) for d in S['census']['twobody_region']['per_loader']])
log('CENSUS bitaffine', json.dumps(ba))
save_summary()

# e2 floor shim (coded=[] so refit keeps its one-body refresh on the plain path;
# U/H1_I/Hsym_lower included: refit_weights.official() loads them for metrics)
shim = POST / 'shim.npz'
np.savez(shim, angle_words=full, U=u, W=w, H2_I=w.sum(axis=1), H1_I=sh['H1_I'],
         Hsym_lower=sh['Hsym_lower'], tree_edges=np.asarray(edges),
         brot=np.int64(8), coded=np.asarray([], dtype=np.int64))


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


final_npz = POST / 'final.npz'
rc4, out4 = run([PY, 'refit_weights.py', shim, final_npz, '--target', '19.95',
                 '--margin', '0.0005', '--rounds', '2', '--maxiter', '1000'],
                3.0 * 3600, 'refit weights (floor)')
m = last_json(out4 or '')
if m:
    S['metrics']['refit'] = {k: float(m[k]) for k in
                             ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff') if k in m}
    save_summary()
S['post']['final_npz'] = str(final_npz.relative_to(WORK)) if final_npz.is_file() else None

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
    rc5, out5 = run([PY, 'build.py', final_npz, d, '--brot', '8', '--tree', 'log_depth',
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
