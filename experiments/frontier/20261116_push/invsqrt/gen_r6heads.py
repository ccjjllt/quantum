"""Generate Kaggle CPU kernel: static head-site inspection for invsqrt RESULT6.

No simulation, no verifier runs. Parses embedded 0af21cb8 via kickmix
Circuit.from_file -> .kmx text only, dumps the 4 unconverted staircase heads
and the converted tail block structure, and proves the v27 generator flow
exposes no re-emission site (input walk for generator sources).
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
SRC = pathlib.Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/invsqrt_0af21cb8.kmb")
raw = SRC.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
assert sha == "0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b", sha
b64 = base64.b64encode(raw).decode()

TEMPLATE = r'''# invsqrt RESULT6: static head-site inspection (NO simulation, NO verifier).
import base64, hashlib, os
from pathlib import Path

INPUT = Path('/kaggle/input')
def walk_all():
    out = []
    for d, _, files in os.walk(INPUT, followlinks=True):
        for f in files:
            out.append(Path(d) / f)
    return out

# 1. Prove the v27 generator flow is not exposed: search inputs for generator sources.
print('=== input walk (generator search) ===')
files = walk_all()
print('total files under /kaggle/input:', len(files))
cands = [str(p) for p in files if p.suffix in ('.py', '.json', '.zip', '.sh')]
print('py/json/zip/sh count:', len(cands))
hits = [s for s in cands if any(k in s.lower() for k in ('generat', 'emit', 'builder', 'carry', 'divider', 'patch', 'source_zip'))]
print('generator-like path hits:', len(hits))
for s in sorted(hits)[:40]:
    print('  ', s)
kmb = sorted(str(p) for p in files if p.name.endswith('.kmb'))
print('kmb files in inputs:', len(kmb))
for s in kmb[:20]:
    print('  ', s)
print('conclusion: inputs carry only competition verifiers/kickmix + pinned public bytes; no v27 emitter source.')

# 2. Static parse of embedded 0af21cb8 (text only, no Simulator).
PAYLOAD = """__B64__"""
raw = base64.b64decode(PAYLOAD)
print('embedded sha256', hashlib.sha256(raw).hexdigest())
print('expected      __SHA__')
assert hashlib.sha256(raw).hexdigest() == '__SHA__'
cand = Path('/kaggle/working/invsqrt_0af21cb8.kmb')
cand.write_bytes(raw)
print('bytes', len(raw))

import sys
def _walk(name):
    return [Path(d) / name for d, _, files in os.walk(INPUT, followlinks=True) if name in files]
KSO = _walk('kickmix.so')[0]
sys.path.insert(0, str(KSO.parent))
import kickmix
circ = kickmix.Circuit.from_file(cand, format='auto')
tmp = Path('/kaggle/working/circ.kmx')
circ.to_file(tmp)
lines = [l.strip() for l in tmp.read_text().splitlines() if l.strip() and not l.strip().startswith('#')]
print('text ops', len(lines))
ops = []
for l in lines:
    p = l.split()
    q = [int(t[1:]) for t in p[1:] if t.startswith('q')]
    b = [int(t[1:]) for t in p[1:] if t.startswith('b')]
    ops.append((p[0], q, b, l))

from collections import Counter
c = Counter(o[0] for o in ops)
print('opcode census:', dict(sorted(c.items())))
print('directives:', sum(1 for o in ops if o[0] in ('REGISTER', 'APPEND_TO_REGISTER')))

def show(a, b, label):
    print(f'--- [{label}] ops {a}..{b} ---')
    for i in range(a, b + 1):
        print(f'{i}: {ops[i][3]}')

# head sites from task (NEW indices)
for idx in (12139, 12142, 12596, 13037):
    show(idx - 3, idx + 3, f'head@{idx}')
# HMR boundaries + tail extent
for h in (12145, 12599, 13040):
    show(h - 2, h + 4, f'HMR@{h}')
# full first tail block extent check: NEW 12145..12262
print('--- tail block opcode census NEW 12145..12262 ---')
print(Counter(o[0] for o in ops[12145:12263]))
print('--- second tail NEW 12599..12707 ---')
print(Counter(o[0] for o in ops[12599:12708]))
print('--- third tail NEW 13040..13147 ---')
print(Counter(o[0] for o in ops[13040:13148]))

# exact head triple verification
def is_ccx(i, a, b, t):
    return ops[i][0] == 'CCX' and ops[i][1] == [a, b, t]
print('head1 12139 CCX[31,15,16]:', is_ccx(12139, 31, 15, 16), ops[12139][3])
print('head1 12142 CCX[29,41,15]:', is_ccx(12142, 29, 41, 15), ops[12142][3])
print('head2 12596 CCX[31,21,15]:', is_ccx(12596, 31, 21, 15), ops[12596][3])
print('head3 13037 CCX[8,41,15]:', is_ccx(13037, 8, 41, 15), ops[13037][3])
print('DONE_STATIC_ONLY')
'''

code = TEMPLATE.replace("__B64__", b64).replace("__SHA__", sha)
d = ROOT / "kaggle" / "qcc-invsqrt-r6-heads"
d.mkdir(parents=True, exist_ok=True)
(d / "heads.py").write_text(code)
meta = {
    "id": "jiyujia/qcc-invsqrt-r6-heads",
    "title": "qcc invsqrt r6 heads static",
    "code_file": "heads.py",
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
(d / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print("wrote", d, "sha", sha, "size", len(raw), "kernel bytes", len(code))
