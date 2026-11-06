"""Measured official-builder counts for the direct phase-tap kernels.

Every number is built with `km.CircuitBuilder` and read from
`OperationStatistics`.  Paid gates are CCX/CCZ/CSWAP.  Nothing here is a
candidate circuit and nothing is phase-verified.

Kernels:
  * coefficient QROM (init_lookup + del_lookup) for 32/128 entries at several
    output widths, including the 114-bit three-register width of variant A;
  * 22-bit leading-one detector;
  * 22-bit barrel shift by a 5-bit amount (x << (21-e));
  * in-place 38-bit 4-stage barrel shifter (coefficient alignment by s);
  * one phase tap: init_and + z_pow + del_and (the per-tap paid cost).
"""
import json
import platform
import random
from fractions import Fraction
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_phase_tap/kernels'


def measure(build, maxq=20000):
    b = km.CircuitBuilder()
    b.set_max_qubits(maxq)
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    d = dict(st)
    return dict(paid=int(st.num_toffoli_like),
                ccx=d.get('CCX', 0), ccz=d.get('CCZ', 0), cswap=d.get('CSWAP', 0),
                cx=d.get('CX', 0), num_instructions=int(st.num_instructions),
                qubits=c.num_qubits,
                t_like=int(st.num_t_like),
                rotations=int(st.num_z_pow(min_clifford_hierarchy_level=4)))


def qrom(n_entries, out_bits, rng_seed=0):
    rng = random.Random(20261107 + n_entries * 131 + out_bits + rng_seed)
    table = [rng.getrandbits(out_bits) for _ in range(n_entries)]

    def build(b):
        addr = b.create_quantum_register((n_entries - 1).bit_length(), name='addr')
        tgt = b.create_quantum_register(out_bits, name='tgt')
        b.init_lookup(table=table, address=addr, target=tgt)
        b.del_lookup(table=table, address=addr, target=tgt)

    r = measure(build)
    r.update(entries=n_entries, output_bits=out_bits)
    return r


def qrom_split_address(n_entries, out_bits):
    """QROM whose address is 6 low mantissa bits + 1 group qubit (non-contiguous)."""
    rng = random.Random(20261107 + n_entries * 131 + out_bits)
    table = [rng.getrandbits(out_bits) for _ in range(n_entries)]

    def build(b):
        reg = b.create_quantum_register(22, name='x')
        grp = b.create_quantum_register(1, name='g')
        tgt = b.create_quantum_register(out_bits, name='tgt')
        addr = km.array([reg[15 + i] for i in range(6)] + [grp[0]])
        b.init_lookup(table=table, address=addr, target=tgt)
        b.del_lookup(table=table, address=addr, target=tgt)

    r = measure(build)
    r.update(entries=n_entries, output_bits=out_bits, address='6 mantissa bits + group')
    return r


def leading_one_detector(nbits=22):
    def build(b):
        x = b.create_quantum_register(nbits, name='x')
        t = b.create_quantum_register(nbits + 1, name='t')
        e = b.create_quantum_register((nbits - 1).bit_length(), name='e')
        for i in reversed(range(nbits)):
            b.cx(t[i + 1], t[i])
            b.cx(x[i], t[i])
            b.ccx(t[i + 1], x[i], t[i])
        for j in range((nbits - 1).bit_length()):
            for i in range(nbits):
                if (i >> j) & 1:
                    b.cx(t[i], e[j])
                    b.cx(t[i + 1], e[j])

    return measure(build)


def barrel_shift(nbits, stages):
    def build(b):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(stages, name='amt')
        for s in range(stages):
            step = 1 << s
            for i in range(nbits - step):
                b.cswap(amt[s], reg[i], reg[i + step])

    r = measure(build)
    r.update(bits=nbits, stages=stages,
             analytic=sum(nbits - (1 << s) for s in range(stages)))
    return r


def one_tap(angle=Fraction(1, 2 ** 20)):
    """init_and(c, m, anc); z_pow(anc, angle); del_and(c, m, anc)."""
    def build(b):
        c = b.create_quantum_register(1, name='c')[0]
        m = b.create_quantum_register(1, name='m')[0]
        anc = b.create_quantum_register(1, name='anc')[0]
        b.init_and(c, m, anc)
        b.z_pow(anc, angle)
        b.del_and(c, m, anc)

    return measure(build)


def tap_chain(n_taps, angle=Fraction(1, 2 ** 20)):
    """n_taps sequential phase taps sharing one control qubit and one monomial."""
    def build(b):
        c = b.create_quantum_register(1, name='c')[0]
        m = b.create_quantum_register(1, name='m')[0]
        anc = b.create_quantum_register(1, name='anc')[0]
        for _ in range(n_taps):
            b.init_and(c, m, anc)
            b.z_pow(anc, angle)
            b.del_and(c, m, anc)

    return measure(build)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = dict(scope='Measured km.CircuitBuilder counts for direct phase-tap kernels; '
                     'no candidate circuit, no phase validation',
               python=platform.python_version(), kickmix=km.__file__,
               qrom=[], lod=None, shifts=[], taps=[])
    for entries, bits in ((32, 85), (128, 38), (128, 64), (128, 114), (32, 114)):
        r = qrom(entries, bits)
        doc['qrom'].append(r)
        print('qrom', r, flush=True)
    r = qrom_split_address(128, 114)
    doc['qrom'].append(r)
    print('qrom_split', r, flush=True)
    doc['lod'] = leading_one_detector(22)
    print('lod', doc['lod'], flush=True)
    for nbits, stages in ((22, 5), (38, 4), (114, 4)):
        r = barrel_shift(nbits, stages)
        doc['shifts'].append(r)
        print('shift', r, flush=True)
    r = one_tap()
    doc['taps'].append(r)
    print('tap', r, flush=True)
    r = tap_chain(100)
    doc['taps'].append(r)
    print('tap_chain_100', r, flush=True)
    (OUT / 'kernels.json').write_text(json.dumps(doc, indent=2) + '\n')


if __name__ == '__main__':
    main()
