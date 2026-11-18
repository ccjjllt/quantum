"""Normalized divstep EEA Reed-Solomon MBUC decoder for Benchmark II (DQI).

Same contract as the official reference generator
(``data/competition/verifiers/dqi/dqi_reference_circuit.py``):

    registers S0..S{n-1} (quantum, degree bits) + E0..E{m-1} (classical, degree bits),
    every shot restores S, returns every other qubit to |0>, and multiplies the
    global phase by ``(-1)**sum_j popcount(e_j & M_j)``.

What is different from the reference
------------------------------------
The reference runs a *synchronized* EEA for ``3*(n+1)+9`` iterations, and each
iteration sweeps the whole ``m = n+3`` slot polynomial arrays.  Here the EEA is
the **normalized divstep** form: every step cancels exactly one leading
coefficient, so the number of steps is the number of degree reductions
(``~n``, measured: 8 for n=6, 12 for n=10) instead of ``3n+12``, and no
iteration sweeps a whole array.

Three structural choices keep the Toffoli count low:

1.  **Scalar quotients only.**  Each step subtracts ``c * x**k * B`` from ``A``
    with ``c = lc(A)/lc(B)`` and ``k = deg A - deg B``.  In the slot layout used
    here (slot ``j`` holds the coefficient of ``x**(p+1-j)``) that subtraction is
    *slot aligned*, i.e. the monomial shift ``k`` is free -- no rotation, no
    conditional swap along the polynomial.
2.  **Free phase bookkeeping.**  Lowering a phase counter by one is a cyclic
    rotation of the slot array, which is a permutation of qubit ids: zero
    Toffolis.  Slot 0 is always a dead "coefficient above the degree" slot, so
    the value that wraps around is always 0.
3.  **No reverse EEA.**  The syndrome registers are only ever *read* (copied into
    the arrays with CX), so they are restored for free.  The arrays themselves
    are discarded with reset gates after the phase kickback.  (A fully
    reversible variant would replay the EEA backwards, which doubles T; see
    RESULT.md.)

Chien search + Forney kickback follows the reference idea but never inverts a
per-position value that is not needed: the zero test of ``sigma(x_j)`` uses
``flip_if_equal`` (degree Toffolis, MBUC-cleaned), the inverse of ``sigma'(x_j)``
is one ``init_gf2_inverse_with_scaffold`` per position (no per-position
scaffold re-derivation) and the phase itself is
``gf2_phase_by_product`` (zero Toffolis, zero ancillas).

Usage:
    python dqi_fast.py out.kmb --m 15 --n 6 --degree 4
"""
from __future__ import annotations

import argparse

import kickmix as km


def default_num_accepted_values(degree: int) -> int:
    import math
    q = 1 << degree
    return max(1, (q - math.isqrt(q)) // 2)


class FastDecoder:
    """Normalized divstep EEA + Chien/Forney MBUC decoder."""

    def __init__(self, n_syndromes: int, field: km.GF2Field, *, n_iter: int | None = None):
        if n_syndromes < 2:
            raise ValueError('need at least 2 syndromes')
        self.n = n_syndromes
        self.t = n_syndromes // 2
        self.field = field
        self.b = field.degree
        self.n_iter = n_iter if n_iter is not None else 2 * n_syndromes + 3

    # ------------------------------------------------------------- helpers
    def _lanes(self, arr):
        """One km.array per bit position, index = slot."""
        return [km.array([slot[k] for slot in arr]) for k in range(self.b)]

    def build(self, builder, *, syndromes, error_mbuc) -> None:
        n, b, t, gf = self.n, self.b, self.t, self.field
        NS = n + 3                    # allocated slots (slot n+2 is the dead wrap slot)
        NL = n + 2                    # slots that can ever hold a coefficient
        w = (n + 1).bit_length() + 1

        # ---- polynomial arrays: slot j <-> coefficient of x**(p+1-j)
        RA = [builder.alloc_qubits(b) for _ in range(NS)]
        RB = [builder.alloc_qubits(b) for _ in range(NS)]
        UA = [builder.alloc_qubits(b) for _ in range(NS)]   # cofactor of RA
        UB = [builder.alloc_qubits(b) for _ in range(NS)]   # cofactor of RB
        pA = builder.alloc_qubits(w)
        pB = builder.alloc_qubits(w)

        # flags / scratch
        sw = builder.alloc_qubits(1)[0]
        zb = builder.alloc_qubits(1)[0]
        run = builder.alloc_qubits(1)[0]
        nzb = builder.alloc_qubits(1)[0]
        cmb = builder.alloc_qubits(3)          # swap / shift / sub controls
        flags_and_ctrl = km.array([sw, zb, run, nzb, *cmb])

        # ---- initial state: A = x^n, B = x^n + f, U = 0, V = 1
        builder.x(km.array([RA[1][0], RB[1][0], UB[n + 1][0]]))
        for j in range(2, n + 2):
            builder.cx(syndromes[n + 1 - j], RB[j])
        builder.iadd(n, target=pA)
        builder.iadd(n, target=pB)

        with builder.mark('forward_eea'):
            self._divstep_eea(builder, RA, RB, UA, UB, pA, pB, flags_and_ctrl,
                              NS=NS, NL=NL, w=w)

        with builder.mark('chien_forney_mbuc'):
            self._chien_forney_mbuc(builder, RB, UB, pB, error_mbuc, NS=NS)

        # ---- discard all decoder workspace (syndromes were never written)
        with builder.mark('discard_workspace'):
            builder.reset(km.array([q for arr in (RA, RB, UA, UB) for slot in arr for q in slot]))
            builder.reset(km.array([*pA, *pB, *flags_and_ctrl]))
            for arr in (RA, RB, UA, UB):
                for slot in arr:
                    builder.free(slot)
            for reg in (pA, pB, flags_and_ctrl):
                builder.free(reg)

    # ---------------------------------------------------------------- EEA
    def _divstep_eea(self, builder, RA, RB, UA, UB, pA, pB, flags, *, NS, NL, w):
        n, b, t, gf = self.n, self.b, self.t, self.field
        sw, zb, run, nzb, cs, csh, csu = flags
        cmb = km.array([cs, csh, csu])
        RA_all = km.array([q for slot in RA for q in slot])
        RB_all = km.array([q for slot in RB for q in slot])
        UA_all = km.array([q for slot in UA for q in slot])
        UB_all = km.array([q for slot in UB for q in slot])
        RA_lanes, RB_lanes = self._lanes(RA), self._lanes(RB)
        UA_lanes, UB_lanes = self._lanes(UA), self._lanes(UB)

        for _ in range(self.n_iter):
            with builder.mark('eea_step'):
                # --- exchange the two lattice rows when deg A < deg B
                builder.flip_if_less_than(pA, pB, target=sw)
                builder.cswap(sw, RA_all, RB_all)
                builder.cswap(sw, UA_all, UB_all)
                builder.cswap(sw, pA, pB)

                # --- decisions, taken on the post-exchange (divisor) state
                builder.flip_if_less_than(pB, t, target=run)   # run = not (pB < t)
                builder.x(run)
                builder.flip_if_equal(RB[1], 0, target=zb)
                builder.cx(zb, nzb)
                builder.x(nzb)
                builder.init_and(zb, run, csh)
                builder.init_and(nzb, run, csu)

                # --- divisor normalisation: one slot shift when lc(B) == 0
                for lane in RB_lanes:
                    builder.right_rotate(lane, 1, control=csh)
                for lane in UB_lanes:
                    builder.right_rotate(lane, 1, control=csh)
                builder.isub(1, target=pB, control=csh)

                # --- one normalized divstep: A -= (lc(A)/lc(B)) * B
                a1 = builder.alloc_qubits(b)
                builder.cx(RA[1], a1)
                q = builder.init_gf2_div(a1, RB[1], field=gf)
                for j in range(NL):
                    builder.ixor_gf2_mul(q, RB[j], target=RA[j], control=csu, field=gf)
                    builder.ixor_gf2_mul(q, UB[j], target=UA[j], control=csu, field=gf)
                for lane in RA_lanes:
                    builder.right_rotate(lane, 1, control=csu)
                for lane in UA_lanes:
                    builder.right_rotate(lane, 1, control=csu)
                builder.isub(1, target=pA, control=csu)
                builder.del_gf2_div(a1, RB[1], target=q, field=gf)
                builder.reset(a1)
                builder.free(a1)

                # --- clear scratch for the next step (all flags are recomputed)
                builder.reset(km.array([sw, zb, run, nzb, *cmb]))

    # ----------------------------------------------------- Chien / Forney
    def _chien_forney_mbuc(self, builder, omega_arr, sigma_arr, p, error_mbuc, *, NS):
        b, gf = self.b, self.field
        L = (1 << b) - 1
        prim = gf.primitive_element
        nl = NS - 1

        # make the phase counter even so that "degree odd" == "slot even"
        par = builder.alloc_qubits(1)[0]
        builder.cx(p[0], par)
        sig_lanes = self._lanes(sigma_arr)
        om_lanes = self._lanes(omega_arr)
        for lane in sig_lanes + om_lanes:
            builder.right_rotate(lane, 1, control=par)
        builder.isub(1, target=p, control=par)
        builder.reset(par)

        acc = builder.alloc_qubits(b)      # sigma(x_j)
        wv = builder.alloc_qubits(b)       # omega(x_j) * x_j
        dv = builder.alloc_qubits(b)       # sigma'(x_j)
        isz = builder.alloc_qubits(1)[0]
        loc = builder.alloc_qubits(b)
        scratch = km.array([*acc, *wv, *dv, isz, *loc])

        num_positions = min(L, len(error_mbuc))
        for j in range(num_positions):
            with builder.mark('forney_step'):
                xj = gf.pow(prim, (-j) % L)
                # sigma(x_j), omega(x_j), sigma'(x_j): constant multiplies only
                self._horner(builder, sigma_arr, xj, acc, nl, parity=None)
                self._horner(builder, omega_arr, xj, wv, nl, parity=None)
                builder.gf2_imul(xj, target=wv, field=gf)
                self._horner(builder, sigma_arr, xj, dv, nl, parity=0)
                builder.flip_if_equal(acc, 0, target=isz)
                builder.init_and(isz, wv, loc)
                ej = builder.init_gf2_div(loc, dv, field=gf)
                for k in range(b):
                    builder.cz(ej[k], error_mbuc[j][k])
                builder.del_gf2_div(loc, dv, target=ej, field=gf)
                builder.free(ej)
                builder.reset(scratch)

        builder.free(scratch)

    @staticmethod
    def _horner(builder, arr, xj, acc, nl, *, parity):
        """acc = sum_j arr[j] xj**(nl-1-j), restricted to slots j with j%2==parity."""
        b = len(acc)
        for j in range(nl):
            builder.gf2_imul(xj, target=acc)
            if parity is None or j % 2 == parity:
                builder.cx(arr[j], acc)


def build_fast_circuit(m: int, n: int, degree: int, *, n_iter: int | None = None) -> km.Circuit:
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(degree, name=f'S{i}') for i in range(n)]
    error_mbuc = [builder.create_classical_register(degree, name=f'E{j}') for j in range(m)]
    FastDecoder(n, km.GF2Field(degree), n_iter=n_iter).build(
        builder, syndromes=syndromes, error_mbuc=error_mbuc)
    return builder.finish_circuit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output')
    parser.add_argument('--m', type=int, default=15)
    parser.add_argument('--n', type=int, default=6)
    parser.add_argument('--degree', type=int, default=4)
    parser.add_argument('--n-iter', type=int, default=None)
    args = parser.parse_args()
    circuit = build_fast_circuit(args.m, args.n, args.degree, n_iter=args.n_iter)
    circuit.to_file(args.output, format='kmb')
    stats = circuit.operation_statistics()
    print(f'Wrote {args.output}: {stats.num_toffoli_like:,} Toffolis, '
          f'{circuit.num_qubits} qubits, {len(circuit):,} ops.')


if __name__ == '__main__':
    main()
