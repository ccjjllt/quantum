"""Q/C ledger for the non-restoring digit-recurrence invsqrt.

Inputs (all produced by the other scripts in this directory):
  artifacts/20261107_digit_recurrence/numeric/numeric_check.json   full-domain integer model
  artifacts/20261107_digit_recurrence/kernels/kernels.json        measured paid gates
  artifacts/20261106_syed_v9/invsqrt/official_run.json            baseline official result

Everything paid is CCX+CCZ+CSWAP.  Rotation synthesis uses the official
formula 0.56*log2(1/eps)+5.3 T per general Z_POW, eps = pi*margin/n_rot,
T/4 in C.  Nothing here is a candidate circuit: no KMB, no verifier run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NUM = ROOT / 'artifacts/20261107_digit_recurrence/numeric/numeric_check.json'
KER = ROOT / 'artifacts/20261107_digit_recurrence/kernels/kernels.json'
BASE = ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json'
OUT = ROOT / 'artifacts/20261107_digit_recurrence'


def rot_cost(n_rot, margin):
    if n_rot == 0:
        return 0.0
    eps = math.pi * margin / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / 4


def t_per_rot(n_rot, margin):
    return 0.56 * math.log2(n_rot / (math.pi * margin)) + 5.3


def main():
    num = {r['n']: r for r in json.loads(NUM.read_text())['results']}
    ker = json.loads(KER.read_text())
    base = json.loads(BASE.read_text())['official_result']
    q0, c0, score0 = base['num_qubits'], base['toffoli_equivalent'], base['score']

    lod = ker['lod_22']['paid']
    shift_norm = ker['shift_norm_23_steps_2_4_8_16']['paid']
    sqrt = {n: ker[f'sqrt_kernel_n{n}']['paid'] for n in (26, 27, 28)}
    recip = {n: ker[f'recip_kernel_n{n}']['paid'] for n in (26, 27, 28)}
    shift_align = {36: ker['shift_align_36_s4']['paid'],
                   37: ker['shift_align_37_s4']['paid'],
                   38: ker['shift_align_38_s4']['paid']}

    front_rot = 694.840824
    budgets = {
        'front_plus_rotations_C_62Q': front_rot,
        'front_plus_rotations_C_61Q': front_rot + c0 / 61,
        'front_plus_rotations_C_63Q': front_rot - c0 / 63,
        'whole_circuit_C_62Q': score0 / 62,
        'whole_circuit_C_61Q': score0 / 61,
        'whole_circuit_C_63Q': score0 / 63,
        'added_C_allowed_for_61Q': c0 / 61,
    }

    out = dict(
        scope=('Constructive Q/C ledger of the radix-2 non-restoring digit-recurrence '
               'invsqrt. Paid gates from complete km.CircuitBuilder kernels (sqrt and '
               'reciprocal recurrences built gate by gate), LOD/barrel shifts measured, '
               'rotation cost from the official synthesis formula. No KMB, no verifier.'),
        baseline=dict(Q=q0, C=c0, score=score0),
        break_even=budgets,
        measured=dict(lod_paid=lod, n_shift_paid=shift_norm,
                      sqrt_paid=sqrt, recip_paid=recip, align_paid=shift_align),
        variants={},
    )

    for n in (26, 27, 28):
        r = num[n]
        margin = r['min_margin_turns']
        align_bits = n + 10
        align = shift_align.get(align_bits)
        if align is None:                      # 37-bit alignment not measured; interpolate
            align = shift_align[36] + (align_bits - 36) * 4
        n_rot = align_bits
        rot = rot_cost(n_rot, margin)
        comp = {
            'lod_compute': lod, 'lod_uncompute': lod,
            'normalization_shift_compute': shift_norm, 'normalization_shift_uncompute': shift_norm,
            'sqrt_compute': sqrt[n], 'sqrt_uncompute': sqrt[n],
            'reciprocal_compute': recip[n], 'reciprocal_uncompute': recip[n],
            'phase_alignment_compute': align, 'phase_alignment_uncompute': align,
            'rotation_synthesis': rot,
            'direct_T': 0.25,
        }
        total = sum(comp.values())
        q = 22 + 4 + (33 + 1) + n + (n + 4) + align_bits + 3
        comp_paid = sum(v for k, v in comp.items()
                        if k not in ('rotation_synthesis', 'direct_T'))
        fixed = (2 * lod + 2 * shift_norm + 2 * align + rot + 0.25)
        out['variants'][f'radix2_n{n}'] = dict(
            n=n, components_C=comp, paid_C=comp_paid, rotation_C=rot,
            total_C=total, Q_qmin=q, score_qmin=q * total,
            score_at_62Q=62 * total, score_at_61Q=61 * total, score_at_63Q=63 * total,
            rotations=dict(count=n_rot, eps=math.pi * margin / n_rot,
                           t_per_rotation=t_per_rot(n_rot, margin), C=rot),
            numeric=dict(worst_error_over_tolerance=r['worst_error_over_tolerance'],
                         min_margin_turns=margin, worst_x=r['worst_x']),
            gap_vs_front_plus_rotations=total - front_rot,
            factor_over_front_plus_rotations=total / front_rot,
            gap_vs_61Q_whole_circuit=total - budgets['whole_circuit_C_61Q'],
            added_C_vs_baseline=total - c0,
            added_C_over_25_8331=(total - c0) / budgets['added_C_allowed_for_61Q'],
            fixed_non_arithmetic_C=fixed,
            fixed_non_arithmetic_over_budget=fixed / front_rot,
        )

    # ---- radix-4 constructive count (30-bit, 15 digits) ---------------------
    # No radix-4 circuit is built or numerically verified; the count uses the
    # measured 30-bit primitives.  Two selection models bracket the cost.
    w = 30
    add30 = ker['primitives']['iadd_equal_width']['30']['paid']       # 29
    cmp30 = ker['primitives']['compare_qq']['30']['paid']            # 30
    qrom32 = next(r['paid'] for r in ker['qrom'] if r['entries'] == 32 and r['out_bits'] == 3)
    iters = 15
    sel_verified = 2 * cmp30 + add30 + 4          # +/-s/2, +/-3s/2, 3s/2 add, digit bits
    sel_qrom = qrom32                              # 5-bit address -> 3-bit digit lookup
    operand_shift = 30                             # conditional x2 shift (CSWAP)
    per_iter = {
        'verified_thresholds': sel_verified + operand_shift + add30,
        'qrom_lookup': sel_qrom + operand_shift + add30,
    }
    n28 = out['variants']['radix2_n28']
    r4 = {}
    for name, pi in per_iter.items():
        arith = 4 * iters * pi                     # sqrt fwd/inv + recip fwd/inv
        total = arith + n28['fixed_non_arithmetic_C']
        q = 22 + 4 + (35 + 1) + 30 + (33 + 1) + 40 + 3
        r4[name] = dict(per_iteration=pi, arithmetic_C=arith, fixed_C=n28['fixed_non_arithmetic_C'],
                        total_C=total, Q_qmin=q, score_qmin=q * total,
                        gap_vs_front_plus_rotations=total - front_rot,
                        factor_over_front_plus_rotations=total / front_rot,
                        gap_vs_61Q_whole_circuit=total - budgets['whole_circuit_C_61Q'],
                        added_C_vs_baseline=total - c0)
    out['radix4_constructive'] = dict(
        scope=('constructive count only: no radix-4 circuit built, no radix-4 numeric scan; '
               'uses measured 30-bit add/compare primitives'),
        digits=iters, bits=30, add30=add30, compare30=cmp30, qrom32=qrom32,
        selection_models=r4)

    # ---- 28-rotation hypothetical (if the 2^-k alignment were free) ---------
    v28 = out['variants']['radix2_n28']
    per_rot = v28['rotation_C'] / v28['rotations']['count']
    out['hypothetical_28_rotations_no_alignment_C'] = (
        v28['total_C'] - 2 * shift_align[38] - 10 * per_rot)
    out['hypothetical_zero_arithmetic_C'] = v28['fixed_non_arithmetic_C']

    (OUT / 'ledger.json').write_text(json.dumps(out, indent=2) + '\n')

    print(f"baseline Q={q0} C={c0:.6f} score={score0:.3f}")
    print(f"front+rotations 694.840824C | whole-circuit 61Q {budgets['whole_circuit_C_61Q']:.6f}C"
          f" | added-C allowance {budgets['added_C_allowed_for_61Q']:.6f}C")
    print(f"measured: LOD {lod}, norm shift {shift_norm}, align36/38 "
          f"{shift_align[36]}/{shift_align[38]}, sqrt {sqrt}, recip {recip}")
    for k, v in out['variants'].items():
        print(f"\n{k}: n={v['n']} Q={v['Q_qmin']} paid={v['paid_C']:.1f} "
              f"rot={v['rotation_C']:.2f} ({v['rotations']['count']} @ "
              f"{v['rotations']['t_per_rotation']:.2f} T) total={v['total_C']:.1f}C")
        print(f"   numeric err/tol {v['numeric']['worst_error_over_tolerance']:.4f}, "
              f"margin {v['numeric']['min_margin_turns']:.4e}")
        print(f"   score: qmin {v['score_qmin']:.0f} | 62Q {v['score_at_62Q']:.0f} | "
              f"61Q {v['score_at_61Q']:.0f} | 63Q {v['score_at_63Q']:.0f}")
        print(f"   gap vs 694.84C {v['gap_vs_front_plus_rotations']:+.1f} "
              f"({v['factor_over_front_plus_rotations']:.2f}x); vs 1601.652C "
              f"{v['gap_vs_61Q_whole_circuit']:+.1f}; added vs baseline "
              f"{v['added_C_vs_baseline']:+.1f} = {v['added_C_over_25_8331']:.1f}x allowance")
        print(f"   fixed non-arithmetic (LOD+shifts+alignment+rotations) "
              f"{v['fixed_non_arithmetic_C']:.1f}C = {v['fixed_non_arithmetic_over_budget']:.2f}x budget")
    print("\nradix-4 constructive:")
    for k, v in out['radix4_constructive']['selection_models'].items():
        print(f"   {k}: {v['per_iteration']}/iter, arith {v['arithmetic_C']}, "
              f"total {v['total_C']:.1f}C, Q={v['Q_qmin']}, "
              f"{v['factor_over_front_plus_rotations']:.2f}x budget")
    print(f"\n28-rotation hypothetical (free alignment): "
          f"{out['hypothetical_28_rotations_no_alignment_C']:.1f}C")
    print(f"zero-arithmetic fixed cost: {out['hypothetical_zero_arithmetic_C']:.1f}C "
          f"({out['hypothetical_zero_arithmetic_C']/front_rot:.2f}x budget)")


if __name__ == '__main__':
    main()
