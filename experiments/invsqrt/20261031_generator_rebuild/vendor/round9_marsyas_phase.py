# SPDX-License-Identifier: Apache-2.0
# Houssem Alayet/Marsyas: fused phase source.
# Optional Gluzdov additions: low four read positions share the affine
# predicate1 XOR f8 XOR f16; exact Z reads use diagonal Clifford gates.
from __future__ import annotations
import kickmix as km
def fused_phase(bb: B, R, h0, angfn, flags4, *, low_fuse=False, clifford=False, s_gadget=False):
    """Phase sum_j ang(j) * bit_j(R << s), s = f2 + 2 f4 + 4 f8 + 8 f16 (s <= 10).
    R: data qubits R[0..h0] followed by 3 clean ext qubits. f2, f4 in place (CSWAP);
    f8/f16 fused: Z_j = R_j ^ f8 (R_j ^ R_{j-4}) ^ f16 (R_j ^ R_{j-8}) into one temp,
    Z_POW, then HMR with Clifford fix-up.  angfn(j) -> Fraction half-turns or None."""
    b = bb.b
    f2, f4, f8, f16 = flags4
    assert len(R) == h0 + 4
    hiR = h0 + 3
    shifts = [(1, f2, h0), (2, f4, h0 + 1)]
    # targets above every earlier write are known-zero: move with an AND (uncomputed for free)
    empty = {(1, h0), (2, h0 + 1), (2, h0)}
    for k, f, hi in shifts:
        for i in range(hi, -1, -1):
            if (k, i) in empty:
                b.init_and(f, R[i], R[i + k]); b.cx(R[i + k], R[i])
            else:
                b.cswap(f, R[i], R[i + k])
    z = b.alloc_qubits(1)[0]
    bb.note(' fused phase')

    def term(f, j, k, act):
        qa = R[j] if j <= hiR else None
        qb = R[j - k] if 0 <= j - k <= (hiR if k == 4 else h0 + 2) else None
        if qa is None and qb is None:
            return False
        if qa is not None and qb is not None:
            b.cx(qb, qa); act(f, qa); b.cx(qb, qa)
        else:
            act(f, qa if qa is not None else qb)
        return True

    for j in range(h0 + 11):
        ex = angfn(j)
        if ex is None or ex % 2 == 0:
            continue
        if (s_gadget and ex % 1 == 0.5 and j > hiR and j-4 > hiR
                and 0 <= j-8 <= h0+2):
            # One controlled-S read: three exact T gates replace one AND.
            # a+b-(a XOR b)=2ab, so this is the same diagonal phase.
            q=R[j-8];b.z_pow(f16,ex/2);b.z_pow(q,ex/2)
            b.cx(f16,q);b.z_pow(q,-ex/2);b.cx(f16,q);continue
        if clifford and ex % 2 == 1:
            if j <= hiR:b.z(R[j])
            term(f8,j,4,lambda f,q:b.cz(f,q))
            term(f16,j,8,lambda f,q:b.cz(f,q))
            continue
        if low_fuse and j < 4:
            # Here both shifted sources are zero, so the read is exactly
            # R_j * (1 XOR f8 XOR f16). Borrow f8 for that affine control.
            b.reset(z);b.x(f8);b.cx(f16,f8);b.ccx(f8,R[j],z)
            b.z_pow(z,ex);m=b.alloc_bits(1)[0];b.hmr(z,m)
            b.push_condition(m);b.cz(f8,R[j]);b.pop_condition();b.free(km.array([m]))
            b.cx(f16,f8);b.x(f8);continue
        b.reset(z)
        has_r = j <= hiR
        if has_r:
            b.cx(R[j], z)
        t8 = term(f8, j, 4, lambda f, q: b.ccx(f, q, z))
        t16 = term(f16, j, 8, lambda f, q: b.ccx(f, q, z))
        if not (has_r or t8 or t16):
            continue
        b.z_pow(z, ex)
        m = b.alloc_bits(1)[0]
        b.hmr(z, m)
        b.push_condition(m)
        if has_r:
            b.z(R[j])
        term(f8, j, 4, lambda f, q: b.cz(f, q))
        term(f16, j, 8, lambda f, q: b.cz(f, q))
        b.pop_condition()
        b.free(km.array([m]))
    b.free(km.array([z]))
    for k, f, hi in reversed(shifts):
        for i in range(0, hi + 1):
            if (k, i) in empty:
                b.cx(R[i + k], R[i]); b.del_and(f, R[i], R[i + k])
            else:
                b.cswap(f, R[i], R[i + k])
