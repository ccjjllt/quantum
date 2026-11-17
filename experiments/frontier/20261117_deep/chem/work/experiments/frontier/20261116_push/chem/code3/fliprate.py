"""How expensive is one bit-0 (parity) word flip in error_2?  Rate measurement for RESULT4.

A word flip here is  v -> v ^ 1  (toggles the value's bit 0, keeps bits 1..7, so the loader's
bit-1/bit-2 XOR codes survive).  The re-code that buys +4 forced cuts per word needs 8 flips per
16-address block, i.e. ~574 flips per word column.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evalkit import Eval, load_pkg  # noqa: E402
from recode import load_words, recode, slopes  # noqa: E402

PKG = ('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push'
       '/bdae_dataset/submission.npz')


def flips_cost(ev, words, cells):
    mod = words.copy()
    for r, c in cells:
        mod[r, c] ^= 1
    return 1e3 * ev.e2(mod), mod


def main():
    d = load_pkg(PKG)
    ev = Eval(d)
    w0 = load_words()
    base, _ = flips_cost(ev, w0, [])
    print(f'base e2 {base:.6f} mHa  (delta^2 budget to 20 mHa: {20**2-base**2:.2f} mHa^2)')
    out = {'base_mha': base}
    cases = {}
    # 1 flip
    cases['1 cell'] = [(0, 20)]
    # 8 flips: one block h=3 of column 20 where the slope differs from column 15
    a20, a15 = slopes(w0, 20), slopes(w0, 15)
    h = min(hh for hh in range(76) if a20[hh][0] != a15[hh][0])
    m = a20[h][0] ^ a15[h][0]
    cells8 = [(16 * h + t, 20) for t in range(16) if bin(m & t).count('1') & 1]
    cases[f'8 cells (block {h}, col 20)'] = cells8
    # 574: the whole column-20 slope-matched set vs column 15
    mod = recode(w0, 4, which=[0], side='right', verbose=False)
    cols = [(r, 20) for r in range(1220) if mod[r, 20] != w0[r, 20]]
    cases['full word-pair (col 20 vs 15)'] = cols
    mod5 = recode(w0, 4, which=[0, 1, 2, 3, 4], side='right', verbose=False)
    cols5 = [(r, c) for r in range(1220) for c in range(20, 25) if mod5[r, c] != w0[r, c]]
    cases['full loader (5 words)'] = cols5
    for name, cells in cases.items():
        e2, _ = flips_cost(ev, w0, cells)
        d2 = e2 ** 2 - base ** 2
        print(f'{name:32s} n={len(cells):5d}  e2 {e2:9.4f} mHa  delta^2 {d2:10.2f}  '
              f'per cell {d2/len(cells):7.3f}')
        out[name] = dict(n=len(cells), e2_mha=e2, d2=d2, per_cell=d2 / len(cells))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
