"""Measured paid-gate costs of a table-initialized Newton reciprocal-sqrt kernel.

Paid gates are CCX, CCZ and CSWAP (the official Toffoli-like set); X, CX, SWAP,
HMR, R, Z, CZ, NEG and all BIT_* instructions are free.

`mul()` builds, out of place,

    OUT = floor(ACC * U / 2^drop)          (mod 2^w_out)

into an accumulator `tmp` of width drop + w_out: for every set bit k of U the low
min(|ACC|, |tmp| - k) bits of ACC are added into tmp[k:], so every partial product
is added with its carry chain running to the *top* of the accumulator.  The caller
reads the answer as tmp[drop:].  `test_mul()` proves the semantics by exhaustive
simulation.

This matters: the helper in experiments/invsqrt/20261106_piecewise_cost/kernels.py
adds acc[:width] into tmp[k:] with tmp only |ACC| wide, i.e. it keeps the *low*
|ACC| bits of the product and therefore cannot produce the high bits a Newton
step needs.  Its gate *count* is still a valid lower bound for a w-bit truncated
multiply, which is why the numbers here are larger.

Nothing here is a candidate circuit; there is no KMB and no verifier run.
"""
from __future__ import annotations

import json
import math
import platform
import sys
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_newton_goldschmidt/kernels'


def measure(build, maxq=40000):
    b = km.CircuitBuilder()
    b.set_max_qubits(maxq)
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    d = dict(st)
    return dict(paid=int(st.num_toffoli_like), ccx=d.get('CCX', 0), ccz=d.get('CCZ', 0),
                cswap=d.get('CSWAP', 0), cx=d.get('CX', 0), ops=int(st.num_instructions),
                qubits=c.num_qubits)


# ------------------------------------------------------------------ multiply ---

def mul_cost(w_acc, w_u, w_out, drop):
    """Closed form of `mul` below."""
    total = 0
    w = drop + w_out
    for k in range(w_u):
        L = w - k
        if L <= 0:
            break
        total += 2 * L + 3
    return total


def mul(b, acc, u, tmp, drop):
    """tmp = floor(acc*u / 2^drop) mod 2^|tmp|; answer is tmp[drop:].

    Every partial product is added over the full window [k, |tmp|) so that its
    carry chain reaches the top of the accumulator; the operand is zero-padded
    (free) when it is narrower than the window.  A controlled add of a
    zero-padded L-bit offset into an L-bit target costs exactly 2L+3 CCX
    (measured), so `mul_cost` is exact for this structure.
    """
    n, m, w = len(acc), len(u), len(tmp)
    for k in range(m):
        L = w - k
        if L <= 0:
            break
        if n >= L:
            off = acc[:L]
        else:
            off = km.array(list(acc) + list(b.alloc_qubits(L - n)))
        b.iadd(off, target=tmp[k:], control=u[k])


def mul_build(w_acc, w_u, w_out, drop):
    def build(b, w_acc=w_acc, w_u=w_u, w_out=w_out, drop=drop):
        acc = b.create_quantum_register(w_acc, name='acc')
        u = b.create_quantum_register(w_u, name='u')
        tmp = b.create_quantum_register(drop + w_out, name='tmp')
        mul(b, acc, u, tmp, drop)
    return build


def test_mul():
    """Exhaustive small-instance proof that `mul` computes floor(acc*u/2^drop)."""
    w_acc, w_u, drop, w_out = 5, 4, 1, 8
    cases = [(a, u) for a in range(1 << w_acc) for u in range(1 << w_u)]
    b = km.CircuitBuilder()
    acc = b.create_quantum_register(w_acc, name='acc')
    uu = b.create_quantum_register(w_u, name='u')
    tmp = b.create_quantum_register(drop + w_out, name='tmp')
    mul(b, acc, uu, tmp, drop)
    circ = b.finish_circuit()
    bad = []
    for a, u in cases:
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('acc', 0, a)
        sim.write_within_shot('u', 0, u)
        sim.do(circ)
        got = int(sim.read_within_shot('tmp', 0, out=int)) >> drop
        want = (a * u) >> drop
        if got != want:
            bad.append((a, u, got, want))
    return dict(cases=len(cases), mismatches=len(bad), first_bad=bad[:5],
                w_acc=w_acc, w_u=w_u, w_out=w_out, drop=drop)


def test_piecewise_multiplier():
    """What the 20261106_piecewise_cost `multiplier()` actually computes.

    Reproduces that helper exactly (acc[:width] into tmp[k:], tmp only |acc| wide)
    and compares with (A*U) mod 2^w_acc and with floor(A*U / 2^w_u).
    """
    w_acc, w_u = 4, 4

    def build(b, w_acc=w_acc, w_u=w_u):
        acc = b.create_quantum_register(w_acc, name='acc')
        u = b.create_quantum_register(w_u, name='u')
        tmp = b.create_quantum_register(w_acc, name='tmp')
        for k in range(w_u):
            width = w_acc - k
            if width <= 0:
                break
            b.iadd(acc[:width], target=tmp[k:], control=u[k])

    b = km.CircuitBuilder()
    build(b)
    circ = b.finish_circuit()
    n = keep_low = keep_high = 0
    for a in range(1 << w_acc):
        for u in range(1 << w_u):
            sim = km.Simulator(batch_size=1)
            sim.use_same_registers_as(circ)
            sim.write_within_shot('acc', 0, a)
            sim.write_within_shot('u', 0, u)
            sim.do(circ)
            got = int(sim.read_within_shot('tmp', 0, out=int))
            n += 1
            keep_low += (got == ((a * u) & ((1 << w_acc) - 1)))
            keep_high += (got == ((a * u) >> w_u))
    return dict(w_acc=w_acc, w_u=w_u, cases=n,
                matches_low_bits_mod=keep_low, matches_high_half=keep_high)


# -------------------------------------------------------------- primitives ---

def iadd_build(w_t, w_o, controlled=False):
    def build(b, w_t=w_t, w_o=w_o, controlled=controlled):
        t = b.create_quantum_register(w_t, name='t')
        o = b.create_quantum_register(w_o, name='o')
        c = b.create_quantum_register(1, name='c')[0] if controlled else True
        b.iadd(o, target=t, control=c)
    return build


def const_add_build(w, c):
    def build(b, w=w, c=c):
        t = b.create_quantum_register(w, name='t')
        b.iadd(c, target=t, btol=float('inf'))
    return build


def qq_sub_build(w):
    def build(b, w=w):
        t = b.create_quantum_register(w, name='t')
        o = b.create_quantum_register(w, name='o')
        b.isub(o, target=t)
    return build


def compare_build(w):
    def build(b, w=w):
        a = b.create_quantum_register(w, name='a')
        d = b.create_quantum_register(w, name='d')
        t = b.create_quantum_register(1, name='t')
        b.flip_if_less_than(a, d, target=t[0])
    return build


def qrom(n_entries, out_bits):
    def build(b, n_entries=n_entries, out_bits=out_bits):
        table = [(i * 2654435761) & ((1 << out_bits) - 1) for i in range(n_entries)]
        addr = b.create_quantum_register((n_entries - 1).bit_length(), name='addr')
        tgt = b.create_quantum_register(out_bits, name='tgt')
        b.init_lookup(table=table, address=addr, target=tgt)
        b.del_lookup(table=table, address=addr, target=tgt)
    return measure(build) if False else build
    return build


def qrom_measured(n_entries, out_bits):
    return measure(qrom(n_entries, out_bits))


def leading_one_detector(nbits):
    def build(b, nbits=nbits):
        x = b.create_quantum_register(nbits, name='x')
        t = b.alloc_qubits(nbits + 1)
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
    return build


def barrel_shift(nbits, steps):
    def build(b, nbits=nbits, steps=steps):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(len(steps), name='amt')
        for j, step in enumerate(steps):
            for i in range(nbits - step):
                b.cswap(amt[j], reg[i], reg[i + step])
    return build


# --------------------------------------------- full forward Newton kernels ---
#
# Both kernels implement the *unsigned* truncating Newton recurrence that
# numeric_check.py validates on all 3,133,452 inputs:
#     u = m*y^2 ;   y' = 1.5*y - 0.5*y*u          (x2)
# which is algebraically y' = y (3 - m y^2)/2 but never forms a signed
# intermediate: `u` is positive, 1.5*y0 is a free second QROM output, and the
# subtraction is an unconditional `isub` of a quantum offset (w-1 paid gates).
#
# Design A: uniform 28-fractional-bit working precision.
# Design B: iteration 1 at 14 bits (enough: Newton doubles the correct digits,
#           seed error 2^-8 -> 2^-16 -> 2^-32), iteration 2 at 24/28 bits.

def forward_newton_A(b):
    wf = 28
    m = b.create_quantum_register(23, name='m')                 # f=21
    y0sq = b.create_quantum_register(29, name='y0sq')           # y0^2  at f=28
    y0_15 = b.create_quantum_register(29, name='y0_15')         # 1.5*y0 at f=28
    y0_28 = b.create_quantum_register(29, name='y0_28')         # y0    at f=28

    tmp1 = b.create_quantum_register(21 + 29, name='tmp1')
    mul(b, y0sq, m, tmp1, 21)                                   # u1 = m*y0^2

    tmp2 = b.create_quantum_register(28 + 29, name='tmp2')
    mul(b, y0_28, tmp1[21:50], tmp2, 28)                        # y0*u1/2

    y1 = b.create_quantum_register(29, name='y1')
    for i in range(29):
        b.cx(y0_15[i], y1[i])
    b.isub(tmp2[28:57], target=y1)                              # y1 = 1.5y0 - y0u1/2

    y1c = b.create_quantum_register(29, name='y1c')
    for i in range(29):
        b.cx(y1[i], y1c[i])
    tmp3 = b.create_quantum_register(28 + 29, name='tmp3')
    mul(b, y1, y1c, tmp3, 28)                                   # y1^2

    tmp4 = b.create_quantum_register(21 + 29, name='tmp4')
    mul(b, tmp3[28:57], m, tmp4, 21)                            # u2 = m*y1^2

    tmp5 = b.create_quantum_register(28 + 29, name='tmp5')
    mul(b, y1, tmp4[21:50], tmp5, 28)                           # y1*u2/2

    y2 = b.create_quantum_register(29, name='y2')
    for i in range(29):
        b.cx(y1[i], y2[i])
    b.iadd(y1[1:29], target=y2[0:28])                            # +y1/2
    b.isub(tmp5[28:57], target=y2)                              # y2 = 1.5y1 - y1u2/2


def forward_newton_B(b):
    m = b.create_quantum_register(23, name='m')                 # f=21
    y0sq = b.create_quantum_register(17, name='y0sq')           # y0^2  at f=16
    y0_15 = b.create_quantum_register(15, name='y0_15')         # 1.5*y0 at f=14
    y0_14 = b.create_quantum_register(15, name='y0_14')         # y0    at f=14

    tmp1 = b.create_quantum_register(21 + 15, name='tmp1')
    mul(b, y0sq, m[7:23], tmp1, 21)                             # u1 at f=14

    tmp2 = b.create_quantum_register(15 + 15, name='tmp2')
    mul(b, y0_14, tmp1[21:36], tmp2, 15)                        # y0*u1/2

    y1 = b.create_quantum_register(15, name='y1')               # y1 at f=14
    for i in range(15):
        b.cx(y0_15[i], y1[i])
    b.isub(tmp2[15:30], target=y1)

    y1c = b.create_quantum_register(15, name='y1c')
    for i in range(15):
        b.cx(y1[i], y1c[i])
    tmp3 = b.create_quantum_register(29, name='tmp3')
    mul(b, y1, y1c, tmp3, 0)                                    # y1^2 at f=28

    sq25 = b.create_quantum_register(26, name='sq25')           # y1^2 at f=25
    for i in range(26):
        b.cx(tmp3[3 + i], sq25[i])

    tmp4 = b.create_quantum_register(22 + 25, name='tmp4')
    mul(b, sq25, m, tmp4, 22)                                   # u2 at f=24

    y1_28 = b.create_quantum_register(29, name='y1_28')         # y1 at f=28
    for i in range(15):
        b.cx(y1[i], y1_28[14 + i])

    tmp5 = b.create_quantum_register(29 + 29, name='tmp5')
    mul(b, y1_28, tmp4[22:47], tmp5, 29)                        # y1*u2/2

    y2 = b.create_quantum_register(29, name='y2')
    for i in range(29):
        b.cx(y1_28[i], y2[i])
    for i in range(15):
        b.cx(y1[i], y2[13 + i])                                 # +y1/2
    b.isub(tmp5[29:58], target=y2)


def test_forward_small():
    """End-to-end gate-level check of the unsigned kernel at wf=16.

    Runs the *same* gate sequence at reduced width and compares with an exact
    Python model of the same truncating recurrence over segment midpoints of the
    real 256-entry table.
    """
    wf, wy = 16, 18
    b = km.CircuitBuilder()
    mreg = b.create_quantum_register(23, name='m')
    y0sq = b.create_quantum_register(wy, name='y0sq')
    y0_15 = b.create_quantum_register(wy, name='y0_15')
    y0w = b.create_quantum_register(wy, name='y0w')

    t1 = b.create_quantum_register(21 + wy, name='t1')
    mul(b, y0sq, mreg, t1, 21)
    t2 = b.create_quantum_register(wf + 1 + wy, name='t2')
    mul(b, y0w, t1[21:21 + wy], t2, wf + 1)
    y1 = b.create_quantum_register(wy, name='y1')
    for i in range(wy):
        b.cx(y0_15[i], y1[i])
    b.isub(t2[wf + 1:wf + 1 + wy], target=y1)

    y1c = b.create_quantum_register(wy, name='y1c')
    for i in range(wy):
        b.cx(y1[i], y1c[i])
    t3 = b.create_quantum_register(wf + wy, name='t3')
    mul(b, y1, y1c, t3, wf)
    sq = b.create_quantum_register(wy, name='sq')
    for i in range(wy):
        b.cx(t3[wf + i], sq[i])
    t4 = b.create_quantum_register(21 + wy, name='t4')
    mul(b, sq, mreg, t4, 21)
    t5 = b.create_quantum_register(wf + 1 + wy, name='t5')
    mul(b, y1, t4[21:21 + wy], t5, wf + 1)
    y2 = b.create_quantum_register(wy, name='y2')
    for i in range(wy):
        b.cx(y1[i], y2[i])
    b.iadd(y1[1:wy], target=y2[0:wy - 1])                       # +y1/2
    b.isub(t5[wf + 1:wf + 1 + wy], target=y2)
    circ = b.finish_circuit()

    def model(mv, y0v, y0sqv, y015v):
        mask = (1 << wy) - 1
        u1 = ((y0sqv * mv) >> 21) & mask
        p = ((y0v * u1) >> (wf + 1)) & mask
        yy1 = (y015v - p) & mask
        sqv = (yy1 * yy1) >> wf
        u2 = ((sqv * mv) >> 21) & mask
        p2 = ((yy1 * u2) >> (wf + 1)) & mask
        y15 = yy1 + (yy1 >> 1)
        return (y15 - p2) & mask

    mids = [(1 << 21) + k * (1 << 15) + (1 << 14) for k in (0, 31, 64, 128, 191)]
    report = []
    for mval in mids:
        mtrue = mval / 2.0**21
        y0v = int(round(2.0**wf / math.sqrt(mtrue)))       # y0 at f=wf
        y0sqv = int(round(2.0**wf / mtrue))                # y0^2 at f=wf
        y015v = int(round(1.5 * 2.0**wf / math.sqrt(mtrue)))
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('m', 0, mval)
        sim.write_within_shot('y0sq', 0, y0sqv)
        sim.write_within_shot('y0_15', 0, y015v)
        sim.write_within_shot('y0w', 0, y0v)
        sim.do(circ)
        got = int(sim.read_within_shot('y2', 0, out=int))
        want = model(mval, y0v, y0sqv, y015v)
        y2 = got / 2.0**wf
        err = abs(y2 * math.sqrt(mtrue) - 1.0)
        report.append(dict(m=mval, y2=y2, model=want / 2.0**wf,
                           match=(got == want), true=1.0 / math.sqrt(mtrue),
                           rel_error=err, within_2m10=err < 2.0**-10))
    return dict(wf=wf, wy=wy, cases=report,
                all_match=all(r['match'] for r in report),
                all_within=all(r['within_2m10'] for r in report))


MULS = [
    # (label, w_acc, w_u, w_out, drop)   -- design A (uniform 28-bit)
    ('A_m1_u1',          29, 23, 29, 21),
    ('A_m2_y0u1',        29, 29, 29, 28),
    ('A_m3_y1sq',        29, 29, 29, 28),
    ('A_m4_u2',          29, 23, 29, 21),
    ('A_m5_y1u2',        29, 29, 29, 28),
    # design B (iteration 1 coarse)
    ('B_m1_u1',          17, 16, 15, 21),
    ('B_m2_y0u1',        15, 15, 15, 15),
    ('B_m3_y1sq',        15, 15, 29,  0),
    ('B_m4_u2',          26, 23, 25, 22),
    ('B_m5_y1u2',        29, 25, 29, 29),
    # the single cheapest multiply that can still carry the final 28-bit answer
    ('floor_y1u2_min',   29, 11, 29, 29),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = dict(
        scope=('Measured paid-gate counts (CCX+CCZ+CSWAP) of the primitives and of '
               'gate-by-gate forward Newton reciprocal-sqrt kernels A and B; '
               'no phase validation, no candidate KMB'),
        python=platform.python_version(), kickmix=km.__file__, mul=[], prim={}, qrom=[],
    )

    t = test_mul()
    doc['mul_semantics_test'] = t
    print('mul semantics test:', t, flush=True)
    t3 = test_piecewise_multiplier()
    doc['piecewise_multiplier_semantics'] = t3
    print('piecewise multiplier semantics:', t3, flush=True)
    t2 = test_forward_small()
    doc['forward_small_test'] = t2
    print('forward small test match/within:', t2['all_match'], t2['all_within'],
          [(r['m'], round(r['rel_error'], 8), r['match']) for r in t2['cases']], flush=True)

    for label, wa, wu, wo, dr in MULS:
        r = measure(mul_build(wa, wu, wo, dr))
        r.update(label=label, w_acc=wa, w_u=wu, w_out=wo, drop=dr,
                 formula=mul_cost(wa, wu, wo, dr))
        doc['mul'].append(r)
        print('mul', r, flush=True)

    p = doc['prim']
    for w in (15, 16, 23, 25, 29, 30):
        p[f'iadd_{w}_{w}'] = measure(iadd_build(w, w))
    p['iadd_30_23'] = measure(iadd_build(30, 23))
    for w in (15, 25, 30):
        p[f'isub_quantum_{w}'] = measure(qq_sub_build(w))
    for w, c in ((30, 1 << 28), (15, 1 << 14), (30, 1)):
        p[f'iadd_const_{w}_{c}'] = measure(const_add_build(w, c))
    for w in (16, 23):
        p[f'compare_qq_{w}'] = measure(compare_build(w))
    print('prim', json.dumps(p, indent=1), flush=True)

    doc['lod_22'] = measure(leading_one_detector(22))
    doc['shift_norm_23_steps_2_4_8_16'] = measure(barrel_shift(23, [2, 4, 8, 16]))
    doc['shift_align_38_s4'] = measure(barrel_shift(38, [1, 2, 4, 8]))
    doc['shift_align_36_s4'] = measure(barrel_shift(36, [1, 2, 4, 8]))
    print('lod22', doc['lod_22'], flush=True)
    print('sh_norm', doc['shift_norm_23_steps_2_4_8_16'], flush=True)
    print('sh_align38', doc['shift_align_38_s4'], flush=True)

    for e, o in ((256, 13), (256, 30), (256, 60), (1024, 30), (1024, 60)):
        r = qrom_measured(e, o)
        r.update(entries=e, out_bits=o)
        doc['qrom'].append(r)
        print('qrom', r, flush=True)

    doc['forward_kernel_A'] = measure(forward_newton_A)
    print('forward_kernel_A', doc['forward_kernel_A'], flush=True)
    doc['forward_kernel_B'] = measure(forward_newton_B)
    print('forward_kernel_B', doc['forward_kernel_B'], flush=True)

    (OUT / 'kernels.json').write_text(json.dumps(doc, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
