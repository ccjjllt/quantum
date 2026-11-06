"""Rebuild the recovered 893Q decoder while counting high-level builder primitives.

No circuit is written; wrappers around CCX/CCZ/CSWAP and the builder's
arithmetic helpers report call counts and Toffoli contributions.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

WORK = Path(__file__).resolve().parents[3] / 'artifacts/20261106_phase_recovery/old_build'
SOURCE = WORK / 'blocks/dqi/pro-q18-900/source'
HELPERS = WORK / 'portable_builder'
sys.path.insert(0, str(HELPERS))

import kickmix as km
sys.modules['circ'] = km

calls = Counter()
ttot = Counter()
qtot = Counter()
current = []
depth = 0


def _wrap_low(name, key):
    orig = getattr(km.CircuitBuilder, name)

    def wrapper(self, *a, **k):
        ttot['<all>'] += 1
        if depth == 0:
            ttot[key] += 1
        return orig(self, *a, **k)
    setattr(km.CircuitBuilder, name, wrapper)


for name, key in [('ccx', 'CCX'), ('ccz', 'CCZ'), ('cswap', 'CSWAP')]:
    _wrap_low(name, key)

WRAPPED = ['init_gf2_mul', 'ixor_gf2_mul', 'init_gf2_inverse', 'init_gf2_div',
           'init_gf2_div_with_scaffold', 'init_gf2_inverse_with_scaffold',
           'del_gf2_mul', 'del_gf2_inverse', 'del_gf2_div',
           'del_gf2_div_with_scaffold', 'del_gf2_inverse_with_scaffold',
           'init_and', 'del_and', 'init_lookup', 'del_lookup',
           'multi_controlled_x', 'iadd', 'isub', 'ixor']


def _wrap_high(name):
    orig = getattr(km.CircuitBuilder, name, None)
    if orig is None:
        return

    def wrapper(self, *a, **k):
        global depth
        before_all = ttot['<all>']
        before_q = self.num_allocated_qubits
        depth += 1
        try:
            return orig(self, *a, **k)
        finally:
            depth -= 1
            calls[name] += 1
            ttot[name] += ttot['<all>'] - before_all
            qtot[name] = max(qtot[name], self.num_allocated_qubits - before_q)
    setattr(km.CircuitBuilder, name, wrapper)


for name in WRAPPED:
    _wrap_high(name)


def main():
    spec = importlib.util.spec_from_file_location('decoder', SOURCE / 'decode_best.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    sys.path.insert(0, str(HELPERS))
    from transform import install
    manager, transformation = install(module.decode, SOURCE)
    builder = km.CircuitBuilder()
    syndromes = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    calls.clear(); ttot.clear(); qtot.clear()
    module.decode(builder, syndromes, masks)
    circuit = builder.finish_circuit()
    out = {
        'Q': circuit.num_qubits,
        'T_static': circuit.operation_statistics().num_toffoli_like,
        'ops': len(circuit),
        'calls': dict(calls),
        'T_including_callees': dict(ttot),
        'max_Q_delta': dict(qtot),
    }
    target = Path(__file__).resolve().parents[3] / 'artifacts/20261106_phase_recovery/primitive_census.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
