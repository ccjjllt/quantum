"""Assemble the Kaggle kernel folder for the C-axis sweep (CPU only).

main.py = wsolve.py (library, inlined) + a payload constant + the driver.
"""
import base64
import io
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
ROOT = pathlib.Path('/Users/zhaohuaxiang/ccjjllt/quantum')
KER = HERE / 'k_caxis'
KER.mkdir(exist_ok=True)

z = np.load(ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
y44 = np.load(ROOT / 'artifacts/20261117_lambda_measure/y_C44_ship.npz')['y']
buf = io.BytesIO()
np.savez_compressed(
    buf,
    angle_words=z['angle_words'].astype(np.uint8),
    tree_edges=z['tree_edges'].astype(np.uint8),
    w_ship=z['W'].astype(np.float32),
    wB_ship=z['H2_I'].astype(np.float32),
    y44=np.asarray(y44, dtype=np.float32),
)
b64 = base64.b64encode(buf.getvalue()).decode()
print('payload npz bytes', buf.tell(), 'b64 chars', len(b64))

ws = (HERE / 'wsolve.py').read_text()
drv = (HERE / 'kernel_driver.py').read_text()
# driver: drop its own imports of wsolve and read the payload from the constant
drv = drv.replace('sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nimport wsolve as WS\n', '')
drv = drv.replace("""def payload():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'payload.b64')) as f:
        raw = base64.b64decode(f.read())
    z = np.load(io.BytesIO(raw))
    return {k: z[k] for k in z.files}""",
                  """def payload():
    raw = base64.b64decode(PAYLOAD_B64)
    z = np.load(io.BytesIO(raw))
    return {k: z[k] for k in z.files}""")
assert 'PAYLOAD_B64' in drv and 'import wsolve' not in drv

main = (ws
        + '\n\n# ---------------------------------------------------------------- module shim\n'
          'import sys as _sys, types as _types\n'
          "WS = _sys.modules['__main__']\n"
          f"PAYLOAD_B64 = '{b64}'\n\n"
        + drv)
(KER / 'main.py').write_text(main)
print('main.py bytes', len(main))
meta = {
    "id": "qingyu1232/qcc-chem-c-axis-frozen-u",
    "title": "Qcc Chem C Axis Frozen U",
    "code_file": "main.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": False,
    "machine_shape": "",
    "dataset_sources": [],
    "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
    "kernel_sources": [],
    "model_sources": [],
}
(KER / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
print('wrote', KER / 'main.py')
