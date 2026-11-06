"""Construction and gate-count measurement of the digit-recurrence kernels.

Two things are measured with the official `km.CircuitBuilder`:

  * primitive cost of add/sub/compare at the widths the recurrence uses;
  * the complete radix-2 sqrt and reciprocal recurrences built gate by gate,
    so the totals are counted, not extrapolated.

The recurrence kernels are also simulated on a small instance to check that the
gate-level construction reproduces the integer model in `numeric_check.py`.

Paid gates are CCX+CCZ+CSWAP; X, CX, SWAP, HMR, R, Z, CZ, NEG, BIT_* are free.
"""
from __future__ import annotations

import json
import platform
import random
import sys
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_digit_recurrence/kernels'

# Fixed-point layout of the residual registers (see README):
#   W  : 33 qubits, binary point at index 29 (weight 2^0) -> weights 2^-29 .. 2^3
#   r  : n+2 qubits, binary point at index n  (weight 2^0) -> weights 2^-n .. 2^1


def measure(build, maxq=8000):
    b = km.CircuitBuilder()
    b.set_max_qubits(maxq)
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    d = dict(st)
    return dict(paid=int(st.num_toffoli_like), ccx=d.get('CCX', 0), ccz=d.get('CCZ', 0),
                cswap=d.get('CSWAP', 0), cx=d.get('CX', 0), ops=int(st.num_instructions),
                qubits=c.num_qubits)


def decrement_at(b, reg, q):
    """reg -= 2**(q - point); free: X at q then a CNOT borrow chain to the top."""
    b.x(reg[q])
    for k in range(q, len(reg) - 1):
        b.cx(reg[k], reg[k + 1])


def build_sqrt_recurrence(b, n, mreg):
    """Radix-2 non-restoring sqrt of m = mreg/2^21 in [1,4).

    mreg: 23 qubits, mreg[k] has weight 2^(k-21).
    Returns the root-digit register (n qubits, b_j at bit j-1).

    W layout: 33 qubits, w[k] has weight 2^(k-29). W_0 = m-1 occupies 8..30.
    Step i: b_i = not sign(W_{i-1});
            W_i = 2 W_{i-1} - d_i A'_i,   d_i = 2 b_i - 1,
            A'_i = 2 s_{i-1} + d_i 2^-i = sum_{j<i} b_j 2^(2-j) + (3+2b_i) 2^-i.
    A'_i is a positive number whose LSB is 1, so +A'_i when d=+1 and
    -A'_i = complement(A'_i)+1 when d=-1 differ only by complementing every
    bit above the LSB; both are a single unconditional `iadd` of an offset
    assembled from the root register with free CX gates.  The doubling is a
    free relabel.  Window [29-i, 32], width i+4.
    """
    W = b.alloc_qubits(33)
    root = b.create_quantum_register(n, name='root')
    const1 = b.alloc_qubits(1)[0]
    pad0 = b.alloc_qubits(2)
    b.x(const1)
    zero_pool = list(b.alloc_qubits(n + 2))
    dropped = []

    # W_0 = m - 1: place m (weights 2^-21..2^1 -> indices 8..30) then subtract 1
    # from the integer part (one-time cost; the per-step -2^-i term is folded
    # into the operand A'_i instead).
    for k in range(23):
        b.cx(mreg[k], W[8 + k])
    b.isub(1, target=km.array(W[29:33]))

    w = list(W)                      # logical index -> physical qubit
    for i in range(1, n + 1):
        z = zero_pool.pop()
        old_top = w[-1]
        w = [z] + w[:-1]
        sign = w[32]                 # sign bit of W_{i-1}; b_i = not sign
        b.cx(sign, old_top)          # dropped sign-extension bit: clear for free
        dropped.append(old_top)
        b.x(sign)                    # b_i
        b.cx(sign, root[i - 1])      # store digit b_i
        b.x(sign)                    # restore sign bit
        m = root[i - 1]
        lo = 29 - i
        # offset over [lo,32]: [1, 1, 0, b_{i-1}^m, ..., b_1^m, m, m]
        op = [const1, const1, pad0[0]]
        op += [root[j - 1] for j in range(i - 1, 0, -1)]
        op += [m, m]
        for q in op[3:3 + (i - 1)]:
            b.cx(m, q)
        b.iadd(km.array(op), target=km.array(w[lo:33]))
        for q in op[3:3 + (i - 1)]:
            b.cx(m, q)
    return root, w, dropped, zero_pool


def build_recip_recurrence(b, n, root):
    """Radix-2 non-restoring division y = 1/s, s = 2B + 2^-n from root digits.

    r layout: n+3 qubits, r[k] has weight 2^(k-n); r_0 = 1.
    Step i: c_i = not sign(r_{i-1});  r_i = 2 r_{i-1} - q_i s q_i = 2 c_i - 1.
    s = [1, b_n, ..., b_1] has LSB 1, so +s and -s = complement(s)+1 differ
    only above the LSB; one unconditional iadd per step.
    """
    R = b.alloc_qubits(n + 3)
    c = b.create_quantum_register(n, name='c')
    const1 = b.alloc_qubits(1)[0]
    pad0 = b.alloc_qubits(2)
    b.x(const1)
    zero_pool = list(b.alloc_qubits(n + 2))
    dropped = []

    b.x(R[n])                       # r_0 = 1, weight 2^0 at index n
    r = list(R)
    for i in range(1, n + 1):
        z = zero_pool.pop()
        old_top = r[-1]
        r = [z] + r[:-1]
        sign = r[-1]                 # sign bit of r_{i-1}; c_i = not sign
        b.cx(sign, old_top)
        dropped.append(old_top)
        b.x(sign)                    # c_i
        b.cx(sign, c[i - 1])         # store quotient digit c_i
        b.x(sign)                    # restore sign bit
        ci = c[i - 1]
        # offset: [1, b_n^c, ..., b_1^c, c, c]
        op = [const1] + [root[n - j] for j in range(1, n + 1)] + [ci, ci]
        for q in op[1:1 + n]:
            b.cx(ci, q)
        b.iadd(km.array(op), target=km.array(r))
        for q in op[1:1 + n]:
            b.cx(ci, q)
    return c, r, dropped, zero_pool


def reference_digits(m_val, n, F=30):
    """Exact integer model of the same recurrence (matches numeric_check.py)."""
    assert (1 << 21) <= m_val < (1 << 23), m_val
    w = (m_val - (1 << 21)) << (F - 21)
    two_s = 2 << F
    b = []
    for i in range(1, n + 1):
        d = 1 if w >= 0 else -1
        b.append(1 if d > 0 else 0)
        w = 2 * w - d * two_s - (1 << (F - i))
        two_s = two_s + (d << (F + 1 - i))
    Bint = 0
    for j in range(1, n + 1):
        Bint += b[j - 1] << (n - j)
    S = 2 * Bint + 1
    r = 1 << n
    c = []
    for i in range(1, n + 1):
        q = 1 if r >= 0 else -1
        c.append(1 if q > 0 else 0)
        r = 2 * r - q * S
    return b, c


def simulate_sqrt(n, m_val):
    """Build the sqrt kernel for a single n and read its root digits.

    Runs the whole kernel (sqrt + reciprocal) and returns (root bits, c bits).
    """
    b = km.CircuitBuilder()
    mreg = b.create_quantum_register(23, name='m')
    root, _, _, _ = build_sqrt_recurrence(b, n, mreg)
    c, _, _, _ = build_recip_recurrence(b, n, root)
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=1)
    sim.use_same_registers_as(circ)
    sim.write_within_shot('m', 0, m_val)
    sim.do(circ)
    rb = [sim.read_within_shot(root[j], 0, out=int) for j in range(n)]
    cb = [sim.read_within_shot(c[j], 0, out=int) for j in range(n)]
    return rb, cb


class Recorder:
    """Proxy that records builder calls so the exact inverse circuit can be replayed."""

    def __init__(self, b):
        self.b = b
        self.ops = []

    def __getattr__(self, name):
        f = getattr(self.b, name)
        if name in ('iadd', 'isub'):
            def g(offset, *, target, control=True):
                self.ops.append((name, offset, target, control))
                f(offset, target=target, control=control)
            return g
        if name in ('x', 'cx', 'ccx', 'cswap'):
            def g(*a):
                self.ops.append((name,) + a)
                f(*a)
            return g
        return f


def replay_inverse(rec, b):
    inv = {'iadd': 'isub', 'isub': 'iadd'}
    for op in reversed(rec.ops):
        name = op[0]
        if name in inv:
            _, offset, target, control = op
            getattr(b, inv[name])(offset, target=target, control=control)
        else:
            getattr(b, name)(*op[1:])


def test_inverse_cleanup():
    """Forward kernel followed by its exact inverse must restore m and clear scratch."""
    n = 10
    rec_b = km.CircuitBuilder()
    rec = Recorder(rec_b)
    mreg = rec.create_quantum_register(23, name='m')
    root, w, dropped, zp = build_sqrt_recurrence(rec, n, mreg)
    c, r, dropped2, zp2 = build_recip_recurrence(rec, n, root)
    replay_inverse(rec, rec_b)
    circ = rec_b.finish_circuit()
    rng = random.Random(20261107)
    ms = [1 << 21, 1 << 22, (1 << 23) - 1] + [rng.randrange(1 << 21, 1 << 23) for _ in range(3)]
    out = []
    for m in ms:
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('m', 0, int(m))
        sim.do(circ)
        got_m = int(sim.read_within_shot('m', 0, out=int))
        mset = set(mreg)
        dirty = [str(km.q(q)) for q in range(circ.num_qubits)
                 if km.q(q) not in mset and int(sim.read_within_shot(km.q(q), 0, out=int))]
        out.append(dict(m=int(m), m_restored=(got_m == int(m)), dirty_qubits=dirty))
    return out


def test_small():
    """Local correctness check of the gate-level construction vs the integer model."""
    n = 10
    rng = random.Random(20261107)
    ms = sorted({1 << 21, (1 << 21) + 1, (1 << 22) - 1, (1 << 22), (1 << 23) - 1,
                 (1 << 22) + 12345, (1 << 21) + 777777,
                 *[rng.randrange(1 << 21, 1 << 23) for _ in range(6)]})
    report = []
    for m in ms:
        true_b, true_c = reference_digits(int(m), n)
        got_b, got_c = simulate_sqrt(n, int(m))
        report.append(dict(m=int(m), sqrt_ok=got_b == true_b, recip_ok=got_c == true_c,
                           sqrt_got=got_b, sqrt_expect=true_b))
    return report


def barrel_shift_steps(nbits, steps):
    """Cyclic barrel shift with an explicit list of conditional step sizes."""
    def build(b, nbits=nbits, steps=steps):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(len(steps), name='amt')
        for j, step in enumerate(steps):
            for i in range(nbits - step):
                b.cswap(amt[j], reg[i], reg[i + step])
    return measure(build)


def primitive_table():
    """Measured cost of the primitive shapes the recurrence and alternatives use."""
    rows = {}

    def add(w_t, w_o):
        def build(b, w_t=w_t, w_o=w_o):
            t = b.create_quantum_register(w_t, name='t')
            o = b.create_quantum_register(w_o, name='o')
            b.iadd(o, target=t)
        return measure(build)

    def sub(w_t, w_o):
        def build(b, w_t=w_t, w_o=w_o):
            t = b.create_quantum_register(w_t, name='t')
            o = b.create_quantum_register(w_o, name='o')
            b.isub(o, target=t)
        return measure(build)

    def cadd(w_t, w_o):
        def build(b, w_t=w_t, w_o=w_o):
            t = b.create_quantum_register(w_t, name='t')
            o = b.create_quantum_register(w_o, name='o')
            ctl = b.create_quantum_register(1, name='ctl')
            b.iadd(o, target=t, control=ctl[0])
        return measure(build)

    def cmp(w):
        def build(b, w=w):
            a = b.create_quantum_register(w, name='a')
            d = b.create_quantum_register(w, name='d')
            t = b.create_quantum_register(1, name='t')
            b.flip_if_less_than(a, d, target=t[0])
        return measure(build)

    rows['iadd_equal_width'] = {str(w): add(w, w) for w in (8, 16, 24, 28, 30, 32, 38)}
    rows['iadd_narrow_offset'] = {f'{wt}/{wo}': add(wt, wo) for wt, wo in
                                  ((28, 17), (30, 17), (30, 20), (32, 24))}
    rows['isub_equal_width'] = {str(w): sub(w, w) for w in (28, 30)}
    rows['iadd_ctrl_equal_width'] = {str(w): cadd(w, w) for w in (28, 30)}
    rows['compare_qq'] = {str(w): cmp(w) for w in (28, 30)}
    return rows


def leading_one_detector(nbits):
    """Suffix-OR leading-one flags t (nbits+1) plus the binary exponent e."""
    def build(b, nbits=nbits):
        x = b.create_quantum_register(nbits, name='x')
        t = b.alloc_qubits(nbits + 1)
        ebits = (nbits - 1).bit_length()
        e = b.create_quantum_register(ebits, name='e')
        for i in reversed(range(nbits)):
            b.cx(t[i + 1], t[i])
            b.cx(x[i], t[i])
            b.ccx(t[i + 1], x[i], t[i])
        for j in range(ebits):
            for i in range(nbits):
                if (i >> j) & 1:
                    b.cx(t[i], e[j])
                    b.cx(t[i + 1], e[j])
    return measure(build)


def qrom(n_entries, out_bits):
    """init_lookup + del_lookup of an n_entries table into an out_bits target."""
    def build(b, n_entries=n_entries, out_bits=out_bits):
        table = [(i * 2654435761) & ((1 << out_bits) - 1) for i in range(n_entries)]
        addr = b.create_quantum_register((n_entries - 1).bit_length(), name='addr')
        tgt = b.create_quantum_register(out_bits, name='tgt')
        b.init_lookup(table=table, address=addr, target=tgt)
        b.del_lookup(table=table, address=addr, target=tgt)
    return measure(build)


def barrel_shift(nbits, stages):
    """Cyclic barrel shift by a `stages`-bit quantum amount (CSWAP ladder)."""
    def build(b, nbits=nbits, stages=stages):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(stages, name='amt')
        for s in range(stages):
            step = 1 << s
            for i in range(nbits - step):
                b.cswap(amt[s], reg[i], reg[i + step])
    return measure(build)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = dict(scope=('Gate-level construction and measured paid-gate counts of the '
                      'radix-2 non-restoring sqrt + reciprocal recurrence kernels. '
                      'Paid = CCX+CCZ+CSWAP from OperationStatistics; no phase check.'),
               python=platform.python_version(), kickmix=km.__file__)

    t = test_small()
    doc['small_instance_simulation'] = dict(n=10, cases=t,
                                            all_sqrt_ok=all(r['sqrt_ok'] for r in t),
                                            all_recip_ok=all(r['recip_ok'] for r in t))
    print('small instance sqrt ok:', doc['small_instance_simulation']['all_sqrt_ok'],
          'recip ok:', doc['small_instance_simulation']['all_recip_ok'], flush=True)

    inv = test_inverse_cleanup()
    doc['inverse_cleanup'] = dict(cases=inv,
                                  all_restored=all(r['m_restored'] and not r['dirty_qubits'] for r in inv))
    print('inverse cleanup ok:', doc['inverse_cleanup']['all_restored'], flush=True)

    doc['primitives'] = primitive_table()
    print(json.dumps(doc['primitives'], indent=1), flush=True)

    # Normalization: 22-bit LOD, and a 43-bit 4-stage barrel shift (shift amount
    # 21-2k, k in [0,10]; the free +1 stage is a relabel; register must be
    # 22 + 21 = 43 wide for the cyclic form to equal a zero-fill shift).
    doc['lod_22'] = leading_one_detector(22)
    doc['qrom'] = [dict(entries=e, out_bits=o, **qrom(e, o))
                   for e, o in ((32, 3), (32, 40), (64, 3), (128, 40))]
    doc['shift_norm_43_s4'] = barrel_shift(43, 4)
    doc['shift_norm_23_steps_2_4_8_16'] = barrel_shift_steps(23, [2, 4, 8, 16])
    doc['shift_align_38_s4'] = barrel_shift(38, 4)
    doc['shift_align_36_s4'] = barrel_shift(36, 4)
    doc['shift_align_37_s4'] = barrel_shift(37, 4)
    doc['shift_align_38_s5'] = barrel_shift(38, 5)
    for k in ('lod_22', 'shift_norm_43_s4', 'shift_norm_23_steps_2_4_8_16',
              'shift_align_38_s4', 'shift_align_36_s4', 'shift_align_37_s4',
              'shift_align_38_s5'):
        print(k, doc[k], flush=True)
    for r in doc['qrom']:
        print('qrom', r, flush=True)

    # Full-width counted kernels at n = 28.
    for n in (26, 27, 28):
        def build_sqrt(b, n=n):
            mreg = b.create_quantum_register(23, name='m')
            build_sqrt_recurrence(b, n, mreg)
        def build_recip(b, n=n):
            root = b.create_quantum_register(n, name='root')
            build_recip_recurrence(b, n, root)
        doc[f'sqrt_kernel_n{n}'] = measure(build_sqrt)
        doc[f'recip_kernel_n{n}'] = measure(build_recip)
        print('sqrt', n, doc[f'sqrt_kernel_n{n}'], flush=True)
        print('recip', n, doc[f'recip_kernel_n{n}'], flush=True)

    (OUT / 'kernels.json').write_text(json.dumps(doc, indent=2) + '\n')
    if not (doc['small_instance_simulation']['all_sqrt_ok']
            and doc['small_instance_simulation']['all_recip_ok']):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
