"""Cost test: does a slope-matched bit-0 code really buy +4 forced cuts / word?

Re-code the 5 word columns of loader `k` (columns 5k..5k+4) so that, at every 16-address
block h, their bit-0 affine *slope* equals that of columns 5k-5..5k-1.  The delta that
loader k loads then has bit 0 constant in the low address bits, i.e. all 15 low monomials
of that output bit are cut (instead of the 11 nonlinear ones).

No metrics here: this only measures the loader cost (census + planner).
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHEM = HERE.parent
sys.path.insert(0, str(CHEM / 'code2'))
sys.path.insert(0, str(CHEM / 'code2' / 'compiler'))

import compile_basis as cb  # noqa: E402
from planner import complete_words, cross_tensor, NDIM  # noqa: E402
from parity_recover import NOUT  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push'
             '/bdae_dataset')
M35 = (1 << NOUT) - 1
NL = [m for m in range(15) if bin(m + 1).count('1') >= 2]      # nonlinear low masks (0-based)
LIN = [m for m in range(15) if bin(m + 1).count('1') == 1]     # masks 1,2,4,8


def load_words():
    with np.load(BUILD / 'submission.npz') as z:
        return np.asarray(z['angle_words'], np.int64)


def affine(bits):
    """(slope, const) if the 16-bit pattern is affine in the 4 low address bits."""
    for a in range(16):
        c = int(bits[0])
        if all(int(bits[t]) == (c ^ (bin(a & t).count('1') & 1)) for t in range(16)):
            return a, c
    return None


def slopes(words, col):
    return [affine([(int(words[16 * h + t, col]) >> 0) & 1 for t in range(16)]) for h in range(76)]


def flip_bit0(words, col, h, mask):
    """Toggle value bit 0 (parity) of the words at (block h, t) for every t with mask&t odd.

    v ^ 1 keeps bits 1..7, so the bit-1 / bit-2 XOR codes of the loader survive.
    """
    out = words.copy()
    for t in range(16):
        if bin(mask & t).count('1') & 1:
            out[16 * h + t, col] ^= 1
    return out


def recode(words, k, which=range(5), side='right', verbose=True):
    """Make group k's bit-0 slope equal group k-1's at every block, for the words in `which`."""
    out = words.copy()
    nflip = 0
    for j in which:
        a_new = slopes(words, 5 * k + j)
        a_old = slopes(words, 5 * k - 5 + j)
        for h in range(76):
            if a_new[h] is None or a_old[h] is None:
                raise RuntimeError(f'non-affine slope col {5*k+j} block {h}')
            m = a_new[h][0] ^ a_old[h][0]
            if m:
                col = 5 * k + j if side == 'right' else 5 * k - 5 + j
                out = flip_bit0(out, col, h, m)
                nflip += 8
    if verbose:
        print(f'recode loader {k} words {list(which)} side {side}: {nflip} word bit-0 flips')
    return out


def census(words, ks):
    """Per loader: forced nonlinear cuts per relation, and (new) forced *linear* cuts."""
    Wc = complete_words(np.asarray(words, np.uint8))
    out = {}
    for k in ks:
        t = cross_tensor(Wc, k)
        rels = [('lsb0', 1 << 0), ('lsb1', 1 << 7), ('lsb2', 1 << 14), ('lsb3', 1 << 21),
                ('lsb4', 1 << 28), ('xor_b1', sum(1 << (7 * z + 1) for z in range(5))),
                ('xor_b2', sum(1 << (7 * z + 2) for z in range(5)))]
        row = {}
        for name, rel in rels:
            nl = sum(all(bin((((x >> (NOUT * m)) & M35) & rel)).count('1') % 2 == 0 for x in t[1:76])
                     for m in NL)
            lin = sum(all(bin((((x >> (NOUT * m)) & M35) & rel)).count('1') % 2 == 0 for x in t[1:76])
                      for m in LIN)
            row[name] = (nl, lin)
        row['forced_nl'] = sum(v[0] for v in row.values() if isinstance(v, tuple))
        row['forced_lin'] = sum(v[1] for v in row.values() if isinstance(v, tuple))
        out[k] = row
    return out


if __name__ == '__main__':
    ks = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '4').split(',')]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'census'
    words = load_words()
    print('shipped census (nonlinear, linear forced cuts per relation):')
    for k, r in census(words, ks).items():
        print('  k', k, {n: v for n, v in r.items()})
    for k in ks:
        mod = recode(words, k)
        print(f'\nre-coded loader {k} census:')
        for kk, r in census(mod, [k, k + 1]).items():
            print('  k', kk, {n: v for n, v in r.items()})
