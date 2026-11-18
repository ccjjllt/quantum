"""Local static-cost measurements (circuit build + counting only; no simulation)."""
import sys
import kickmix as km

sys.path.insert(0, 'data/competition/verifiers')
from dqi.dqi_reference_circuit import ProosAndZalkaDecoder, build_reference_circuit, default_n_iters


class NoChien(ProosAndZalkaDecoder):
    def _chien_search_and_forney_mbuc(self, builder, reg_b, error_mbuc, n_b, n_B):
        return


class NoEEA(ProosAndZalkaDecoder):
    def _synchronized_eea(self, builder, *a, **kw):
        return


def build(cls, m, n, d):
    b = km.CircuitBuilder()
    syn = [b.create_quantum_register(d, name=f'S{i}') for i in range(n)]
    emb = [b.create_classical_register(d, name=f'E{j}') for j in range(m)]
    cls(n, km.GF2Field(d)).build_syndrome_decoding_mbuc(
        b, syndromes=syn, error_mbuc=emb, n_iters=default_n_iters(n))
    return b.finish_circuit()


def T(c):
    return c.operation_statistics().num_toffoli_like


if __name__ == '__main__':
    for (m, n, d) in [(15, 6, 4), (63, 6, 6), (255, 10, 8), (511, 10, 9)]:
        full = build(ProosAndZalkaDecoder, m, n, d)
        no_chien = build(NoChien, m, n, d)
        no_eea = build(NoEEA, m, n, d)
        print(f'ref ({m},{n},{d}): Q={full.num_qubits} T={T(full)} '
              f'chien={T(full)-T(no_chien)} eea={T(full)-T(no_eea)} '
              f'(fwd=eea/2) rest={T(no_eea)-0}')

    print('--- primitive costs ---')
    for d in (4, 6, 8, 9, 12):
        f = km.GF2Field(d)
        b = km.CircuitBuilder()
        x = b.alloc_qubits(d)
        inv, sc = b.init_gf2_inverse_with_scaffold(x, field=f)
        c1 = b.finish_circuit()
        print(f'  init_inv_scaffold d={d}: T={T(c1)} scaffold={len(sc)}')

        b = km.CircuitBuilder()
        x = b.alloc_qubits(d)
        y = b.alloc_qubits(d)
        q, sc = b.init_gf2_div_with_scaffold(x, y, field=f)
        c2 = b.finish_circuit()
        print(f'  init_div_scaffold  d={d}: T={T(c2)} scaffold={len(sc)}')

        b = km.CircuitBuilder()
        x = b.alloc_qubits(d)
        y = b.alloc_qubits(d)
        t = b.alloc_qubits(d)
        b.ixor_gf2_mul(x, y, target=t, field=f)
        print(f'  ixor_mul           d={d}: T={T(b.finish_circuit())}')

        b = km.CircuitBuilder()
        x = b.alloc_qubits(d)
        y = b.alloc_qubits(d)
        t = b.init_gf2_mul(x, y, field=f)
        print(f'  init_mul           d={d}: T={T(b.finish_circuit())}')

        b = km.CircuitBuilder()
        a = b.alloc_bits(d)
        s = b.alloc_qubits(1)[0]
        b.flip_if_equal(a, 0, target=s)
        print(f'  flip_if_equal(c)   d={d}: T={T(b.finish_circuit())}')

        b = km.CircuitBuilder()
        a = b.alloc_qubits(d)
        s = b.alloc_qubits(1)[0]
        b.flip_if_equal(a, 0, target=s)
        print(f'  flip_if_equal(q)   d={d}: T={T(b.finish_circuit())}')
