"""Q/C ledger for the hyperbolic-CORDIC reciprocal square root.

Inputs (produced by the other scripts in this directory):
  artifacts/20261107_cordic/numeric/numeric_check.json   full-domain integer model
  artifacts/20261107_cordic/kernels/kernels.json         measured paid gates
  artifacts/20261106_syed_v9/invsqrt/official_run.json   baseline official result

Paid = CCX+CCZ+CSWAP.  Rotation synthesis uses the verifier's own formula
0.56*log2(1/eps)+5.3 T per general Z_POW, eps = pi*margin/n_rot, T/4 in C.
Rotations by 2^-1 turn are Clifford (free) and by 2^-2 turn are 1 T: measured
with km's own z_pow classifier (`num_z_pow(min_clifford_hierarchy_level=4)`),
so positions 3..38 are the general rotations.

Nothing here is a candidate circuit: no KMB, no verifier run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NUM = ROOT / 'artifacts/20261107_cordic/numeric/numeric_check.json'
KER = ROOT / 'artifacts/20261107_cordic/kernels/kernels.json'
BASE = ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json'
OUT = ROOT / 'artifacts/20261107_cordic'

FRONT_ROT = 694.840824
ALIGN_BITS = 39                     # 2^0 bit (only when y >= 1) .. 2^-38
MAX_ROT_POSITION = 38
N_GENERAL = MAX_ROT_POSITION - 2    # positions 3..38; position 1 Clifford, 2 T
DIRECT_T = 0.25                     # the 2^-2-turn rotation at position 2


def rot_cost(n_rot, margin):
    eps = math.pi * margin / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / 4, eps


def main():
    num = json.loads(NUM.read_text())
    ker = json.loads(KER.read_text())
    base = json.loads(BASE.read_text())['official_result']
    q0, c0, score0 = base['num_qubits'], base['toffoli_equivalent'], base['score']

    budgets = {
        'front_plus_rotations_C_62Q': FRONT_ROT,
        'front_plus_rotations_C_61Q': FRONT_ROT + c0 / 61,
        'front_plus_rotations_C_63Q': FRONT_ROT - c0 / 63,
        'whole_circuit_C_62Q': score0 / 62,
        'whole_circuit_C_61Q': score0 / 61,
        'whole_circuit_C_63Q': score0 / 63,
        'added_C_allowed_for_61Q': c0 / 61,
    }

    lod = ker['lod_22']['paid']
    shift_norm = ker['shift_norm_23_steps_2_4_8_16']['paid']
    align = ker['shift_align_39_s4']['paid']
    recip = ker['recip_n28']['paid']

    variants = {}

    def add(name, full_kernel, n_models, margin, q_base, extra_q, scope_note,
            with_recip=False):
        comp = {
            'lod_compute': lod, 'lod_uncompute': lod,
            'normalization_shift_compute': shift_norm,
            'normalization_shift_uncompute': shift_norm,
            'prep_cordic_pq_compute_uncompute': full_kernel,
            'phase_alignment_compute': align, 'phase_alignment_uncompute': align,
        }
        if with_recip:
            comp['reciprocal_compute'] = recip
            comp['reciprocal_uncompute'] = recip
        rot, eps = rot_cost(N_GENERAL, margin)
        comp['rotation_synthesis'] = rot
        comp['direct_T'] = DIRECT_T
        total = sum(comp.values())
        q = q_base + extra_q
        fixed = (2 * lod + 2 * shift_norm + 2 * align + rot + DIRECT_T)
        variants[name] = dict(
            components_C=comp, paid_C=total - rot - DIRECT_T, total_C=total,
            Q=q, score=q * total,
            score_at_62Q=62 * total, score_at_61Q=61 * total, score_at_63Q=63 * total,
            rotations=dict(general=N_GENERAL, t_rotations=1, clifford=1,
                           eps=eps, C=rot),
            numeric=dict(worst_error_over_tolerance=n_models['worst_error_over_tolerance'],
                         min_margin_turns=margin),
            gap_vs_front_plus_rotations=total - FRONT_ROT,
            factor_over_front_plus_rotations=total / FRONT_ROT,
            gap_vs_61Q_whole_circuit=total - budgets['whole_circuit_C_61Q'],
            added_C_vs_baseline=total - c0,
            added_C_over_25_8331=(total - c0) / budgets['added_C_allowed_for_61Q'],
            fixed_non_arithmetic_C=fixed,
            fixed_non_arithmetic_over_budget=fixed / FRONT_ROT,
            scope=scope_note,
        )

    # ---- variant A: dual shared-sigma CORDIC (the specified algorithm) ------
    a34 = next(r for r in num['results'] if r['mode'] == 'A_dual_shared_sigma'
               and r['G'] == 34 and r['N'] == 28)
    full_a = ker['full_compute_uncompute_N28']
    q_extra = 22 + 4 + 28 + ALIGN_BITS      # x, k, LOD ancillas, alignment destination
    add('A_dual_cordic_G34_N28', full_a['paid'], a34, a34['min_margin_turns'],
        full_a['qubits'], q_extra,
        'the specified hyperbolic-CORDIC rsqrt; measured compute+uncompute kernel')
    b_alt34 = ker['full_compute_uncompute_N28_ctrladd']
    add('A_dual_cordic_G34_N28_naive_controlled_add', b_alt34['paid'], a34,
        a34['min_margin_turns'], b_alt34['qubits'], q_extra,
        'same algorithm with iadd(control=sigma) as a true controlled add (2w+3)')

    for N in (25, 26, 27):
        r = next(x for x in num['results'] if x['mode'] == 'A_dual_shared_sigma'
                 and x['G'] == 34 and x['N'] == N)
        k = ker[f'full_compute_uncompute_N{N}']
        add(f'A_dual_cordic_G34_N{N}', k['paid'], r, r['min_margin_turns'],
            k['qubits'], q_extra, f'iteration count swept down to N={N}')

    for G in (32, 33):
        r = next(x for x in num['results'] if x['mode'] == 'A_dual_shared_sigma'
                 and x['G'] == G and x['N'] == 28)
        add(f'A_dual_cordic_G{G}_N28', full_a['paid'], r, r['min_margin_turns'],
            full_a['qubits'], q_extra,
            f'narrower grid G={G} (measured kernel is G=34; cost is a same-shape bound)')

    # ---- variant B: CORDIC vectoring + non-restoring reciprocal -------------
    b28 = next(r for r in num['variant_b'] if r['n_digits'] == 28)
    vec_full = ker['vectoring_full_compute_uncompute']
    add('B_vectoring_plus_digit_reciprocal', vec_full['paid'], b28,
        b28['min_margin_turns'], vec_full['qubits'], q_extra + 31 + 28,
        'CORDIC vectoring for sqrt(m) then a 28-digit non-restoring reciprocal',
        with_recip=True)

    out = dict(
        scope=('Constructive Q/C ledger of the hyperbolic-CORDIC reciprocal square '
               'root. Paid gates measured from complete km.CircuitBuilder kernels '
               '(37 CORDIC iterations of 4 conditional add/sub each, gate-level '
               'PREP/CORDIC/P+Q and their exact inverse), LOD and barrel shifts '
               'measured, rotation cost from the official synthesis formula. '
               'No KMB, no verifier run.'),
        baseline=dict(Q=q0, C=c0, score=score0),
        break_even=budgets,
        measured=dict(lod_paid=lod, norm_shift_paid=shift_norm, align_paid=align,
                      recip_paid=recip,
                      full_N28=full_a, vectoring_fwd=ker['vectoring_forward'],
                      dual_fwd=ker['dual_forward'],
                      step_costs={k: ker[k]['paid'] for k in
                                  ('step_i1', 'step_i14', 'step_i28')},
                      cadd_controlled={k: v['paid'] for k, v in
                                       ker['cadd_controlled_equal_width'].items()},
                      iadd={k: v['paid'] for k, v in ker['iadd_equal_width'].items()},
                      large_spotcheck_max_rel_error=max(
                          abs(r['rel_error']) for r in ker['large_spotcheck']['cases'])),
        variants=variants,
        arithmetic_free_bound=dict(
            note=('fixed scaffolding only: LOD + normalisation shift + alignment + '
                  'rotations + prep/P+Q; the 37 CORDIC iterations are set to 0'),
            C=(2 * lod + 2 * shift_norm + 2 * align + variants[
                'A_dual_cordic_G34_N28']['rotations']['C'] + DIRECT_T + 74),
        ),
    )
    out['arithmetic_free_bound']['over_budget'] = (
        out['arithmetic_free_bound']['C'] / FRONT_ROT)

    (OUT / 'ledger.json').write_text(json.dumps(out, indent=2) + '\n')

    print(f'baseline Q={q0} C={c0:.6f} score={score0:.3f}')
    print(f'front+rotations 694.840824C | whole-circuit 61Q '
          f"{budgets['whole_circuit_C_61Q']:.6f}C | added-C allowance "
          f"{budgets['added_C_allowed_for_61Q']:.6f}C")
    print(f'measured: LOD {lod}, norm shift {shift_norm}, align38 {align}, '
          f'recip28 {recip}; full N=28 {full_a["paid"]}C Q={full_a["qubits"]}')
    print(f'per-step CORDIC cost: {[ker[k]["paid"] for k in ("step_i1","step_i14","step_i28")]}'
          f'  (4 conditional add/sub of 35 paid each)')
    for k, v in variants.items():
        r = v['rotations']
        print(f'\n{k}')
        print(f'   paid+rot total {v["total_C"]:.1f}C  Q={v["Q"]}  '
              f'score {v["score"]:.0f}')
        print(f'   rotations {r["general"]} general + {r["t_rotations"]} T + '
              f'{r["clifford"]} Clifford: {r["C"]:.2f}C (eps {r["eps"]:.3e})')
        print(f'   numeric err/tol {v["numeric"]["worst_error_over_tolerance"]:.4f}, '
              f'margin {v["numeric"]["min_margin_turns"]:.4e} turns')
        print(f'   gap vs 694.840824C {v["gap_vs_front_plus_rotations"]:+.1f} '
              f'({v["factor_over_front_plus_rotations"]:.2f}x); vs 1601.652C '
              f'{v["gap_vs_61Q_whole_circuit"]:+.1f}')
        print(f'   added C vs baseline {v["added_C_vs_baseline"]:+.1f} = '
              f'{v["added_C_over_25_8331"]:.1f}x the 61Q allowance')
        print(f'   fixed scaffolding {v["fixed_non_arithmetic_C"]:.1f}C = '
              f'{v["fixed_non_arithmetic_over_budget"]:.3f}x budget')
    ab = out['arithmetic_free_bound']
    print(f'\narithmetic-free bound: {ab["C"]:.1f}C = {ab["over_budget"]:.3f}x the '
          f'694.840824C budget')


if __name__ == '__main__':
    main()
