"""Exact cost frontier for the DQI candidate eae396ba.

score = R * Q^2 * meanT,  R = 1.19126046 (from the 102,400-shot 0/0 local PASS),
meanT/static = 0.98200 (eae measured ratio).

All numbers here are arithmetic on measured quantities, not new measurements.
"""
from __future__ import annotations

import json
import math

R = 1.19126046
Q0 = 892
STATIC0 = 401_313
MEAN0 = 394_089.27
RATIO = MEAN0 / STATIC0
COST0 = R * Q0 ** 2 * MEAN0
REF_COST = 24_439_463_583_672.93
GM0 = 25.40482

STAGES = {
    'extract': 58_742,
    'synthesis': 31_635,
    'convert': 60_663,
    'scan': 44_275,
    'unconvert': 62_534,
    'unsynthesis': 40_429,
    'unextract': 103_035,
}
MULT = {  # motif census, 20261112_decoder_family
    'extract': 42_482,
    'synthesis': 30_984,
    'convert': 50_239,
    'scan': 0,
    'unconvert': 52_754,
    'unsynthesis': 38_687,
    'unextract': 73_717,
}

TARGETS = {
    'eae (now)': 1.0,
    '-10% (min line)': 0.90,
    '-13.5% (old goal)': 0.865,
    '-16.7% (GM 27.0)': 0.833,
    '-20% (structural)': 0.80,
    '-29.2% (GM 28.5)': 0.708,
}


def main() -> None:
    out = {
        'cost0': COST0,
        'gm0': GM0,
        'mean_static_ratio': RATIO,
        'tables': {},
        'stage_split': {},
        'mirror_bound': {},
        'frontier': {},
    }
    print(f'eae cost        = {COST0:.6e}  (GM {GM0})')
    print(f'mean/static     = {RATIO:.5f}')
    print()
    print('=== A. required static T at fixed Q (to reach each target) ===')
    rows = []
    for name, f in TARGETS.items():
        cost = COST0 * f
        gm = GM0 * (1.0 / f) ** (1 / 3)
        line = [name, f'{cost:.4e}', f'{gm:.3f}']
        for Q in (892, 889, 880, 870, 860, 850, 845, 840):
            mean_allow = cost / (R * Q * Q)
            static_allow = mean_allow / RATIO
            line.append(f'{static_allow:,.0f}')
        rows.append(line)
    hdr = ['target', 'cost', 'GM', 'Q=892', 'Q=889', 'Q=880', 'Q=870', 'Q=860', 'Q=850', 'Q=845', 'Q=840']
    print(' | '.join(hdr))
    for line in rows:
        print(' | '.join(line))
    out['tables']['required_static'] = [dict(zip(hdr, r)) for r in rows]

    print()
    print('=== B. stage split and multiplication share ===')
    tot = sum(STAGES.values())
    tot_mult = sum(MULT.values())
    for k, v in STAGES.items():
        print(f'{k:12s} static={v:7,d} mult={MULT[k]:7,d} nonmult={v - MULT[k]:7,d} '
              f'({100 * v / tot:5.2f}% of total)')
    print(f'{"total":12s} static={tot:7,d} mult={tot_mult:7,d} nonmult={tot - tot_mult:7,d}')
    out['stage_split'] = {
        'total': tot,
        'mult_total': tot_mult,
        'nonmult_total': tot - tot_mult,
        'per_stage': {k: {'static': v, 'mult': MULT[k], 'nonmult': v - MULT[k]} for k, v in STAGES.items()},
    }

    print()
    print('=== C. perfect compute/uncompute mirror bound ===')
    fwd_data = STAGES['extract'] + STAGES['synthesis'] + STAGES['convert']
    rev_actual = STAGES['unextract'] + STAGES['unsynthesis'] + STAGES['unconvert']
    mirrored = STAGES['extract'] + STAGES['synthesis'] + STAGES['convert'] + STAGES['scan'] + fwd_data
    print(f'forward (excl scan) = {fwd_data:,d}')
    print(f'reverse actual      = {rev_actual:,d}  (+{rev_actual - fwd_data:,d} = '
          f'{100 * (rev_actual / fwd_data - 1):.2f}% vs a pure mirror)')
    print(f'static if reverse were a pure mirror = {mirrored:,d} '
          f'({100 * (mirrored / tot - 1):.2f}%)')
    mirror_cost = R * Q0 ** 2 * (mirrored * RATIO)
    print(f'-> cost {mirror_cost:.4e}  ({100 * (mirror_cost / COST0 - 1):.2f}%)')
    out['mirror_bound'] = {
        'forward_excl_scan': fwd_data,
        'reverse_actual': rev_actual,
        'mirror_static': mirrored,
        'mirror_cost': mirror_cost,
    }

    print()
    print('=== D. frontier in (Q, static) for the -20% goal ===')
    target = COST0 * 0.80
    for Q in (892, 889, 880, 870, 860, 850, 845, 840):
        static_allow = target / (R * Q * Q) / RATIO
        # what multiplication T would be needed if non-mult stayed at eae's level
        mult_allow = static_allow - (tot - tot_mult)
        need_rank12 = None
        print(f'Q={Q}: static <= {static_allow:,.0f} (dT = {static_allow - tot:+,.0f}); '
              f'mult T <= {mult_allow:,.0f} (= {100 * mult_allow / tot_mult:.1f}% of now); '
              f'rank12 <= {42 * mult_allow / tot_mult:.2f}')
        out['frontier'][str(Q)] = {
            'static_allow': static_allow,
            'delta_static': static_allow - tot,
            'mult_allow': mult_allow,
            'rank12_equivalent': 42 * mult_allow / tot_mult,
        }

    with open('artifacts/20261112_next_decoder/frontier.json', 'w') as fh:
        json.dump(out, fh, indent=1)
    print('\nwrote artifacts/20261112_next_decoder/frontier.json')
    print(f'GM at -20%: {GM0 * 1.25 ** (1 / 3):.5f}')


if __name__ == '__main__':
    main()
