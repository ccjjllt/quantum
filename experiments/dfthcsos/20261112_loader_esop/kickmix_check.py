"""Real kickmix (stateful, no symbolic model) check of the basis-transform roundtrip.

A. the loader circuit for g = B f (per-output ESOP, built by basis_roundtrip.py) simulated on all
   1220 addresses must leave g in the word registers;
B. a CX-only recovery network, simulated with g written into the word registers, must turn them
   back into f = B^-1 g.  CX count is free in the score, and the network is a real invertible
   in-place elimination: Binv is unit lower triangular, so applying CX(c -> o) for o = 39..0 and
   c < o with Binv[o,c] = 1 reads only untouched source rows;
C. the same network applied to f gives g back (CX networks are self-inverse).

Usage: python kickmix_check.py [kmx_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(Path(__file__).parent))
import basis_roundtrip as br  # noqa: E402
import tensorqrom8 as tq  # noqa: E402

W_PATH = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
N = 1220
NALL = 2048


def unit_lower(rng, n=40) -> np.ndarray:
    M = np.eye(n, dtype=np.uint8)
    for o in range(n):
        for c in range(o):
            M[o, c] = rng.integers(0, 2)
    return M


def inverse_unit_lower(M: np.ndarray) -> np.ndarray:
    """Inverse of a unit lower triangular GF(2) matrix (forward substitution)."""
    n = M.shape[0]
    Inv = np.eye(n, dtype=np.uint8)
    for o in range(n):
        for c in range(o):
            if M[o, c]:
                Inv[o] ^= Inv[c]
    return Inv


def main() -> None:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/esop_roundtrip_kmsim')
    d.mkdir(parents=True, exist_ok=True)
    W = np.load(W_PATH)['angle_words']
    b_id = br.bits40(br.delta_of(W, 4))
    rng = np.random.default_rng(23)
    Binv = unit_lower(rng)
    B = inverse_unit_lower(Binv)
    assert np.array_equal((B.astype(int) @ Binv.astype(int)) % 2, np.eye(40, dtype=int))
    bits_g = ((b_id.astype(np.int64) @ B.T.astype(np.int64)) & 1).astype(np.uint8)

    # build the loader for g
    dg = br.pack_words(bits_g)
    C = tq.anf_tensor(dg, br.BROT, br.LOWBITS, full=True)
    terms = tq.per_output(C)
    c = tq.build_circuit(dg, terms, 11, br.BROT, br.LOWBITS, full=True)
    c.to_file(d / 'unitB.kmx', format='kmx')

    sel = km.array([km.q(i) for i in range(11)])
    wq = km.array([km.q(i) for i in range(11, 51)])
    sim = km.Simulator(batch_size=NALL, debug_print=False, seed=20261112, counting_operations=True)
    sim.use_same_registers_as(c)
    addr = np.arange(NALL, dtype=np.int64)
    selbits = ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool)
    sim.write_across_shots(sel, selbits)
    sim.do(c)
    got = sim.read_across_shots(wq)[:, :N].astype(np.uint8)
    ok_a = np.array_equal(got.T, bits_g)
    print(f'A. kickmix loader for g=Bf: CCX={c.operation_statistics().num_toffoli_like}'
          f' qubits={c.num_qubits} | g correct on all {N} addresses: {ok_a}')

    # recovery network (CX only)
    b = km.CircuitBuilder()
    b.create_quantum_register(11, 'selection')
    for j in range(5):
        b.create_quantum_register(8, f'word_{j}')
    ops = []
    for o in range(39, -1, -1):
        for cc in range(o):
            if Binv[o, cc]:
                ops.append((cc, o))
                b.cx(km.q(11 + cc), km.q(11 + o))
    rec = b.finish_circuit()
    print(f'B. recovery network: CX={len(ops)} toffoli={rec.operation_statistics().num_toffoli_like}'
          f' qubits={rec.num_qubits}')

    def run(circ, words_bits):
        s = km.Simulator(batch_size=NALL, debug_print=False, seed=7, counting_operations=True)
        s.use_same_registers_as(circ)
        s.write_across_shots(sel, selbits)
        arr = np.zeros((40, NALL), bool)
        arr[:, :N] = words_bits.T.astype(bool)
        s.write_across_shots(wq, arr)
        s.do(circ)
        return s.read_across_shots(wq)[:, :N].astype(np.uint8)

    out = run(rec, bits_g)
    ok_b = np.array_equal(out.T, b_id)
    print(f'C. recovery on g gives f on all {N} addresses: {ok_b}')
    b2 = km.CircuitBuilder()
    b2.create_quantum_register(11, 'selection')
    for j in range(5):
        b2.create_quantum_register(8, f'word_{j}')
    for o in range(39, -1, -1):
        for cc in range(o):
            if B[o, cc]:
                b2.cx(km.q(11 + cc), km.q(11 + o))
    recB = b2.finish_circuit()
    back = run(recB, b_id)
    ok_c = np.array_equal(back.T, bits_g)
    print(f'D. the transposed network on f gives g (B = Binv^-1): {ok_c}')
    print(f'\nreal-simulator roundtrip: {ok_a and ok_b and ok_c}'
          f'  |  loader CCX {c.operation_statistics().num_toffoli_like}'
          f' + recovery 0 T')


if __name__ == '__main__':
    main()
