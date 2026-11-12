"""Official structural check of a built family: do the circuits load the table, and does the simulated
Toffoli count equal 2 x the static count? (1 shot per address, not the 64-shot accuracy run.)"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import numpy as np
import common as C
from dfthcsos.scoreinfra.circuits import load_circuits, recover_words_from_circuits

fam_dir = sys.argv[1]
with np.load(os.path.join(fam_dir, 'submission.npz'), allow_pickle=False) as z:
    words = np.asarray(z['angle_words'], np.int64)
    params = {k: np.array(z[k]) for k in C.KEYS}
fam = load_circuits(fam_dir)
got, layout, toff = recover_words_from_circuits(fam, num_vectors=1220, num_angles=75, shots_per_address=1, seed=0)
print(json.dumps({'words_equal': bool(np.array_equal(got, words)),
                  'toffoli_per_pass': toff/2, 'n_circuits': len(fam),
                  'brot': layout.brot, 'J': layout.batch_size}))
