"""Assemble a package = shipped marculera build with chosen loaders replaced by
locally emitted .kmx.  Static counts only.
"""
import json, shutil, sys, argparse
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def count(p):
    c = km.Circuit.from_file(str(p))
    return int(c.operation_statistics().num_toffoli_like), int(c.num_qubits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replace', default='', help='comma list of loader indices taken from build_new')
    ap.add_argument('--out', type=Path, default=HERE / 'pkg_new' / 'dfthcsos')
    a = ap.parse_args()
    ks = [int(x) for x in a.replace.split(',') if x.strip()]
    a.out.mkdir(parents=True, exist_ok=True)
    for old in a.out.glob('*'):
        old.unlink()
    shutil.copy(BUILD / 'submission.npz', a.out / 'submission.npz')
    rows, total = [], 0
    for k in range(15):
        if k in ks:
            src = HERE / 'build_new' / f'angle_k_{k}.kmx'
            dst = a.out / f'angle_k_{k}.kmb'
            km.Circuit.from_file(str(src)).to_file(str(dst), format='kmb')
            tag = 'new'
        else:
            dst = a.out / f'angle_k_{k}.kmb'
            shutil.copy(BUILD / f'angle_k_{k}.kmb', dst)
            tag = 'shipped'
        t, q = count(dst)
        rows.append({'k': k, 'src': tag, 'toffoli': t, 'qubits': q, 'shipped': SHIPPED[k],
                     'delta': t - SHIPPED[k]})
        total += t
        print(json.dumps(rows[-1]), flush=True)
    print('TOTAL', total, 'shipped', sum(SHIPPED), 'delta', total - sum(SHIPPED), flush=True)
    (a.out.parent / 'pkg_new.json').write_text(json.dumps({'rows': rows, 'total': total}, indent=1))


if __name__ == '__main__':
    main()
