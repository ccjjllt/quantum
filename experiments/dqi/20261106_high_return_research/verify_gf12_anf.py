"""Manual symbolic evidence for the pinned PolyTOF GF(2^12) MAC.

Interprets only CNOT/Toffoli text gates, never executes upstream Python.
ANF monomials are bitmasks; multiplication unions masks modulo x_i^2=x_i.
"""
from pathlib import Path
from collections import Counter
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'artifacts/20261106_high_return_research/literature'
POLY = (1 << 12) | (1 << 3) | 1

def mul(a, b):
    out = set()
    for x in a:
        for y in b:
            m = x | y
            if m in out:
                out.remove(m)
            else:
                out.add(m)
    return out

def field_monomial_power(k):
    n = 1 << k
    while n.bit_length() > 12:
        n ^= POLY << (n.bit_length() - 13)
    return n

def main():
    wires = [{1 << i} for i in range(36)]
    counts = Counter()
    for line in (HERE / 'gf2p012.qc').read_text().splitlines():
        if line.startswith(('#', '.')) or line in ('BEGIN', 'END', ''):
            continue
        op, *qs = line.split()
        ids = [int(q[1:]) for q in qs]
        assert len(set(ids)) == len(ids)
        counts[op] += 1
        if op == 'cnot':
            a, b = ids
            wires[b] ^= wires[a]
        elif op == 'tof':
            a, b, c = ids
            wires[c] ^= mul(wires[a], wires[b])
        else:
            raise ValueError(op)
    expected = [{1 << i} for i in range(36)]
    for a in range(12):
        for b in range(12):
            bits = field_monomial_power(a + b)
            for c in range(12):
                if (bits >> c) & 1:
                    expected[24 + c].add((1 << a) | (1 << (12 + b)))
    mismatch = [i for i in range(36) if wires[i] != expected[i]]
    result = {
        'scope': 'exact Boolean ANF equality of all 36 output wires for all 2^36 basis inputs; no phase gates, no measurements; not official DQI verification',
        'source': 'ZIB-IOL/polytof',
        'commit': '0dcac107d15adc34dc646242d222f21ae7d32699',
        'path': 'data/paper/circuits/gf2p012.qc',
        'polynomial': 't^12+t^3+1',
        'qubits': 36,
        'ancillas': 0,
        'gates': dict(counts),
        'mismatched_output_wires': mismatch,
        'exact_anf_match': not mismatch,
        'max_anf_degree': max(m.bit_count() for p in wires for m in p),
    }
    assert not mismatch
    (HERE / 'gf12_anf_evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
