"""per_output proxy of already-saved tables (same tables the real loader was built from)."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, numpy as np, common as C
import tensorqrom8 as tq
from fourqrom import batch_deltas
rows = []
for d in sorted(__import__('glob').glob('work/tree_*/submission.npz')):
    with np.load(d, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
    tot = 0
    for delta in batch_deltas(words, 5):
        t = tq.anf_tensor(delta, 8, 4, full=True)
        tot += int(tq.cost(tq.per_output(t), t.shape[0], t.shape[1]))
    rows.append((d.split('/')[1][5:], tot))
for name, tot in rows:
    print(f'{name:12s} proxy {tot}')
C.dump({'stage': 'proxy_saved', 'rows': rows}, C.HERE/'logs/proxy_saved.jsonl')
