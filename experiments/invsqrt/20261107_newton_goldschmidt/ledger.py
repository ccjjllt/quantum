"""Complete Q/C ledger for a table-initialized Newton / Goldschmidt rsqrt.

Inputs
  artifacts/20261107_newton_goldschmidt/numeric/numeric_check.json   full-domain model
  artifacts/20261107_newton_goldschmidt/kernels/kernels.json        measured paid gates
  artifacts/20261106_syed_v9/invsqrt/official_run.json              baseline official result

Paid is CCX+CCZ+CSWAP.  General Z_POW rotations are priced with the official
mixed-fallback formula 0.56 log2(1/eps) + 5.3 T with eps = pi*margin/n_rot, T/4
in C.  The 38 phase positions are 1 Clifford (2^-1), 1 T (2^-4) and 36 general
rotations (2^-3, 2^-5 .. 2^-38), priced exactly as the verifier's
`num_z_pow(min_clifford_hierarchy_level=4)` / `num_t_like` split.

Nothing here is a candidate circuit: no KMB, no verifier run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NUM = ROOT / 'artifacts/20261107_newton_goldschmidt/numeric/numeric_check.json'
KER = ROOT / 'artifacts/20261107_newton_goldschmidt/kernels/kernels.json'
BASE = ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json'
OUT = ROOT / 'artifacts/20261107_newton_goldschmidt'

FRONT_ROT = 694.840824          # baseline front + both rotation clusters (62Q)
T_PER_TOFFOLI = 4.0


def rot_cost(n_rot, margin_turns):
    if n_rot == 0:
        return 0.0
    eps = math.pi * margin_turns / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / T_PER_TOFFOLI


def t_per_rot(n_rot, margin_turns):
    return 0.56 * math.log2(n_rot / (math.pi * margin_turns)) + 5.3


def main():
    num = {r['name']: r for r in json.loads(NUM.read_text())['results']}
    ker = json.loads(KER.read_text())
    base = json.loads(BASE.read_text())['official_result']
    q0, c0, score0 = base['num_qubits'], base['toffoli_equivalent'], base['score']

    lod = ker['lod_22']['paid']
    shift_norm = ker['shift_norm_23_steps_2_4_8_16']['paid']
    align38 = ker['shift_align_38_s4']['paid']
    qrom256 = next(r['paid'] for r in ker['qrom'] if r['entries'] == 256 and r['out_bits'] == 30)
    qrom1024 = next(r['paid'] for r in ker['qrom'] if r['entries'] == 1024 and r['out_bits'] == 30)
    fwd = {'A': ker['forward_kernel_A']['paid'], 'B': ker['forward_kernel_B']['paid']}
    muls = {r['label']: r['paid'] for r in ker['mul']}

    budgets = {
        'front_plus_rotations_C_62Q': FRONT_ROT,
        'front_plus_rotations_C_61Q': FRONT_ROT + c0 / 61,
        'front_plus_rotations_C_63Q': FRONT_ROT - c0 / 63,
        'whole_circuit_C_62Q': score0 / 62,
        'whole_circuit_C_61Q': score0 / 61,
        'whole_circuit_C_63Q': score0 / 63,
        'added_C_allowed_for_61Q': c0 / 61,
        'added_C_allowed_for_63Q': c0 / 63,
    }

    # Q-min schedule: (register, bits, first stage, last stage).  Stages are
    # 0 LOD, 1 normalise, 2 QROM, 3..7 the five multiplies (with their isub),
    # 8 phase alignment, 9 rotations.  This is a scheduling count, not a built
    # circuit: the builder in kernels.py never frees, so its num_qubits is only
    # an upper bound.
    q_A = [
        ('x', 22, 0, 9), ('lod_flags', 23, 0, 1), ('e_k', 5, 0, 8),
        ('R_m', 23, 1, 6), ('y0sq', 29, 2, 3), ('y0_15', 29, 2, 4), ('y0_28', 29, 2, 4),
        ('tmp1_u1', 50, 3, 4), ('tmp2', 57, 4, 4), ('y1', 29, 4, 9),
        ('y1c', 29, 5, 5), ('tmp3_sq', 57, 5, 6), ('tmp4_u2', 50, 6, 7),
        ('tmp5', 57, 7, 7), ('y2', 29, 7, 9), ('aligned_38', 38, 8, 9),
        ('rot_ancilla', 4, 9, 9),
    ]
    q_B = [
        ('x', 22, 0, 9), ('lod_flags', 23, 0, 1), ('e_k', 5, 0, 8),
        ('R_m', 23, 1, 6), ('y0sq', 17, 2, 3), ('y0_15', 15, 2, 4), ('y0_14', 15, 2, 4),
        ('tmp1_u1', 36, 3, 4), ('tmp2', 30, 4, 4), ('y1', 15, 4, 9),
        ('y1c', 15, 5, 5), ('tmp3_sq', 29, 5, 6), ('sq25', 26, 6, 6),
        ('tmp4_u2', 47, 6, 7), ('y1_28', 29, 7, 9), ('tmp5', 58, 7, 7),
        ('y2', 29, 7, 9), ('aligned_38', 38, 8, 9), ('rot_ancilla', 4, 9, 9),
    ]

    def q_peak(sched):
        peaks = {}
        for st in range(10):
            peaks[st] = sum(b for _, b, a, z in sched if a <= st <= z)
        st = max(peaks, key=peaks.get)
        return peaks[st], st, peaks

    designs = {
        'A_uniform28': dict(
            numeric='newton2_E256_B12_W30', qrom=qrom256,
            fwd=fwd['A'], n_rot=36, n_t=1, sched=q_A,
            mul_labels=['A_m1_u1', 'A_m2_y0u1', 'A_m3_y1sq', 'A_m4_u2', 'A_m5_y1u2'],
            note='uniform 28-fractional-bit working precision'),
        'B_reduced': dict(
            numeric='newton2_E256_B10_W28_iter1_16_14', qrom=qrom256,
            fwd=fwd['B'], n_rot=36, n_t=1, sched=q_B,
            mul_labels=['B_m1_u1', 'B_m2_y0u1', 'B_m3_y1sq', 'B_m4_u2', 'B_m5_y1u2'],
            note='iteration 1 at 14 bits, iteration 2 at 24/28 bits'),
    }

    out = dict(
        scope=('Constructive Q/C ledger of a table-initialized Newton reciprocal square '
               'root: full-domain integer numeric model, gate-by-gate counted forward '
               'kernels, measured primitives, official rotation synthesis formula. '
               'No KMB, no verifier run, no phase validation.'),
        baseline=dict(Q=q0, C=c0, score=score0),
        break_even=budgets,
        measured=dict(lod_paid=lod, norm_shift_paid=shift_norm, align38_paid=align38,
                      qrom256_paid=qrom256, qrom1024_paid=qrom1024,
                      forward_kernel_A=fwd['A'], forward_kernel_B=fwd['B'],
                      multiplies=muls),
        designs={},
        goldschmidt=dict(
            numeric_e16=num['goldschmidt2_E256_B12_e16']['worst_error_over_tolerance'],
            numeric_e16_failures=num['goldschmidt2_E256_B12_e16']['tolerance_failures'],
            numeric_e30=num['goldschmidt2_E256_B12_e30']['worst_error_over_tolerance'],
            numeric_e30_failures=num['goldschmidt2_E256_B12_e30']['tolerance_failures'],
            extra_iteration_gain='none (2 and 3 iterations give identical results)',
            multiply_count=5,
            verdict=('Goldschmidt needs the same five multiplies as Newton and needs the '
                     'same 30-bit precision on e (a 16-bit e fails by 144x tolerance), '
                     'so it has no cost advantage; its only saving is two cheap '
                     'additions, at the price of a linear error term.'),
        ),
        floor_argument={},
    )

    for name, d in designs.items():
        r = num[d['numeric']]
        q, q_stage, q_peaks = q_peak(d['sched'])
        margin = r['min_margin_turns']
        rot = rot_cost(d['n_rot'], margin)
        t_rot = t_per_rot(d['n_rot'], margin)
        comp = {
            'lod_compute': lod, 'lod_uncompute': lod,
            'normalization_shift_compute': shift_norm,
            'normalization_shift_uncompute': shift_norm,
            'qrom_256_init_plus_del': d['qrom'],
            'newton_forward': d['fwd'],
            'newton_inverse': d['fwd'],
            'phase_alignment_38_compute': align38,
            'phase_alignment_38_uncompute': align38,
            'general_rotations': rot,
            't_gates': 0.25 * d['n_t'],
        }
        total = sum(comp.values())
        mul_total = sum(muls[k] for k in d['mul_labels'])
        paid = sum(v for k, v in comp.items() if k not in ('general_rotations', 't_gates'))
        out['designs'][name] = dict(
            note=d['note'],
            Q_qmin=q, Q_peak_stage=q_stage, Q_peaks_by_stage=q_peaks,
            numeric=dict(worst_error_over_tolerance=r['worst_error_over_tolerance'],
                         min_margin_turns=margin, worst_x=r['worst_x'],
                         tolerance_failures=r['tolerance_failures']),
            components_C=comp,
            total_C=total,
            paid_C=paid,
            rotation_C=rot,
            rotations=dict(count=d['n_rot'], t_gates=d['n_t'], eps=math.pi * margin / d['n_rot'],
                           t_per_rotation=t_rot),
            score_qmin=q * total,
            score_at_61Q=61 * total,
            score_at_62Q=62 * total,
            score_at_63Q=63 * total,
            gap_vs_front_plus_rotations=total - FRONT_ROT,
            factor_over_front_plus_rotations=total / FRONT_ROT,
            gap_vs_61Q_whole_circuit=total - budgets['whole_circuit_C_61Q'],
            factor_over_61Q_whole_circuit=total / budgets['whole_circuit_C_61Q'],
            added_C_vs_baseline=total - c0,
            added_C_over_25_8331=(total - c0) / budgets['added_C_allowed_for_61Q'],
            multiply_total_C=2 * mul_total,
            multiply_share_of_arithmetic=2 * mul_total / (2 * d['fwd']),
            multiply_share_of_total=2 * mul_total / total,
        )

    # ---- floor: the last Newton multiply alone ------------------------------
    last = muls['floor_y1u2_min']
    out['floor_argument'] = dict(
        statement=('The second Newton iteration cannot avoid y1*u2/2 with y1 at the '
                   'final 28-bit precision.  With 11 multiplier bits (the fewest that '
                   'still leave a 2^-26 absolute correction) and a 29-bit accumulator '
                   'this single truncated multiply costs the measured value below, '
                   'forward and again for the exact inverse.'),
        one_last_multiply_forward_C=last,
        one_last_multiply_compute_plus_uncompute_C=2 * last,
        times_front_plus_rotations=2 * last / FRONT_ROT,
        times_61Q_whole_circuit=2 * last / budgets['whole_circuit_C_61Q'],
        full_29x29_forward_C=muls['A_m3_y1sq'],
        full_29x29_compute_plus_uncompute_C=2 * muls['A_m3_y1sq'],
        full_29x29_times_front_plus_rotations=2 * muls['A_m3_y1sq'] / FRONT_ROT,
        ratio_vs_25_8331=2 * last / budgets['added_C_allowed_for_61Q'],
    )

    (OUT / 'ledger.json').write_text(json.dumps(out, indent=2) + '\n')

    print(f"baseline Q={q0} C={c0:.6f} score={score0:.3f}")
    print(f"front+rotations 694.840824C | whole 61Q {budgets['whole_circuit_C_61Q']:.6f}C"
          f" | added-C allowance {budgets['added_C_allowed_for_61Q']:.6f}C")
    print(f"measured: LOD {lod}, norm shift {shift_norm}, align38 {align38}, "
          f"QROM256 {qrom256}, QROM1024 {qrom1024}, fwdA {fwd['A']}, fwdB {fwd['B']}")
    print()
    for name, v in out['designs'].items():
        print(f"{name}: Q~{v['Q_qmin']} (stage {v['Q_peak_stage']}) total={v['total_C']:.2f}C "
              f"(paid {v['paid_C']:.1f} + rot {v['rotation_C']:.2f})")
        for k, c in v['components_C'].items():
            print(f"    {k:34s} {c:10.2f}")
        print(f"    numeric err/tol {v['numeric']['worst_error_over_tolerance']:.4f}, "
              f"margin {v['numeric']['min_margin_turns']:.4e} turns")
        print(f"    score: qmin {v['score_qmin']:.0f} | 61Q {v['score_at_61Q']:.0f}")
        print(f"    gap vs 694.84C {v['gap_vs_front_plus_rotations']:+.1f} "
              f"({v['factor_over_front_plus_rotations']:.2f}x); vs 1601.652C "
              f"{v['gap_vs_61Q_whole_circuit']:+.1f} "
              f"({v['factor_over_61Q_whole_circuit']:.2f}x)")
        print(f"    added vs baseline {v['added_C_vs_baseline']:+.1f} = "
              f"{v['added_C_over_25_8331']:.1f}x the 25.8331C allowance")
        print(f"    multiplication share of arithmetic "
              f"{100*v['multiply_share_of_arithmetic']:.1f}%, of total "
              f"{100*v['multiply_share_of_total']:.1f}%")
        print()
    f = out['floor_argument']
    print(f"floor: one last 29x11 multiply {f['one_last_multiply_forward_C']}C forward, "
          f"{f['one_last_multiply_compute_plus_uncompute_C']}C both ways = "
          f"{f['times_front_plus_rotations']:.2f}x front+rotations, "
          f"{f['times_61Q_whole_circuit']:.2f}x the 61Q whole-circuit budget")
    print(f"       full 29x29 multiply {f['full_29x29_forward_C']}C forward, "
          f"{f['full_29x29_compute_plus_uncompute_C']}C both ways = "
          f"{f['full_29x29_times_front_plus_rotations']:.2f}x front+rotations")
    print()
    print('goldschmidt:', out['goldschmidt']['verdict'])


if __name__ == '__main__':
    main()
