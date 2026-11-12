"""Per-stage Toffoli accounting of the public v21 generator (889Q / 456,456 T).

Builds a patched copy of the public source with call counters in the field
kernels, tagging every call with the enclosing top-level `mark()` stage.
Nothing here is a candidate: the patched build is a cost census only.

Usage:
  .venv/bin/python experiments/dqi/20261112_decoder_family/stage_mulcensus.py OUTDIR

Outputs OUTDIR/v21_stage_mulcensus.json and prints the table.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[2] / 'artifacts' / '20261112_decoder_family'
SRC = HERE.parents[2] / 'artifacts' / '20261112_mulrank' / 'source_copy'
TMP = Path(os.environ.get('DECFAM_TMP', '/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/decfam'))

TRACK = '''\
# stage tracker injected by 20261112_decoder_family/stage_mulcensus.py
import json
STAGES = ("mask_projection","initial","extract","synthesis","convert","scan",
          "unconvert","unsynthesis","unextract","uninitial","restore_masks")
_stack = []
_COUNTS = {}


def _cur():
    for s in reversed(_stack):
        if s in STAGES:
            return s
    return "outside"


def bump(what):
    k = (_cur(), what)
    _COUNTS[k] = _COUNTS.get(k, 0) + 1


class Wrap:
    def __init__(self, cm, name):
        self.cm, self.name = cm, name

    def __enter__(self):
        _stack.append(self.name)
        return self.cm.__enter__()

    def __exit__(self, *a):
        try:
            return self.cm.__exit__(*a)
        finally:
            _stack.pop()


def wrap(cm, name):
    return Wrap(cm, name)


def dump(path):
    with open(path, "w") as f:
        json.dump({f"{k[0]}/{k[1]}": v for k, v in sorted(_COUNTS.items())}, f, indent=1)
'''

COUNTERS = '''

# --- stage counters appended by 20261112_decoder_family/stage_mulcensus.py ---
import stagetrack as _st
_orig_mul_xor = mul_xor
def mul_xor(b,x,y,z):
    _st.bump(f"mul_xor_{len(x)}"); return _orig_mul_xor(b,x,y,z)
_orig_mul_xor0 = mul_xor0
def mul_xor0(b,x,y,z):
    _st.bump(f"mul_xor0_{len(x)}"); return _orig_mul_xor0(b,x,y,z)
'''

BUILD_PATCH = '''
import stagetrack as _st
_orig_mark = km.CircuitBuilder.mark
def _mark(self, name):
    return _st.wrap(_orig_mark(self, name), name)
km.CircuitBuilder.mark = _mark
'''


def main(outdir):
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    build = TMP / 'src'
    if build.exists():
        shutil.rmtree(build)
    shutil.copytree(SRC, build)
    (build / 'stagetrack.py').write_text(TRACK)
    f = build / 'playbook/kit/decoder/exp/arithmetic/field.py'
    s = f.read_text()
    assert s.count('import circ as km') == 1
    f.write_text(s + COUNTERS)
    g = build / 'playbook/kit/decoder/exp/mul99/kernels.py'
    s = g.read_text()
    old = 'def multiplier(b,x,y,z,terms):'
    assert s.count(old) == 1
    g.write_text(s.replace(old, 'def multiplier(b,x,y,z,terms):\n    _st.bump("mul99")\n', 1).replace(
        'from field import *', 'from field import *\nimport stagetrack as _st', 1))
    h = build / 'playbook/kit/decoder/exp/noscratch/kernels.py'
    s = h.read_text()
    old = 'def tensor_xor_noscratch(b,x,y,z,terms):'
    assert s.count(old) == 1
    h.write_text(s.replace(old, 'def tensor_xor_noscratch(b,x,y,z,terms):\n    _st.bump(f"noscratch_{len(x)}")\n', 1)
                 .replace('from field import *', 'from field import *\nimport stagetrack as _st', 1))
    buildpy = build / 'build.py'
    s = buildpy.read_text()
    s = s.replace('import kickmix as km', 'import kickmix as km\n' + BUILD_PATCH, 1)
    s = s.replace('print(json.dumps(record), flush=True)',
                  "print(json.dumps(record), flush=True)\n"
                  "import stagetrack as _st, os as _os\n"
                  "_st.dump(_os.environ.get('STAGECOUNT', '/tmp/stagecount.json'))", 1)
    buildpy.write_text(s)
    env = dict(os.environ, STAGECOUNT=str(outdir / 'v21_stage_mulcensus.json'),
               PYTHONPATH=str(build))
    target = TMP / 'v21_count.kmb'
    target.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(buildpy), str(target)], cwd=str(build), env=env,
                       text=True, capture_output=True)
    print(r.stdout[-2000:])
    if r.returncode:
        print(r.stderr[-4000:])
        raise SystemExit(r.returncode)
    data = json.loads((outdir / 'v21_stage_mulcensus.json').read_text())
    stages = ["extract", "synthesis", "convert", "scan", "unconvert", "unsynthesis", "unextract"]
    print(f"{'stage':13s} " + " ".join(f"{k:>11s}" for k in
          ("mul42", "mul105", "mul99", "noscr12", "noscr6", "mul3/6")))
    tot = {k: 0 for k in ("mul42", "mul105", "mul99", "noscr12", "noscr6", "mul36")}
    for st in stages:
        row = dict(mul42=data.get(f'{st}/mul_xor0_12', 0) + data.get(f'{st}/mul_xor_12', 0),
                   mul105=data.get(f'{st}/mul_xor0_24', 0) + data.get(f'{st}/mul_xor_24', 0),
                   mul99=data.get(f'{st}/mul99', 0),
                   noscr12=data.get(f'{st}/noscratch_12', 0),
                   noscr6=data.get(f'{st}/noscratch_6', 0),
                   mul36=data.get(f'{st}/noscratch_3', 0) + data.get(f'{st}/mul_xor_3', 0)
                   + data.get(f'{st}/mul_xor_6', 0))
        for k in tot:
            tot[k] += row[k]
        print(f"{st:13s} " + " ".join(f"{row[k]:11d}" for k in
              ("mul42", "mul105", "mul99", "noscr12", "noscr6", "mul36")))
    print(f"{'TOTAL':13s} " + " ".join(f"{tot[k]:11d}" for k in
          ("mul42", "mul105", "mul99", "noscr12", "noscr6", "mul36")))
    print("raw:", json.dumps(data))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else str(ART))
