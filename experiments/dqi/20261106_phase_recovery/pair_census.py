"""Count compute/uncompute CCX pairs that measurement-based uncompute could replace.

A candidate is a CCX writing t immediately after another CCX with the same
control pair wrote t, with t known |0> before the first CCX.  The second CCX
can then be replaced by `HMR t; CZ(a,b) if measured`, which costs no Toffoli.
This is a purely syntactic census; semantic validity is checked separately.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
KMX = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/dqi_phase/syed_v9.kmx')


def main():
    t0 = time.monotonic()
    last = {}          # target -> (ctrl1, ctrl2, op_index)
    zero = defaultdict(lambda: False)  # unknown until proven zero; strings are qubit ids
    stage = '<outside>'
    stack = []
    pairs = []
    total_ccx = 0
    with open(KMX, 'rb') as f:
        for i, line in enumerate(f):
            if line.startswith(b'INFO_TAG '):
                tag = line.strip().split(b'"', 2)[1].decode()
                if tag.startswith('@enter:'):
                    stack.append(tag[7:])
                    if len(stack) == 1:
                        stage = tag[7:]
                elif tag.startswith('@exit:'):
                    if stack:
                        stack.pop()
                    if not stack:
                        stage = '<outside>'
                continue
            op = line.split(b' ', 1)[0]
            if op == b'CCX':
                parts = line.split()
                a, b, t = parts[1].decode(), parts[2].decode(), parts[3].decode()
                total_ccx += 1
                prev = last.pop(t, None)
                if (zero[t] and prev is not None and prev[0] == a and prev[1] == b):
                    pairs.append({'op': i, 'stage': stage, 'a': a, 'b': b, 't': t,
                                  'first_op': prev[2], 'span': i - prev[2]})
                zero[t] = False
                last[t] = (a, b, i)
            elif op == b'CSWAP':
                parts = line.split()
                for w in (parts[1], parts[2]):
                    w = w.decode()
                    zero[w] = False
                    last.pop(w, None)
            elif op in (b'CX', b'X', b'R', b'HMR', b'SWAP'):
                parts = line.split()
                if op == b'SWAP':
                    ws = [parts[1].decode(), parts[2].decode()]
                elif op == b'CX':
                    ws = [parts[2].decode()]
                else:
                    ws = [parts[1].decode()]
                for w in ws:
                    zero[w] = (op in (b'R', b'HMR'))
                    last.pop(w, None)
    counts = Counter(p['stage'] for p in pairs)
    spans = sorted(p['span'] for p in pairs)
    out = {
        'total_ccx': total_ccx,
        'candidate_pairs': len(pairs),
        'candidate_pairs_by_stage': dict(counts),
        'span_median': spans[len(spans)//2] if spans else None,
        'span_max': spans[-1] if spans else None,
        'first_20': pairs[:20],
        'elapsed_seconds': round(time.monotonic()-t0, 1),
    }
    target = ROOT/'artifacts/20261106_phase_recovery/ccx_pairs.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != 'first_20'}, indent=1))


if __name__ == '__main__':
    main()
