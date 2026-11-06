"""Exact paid-gate counts for the building blocks of a piecewise phase circuit.

Every number here is measured by building the kernel with the official
`km.CircuitBuilder` and reading `OperationStatistics`.  Nothing is verified
against the reference phases; this only sizes the reversible kernels.

Paid gates are CCX, CCZ and CSWAP (the official cost model's Toffoli-like set).
X, CX, SWAP, HMR, R, Z, CZ, NEG and all BIT_* instructions are free.
"""
import json
import platform
import random
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261106_piecewise_cost/kernels'


def measure(build, maxq=8000):
    b = km.CircuitBuilder()
    b.set_max_qubits(maxq)
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    d = dict(st)
    return dict(
        paid=int(st.num_toffoli_like),
        ccx=d.get('CCX', 0), ccz=d.get('CCZ', 0), cswap=d.get('CSWAP', 0),
        cx=d.get('CX', 0), ops=int(st.num_instructions), qubits=c.num_qubits,
    )


def qrom(n_entries, out_bits):
    rng = random.Random(20261106 + n_entries * 131 + out_bits)
    table = [rng.getrandbits(out_bits) for _ in range(n_entries)]
    def build(b):
        addr = b.create_quantum_register((n_entries - 1).bit_length(), name='addr')
        tgt = b.create_quantum_register(out_bits, name='tgt')
        b.init_lookup(table=table, address=addr, target=tgt)
        b.del_lookup(table=table, address=addr, target=tgt)
    return measure(build)


def multiplier(w_acc, w_u):
    """acc = (acc * u) truncated to w_acc bits, out of place into a fresh register."""
    def build(b):
        acc = b.create_quantum_register(w_acc, name='acc')
        u = b.create_quantum_register(w_u, name='u')
        tmp = b.create_quantum_register(w_acc, name='tmp')
        for k in range(w_u):
            width = w_acc - k
            if width <= 0:
                break
            b.iadd(acc[:width], target=tmp[k:], control=u[k])
    return measure(build)


def multiplier_inverse(w_acc, w_u):
    def build(b):
        acc = b.create_quantum_register(w_acc, name='acc')
        u = b.create_quantum_register(w_u, name='u')
        tmp = b.create_quantum_register(w_acc, name='tmp')
        for k in reversed(range(w_u)):
            width = w_acc - k
            if width <= 0:
                continue
            b.isub(acc[:width], target=tmp[k:], control=u[k])
    return measure(build)


def adder(w, offset_w, quantum_offset=True, controlled=False):
    def build(b):
        t = b.create_quantum_register(w, name='t')
        ctl = b.create_quantum_register(1, name='ctl')
        c = ctl[0] if controlled else True
        if quantum_offset:
            o = b.create_quantum_register(offset_w, name='o')
            b.iadd(o, target=t, control=c)
        else:
            b.iadd((1 << (offset_w - 1)) | 12345, target=t, control=c, btol=float('inf'))
    return measure(build)


def leading_one_detector(nbits):
    """One-hot leading-bit flags L[i] and the binary exponent e (free parities)."""
    def build(b):
        x = b.create_quantum_register(nbits, name='x')
        t = b.create_quantum_register(nbits + 1, name='t')
        e = b.create_quantum_register((nbits - 1).bit_length(), name='e')
        # suffix OR: t[i] = OR_{j>=i} x[j], with t[nbits] = 0
        for i in reversed(range(nbits)):
            b.cx(t[i + 1], t[i])
            b.cx(x[i], t[i])
            b.ccx(t[i + 1], x[i], t[i])
        # L[i] = t[i] xor t[i+1]; e's bits are XORs of L, all CX.
        for j in range((nbits - 1).bit_length()):
            for i in range(nbits):
                if (i >> j) & 1:
                    b.cx(t[i], e[j])
                    b.cx(t[i + 1], e[j])
    return measure(build)


def barrel_shift(nbits, amount_bits=None):
    """Right-shift an nbits register by a quantum amount (log-depth CSWAP cascade)."""
    stages = amount_bits if amount_bits is not None else (nbits - 1).bit_length()
    def build(b):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(stages, name='amt')
        for s in range(stages):
            step = 1 << s
            for i in range(nbits - step):
                b.cswap(amt[s], reg[i], reg[i + step])
    return measure(build)


def horner(degree, w_acc, w_u):
    """p = ((c_d*u + c_{d-1})*u + ...) + c_0, truncated to w_acc bits."""
    def build(b):
        u = b.create_quantum_register(w_u, name='u')
        coeffs = [b.create_quantum_register(w_acc, name=f'c{j}') for j in range(degree + 1)]
        acc = b.create_quantum_register(w_acc, name='acc0')
        b.cx(coeffs[degree], acc)
        for j in reversed(range(degree)):
            tmp = b.create_quantum_register(w_acc, name=f'acc{degree - j}')
            for k in range(w_u):
                width = w_acc - k
                if width <= 0:
                    break
                b.iadd(acc[:width], target=tmp[k:], control=u[k])
            b.iadd(coeffs[j], target=tmp)
            acc = tmp
    return measure(build)


def horner_scaled(widths, u_bits):
    """Horner with per-term widths: widths[0] is the constant term (widest)."""
    degree = len(widths) - 1
    def build(b):
        u = b.create_quantum_register(u_bits, name='u')
        coeffs = [b.create_quantum_register(widths[j], name=f'c{j}') for j in range(degree + 1)]
        acc = b.create_quantum_register(widths[degree], name='acc0')
        b.cx(coeffs[degree], acc)
        for j in reversed(range(degree)):
            tmp = b.create_quantum_register(widths[j], name=f'acc{degree - j}')
            for k in range(u_bits):
                width = widths[j] - k
                if width <= 0:
                    break
                b.iadd(acc[:width], target=tmp[k:], control=u[k])
            b.iadd(coeffs[j], target=tmp)
            acc = tmp
    return measure(build)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = dict(scope='Measured paid-gate counts of official CircuitBuilder kernels (CCX+CCZ+CSWAP); no phase validation, no candidate circuit',
               python=platform.python_version(), kickmix=km.__file__,
               qrom=[], multipliers=[], multipliers_inverse=[], adders=[],
               leading_one_detector={}, barrel_shift={}, horner={}, horner_scaled={})
    for n in (16, 32, 64, 128, 256, 512, 1024):
        for bits in (28, 40):
            r = qrom(n, bits)
            r.update(entries=n, output_bits=bits)
            doc['qrom'].append(r)
            print('qrom', r, flush=True)
    for w_acc, w_u in ((28, 17), (28, 16), (24, 17), (20, 14), (17, 17), (17, 10), (14, 10), (12, 8)):
        r = multiplier(w_acc, w_u); r.update(acc_bits=w_acc, u_bits=w_u)
        doc['multipliers'].append(r)
        print('mul', r, flush=True)
        r = multiplier_inverse(w_acc, w_u); r.update(acc_bits=w_acc, u_bits=w_u)
        doc['multipliers_inverse'].append(r)
        print('mul^-1', r, flush=True)
    for w, ow, q, c in ((28, 17, True, False), (28, 28, True, False), (17, 17, True, False),
                        (28, 28, True, True), (28, 17, True, True), (40, 40, True, False),
                        (28, 28, False, False), (28, 28, False, True)):
        r = adder(w, ow, q, c); r.update(target_bits=w, offset_bits=ow, quantum_offset=q, controlled=c)
        doc['adders'].append(r)
        print('add', r, flush=True)
    for n in (22, 16):
        r = leading_one_detector(n); r.update(bits=n)
        doc['leading_one_detector'][str(n)] = r
        print('lod', r, flush=True)
    for n in (21, 22):
        r = barrel_shift(n); r.update(bits=n)
        doc['barrel_shift'][str(n)] = r
        print('shift', r, flush=True)
    for name, widths, u in (
            ('d2_s128w28', [28, 21, 15], 15),
            ('d2_s256w27', [27, 19, 12], 14),
            ('d2_s512w27', [27, 18, 10], 13),
            ('d3_s32w27', [27, 22, 18, 14], 17),
            ('d3_s32w28', [28, 23, 19, 15], 17),
            ('d3_s64w27', [27, 21, 16, 11], 16),
            ('d3_s64w28', [28, 22, 17, 12], 16),
            ('d3_s128w27', [27, 20, 14, 8], 15),
            ('d3_s256w27', [27, 19, 12, 5], 14),
            ('d3_s512w27', [27, 18, 10, 2], 13),
            ('d4_s16w28', [28, 24, 21, 18, 14], 18),
            ('d4_s32w28', [28, 23, 19, 15, 10], 17),
            ('d4_s64w28', [28, 22, 17, 12, 7], 16),
            ('d4_s128w27', [27, 20, 14, 8, 2], 15),
            ('d4_s256w27', [27, 19, 12, 5, 1], 14),
            ('d4_s512w27', [27, 18, 10, 2, 1], 13)):
        r = horner_scaled(widths, u)
        r.update(widths=widths, u_bits=u, degree=len(widths) - 1)
        doc['horner_scaled'][name] = r
        print('horner_scaled', name, r, flush=True)
    for d, w, u in ((1, 28, 17), (2, 28, 17), (3, 28, 17), (3, 28, 16), (3, 27, 17),
                    (2, 28, 15), (2, 27, 14), (4, 28, 18), (3, 24, 14), (2, 20, 12)):
        r = horner(d, w, u); r.update(degree=d, acc_bits=w, u_bits=u)
        doc['horner'][f'd{d}_w{w}_u{u}'] = r
        print('horner', r, flush=True)
    (OUT / 'kernels.json').write_text(json.dumps(doc, indent=2) + '\n')


if __name__ == '__main__':
    main()
