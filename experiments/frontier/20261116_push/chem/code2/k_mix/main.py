import glob, json, sys
from pathlib import Path
import numpy as np

COMP = 'google-verifiable-quantum-circuit-compilation'
DATA = next(p for p in (Path('/kaggle/input/competitions') / COMP, Path('/kaggle/input') / COMP) if (p / 'verifiers').is_dir())
for p in [DATA / 'kickmix', DATA / 'verifiers']:
    sys.path.insert(0, str(p))
import kickmix as km
from dfthcsos import verify as V
from dfthcsos.scoreinfra.circuits import register_layout

BUILD = next(Path(h).parent for h in glob.glob('/kaggle/input/**/angle_k_14.kmb', recursive=True) if Path(h).is_file())
print('build:', BUILD, sorted(p.name for p in BUILD.iterdir()), flush=True)

out = {}
for salt in ['', 'dfthcsos-20261116-a', 'dfthcsos-20261116-b']:
    r = V.verify(BUILD, salt=salt)
    out[salt or 'default'] = r
    print(f"--- salt={salt!r}: {r['status']} score {r['score']:.6f} T {r['toffoli_count']:.0f} "
          f"Q {r['num_qubits']} lambda_eff {r['lambda_eff']:.6f}", flush=True)

res, met = out['default']['resources'], out['default']['metrics']
print('RESOURCES', json.dumps({k: float(v) for k, v in res.items()}, indent=1), flush=True)
print('METRICS', json.dumps({k: float(v) for k, v in met.items()}, indent=1), flush=True)

fam = V.load_circuits(BUILD)
stats = [{'k': k, 'toffoli': int(c.operation_statistics().num_toffoli_like), 'qubits': int(c.num_qubits)}
         for k, c in enumerate(fam)]
print('static per loader:', stats, flush=True)
print('sum', sum(s['toffoli'] for s in stats), flush=True)
layout = register_layout(fam)
print('layout: selection', len(layout.selection), 'J', layout.batch_size, 'brot', layout.brot, flush=True)

# the table the circuits actually load vs the shipped npz words
z = np.load(BUILD / 'submission.npz')
W_ = np.asarray(z['angle_words'], np.int64)
got = np.asarray(out['default']['angle_words'], np.int64)
diff = np.argwhere(got != W_)
print('recovered words equal npz angle_words:', bool(np.array_equal(got, W_)), 'diffs', int(len(diff)), flush=True)
if len(diff):
    print('first diffs', [(int(i), int(j), int(W_[i, j]), int(got[i, j])) for i, j in diff[:12]], flush=True)

Path('/kaggle/working/code2_verify.json').write_text(json.dumps(
    {'verify': {k: {kk: float(vv) for kk, vv in v.items()
                    if kk in ('score', 'toffoli_count', 'num_qubits', 'lambda_eff')} for k, v in out.items()},
     'resources': {k: float(v) for k, v in res.items()},
     'metrics': {k: float(v) for k, v in met.items()},
     'loaders': stats,
     'words_match_npz': bool(np.array_equal(got, W_)),
     'n_word_diffs': int(len(diff))}, indent=1))
print('wrote /kaggle/working/code2_verify.json')
