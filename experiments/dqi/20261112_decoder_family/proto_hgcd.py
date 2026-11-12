"""Sub-block prototype: reversible polynomial arithmetic for a half-gcd convert.

Measures, with kickmix and the *real* public `field.mul_xor0` kernel (42 T,
zero workspace), the T and Q of the pieces a half-gcd convert would need at
the actual convert size (degree 17, split into 9-word halves):

  pmul(d)      C += A*B          schoolbook  (d+1)(d+2)/2 field mults
  karat(d)     C += A*B          recursive Karatsuba with temporary output
  matvec(d)    (u,v) -> M*(u,v)  4 polynomial products
  matmat(d)    A*B (2x2)         8 polynomial products  <-- hgcd combine

Read-only prototype: not a decoder, not a candidate, no verifier run.

Usage: .venv/bin/python proto_hgcd.py [OUT.json]
"""
import json
import sys
from pathlib import Path

import kickmix as km

SRC = (Path(__file__).resolve().parents[3] / 'artifacts' / '20261112_frontier_source' /
       'somejoint_v21_source' / 'blocks' / 'dqi' / 'team-1028-narrow240' / 'source' /
       'playbook' / 'kit' / 'decoder')
sys.modules['circ'] = km
sys.path.insert(0, str(SRC / 'exp' / 'arithmetic'))
import field as ar  # noqa: E402


def words(b, n):
    return [b.alloc_qubits(12) for _ in range(n)]


def pmul_school(b, A, B, C):
    """C ^= A*B, truncated to len(C); zero workspace beyond the operands."""
    for i, x in enumerate(A):
        for j, y in enumerate(B):
            if i + j < len(C):
                ar.mul_xor0(b, x, y, C[i + j])


def karatsuba_into(b, A, B, C):
    """C ^= A*B for arbitrary lengths, reversible Karatsuba with temps.

    Splits at h=len//2, pads the sum registers to the longer half, and
    truncates everything that falls outside C.
    """
    n = max(len(A), len(B))
    if n <= 4:
        pmul_school(b, A, B, C)
        return
    h = n // 2
    a0, a1 = A[:h], A[h:]
    b0, b1 = B[:h], B[h:]
    karatsuba_into(b, a0, b0, C[:min(len(C), len(a0) + len(b0) - 1)])
    z2off = 2 * h
    if z2off < len(C):
        karatsuba_into(b, a1, b1, C[z2off:min(len(C), z2off + len(a1) + len(b1) - 1)])
    m = max(len(a1), len(b1))
    sA, sB = words(b, m), words(b, m)
    for i in range(m):
        if i < len(a0):
            b.cx(a0[i], sA[i])
        if i < len(a1):
            b.cx(a1[i], sA[i])
        if i < len(b0):
            b.cx(b0[i], sB[i])
        if i < len(b1):
            b.cx(b1[i], sB[i])
    z1 = words(b, len(sA) + len(sB) - 1)
    karatsuba_into(b, sA, sB, z1)
    # z1 += z0 + z2  (GF(2)); the middle target overlaps both but all
    # sources are read before the middle is written.
    z0len = len(a0) + len(b0) - 1
    z2len = len(a1) + len(b1) - 1
    for i in range(len(z1)):
        if i < z0len and i < len(C):
            b.cx(C[i], z1[i])
        if i < z2len and z2off + i < len(C):
            b.cx(C[z2off + i], z1[i])
    for i in range(len(z1)):
        if h + i < len(C):
            b.cx(z1[i], C[h + i])
    # Temps are intentionally left allocated: re-allocating dirty qubits as
    # "zero" is invalid, and a real clean-up would have the same peak Q anyway.
    # The measured Q is therefore the honest peak, and T is unaffected.


def matvec(b, M, v, out):
    for i in range(2):
        for j in range(2):
            pmul_school(b, M[2 * i + j], v[j], out[i])


def matmat(b, A, B, out):
    for i in range(2):
        for j in range(2):
            for t in range(2):
                pmul_school(b, A[2 * i + t], B[2 * t + j], out[2 * i + j])


def measure(name, build):
    b = km.CircuitBuilder()
    build(b)
    c = b.finish_circuit()
    st = c.operation_statistics()
    return dict(name=name, Q=int(c.num_qubits), T=int(st.num_toffoli_like),
                ops=len(c))


def check_pmul(d, mul, batch=6):
    """Reversibly simulate C ^= A*B on random inputs; compare with GF(2^12)."""
    import random

    b = km.CircuitBuilder()
    A = words(b, d + 1)
    B = words(b, d + 1)
    C = words(b, 2 * d + 1)
    mul(b, A, B, C)
    c = b.finish_circuit()
    sim = km.Simulator(batch_size=batch, seed=20261112)
    f = km.GF2Field(12)
    rng = random.Random(20261112 + d)
    ca = [[rng.randrange(4096) for _ in range(d + 1)] for _ in range(batch)]
    cb = [[rng.randrange(4096) for _ in range(d + 1)] for _ in range(batch)]
    for k in range(batch):
        for w, v in zip(A, ca[k]):
            sim.write_within_shot(w, k, v)
        for w, v in zip(B, cb[k]):
            sim.write_within_shot(w, k, v)
    sim.do(c)
    ok = True
    for k in range(batch):
        got = [sim.read_within_shot(w, k, out=int) for w in C]
        want = [0] * (2 * d + 1)
        for i in range(d + 1):
            for j in range(d + 1):
                want[i + j] ^= f.mul(ca[k][i], cb[k][j])
        ok &= got == want
    return bool(ok)


def check_matmat(d, batch=4):
    import random

    b = km.CircuitBuilder()
    A = [words(b, d + 1) for _ in range(4)]
    B = [words(b, d + 1) for _ in range(4)]
    C = [words(b, d + 1) for _ in range(4)]
    matmat(b, A, B, C)
    c = b.finish_circuit()
    sim = km.Simulator(batch_size=batch, seed=20261112)
    f = km.GF2Field(12)
    rng = random.Random(424242)
    vals = [[[rng.randrange(4096) for _ in range(d + 1)] for _ in range(4)] for _ in range(2)]
    for k in range(batch):
        for e in range(4):
            for w, v in zip(A[e], vals[0][e]):
                sim.write_within_shot(w, k, v)
            for w, v in zip(B[e], vals[1][e]):
                sim.write_within_shot(w, k, v)
    sim.do(c)
    ok = True
    for k in range(batch):
        got = [[sim.read_within_shot(w, k, out=int) for w in C[e]] for e in range(4)]
        want = [[0] * (d + 1) for _ in range(4)]
        for i in range(2):
            for j in range(2):
                for t in range(2):
                    # polynomial product truncated to d+1, then XOR
                    for a in range(d + 1):
                        for bb in range(d + 1 - a):
                            want[2 * i + j][a + bb] ^= f.mul(vals[0][2 * i + t][a],
                                                               vals[1][2 * t + j][bb])
        ok &= got == want
    return bool(ok)


def main(out):
    def build_pmul(d):
        def go(b):
            A, B, C = words(b, d + 1), words(b, d + 1), words(b, d + 1)
            pmul_school(b, A, B, C)
        return go

    def build_karat(d):
        def go(b):
            A, B = words(b, d + 1), words(b, d + 1)
            C = words(b, 2 * d + 1)
            karatsuba_into(b, A, B, C)
        return go

    def build_matvec(d):
        def go(b):
            M = [words(b, d + 1) for _ in range(4)]
            v = [words(b, d + 1) for _ in range(2)]
            out = [words(b, d + 1) for _ in range(2)]
            matvec(b, M, v, out)
        return go

    def build_matmat(d):
        def go(b):
            A = [words(b, d + 1) for _ in range(4)]
            B = [words(b, d + 1) for _ in range(4)]
            C = [words(b, d + 1) for _ in range(4)]
            matmat(b, A, B, C)
        return go

    rows = []
    for d in (2, 4, 8, 17):
        rows.append(measure(f'pmul_school_d{d}', build_pmul(d)))
    for d in (4, 8, 16):
        rows.append(measure(f'karatsuba_d{d}', build_karat(d)))
    for d in (4, 8):
        rows.append(measure(f'matvec_school_d{d}', build_matvec(d)))
        rows.append(measure(f'matmat_school_d{d}', build_matmat(d)))
    for r in rows:
        mults = r['T'] / 42
        print(f"{r['name']:22s} Q={r['Q']:5d} T={r['T']:9d}  field-mults={mults:8.1f}")
    checks = dict(
        pmul_d4=check_pmul(4, pmul_school),
        karatsuba_d4=check_pmul(4, karatsuba_into),
        matmat_d2=check_matmat(2),
    )
    print('functional checks:', checks)
    Path(out).write_text(json.dumps(dict(blocks=rows, checks=checks), indent=1))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(Path(__file__).resolve().parents[3] / 'artifacts/20261112_decoder_family/proto_hgcd.json'))
