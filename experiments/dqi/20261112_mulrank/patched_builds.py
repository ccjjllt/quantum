"""Cost-model builds: measure the exact marginal static T of one multiplication rank term.

Four derived source copies are produced from source_copy/ by a clearly labelled patch:

  c36     GF(2^12) tensor truncated 42 -> 36 terms   (T(36,99))
  c90     GF(2^24) tensor truncated 99 -> 90 terms   (T(42,90))
  c3690   both                                       (T(36,90))
  count   no truncation, call counters in the multiplier kernels

The truncated circuits are MATHEMATICALLY WRONG on purpose; they exist only to
measure dT/dterm of the real build.  Q is unaffected, so the .kmb files are not
candidates and are never verified.

Usage: .venv/bin/python artifacts/20261112_mulrank/patched_builds.py [c36|c90|c3690|count|all]
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[2] / 'artifacts' / '20261112_mulrank'
SRC = ART / 'source_copy'
TMP = Path(os.environ.get('MULRANK_TMP',
                          '/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/mulrank'))

COUNTERS = '''
import atexit as _ae, os as _os
_C = {}
def _bump(k):
    _C[k] = _C.get(k, 0) + 1
def _dump():
    with open(_os.environ.get('MULCOUNT', '/tmp/mulcount.txt'), 'w') as f:
        for k in sorted(_C):
            f.write(f'{k} {_C[k]}\\n')
_ae.register(_dump)
'''

T12_OLD = "    assert all(out)\n    return tuple(zip(masks,out))"
T24_OLD = "    out=extension_tensor(24,4,6,tensor4());assert len(out)==99\n    return out"


def make(tag, r12=None, r24=None, counters=False):
    dst = ART / f'src_{tag}'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst)
    if r12:
        f = dst / 'playbook/kit/decoder/exp/arithmetic/field.py'
        s = f.read_text()
        new = (f"    assert all(out)\n    if n==12: return tuple(zip(masks,out))[:{r12}]"
               "   # COST-MODEL PATCH\n    return tuple(zip(masks,out))")
        assert s.count(T12_OLD) == 1
        f.write_text(s.replace(T12_OLD, new))
    if r24:
        g = dst / 'playbook/kit/decoder/exp/mul99/kernels.py'
        s = g.read_text()
        new = T24_OLD.replace('return out', f'return out[:{r24}]   # COST-MODEL PATCH')
        assert s.count(T24_OLD) == 1
        g.write_text(s.replace(T24_OLD, new))
    if counters:
        f = dst / 'playbook/kit/decoder/exp/arithmetic/field.py'
        s = f.read_text().replace('import circ as km', 'import circ as km\n' + COUNTERS, 1)
        s = s.replace('def mul_xor(b,x,y,z):',
                      'def mul_xor(b,x,y,z):\n    _bump(f\'mul_xor_{len(x)}\')', 1)
        s = s.replace('def mul_xor0(b,x,y,z):',
                      'def mul_xor0(b,x,y,z):\n    _bump(f\'mul_xor0_{len(x)}\')', 1)
        f.write_text(s)
        g = dst / 'playbook/kit/decoder/exp/noscratch/kernels.py'
        s = g.read_text().replace('from field import *', 'from field import *\nfrom field import _bump', 1)
        s = s.replace('def tensor_xor_noscratch(b,x,y,z,terms):',
                      'def tensor_xor_noscratch(b,x,y,z,terms):\n    _bump(f\'noscratch_{len(x)}\')', 1)
        g.write_text(s)
        h = dst / 'playbook/kit/decoder/exp/mul99/kernels.py'
        s = h.read_text().replace('from field import *', 'from field import *\nfrom field import _bump', 1)
        s = s.replace('def multiplier(b,x,y,z,terms):',
                      'def multiplier(b,x,y,z,terms):\n    _bump(\'mul99_multiplier\')', 1)
        h.write_text(s)
    return dst


def build(tag, **kw):
    dst = make(tag, **kw)
    out = TMP / f'{tag}.kmb'
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MULCOUNT=str(TMP / 'mulcount.txt'))
    subprocess.run([sys.executable, str(dst / 'build.py'), str(out)], check=True, env=env)
    rec = json.loads(Path(out).with_suffix('.build.json').read_text())
    print(tag, json.dumps(rec), flush=True)
    return rec


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    plan = {
        'c36': dict(r12=36),
        'c90': dict(r24=90),
        'c3690': dict(r12=36, r24=90),
        'count': dict(counters=True),
    }
    todo = plan if which == 'all' else {which: plan[which]}
    for tag, kw in todo.items():
        build(tag, **kw)
