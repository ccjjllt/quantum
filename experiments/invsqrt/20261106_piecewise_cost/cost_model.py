"""Resource ledger and break-even analysis for a dyadic piecewise phase circuit.

Inputs
  - artifacts/20261106_piecewise_cost/numeric/results.json   (full-domain numeric scan)
  - artifacts/20261106_piecewise_cost/kernels/kernels.json   (measured official-builder kernels)
  - artifacts/20261106_syed_v9/invsqrt/official_run.json     (baseline official local result)

Everything is a cost model.  No circuit is generated, no phase is verified.
Paid gates are CCX/CCZ/CSWAP; rotations are priced with the official formula
0.56*log2(1/eps)+5.3 T per rotation, eps = pi*min_margin/n_rot.

Architecture assumed for the ledger (all reversible, measurement-based uncompute
only where the official builder provably does it):
    x (22) -> normalize (leading-one detector + barrel shift)
           -> (d+1) coefficient QROM loads indexed by (octave, 4 mantissa bits)
           -> degree-d truncated Horner in w fractional bits on r residual bits
           -> barrel-shift the phase by floor(log2 x / 2)   [4 stages]
           -> one Z_POW per phase bit
           -> exact inverse of the arithmetic, then del_lookup
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NUM = ROOT / 'artifacts/20261106_piecewise_cost/numeric/results.json'
KER = ROOT / 'artifacts/20261106_piecewise_cost/kernels/kernels.json'
BASE = ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json'
OUT = ROOT / 'artifacts/20261106_piecewise_cost/cost_model.json'


def rotation_cost(n_rot, margin_turns):
    if n_rot == 0:
        return 0.0
    eps = math.pi * margin_turns / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / 4


def horner_cost(d, w, r):
    """Nearest measured (degree, acc bits, residual bits) uniform-width Horner."""
    rows = json.loads(KER.read_text())['horner']
    best = None
    for row in rows.values():
        key = (row['degree'], row['acc_bits'], row['u_bits'])
        dist = abs(key[0] - d) * 1000 + abs(key[1] - w) * 10 + abs(key[2] - r)
        if best is None or dist < best[0]:
            best = (dist, row)
    return best[1]


def term_widths(cfg):
    """Per-term register widths from the measured coefficient magnitudes."""
    w = cfg['coefficient_fraction_bits']
    widths = [w + math.floor(math.log2(m)) + 1 for m in cfg['max_abs_coefficients']]
    return [max(1, v) for v in widths]


def horner_scaled_cost(widths, u_bits):
    """Nearest measured scaled-width Horner (degree, width profile, residual)."""
    rows = json.loads(KER.read_text())['horner_scaled']
    best = None
    for row in rows.values():
        if row['degree'] != len(widths) - 1 or row['u_bits'] != u_bits:
            continue
        dist = sum(abs(a - b) for a, b in zip(row['widths'], widths))
        if best is None or dist < best[0]:
            best = (dist, row)
    return None if best is None else best[1]


def qrom_cost(entries):
    rows = [r for r in json.loads(KER.read_text())['qrom'] if r['output_bits'] == 28]
    for r in rows:
        if r['entries'] == entries:
            return r['paid']
    raise KeyError(entries)


def barrel_shift_cost(width, stages):
    return sum(max(0, width - (1 << s)) for s in range(stages))


def ledger(cfg, kernel_q_extra=49):
    d = cfg['degree']
    s = cfg['segments']
    w = cfg['coefficient_fraction_bits']
    r = max(cfg['residual_bits_group0'], cfg['residual_bits_group1'])
    margin = cfg['min_margin_turns']

    widths = term_widths(cfg)
    scaled = horner_scaled_cost(widths, r)
    uniform = horner_cost(d, w, r)
    horner = scaled if scaled is not None else uniform
    horner_fwd = horner['paid']
    norm_fwd = 22 + barrel_shift_cost(21, 5)          # LOD(22) + 21-bit shift by 5-bit amount
    phase_shift = barrel_shift_cost(w, 4)             # shift by floor(e/2) in 0..10 -> 4 stages
    n_general = max(0, w - 3)                         # 2^-1,2^-2 Clifford; 2^-3 T; rest general
    rot = rotation_cost(n_general, margin)

    components = {
        'normalization_compute': norm_fwd,
        'normalization_uncompute': norm_fwd,
        'coefficient_qrom': (d + 1) * qrom_cost(s),
        'horner_compute': horner_fwd,
        'horner_uncompute': horner_fwd,
        'phase_barrel_shift_compute': phase_shift,
        'phase_barrel_shift_uncompute': phase_shift,
        'general_rotations': rot,
        'direct_T': 0.25 * (1 if n_general else 0),
    }
    total = sum(components.values())

    # Optimistic floor: one AND per kept partial product of each truncated
    # multiplication, coefficient adds at one CCX per bit, no carry/control
    # overhead.  Everything else as measured.
    partial = 0
    for j in range(d):
        partial += sum(max(0, widths[j] - k) for k in range(r))
    floor_components = dict(components)
    floor_horner = partial + sum(max(0, v - 1) for v in widths[:-1])
    floor_components['horner_compute'] = floor_horner
    floor_components['horner_uncompute'] = floor_horner
    floor_total = sum(floor_components.values())

    q_horner = horner['qubits']
    q_builder = q_horner + kernel_q_extra
    q_lower = 22 + r + sum(widths) + 5 + max(widths)   # x, u, live terms, exponent, adder workspace

    return dict(
        parameters=dict(degree=d, segments=s, coefficient_fraction_bits=w, residual_bits=r,
                        term_widths=widths, horner_variant=('scaled' if scaled is not None else 'uniform'),
                        horner_uniform_C=uniform['paid'],
                        worst_error_over_tolerance=cfg['worst_error_over_tolerance'],
                        min_margin_turns=margin,
                        raw_coefficient_table_bits=cfg['raw_coefficient_table_bits']),
        components_C=components, total_C=total,
        optimistic_floor_components_C=floor_components, optimistic_floor_C=floor_total,
        rotations=dict(general=n_general, t=1, eps=math.pi * margin / n_general if n_general else None),
        qubits=dict(horner_kernel=q_horner, builder_total=q_builder, lower_bound=q_lower),
        score=dict(builder=q_builder * total, lower_bound=q_lower * floor_total),
    )


def main():
    base = json.loads(BASE.read_text())['official_result']
    score0, q0, c0 = base['score'], base['num_qubits'], base['toffoli_equivalent']
    num = json.loads(NUM.read_text())
    kern = json.loads(KER.read_text())
    census = json.loads((ROOT / 'artifacts/20261106_direction_research/cost/census.json').read_text())
    stages = {tuple(s['window']): s for s in census['stages']}
    front = stages[(0, 15278)]['sample_mean_paid']
    rot_logic = stages[(15278, 15617)]['sample_mean_paid'] + stages[(25408, 25649)]['sample_mean_paid']
    rotation_c = base['rotation_count'] * (0.56 * math.log2(1 / base['rotation_eps']) + 5.3) / 4
    front_plus_rot = front + rot_logic + rotation_c

    break_even = dict(
        baseline=dict(Q=q0, C=c0, score=score0, rotations=base['rotation_count'], rotation_C=rotation_c),
        front_normalization_C=front,
        rotation_cluster_surrounding_C=rot_logic,
        rotation_synthesis_C=rotation_c,
        front_plus_rotations_C=front_plus_rot,
        fixed_Q_budget_C=dict((str(q), score0 / q) for q in (60, 61, 62, 63, 64, 70, 80, 100, 128, 150, 200)),
        strict_improvement_requires=f'C_new < {score0/q0:.6f} at Q=62; C_new < {score0/61:.6f} at Q=61; C_new < {score0/63:.6f} at Q=63',
        note='Replacing the front and both rotation clusters also removes their inverse (the 503.75C suffix), so the new self-contained block must fit in the 694.84C front+rotation budget including its own uncompute.',
    )

    # All cheapest-passing (degree, segments) rows; de-duplicated.
    cfgs = {}
    for row in num['cheapest_passing_per_degree_segments']:
        cfgs[(row['degree'], row['segments'])] = row
    # Add the w=28 variants explicitly so the requested 32/64/16 cases are visible.
    for row in num['rows']:
        if row['tolerance_failures']:
            continue
        if row['coefficient_fraction_bits'] == 28 and row['segments'] in (32, 64):
            cfgs.setdefault((row['degree'], row['segments'], 'w28'), row)

    results = []
    for key, row in sorted(cfgs.items(), key=lambda kv: (kv[1]['degree'], kv[1]['segments'], kv[1]['coefficient_fraction_bits'])):
        led = ledger(row)
        led['key'] = list(key)
        led['break_even'] = dict(
            gap_vs_front_plus_rotations_C=led['total_C'] - front_plus_rot,
            gap_vs_whole_baseline_C=led['total_C'] - c0,
            factor_over_front_plus_rotations=led['total_C'] / front_plus_rot,
            max_Q_at_this_C=score0 / led['total_C'],
            max_C_at_builder_Q=score0 / led['qubits']['builder_total'],
            max_C_at_lower_bound_Q=score0 / led['qubits']['lower_bound'],
        )
        led['verdict'] = ('WIN' if led['qubits']['builder_total'] * led['total_C'] < score0 else 'LOSS')
        results.append(led)

    best_measured = min(results, key=lambda r: r['score']['builder'])
    best_floor = min(results, key=lambda r: r['score']['lower_bound'])
    doc = dict(
        scope='Analytical cost model from measured official-builder kernels; no candidate circuit and no official validation',
        baseline_official=base,
        break_even=break_even,
        kernels_used=dict(qrom_by_entries={str(r['entries']): r['paid'] for r in kern['qrom'] if r['output_bits'] == 28},
                          lod_22=kern['leading_one_detector']['22']['paid'],
                          shift_21=kern['barrel_shift']['21']['paid'],
                          horner={k: v['paid'] for k, v in kern['horner'].items()}),
        configs=results,
        best_measured=dict(key=best_measured['key'], score=best_measured['score']['builder'],
                           total_C=best_measured['total_C'], Q=best_measured['qubits']['builder_total'],
                           gap_vs_front_plus_rotations_C=best_measured['break_even']['gap_vs_front_plus_rotations_C']),
        best_optimistic_floor=dict(key=best_floor['key'], score=best_floor['score']['lower_bound'],
                                   total_C=best_floor['optimistic_floor_C'],
                                   Q=best_floor['qubits']['lower_bound']),
        conclusion=None,
    )
    wins = [r for r in results if r['verdict'] == 'WIN']
    doc['conclusion'] = (
        'No parameter combination beats the baseline. '
        f'Cheapest measured member {best_measured["key"]}: {best_measured["total_C"]:.1f}C at Q={best_measured["qubits"]["builder_total"]} '
        f'(score {best_measured["score"]["builder"]:.0f} vs {score0:.0f}); '
        f'even its optimistic AND-count floor ({best_measured["optimistic_floor_C"]:.1f}C) exceeds the whole baseline C.'
        if not wins else f'{len(wins)} configurations pass the crude screen; see configs.')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + '\n')
    print(json.dumps(dict(best_measured=doc['best_measured'], best_floor=doc['best_optimistic_floor'],
                          conclusion=doc['conclusion']), indent=2))
    print(f"{'cfg':>18} {'C':>9} {'floorC':>9} {'Qker':>5} {'Qbld':>5} {'Qlb':>4} {'score_b':>12} {'gapC':>9} {'maxQ@C':>7}")
    for r in results:
        print(f"{str(r['key']):>18} {r['total_C']:>9.1f} {r['optimistic_floor_C']:>9.1f} "
              f"{r['qubits']['horner_kernel']:>5} {r['qubits']['builder_total']:>5} {r['qubits']['lower_bound']:>4} "
              f"{r['score']['builder']:>12.0f} {r['break_even']['gap_vs_front_plus_rotations_C']:>9.1f} "
              f"{r['break_even']['max_Q_at_this_C']:>7.1f}")


if __name__ == '__main__':
    main()
