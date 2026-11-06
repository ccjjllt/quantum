"""Q/C ledger for the direct phase-tap variants A and B.

Inputs
  artifacts/20261107_phase_tap/numeric_check.json        full-domain phase model
  artifacts/20261107_phase_tap/kernels/kernels.json      measured official-builder kernels
  artifacts/20261106_syed_v9/invsqrt/official_run.json   baseline official local result

Architecture costed here (one coefficient register at a time = the Q-cheapest
schedule; the C-cheapest schedule keeps all coefficient registers at once):

    x(22) --LOD(22 CCX)--> e(5); s = e//2, g = e&1 (free CX parities)
          --barrel shift by 21-e (5 stages, 79 CSWAP)--> N = x<<(21-e) in [2^21,2^22)
          address = (g, N_20..N_15), residual v = N_14..N_0 (15/16 bits)
          for j = degree..0:
              QROM(segments entries, 38-bit aligned target)     [init_lookup]
              barrel-shift the coefficient register by s (4 stages, 137 CSWAP)
              taps: one Z_POW per (aligned coefficient bit, monomial of v^j)
              unshift (137 CSWAP), del_lookup
          inverse x barrel shift, inverse LOD

Paid gates are CCX/CCZ/CSWAP measured with km.CircuitBuilder.  Each j>=1 tap
costs exactly one init_and CCX (del_and is measurement-based and free); a j=0
tap is a Z_POW directly on the coefficient register bit and costs no paid gate.

Nothing here is a candidate circuit: no KMB, no official verifier run.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'artifacts/20261107_phase_tap'
BASE = ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json'

# smallest absolute tap cutoff with zero tolerance failures in numeric_check.py
CUTOFF = {'A': 42, 'B': 43}


def rotation_cost(n_rot, margin_turns):
    if n_rot == 0:
        return 0.0
    eps = math.pi * margin_turns / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / 4


def monomials(degree, rbits):
    """Monomials of v^degree: (index tuple, multiplicity, sum of indices)."""
    out = []
    if degree == 0:
        return [((), 1, 0)]

    def rec(start, depth, chosen):
        if depth == degree:
            counts = {}
            for i in chosen:
                counts[i] = counts.get(i, 0) + 1
            mult = math.factorial(degree)
            for c in counts.values():
                mult //= math.factorial(c)
            out.append((tuple(chosen), mult, sum(chosen)))
            return
        for i in range(start, rbits + 1):
            rec(i, depth + 1, chosen + [i])

    rec(1, 0, [])
    return out


def used_monomials(degree, rbits, stored, cutoff):
    """Distinct index-sets that carry at least one kept tap, with AND cost.

    A kept tap needs a coefficient bit b in [lo_j, 28] and an aligned position
    p = b + s (s = 0..10) with mult*2^-cutoff <= 2^-(p+k), i.e.
    mult*2^cutoff >= 2^(p+k).  The cheapest such p is p = lo_j (s = 0).
    """
    used = {}
    for j in range(1, degree + 1):
        lo = stored[j][0]
        for (idx, mult, k) in monomials(j, rbits):
            if mult * (1 << cutoff) >= (1 << (lo + k)):
                key = tuple(sorted(set(idx)))
                used[key] = len(key) - 1          # 0, 1 or 2 CCX to build the monomial
    return used


def main():
    num = json.loads((ART / 'numeric_check.json').read_text())
    ker = json.loads((ART / 'kernels' / 'kernels.json').read_text())
    base = json.loads(BASE.read_text())['official_result']
    score0, q0, c0 = base['score'], base['num_qubits'], base['toffoli_equivalent']

    qrom_paid = {(r['entries']): r['paid'] for r in ker['qrom']}
    tap_paid = ker['taps'][0]['paid']                       # 1 CCX per j>=1 tap
    lod_paid = ker['lod']['paid']
    shift22 = next(r['paid'] for r in ker['shifts'] if r['bits'] == 22)
    shift38 = next(r['paid'] for r in ker['shifts'] if r['bits'] == 38)

    front_rot = 694.840824
    rot_c0 = base['rotation_count'] * (0.56 * math.log2(1 / base['rotation_eps']) + 5.3) / 4
    budgets = {
        'front_plus_rotations_C': front_rot,
        'front_plus_rotations_at_61Q_C': front_rot + c0 / 61,
        'front_plus_rotations_at_63Q_C': front_rot - c0 / 63,
        'whole_circuit_62Q_C': score0 / 62,
        'whole_circuit_61Q_C': score0 / 61,
        'whole_circuit_63Q_C': score0 / 63,
        'added_C_allowed_for_61Q': c0 / 61,
    }

    out = dict(
        scope=('Constructive Q/C ledger of the direct phase-tap variants; paid gates from '
               'km.CircuitBuilder kernels, rotation cost from the official synthesis formula; '
               'no KMB and no official verification'),
        baseline=dict(Q=q0, C=c0, score=score0, rotation_C=rot_c0),
        break_even=budgets, variants={})

    for name in ('A', 'B'):
        v = num['variants'][name]
        cutoff = CUTOFF[name]
        census = v['tap_census'][str(cutoff)]
        numeric = v['numeric'][str(cutoff)]
        degree = v['degree']
        segments = v['segments']
        n_coeff = degree + 1
        rbits = 22 - int(math.log2(segments))
        stored = [tuple(x) for x in v['tables']['stored_bit_ranges']]
        n_rot = census['rotation']
        margin = numeric['min_margin_turns']
        rot_c = rotation_cost(n_rot, margin)
        t_per_rot = 0.56 * math.log2(n_rot / (math.pi * margin)) + 5.3

        used = used_monomials(degree, rbits, stored, cutoff)
        monomial_ccx = sum(used.values())
        n_pair = sum(1 for k in used if len(k) == 2)
        n_triple = sum(1 for k in used if len(k) == 3)
        taps_ccx = sum(c for j, c in census['by_degree'].items() if int(j) >= 1) * tap_paid

        def schedule(all_regs):
            if all_regs:
                qrom_calls = 1
                coeff_bits = n_coeff * 38
                q = 22 + 5 + coeff_bits + int(math.log2(segments))
            else:
                qrom_calls = n_coeff
                coeff_bits = 38
                anc = 3 if degree == 3 else 2
                q = max(22 + 5 + 38 + int(math.log2(segments)), 22 + 5 + 38 + anc)
            comp = {
                'lod_compute': lod_paid,
                'lod_uncompute': lod_paid,
                'x_barrel_shift_compute': shift22,
                'x_barrel_shift_uncompute': shift22,
                'coefficient_qrom_compute_and_uncompute': qrom_calls * qrom_paid[segments],
                'coefficient_align_shift_compute': n_coeff * shift38,
                'coefficient_align_shift_uncompute': n_coeff * shift38,
                'monomial_and_ccx': monomial_ccx,
                'tap_control_ccx': taps_ccx,
                'direct_T_C': 0.25 * census['t'],
                'rotation_synthesis_C': rot_c,
            }
            total = sum(comp.values())
            return dict(Q=q, components_C=comp, total_C=total, score=q * total,
                        score_at_62Q=62 * total, score_at_61Q=61 * total,
                        score_at_63Q=63 * total)

        out['variants'][name] = dict(
            segments=segments, degree=degree, cutoff=cutoff,
            numeric=dict(worst_error_over_tolerance=numeric['worst_error_over_tolerance'],
                         min_margin_turns=margin, worst_x=numeric['worst_x']),
            taps=dict(total=census['taps'], by_degree=census['by_degree'],
                      clifford=census['clifford'], t=census['t'],
                      rotations=n_rot, taps_needing_ccx=taps_ccx,
                      distinct_pairs=n_pair, distinct_triples=n_triple,
                      monomial_and_ccx=monomial_ccx),
            rotations=dict(count=n_rot, eps=math.pi * margin / n_rot,
                           t_per_rotation=t_per_rot, C=rot_c,
                           fraction_of_total_C=None),
            schedule_q_min=schedule(False),
            schedule_c_min=schedule(True),
        )

    for name, v in out['variants'].items():
        for key in ('schedule_q_min', 'schedule_c_min'):
            s = v[key]
            s['paid_gates'] = sum(x for k, x in s['components_C'].items()
                                  if k not in ('rotation_synthesis_C', 'direct_T_C'))
            s['gap_vs_front_plus_rotations_C'] = s['total_C'] - front_rot
            s['factor_over_front_plus_rotations'] = s['total_C'] / front_rot
            s['gap_vs_61Q_whole_circuit_C'] = s['total_C'] - budgets['whole_circuit_61Q_C']
        v['rotations']['fraction_of_total_C'] = (
            v['rotations']['C'] / v['schedule_q_min']['total_C'])
        # cutoff sensitivity: same architecture, every cutoff the numeric scan ran
        sens = []
        raw = num['variants'][name]
        for key, numrow in raw['numeric'].items():
            cut = numrow['cutoff']
            cen = raw['tap_census'][key]
            rot = (rotation_cost(cen['rotation'], numrow['min_margin_turns'])
                   if numrow['min_margin_turns'] > 0 else None)
            taps_ccx = sum(c for j, c in cen['by_degree'].items() if int(j) >= 1)
            fixed = (2 * lod_paid + 2 * shift22 + (v['degree'] + 1) * qrom_paid[v['segments']]
                     + 2 * (v['degree'] + 1) * shift38 + v['taps']['monomial_and_ccx'])
            total = fixed + taps_ccx + 0.25 * cen['t'] + (rot if rot is not None else 0.0)
            sens.append(dict(cutoff=cut, rotations=cen['rotation'], taps=cen['taps'],
                             tolerance_failures=numrow['tolerance_failures'],
                             worst_error_over_tolerance=numrow['worst_error_over_tolerance'],
                             min_margin_turns=numrow['min_margin_turns'],
                             rotation_C=rot, total_C=total,
                             passes=numrow['tolerance_failures'] == 0))
        v['cutoff_sensitivity_q_min'] = sens

    # how many fine rotations would fit inside the whole front+rotation budget
    for v in out['variants'].values():
        m = v['numeric']['min_margin_turns']
        lo, hi = 1, 20000
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if rotation_cost(mid, m) <= front_rot:
                lo = mid
            else:
                hi = mid - 1
        v['rotations']['max_rotations_inside_694_84C'] = lo

    (ART / 'ledger.json').write_text(json.dumps(out, indent=2) + '\n')

    print(f"baseline Q={q0} C={c0:.6f} score={score0:.3f}")
    print(f"front+rotations 694.840824C; whole-circuit 61Q budget "
          f"{budgets['whole_circuit_61Q_C']:.6f}C; allowed added C {c0/61:.6f}")
    for name, v in out['variants'].items():
        print(f"\nVariant {name}: {v['segments']} segments, degree {v['degree']}, "
              f"cutoff 2^-{v['cutoff']}")
        print(f"  numeric worst err/tol {v['numeric']['worst_error_over_tolerance']:.4f}, "
              f"margin {v['numeric']['min_margin_turns']:.4e} turns")
        t = v['taps']
        print(f"  taps {t['total']} (rotations {t['rotations']}, T {t['t']}, "
              f"clifford {t['clifford']}); by degree {t['by_degree']}; "
              f"pairs {t['distinct_pairs']}, triples {t['distinct_triples']}, "
              f"monomial CCX {t['monomial_and_ccx']}")
        r = v['rotations']
        print(f"  rotation eps {r['eps']:.3e}, {r['t_per_rotation']:.3f} T/rot, "
              f"{r['count']} rotations = {r['C']:.1f}C "
              f"({100*r['fraction_of_total_C']:.1f}% of total)")
        print(f"  rotations that would fit in 694.84C at this margin: "
              f"{r['max_rotations_inside_694_84C']}")
        for key in ('schedule_q_min', 'schedule_c_min'):
            s = v[key]
            print(f"  [{key}] Q={s['Q']} paid={s['paid_gates']:.1f} T_C=0.25*{t['t']} "
                  f"rotC={r['C']:.1f} totalC={s['total_C']:.1f}")
            print(f"      score: actual {s['score']:.0f} | 62Q {s['score_at_62Q']:.0f} | "
                  f"61Q {s['score_at_61Q']:.0f} | 63Q {s['score_at_63Q']:.0f}")
            print(f"      gap vs 694.84C {s['gap_vs_front_plus_rotations_C']:+.1f} "
                  f"({s['factor_over_front_plus_rotations']:.1f}x); "
                  f"gap vs 61Q whole-circuit {s['gap_vs_61Q_whole_circuit_C']:+.1f}C")


if __name__ == '__main__':
    main()
