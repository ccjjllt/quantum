"""Code-axis probe: does any legal bit-0/bit-1/bit-2 code change survive the gates?

The metrics are computed from the word table only (classical algebra, no circuit
simulation): theta/pi = word/128, decoded on the Givens tree.

Baseline (shipped, refit weights): e1 19.9992 / e2 19.99997 mHa (gates 20),
Lambda 283.2165, E_gap 3.914902 (floor 3.914898), lambda_eff 46.9276.

A code change at bit b flips that bit of the affected words on a set of
addresses, i.e. moves the angle by 2**b * pi/128.  Here: legal code moves
(affine replacements keep the code family; nonlinear ones only show the size of
the effect).
"""
import sys, json
from pathlib import Path
import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dfthcsos import verify as V  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
inputs = V.load_inputs(BUILD / 'submission.npz')
z = np.load(BUILD / 'submission.npz', allow_pickle=False)
words = np.asarray(z['angle_words'], np.int64)
edges = np.asarray(z['tree_edges'])
BROT = 8


def metrics(w):
    m = V.evaluate_words(inputs, w, edges, BROT)
    return {k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}


def show(tag, m):
    print(json.dumps({'tag': tag, 'e1_mHa': round(1e3 * m['error_1'], 4),
                      'e2_mHa': round(1e3 * m['error_2'], 5), 'Lambda': round(m['Lambda'], 4),
                      'E_gap': round(m['E_gap'], 6), 'lambda_eff': round(m['lambda_eff'], 6),
                      'e1_ok': m['error_1'] <= 20e-3, 'e2_ok': m['error_2'] <= 20e-3,
                      'gap_ok': m['E_gap'] > 3.914898}), flush=True)


base = metrics(words)
show('baseline', base)

addr = np.arange(1220)
low = addr & 15
out = {'baseline': base}

# (1) legal: flip bit 0 of one word everywhere (constant affine code change)
for col in (0, 7, 37, 74):
    w = words.copy()
    w[:, col] ^= 1
    m = metrics(w)
    out[f'bit0_const_col{col}'] = m
    show(f'bit0 const flip, column {col}', m)

# (2) legal: flip bit 0 where low bit 0 = 1 (affine code change, one word)
w = words.copy()
w[low & 1 == 1, 37] ^= 1
m = metrics(w)
out['bit0_lin_col37'] = m
show('bit0 flip on low-bit-0, column 37', m)

# (3) legal: flip bit 1 of the XOR of five words where low bit 1 = 1 (one batch)
w = words.copy()
for j in range(5):
    w[low & 2 == 2, 35 + j] ^= 2
m = metrics(w)
out['xor5_bit1_lin_batch7'] = m
show('XOR-of-5 bit1 flip on low-bit-1, batch 7', m)

# (4) legal: flip bit 2 of the XOR of five words on a quadratic low monomial
w = words.copy()
sel = (low & 3) == 3
for j in range(5):
    w[sel, 35 + j] ^= 4
m = metrics(w)
out['xor5_bit2_quad_batch7'] = m
show('XOR-of-5 bit2 flip on low monomial 3, batch 7', m)

# (5) pi-gauge: flip bit 7 of one whole column (theta -> theta + pi on that angle)
w = words.copy()
w[:, 37] ^= 128
m = metrics(w)
out['pigauge_col37'] = m
show('pi-gauge (bit 7) on column 37', m)

# (6) pi-gauge on the whole first batch (5 columns)
w = words.copy()
w[:, 0:5] ^= 128
m = metrics(w)
out['pigauge_batch0'] = m
show('pi-gauge (bit 7) on batch 0', m)

(Path(__file__).resolve().parent / 'code_probe.json').write_text(json.dumps(out, indent=1))
