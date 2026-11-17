"""Calibration: re-emit the shipped 15 plans locally and compare the emitter's
Toffoli count with the officially measured per-loader counts.

No circuit simulation: emit_plan only builds the .kmx text and reports
len(products with high support) + len(computes).
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SRC = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/src/dfthcsos_source')
sys.path.insert(0, str(HERE / 'compiler'))

z = np.load(SRC / 'submission.npz', allow_pickle=False)
words = np.asarray(z['angle_words'], dtype=np.int64)
assert words.shape == (1220, 75)


def complete(words):
    a = np.zeros((1232, 75), dtype=np.uint8)
    a[:1220] = words.astype(np.uint8)
    f = a.reshape(77, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    f[76, 4:] = 0
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    assert np.array_equal(a[:1220], words.astype(np.uint8))
    return a


Wc = complete(words)
from emit_plan import emit as emit_regular  # noqa: E402
from emit_k0 import emit as emit_first      # noqa: E402

OFFICIAL = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]
out = []
for k in range(15):
    state = json.loads((SRC / 'plans' / f'angle_k_{k}.json').read_text())
    rep = (emit_first if k == 0 else emit_regular)(state, Wc, HERE / 'build' / f'angle_k_{k}.kmx')
    out.append(rep)
    print(json.dumps({'k': k, 'products': rep['product_count'], 'toffoli': rep['toffoli_count'],
                      'qubits': rep['num_qubits'], 'official': OFFICIAL[k],
                      'match': rep['toffoli_count'] == OFFICIAL[k],
                      'low_computes': rep.get('low_computes'),
                      'windows': len(state.get('windows', []))}), flush=True)
tot = sum(r['toffoli_count'] for r in out)
print('TOTAL re-emitted', tot, 'official', sum(OFFICIAL), 'match', tot == sum(OFFICIAL))
(HERE / 'calib_emit.json').write_text(json.dumps({'report': out, 'total': tot, 'official': OFFICIAL}, indent=1))
