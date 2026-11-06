"""Check whether the first exact 99-CCX compute/uncompute pair is MBU-able.

Tracks known-zero state and last CCX writer over the full stream, then reports
the states of the targets inside the first 99-CCX segment at line 57,512,697.
"""
from collections import defaultdict
import json
from pathlib import Path

KMX = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/dqi_phase/syed_v9.kmx')
START = 57512697
END = 57519075


def main():
    zero = defaultdict(bool)
    for q in range(840, 892):
        zero[f'q{q}'] = True
    last = {}
    rows = []
    with open(KMX, 'rb') as f:
        for i, line in enumerate(f):
            if i > END:
                break
            op = line.split(b' ', 1)[0]
            if op == b'CCX':
                parts = line.split()
                a, b, t = parts[1].decode(), parts[2].decode(), parts[3].decode()
                if START <= i < END:
                    rows.append({'line': i, 'a': a, 'b': b, 't': t,
                                 'zero_t': zero[t], 'last': last.get(t)})
                zero[t] = False
                last[t] = (a, b, i)
            elif op in (b'CX', b'X', b'R', b'HMR', b'SWAP', b'CSWAP'):
                parts = line.split()
                if op in (b'SWAP', b'CSWAP'):
                    ws = [parts[1].decode(), parts[2].decode()]
                elif op == b'CX':
                    ws = [parts[2].decode()]
                else:
                    ws = [parts[1].decode()]
                for w in ws:
                    zero[w] = op in (b'R', b'HMR')
                    last.pop(w, None)
    out = {
        'segment': [START, END],
        'ccx': len(rows),
        'zero_at_first_write': sum(1 for r in rows if r['zero_t']),
        'same_control_previous': sum(1 for r in rows if r['zero_t'] and r['last'] and {r['last'][0], r['last'][1]} == {r['a'], r['b']}),
        'first_5': rows[:5],
        'targets': sorted({r['t'] for r in rows}),
    }
    target = Path(__file__).resolve().parents[3] / 'artifacts/20261106_phase_recovery/dup99_check.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
