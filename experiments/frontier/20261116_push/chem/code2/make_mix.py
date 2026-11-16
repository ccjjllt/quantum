"""Assemble a package: pick, per loader, the circuit with the fewest Toffoli.

Sources
  BUILD  marculera/dfthc-c44-build (official verified 4,025 package)
  MINE   .kmx emitted locally from the shipped syed_v12 plans (calib_emit.py)

Static counts only (kickmix parses the circuit and counts gates; nothing is
simulated).
"""
import json
import shutil
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
MINE = HERE / 'build'
OUT = HERE / 'pkg_mix'


def stat(path):
    c = km.Circuit.from_file(str(path))
    return {'toffoli': int(c.operation_statistics().num_toffoli_like), 'qubits': int(c.num_qubits),
            'regs': sorted(c.register_data)}


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob('*'):
        old.unlink()
    shutil.copy(BUILD / 'submission.npz', OUT / 'submission.npz')
    rows = []
    for k in range(15):
        mine = MINE / f'angle_k_{k}.kmx'
        theirs = BUILD / f'angle_k_{k}.kmb'
        a, b = stat(mine), stat(theirs)
        pick = 'mine' if a['toffoli'] < b['toffoli'] else 'shipped'
        src = mine if pick == 'mine' else theirs
        dst = OUT / f'angle_k_{k}.kmb'
        if src.suffix == '.kmx':
            km.Circuit.from_file(str(src)).to_file(str(dst), format='kmb')
        else:
            shutil.copy(src, dst)
        got = stat(dst)
        rows.append({'k': k, 'mine': a['toffoli'], 'shipped': b['toffoli'], 'pick': pick,
                     'packed': got['toffoli'], 'qubits': got['qubits']})
        print(json.dumps(rows[-1]), flush=True)
    total = sum(r['packed'] for r in rows)
    print('TOTAL', total, 'shipped', sum(r['shipped'] for r in rows))
    fam = [km.Circuit.from_file(str(OUT / f'angle_k_{k}.kmb')) for k in range(15)]
    regs = [sorted(c.register_data) for c in fam]
    same = all(r == regs[0] for r in regs)
    print('register sets identical:', same, regs[0])
    print('qubit ids of registers identical:',
          all(all(fam[i].register_data[n] == fam[0].register_data[n] for n in regs[0]) for i in range(15)))
    (HERE / 'pkg_mix.json').write_text(json.dumps({'rows': rows, 'total': total}, indent=1))


if __name__ == '__main__':
    main()
