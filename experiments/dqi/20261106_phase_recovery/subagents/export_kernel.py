"""Export exact kernel function: inputs, outputs, affine and quadratic ANF.

Usage:
    python export_kernel.py <kernel.kmx> <out.json>
"""
import json
import sys
from pathlib import Path

from kernel_anf import parse, propagate, split_quadratic


def main():
    src, dst = sys.argv[1], sys.argv[2]
    info = propagate(parse(src))
    inputs, outs = split_quadratic(info)
    data = {
        'source': src,
        'wires': info['wires'],
        'gate_counts': info['counts'],
        'inputs': inputs,
        'outputs': {str(w): {
            'const': d['const'],
            'linear': sorted(d['linear']),
            'quadratic': sorted([list(p) for p in d['quadratic']]),
        } for w, d in sorted(outs.items())},
    }
    Path(dst).write_text(json.dumps(data, indent=1) + '\n')
    print(f'wrote {dst}: {len(inputs)} inputs, {len(outs)} outputs')


if __name__ == '__main__':
    main()
