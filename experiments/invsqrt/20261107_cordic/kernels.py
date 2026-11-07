"""Construction and paid-gate measurement of the hyperbolic-CORDIC kernels.

Everything paid is counted with the official `km.CircuitBuilder` from complete
gate-level circuits (CCX+CCZ+CSWAP from `OperationStatistics`).  The only number
taken from a formula is the rotation-synthesis T count, which uses the
verifier's own `0.56*log2(1/eps)+5.3`.

Register layout (see README):
  F = 34 fractional bits, W = F + 2 = 36 qubits per CORDIC register.
  Index j has weight 2^(j-F); j = F is weight 2^0 and j = F+1 is the sign bit,
  so each register represents [-2, 2).  Measured ranges over all 3,133,452 x:
  a in [0.5, 0.875], b in [-0.75, 0.75], p in [0.30, 0.34], q in [-0.23, 0.23].

One CORDIC step i, with a single shared sign qubit:
      a <- a + sigma*(b >> i)      b <- b + sigma*(a_old >> i)
      p <- p + sigma*(q >> i)      q <- q + sigma*(p_old >> i)
sigma = -sign(b), i.e. subtract exactly when sign(b) = 0.

"b >> i" is the arithmetic shift, i.e. the signed value of bits i..W-1; it is
sign-extended to W bits by copying y[W-1] into scratch (free CX), because
`km.iadd` zero-extends a narrow offset.  The conditional add/subtract uses the
identity  x - y = NOT(NOT(x) + y)  (mod 2^W), so both branches are one
unconditional `iadd` plus two free conditional complements of x -- no
controlled adder and no carry-in port are needed.

The old value is kept in a copy register T (free CX); T is reused every
iteration and is cleared by the reverse pass, so the CORDIC block is only
meaningful as compute+uncompute, which is how it is used here.
"""
from __future__ import annotations

import json
import math
import platform
import random
import sys
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_cordic/kernels'

F = 34
W = F + 2                      # 36
MW = W + 2                     # 38: holds m in [1,4), binary point at index F


def measure(build, maxq=4000):
    b = km.CircuitBuilder()
    b.set_max_qubits(maxq)
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    d = dict(st)
    return dict(paid=int(st.num_toffoli_like), ccx=d.get('CCX', 0), ccz=d.get('CCZ', 0),
                cswap=d.get('CSWAP', 0), cx=d.get('CX', 0), ops=int(st.num_instructions),
                qubits=c.num_qubits)


def iteration_index_set(N):
    out = []
    for i in range(1, N + 1):
        out.append(i)
        if i >= 4 and (i - 1) % 3 == 0:
            out.append(i)
    return out


IDX = iteration_index_set(28)     # 37 iterations


# ------------------------------------------------- conditional add / subtract

def _ext_operand(b, i, y, E, width=W):
    """Sign-extended bits i..width-1 of y as a width-bit two's-complement operand."""
    top = list(y[i:width])
    if i == 0:
        return top
    for j in range(width - i, width):
        b.cx(y[width - 1], E[j])
    return top + list(E[width - i:width])


def _ext_operand_inv(b, i, y, E, width=W):
    if i == 0:
        return
    for j in reversed(range(width - i, width)):
        b.cx(y[width - 1], E[j])


def cas_fwd(b, i, x, y, mask, E, width=W):
    """x += (y >> i) if mask==0 else x -= (y >> i)   (two's complement, mod 2^W)."""
    for j in range(width):
        b.cx(mask, x[j])                                  # x' = NOT x when subtracting
    op = _ext_operand(b, i, y, E, width)
    b.iadd(km.array(op), target=km.array(x))
    _ext_operand_inv(b, i, y, E, width)
    for j in range(width):
        b.cx(mask, x[j])                                  # NOT(x' + y>>i) when subtracting


def cas_inv(b, i, x, y, mask, E, width=W):
    for j in range(width):
        b.cx(mask, x[j])
    op = _ext_operand(b, i, y, E, width)
    b.isub(km.array(op), target=km.array(x))
    _ext_operand_inv(b, i, y, E, width)
    for j in range(width):
        b.cx(mask, x[j])


def cadd_prim(b, i, x, y, mask, E, width=W):
    """Comparison point: true controlled add (add when mask=1), cost 2(W-i)+3."""
    if i >= width - 1:
        return
    b.iadd(km.array(y[i:width]), target=km.array(x), control=mask)


# --------------------------------------------------------------- CORDIC steps

def copy_high(b, x, t, i, width=W):
    for j in range(i, width):
        b.cx(x[j], t[j])


def step_fwd(b, i, X, Y, T, mask, E, width=W, prim=cas_fwd):
    copy_high(b, X, T, i, width)
    prim(b, i, X, Y, mask, E, width)
    prim(b, i, Y, T, mask, E, width)


def step_inv(b, i, X, Y, T, mask, E, width=W):
    cas_inv(b, i, Y, T, mask, E, width)
    cas_inv(b, i, X, Y, mask, E, width)
    copy_high(b, X, T, i, width)


def make_snapshots(b, n, width=W):
    """One fresh |0> snapshot per CORDIC step and per subsystem.

    A snapshot cannot be reused across steps: the copy is a CX, so a second use
    would XOR two different old values together.  Within compute+uncompute the
    reverse pass clears every snapshot for free.
    """
    return [b.create_quantum_register(width, name=f'T{k}') for k in range(n)]


def cordic_fwd(b, idx, A, B, T, M, E, width=W, P=None, Q=None, prim=cas_fwd):
    for k, i in enumerate(idx):
        b.cx(B[width - 1], M[k])                 # free sign copy
        b.x(M[k])                                # mask = "subtract" = NOT sign(b)
        step_fwd(b, i, A, B, T[2 * k] if P is not None else T[k], M[k], E, width, prim)
        if P is not None:
            step_fwd(b, i, P, Q, T[2 * k + 1], M[k], E, width, prim)


def cordic_inv(b, idx, A, B, T, M, E, width=W, P=None, Q=None):
    for k in reversed(range(len(idx))):
        i = idx[k]
        if P is not None:
            step_inv(b, i, P, Q, T[2 * k + 1], M[k], E, width)
        step_inv(b, i, A, B, T[2 * k] if P is not None else T[k], M[k], E, width)
        b.x(M[k])                                # B is back to B_old here
        b.cx(B[width - 1], M[k])


# ------------------------------------------------------- fixed-point prepare

def prep_fwd(b, M, A, B, width=W, f=F):
    """M = m in [1,4) -> A = (m+1)/4, B = (m-1)/4.  Destroys M."""
    b.isub(1, target=km.array(M[f:f + 3]))            # u = m - 1 (u >= 0)
    for j in range(width):
        b.cx(M[j + 2], B[j])                          # B = u >> 2
    for j in range(width):
        b.cx(B[j], A[j])                              # A = B
    b.iadd(1, target=km.array(A[f - 1:f + 2]))        # A += 1/2 (slice LSB)


def prep_inv(b, M, A, B, width=W, f=F):
    b.isub(1, target=km.array(A[f - 1:f + 2]))
    for j in reversed(range(width)):
        b.cx(B[j], A[j])
    for j in reversed(range(width)):
        b.cx(M[j + 2], B[j])
    b.iadd(1, target=km.array(M[f:f + 3]))


# ------------------------------------------------------------------ kernels

def kernel_vectoring(N, prim=cas_fwd):
    def build(b, N=N, prim=prim):
        A = b.create_quantum_register(W, name='A')
        B = b.create_quantum_register(W, name='B')
        E = b.create_quantum_register(W, name='E')
        idx = iteration_index_set(N)
        T = make_snapshots(b, 2 * len(idx), W)
        M = b.alloc_qubits(len(idx))
        cordic_fwd(b, idx, A, B, T, M, E, W, prim=prim)
    return measure(build)


def kernel_dual(N, prim=cas_fwd):
    def build(b, N=N, prim=prim):
        A = b.create_quantum_register(W, name='A')
        B = b.create_quantum_register(W, name='B')
        E = b.create_quantum_register(W, name='E')
        P = b.create_quantum_register(W, name='P')
        Q = b.create_quantum_register(W, name='Q')
        idx = iteration_index_set(N)
        T = make_snapshots(b, 2 * len(idx), W)
        M = b.alloc_qubits(len(idx))
        cordic_fwd(b, idx, A, B, T, M, E, W, P, Q, prim=prim)
    return measure(build)


def kernel_full(N, prim=cas_fwd, inverse=True, dual=True):
    """prep + CORDIC + Y=P+Q, then the exact inverse (compute+uncompute)."""
    def build(b, N=N):
        idx = iteration_index_set(N)
        M = b.create_quantum_register(MW, name='M')
        A = b.create_quantum_register(W, name='A')
        B = b.create_quantum_register(W, name='B')
        E = b.create_quantum_register(W, name='E')
        P = b.create_quantum_register(W, name='P')
        Q = b.create_quantum_register(W, name='Q')
        T = make_snapshots(b, (2 if dual else 1) * len(idx), W)
        Msk = b.alloc_qubits(len(idx))
        prep_fwd(b, M, A, B)
        if dual:
            cordic_fwd(b, idx, A, B, T, Msk, E, W, P, Q, prim=prim)
            b.iadd(km.array(Q), target=km.array(P))         # Y = P + Q
        else:
            cordic_fwd(b, idx, A, B, T, Msk, E, W, prim=prim)
        if inverse:
            if dual:
                b.isub(km.array(Q), target=km.array(P))
                cordic_inv(b, idx, A, B, T, Msk, E, W, P, Q)
            else:
                cordic_inv(b, idx, A, B, T, Msk, E, W)
            prep_inv(b, M, A, B)
    return measure(build)


def leading_one_detector(nbits):
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


def barrel_shift_steps(nbits, steps):
    def build(b, nbits=nbits, steps=steps):
        reg = b.create_quantum_register(nbits, name='reg')
        amt = b.create_quantum_register(len(steps), name='amt')
        for j, step in enumerate(steps):
            for i in range(nbits - step):
                b.cswap(amt[j], reg[i], reg[i + step])
    return measure(build)


# ------------------------------------------------------- variant B: reciprocal

def recip_kernel(b, n, root):
    """Non-restoring division r0 = C, r_i = 2 r_{i-1} - q_i s with LSB(s) forced to 1."""
    width = n + 3
    R = b.alloc_qubits(width)
    c = b.create_quantum_register(n, name='c')
    const1 = b.alloc_qubits(1)[0]
    pad0 = b.alloc_qubits(2)
    b.x(const1)
    zero_pool = list(b.alloc_qubits(n + 2))
    b.x(R[n])
    r = list(R)
    for i in range(1, n + 1):
        z = zero_pool.pop()
        old_top = r[-1]
        r = [z] + r[:-1]
        sign = r[-1]
        b.cx(sign, old_top)
        b.x(sign)
        b.cx(sign, c[i - 1])
        b.x(sign)
        ci = c[i - 1]
        op = [const1] + [root[n - j] for j in range(1, n + 1)] + [ci, ci]
        for q in op[1:1 + n]:
            b.cx(ci, q)
        b.iadd(km.array(op), target=km.array(r))
        for q in op[1:1 + n]:
            b.cx(ci, q)
    return c, r, zero_pool


# -------------------------------------------------- small-instance validation

def reference_model(m_val, Ff, idx, K):
    base = 1 << Ff
    b = (m_val - base) >> 2
    a = b + (1 << (Ff - 1))
    p = int(round((1 << (Ff - 2)) / K))
    q = 0
    for i in idx:
        s = -1 if b >= 0 else 1
        a_old, p_old = a, p
        a = a + s * (b >> i)
        b = b + s * (a_old >> i)
        p = p + s * (q >> i)
        q = q + s * (p_old >> i)
    return a, b, p, q


def simulate_small(Ff, N, m_vals):
    """Small-grid gate-level kernel vs the integer model (reads P after Y = P+Q)."""
    Wf = Ff + 2
    idx = iteration_index_set(N)
    K = 1.0
    for i in idx:
        K *= math.sqrt(1.0 - 4.0 ** (-i))
    bb = km.CircuitBuilder()
    M = bb.create_quantum_register(Wf + 2, name='M')
    A = bb.create_quantum_register(Wf, name='A')
    B = bb.create_quantum_register(Wf, name='B')
    E = bb.create_quantum_register(Wf, name='E')
    P = bb.create_quantum_register(Wf, name='P')
    Q = bb.create_quantum_register(Wf, name='Q')
    Msk = bb.alloc_qubits(len(idx))
    prep_fwd(bb, M, A, B, Wf, Ff)
    p0 = int(round((1 << (Ff - 2)) / K))
    for j in range(Wf):
        if (p0 >> j) & 1:
            bb.x(P[j])                     # classical constant 1/K/4 (free)
    T = make_snapshots(bb, 2 * len(idx), Wf)
    cordic_fwd(bb, idx, A, B, T, Msk, E, Wf, P, Q)
    bb.iadd(km.array(Q), target=km.array(P))
    circ = bb.finish_circuit()
    out = []
    for m in m_vals:
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('M', 0, int(m))
        sim.do(circ)
        got = sum(int(sim.read_within_shot(P[j], 0, out=int)) << j for j in range(Wf))
        ra, rb, rp, rq = reference_model(int(m), Ff, idx, K)
        out.append(dict(m=int(m), sim_pq=got, model_pq=rp + rq, match=(got == rp + rq),
                        y_sim=(got * 4) / 2**Ff, y_model=(rp + rq) * 4 / 2**Ff))
    return out


def inverse_cleanup(Ff, N, m_vals):
    """Full compute+uncompute on a small grid: M restored, every scratch |0>."""
    Wf = Ff + 2
    idx = iteration_index_set(N)
    bb = km.CircuitBuilder()
    M = bb.create_quantum_register(Wf + 2, name='M')
    A = bb.create_quantum_register(Wf, name='A')
    B = bb.create_quantum_register(Wf, name='B')
    E = bb.create_quantum_register(Wf, name='E')
    P = bb.create_quantum_register(Wf, name='P')
    Q = bb.create_quantum_register(Wf, name='Q')
    Msk = bb.alloc_qubits(len(idx))
    prep_fwd(bb, M, A, B, Wf, Ff)
    K = 1.0
    for i in idx:
        K *= math.sqrt(1.0 - 4.0 ** (-i))
    p0 = int(round((1 << (Ff - 2)) / K))
    for j in range(Wf):
        if (p0 >> j) & 1:
            bb.x(P[j])
    T = make_snapshots(bb, 2 * len(idx), Wf)
    cordic_fwd(bb, idx, A, B, T, Msk, E, Wf, P, Q)
    bb.iadd(km.array(Q), target=km.array(P))
    bb.isub(km.array(Q), target=km.array(P))
    cordic_inv(bb, idx, A, B, T, Msk, E, Wf, P, Q)
    for j in range(Wf):
        if (p0 >> j) & 1:
            bb.x(P[j])
    prep_inv(bb, M, A, B, Wf, Ff)
    circ = bb.finish_circuit()
    mset = set(M)
    out = []
    for m in m_vals:
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('M', 0, int(m))
        sim.do(circ)
        got = int(sim.read_within_shot('M', 0, out=int))
        dirty = [str(km.q(q)) for q in range(circ.num_qubits)
                 if km.q(q) not in mset and int(sim.read_within_shot(km.q(q), 0, out=int))]
        out.append(dict(m=int(m), m_restored=(got == int(m)), dirty=dirty))
    return out


def cas_primitive_check(width=8, trials=120, seed=20261109):
    """Bit-exact check of the conditional add/subtract primitive and its inverse."""
    rng = random.Random(seed)
    def build(apply_inverse):
        bb = km.CircuitBuilder()
        x = bb.create_quantum_register(width, name='x')
        y = bb.create_quantum_register(width, name='y')
        E = bb.create_quantum_register(width, name='E')
        m = bb.alloc_qubits(1)[0]
        for i in range(1, width - 1):
            cas_fwd(bb, i, x, y, m, E, width)
            if apply_inverse:
                cas_inv(bb, i, x, y, m, E, width)
        return bb.finish_circuit(), x, y, m
    rt, xq, yq, maskq = build(True)
    bad = 0
    for _ in range(trials):
        xv = rng.randrange(1 << width)
        yv = rng.randrange(1 << width)
        sub = rng.randrange(2)
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(rt)
        sim.write_within_shot('x', 0, xv)
        sim.write_within_shot('y', 0, yv)
        sim.write_within_shot(maskq, 0, sub)
        sim.do(rt)
        if (int(sim.read_within_shot(xq, 0, out=int)) != xv
                or int(sim.read_within_shot(yq, 0, out=int)) != yv):
            bad += 1
    return dict(width=width, trials=trials, index_sequence=f'1..{width-2}',
                roundtrip_failures=bad, all_ok=(bad == 0))


def simulate_large(Ff, N, xs):
    """Real-size gate-level kernel vs closed-form 1/sqrt(m) on a few x."""
    Wf = Ff + 2
    MWf = Wf + 2
    idx = iteration_index_set(N)
    Kc = 1.0
    for i in idx:
        Kc *= math.sqrt(1.0 - 4.0 ** (-i))
    p0 = int(round((1 << (Ff - 2)) / Kc))
    bb = km.CircuitBuilder()
    bb.set_max_qubits(4000)
    M = bb.create_quantum_register(MWf, name='M')
    A = bb.create_quantum_register(Wf, name='A')
    B = bb.create_quantum_register(Wf, name='B')
    E = bb.create_quantum_register(Wf, name='E')
    P = bb.create_quantum_register(Wf, name='P')
    Q = bb.create_quantum_register(Wf, name='Q')
    T = make_snapshots(bb, 2 * len(idx), Wf)
    Msk = bb.alloc_qubits(len(idx))
    prep_fwd(bb, M, A, B, Wf, Ff)
    for j in range(Wf):
        if (p0 >> j) & 1:
            bb.x(P[j])
    cordic_fwd(bb, idx, A, B, T, Msk, E, Wf, P, Q)
    bb.iadd(km.array(Q), target=km.array(P))
    circ = bb.finish_circuit()
    out = []
    for x in xs:
        e = int(x).bit_length() - 1
        k = e >> 1
        Mv = int(x) << (Ff - 2 * k)
        sim = km.Simulator(batch_size=1)
        sim.use_same_registers_as(circ)
        sim.write_within_shot('M', 0, Mv)
        sim.do(circ)
        Y = sum(int(sim.read_within_shot(P[j], 0, out=int)) << j for j in range(Wf))
        y = 4 * Y / 2**Ff
        true = 1 / math.sqrt(int(x) / 4**k)
        out.append(dict(x=int(x), k=k, y=y, true=true, rel_error=y / true - 1))
    return dict(F=Ff, N=N, iterations=len(idx), qubits=circ.num_qubits,
                ops=len(circ), cases=out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = dict(scope=('Gate-level construction and measured paid-gate counts of the '
                      'hyperbolic-CORDIC reciprocal square root. F=34 fractional bits, '
                      'W=36-bit registers, 37 iterations (i=1..28 with i=4,7,...,28 '
                      'repeated). Paid = CCX+CCZ+CSWAP from OperationStatistics.'),
               python=platform.python_version(), kickmix=km.__file__,
               F=F, W=W, iterations=IDX)

    # 1. primitive costs
    def cadd(width):
        def build(b, width=width):
            xx = b.create_quantum_register(width, name='x')
            tt = b.create_quantum_register(width, name='t')
            c = b.alloc_qubits(1)[0]
            b.iadd(km.array(tt), target=km.array(xx), control=c)
        return measure(build)

    def uadd(width):
        def build(b, width=width):
            xx = b.create_quantum_register(width, name='x')
            tt = b.create_quantum_register(width, name='t')
            b.iadd(km.array(tt), target=km.array(xx))
        return measure(build)

    doc['cadd_controlled_equal_width'] = {str(w): cadd(w) for w in (8, 16, 24, 28, 32, 36)}
    doc['iadd_equal_width'] = {str(w): uadd(w) for w in (8, 16, 24, 28, 32, 36)}
    print('cadd(control)', {k: v['paid'] for k, v in doc['cadd_controlled_equal_width'].items()},
          flush=True)
    print('iadd', {k: v['paid'] for k, v in doc['iadd_equal_width'].items()}, flush=True)

    # 2. individual steps
    for i in (1, 14, 28):
        def build_step(b, i=i):
            A = b.create_quantum_register(W, name='A')
            B = b.create_quantum_register(W, name='B')
            T1 = b.create_quantum_register(W, name='T1')
            T2 = b.create_quantum_register(W, name='T2')
            E = b.create_quantum_register(W, name='E')
            P = b.create_quantum_register(W, name='P')
            Q = b.create_quantum_register(W, name='Q')
            mask = b.alloc_qubits(1)[0]
            b.cx(B[W - 1], mask)
            b.x(mask)
            step_fwd(b, i, A, B, T1, mask, E)
            step_fwd(b, i, P, Q, T2, mask, E)
            b.x(mask)
            b.cx(B[W - 1], mask)
        doc[f'step_i{i}'] = measure(build_step)
        print(f'step i={i}', doc[f'step_i{i}']['paid'], flush=True)

    # 3. full kernels
    doc['vectoring_forward'] = kernel_vectoring(28)
    doc['dual_forward'] = kernel_dual(28)
    for N in (25, 26, 27):
        doc[f'vectoring_forward_N{N}'] = kernel_vectoring(N)
        doc[f'dual_forward_N{N}'] = kernel_dual(N)
    for N in (25, 26, 27, 28):
        doc[f'full_compute_uncompute_N{N}'] = kernel_full(N)
    doc['vectoring_full_compute_uncompute'] = kernel_full(28, dual=False)
    doc['dual_forward_ctrladd'] = kernel_dual(28, prim=cadd_prim)
    doc['full_compute_uncompute_N28_ctrladd'] = kernel_full(28, prim=cadd_prim)
    print('vectoring', doc['vectoring_forward']['paid'],
          'dual', doc['dual_forward']['paid'], flush=True)
    print('full N=28', doc['full_compute_uncompute_N28'], flush=True)
    print('vectoring full', doc['vectoring_full_compute_uncompute'], flush=True)
    print('naive controlled add: dual', doc['dual_forward_ctrladd']['paid'],
          'full', doc['full_compute_uncompute_N28_ctrladd']['paid'], flush=True)

    # 4. scaffolding
    doc['lod_22'] = leading_one_detector(22)
    doc['shift_norm_23_steps_2_4_8_16'] = barrel_shift_steps(23, [2, 4, 8, 16])
    doc['shift_align_38_s4'] = barrel_shift_steps(38, [1, 2, 4, 8])
    doc['shift_align_39_s4'] = barrel_shift_steps(39, [1, 2, 4, 8])
    for k in ('lod_22', 'shift_norm_23_steps_2_4_8_16', 'shift_align_38_s4',
              'shift_align_39_s4'):
        print(k, doc[k]['paid'], flush=True)

    # 5. variant-B reciprocal
    for n in (28, 30):
        def build_recip(b, n=n):
            root = b.create_quantum_register(n, name='root')
            recip_kernel(b, n, root)
        doc[f'recip_n{n}'] = measure(build_recip)
        print('recip', n, doc[f'recip_n{n}']['paid'], flush=True)

    # 6. primitive check, small-instance gate-level vs integer model, cleanup
    doc['cas_primitive_check'] = cas_primitive_check()
    print('cas primitive roundtrip ok:', doc['cas_primitive_check']['all_ok'], flush=True)
    rng = random.Random(20261107)
    small_ms = sorted({1 << 10, (1 << 10) + 1, 2 << 10, 3 << 10, (1 << 12) - 1,
                       *[rng.randrange(1 << 10, 1 << 12) for _ in range(4)]})
    sim = simulate_small(10, 8, small_ms)
    doc['small_instance_simulation'] = dict(F=10, N=8, cases=sim,
                                            all_match=all(r['match'] for r in sim))
    print('small sim all_match:', doc['small_instance_simulation']['all_match'], flush=True)
    for r in sim:
        print('   ', r, flush=True)

    # real-size gate-level spot check
    spot = simulate_large(F, 28, [1, 2, 3, 161, 1024, 1234567, 3133452])
    doc['large_spotcheck'] = spot
    print('large spotcheck max |rel error|:',
          max(abs(r['rel_error']) for r in spot['cases']), flush=True)

    cleanup = inverse_cleanup(8, 6, small_ms[:4])
    doc['inverse_cleanup'] = dict(F=8, N=6, cases=cleanup,
                                  all_restored=all(r['m_restored'] and not r['dirty']
                                                   for r in cleanup))
    print('inverse cleanup all_restored:', doc['inverse_cleanup']['all_restored'], flush=True)

    (OUT / 'kernels.json').write_text(json.dumps(doc, indent=2) + '\n')
    ok = (doc['cas_primitive_check']['all_ok']
          and doc['small_instance_simulation']['all_match']
          and doc['inverse_cleanup']['all_restored'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
