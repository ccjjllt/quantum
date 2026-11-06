"""Report first write / first use of selected wires in a full KMB circuit.

Streams kmb -> kmx text and records, for each wire of interest, the first gate
that mentions it and the first gate that targets it (X, CX/CCX target, SWAP).
A wire with no earlier target is still |0> at that point (assuming standard
|0..0> initialization).  Read-only.

Usage:
    python wire_first_touch.py <kmb> <wire> [wire ...]
"""
import io
import sys

import kickmix as km


class Sink:
    def write(self, value):
        self.data = value.encode() if isinstance(value, str) else value

    def flush(self):
        pass


def main():
    kmb = sys.argv[1]
    wires = {int(x) for x in sys.argv[2:]}
    c = km.Circuit.from_file(kmb, format='kmb')
    sink = Sink()
    c.to_file(sink, format='kmx')
    first = {}
    first_target = {}
    idx = 0
    for raw in io.BytesIO(sink.data):
        line = raw.decode().rstrip()
        if not line or line.startswith('INFO_TAG'):
            continue
        parts = line.split()
        op = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        idx += 1
        for q in qs:
            if q in wires and q not in first:
                first[q] = (idx, line)
        targets = []
        if op in ('X', 'R', 'HMR'):
            targets = qs[:1]
        elif op in ('CX', 'CCX', 'CZ', 'CCZ'):
            targets = qs[1:2] if op in ('CX', 'CZ') else qs[2:3]
        elif op == 'SWAP':
            targets = qs
        for q in targets:
            if q in wires and q not in first_target:
                first_target[q] = (idx, line)
    for q in sorted(wires):
        print(f'q{q}: first={first.get(q)} first_target={first_target.get(q)}')


if __name__ == '__main__':
    main()
