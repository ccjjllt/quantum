"""Generate a Kaggle CPU verifier kernel for a candidate invsqrt .kmb.

Usage:
  python gen_verify.py <kmb> <kernel-slug> "<label>:<args>" ["<label>:<args>" ...]

Each spec is "<label>:<verifier args>" where args is a shell-like string appended to
  python verifiers/invsqrt/verify_submission_invsqrt.py /tmp/cand.kmb <args>
e.g. "default_full:" or "s1_fast:--salt s1 --shots-per-x 1".
"""
import base64
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
kmb_path = pathlib.Path(sys.argv[1])
slug = sys.argv[2]
specs = [s.split(':', 1) for s in sys.argv[3:]] or [('default_full', '')]
raw = kmb_path.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
b64 = base64.b64encode(raw).decode()

TEMPLATE = r'''# QCC invsqrt candidate verification (official verifier, unmodified).
import base64, hashlib, json, os, subprocess, sys
from pathlib import Path

INPUT = Path('/kaggle/input')
def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]
KSO = _walk('kickmix.so')[0]
COMP = next(p for p in _walk('verify_submission_invsqrt.py') if 'verifiers' in str(p)).parents[2]
print('competition data', COMP, 'kickmix.so', KSO)
PAYLOAD = """__B64__"""
raw = base64.b64decode(PAYLOAD)
cand = Path('/kaggle/working/cand.kmb')
cand.write_bytes(raw)
print('candidate sha256', hashlib.sha256(raw).hexdigest(), 'bytes', len(raw))
print('expected        __SHA__')

env = dict(os.environ, PYTHONPATH=f'{KSO.parent}:{COMP / "verifiers"}')
SPECS = __SPECS__

for label, args in SPECS:
    cmd = [sys.executable, str(COMP / 'verifiers/invsqrt/verify_submission_invsqrt.py'), str(cand)] + args.split()
    print('=' * 20, label, ' '.join(args.split()), flush=True)
    out = subprocess.run(cmd, capture_output=True, text=True, env=env)
    text = out.stdout
    try:
        rep = json.loads(text[text.index('{'):])
        print('STATUS', rep['status'], 'score', rep['score'], 'Q', rep['num_qubits'],
              'meanT', rep.get('mean_toffolis'), 'worst', rep.get('worst_error_over_tolerance'))
        print(json.dumps(rep, indent=1)[:3000])
    except Exception as e:
        print('PARSE_FAIL', e)
        print('rc', out.returncode)
        print(text[-4000:])
        print(out.stderr[-4000:])
print('DONE')
'''

code = TEMPLATE.replace('__B64__', b64).replace('__SHA__', sha).replace('__SPECS__', repr(specs))
d = ROOT / 'kaggle' / slug
d.mkdir(parents=True, exist_ok=True)
(d / 'verify.py').write_text(code)
meta = {
    "id": f"jiyujia/{slug}",
    "title": slug.replace('-', ' ')[:50],
    "code_file": "verify.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": [],
    "dataset_sources": [],
    "kernel_sources": [],
    "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
    "model_sources": [],
}
(d / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
print('wrote', d, 'sha', sha, 'size', len(raw))
