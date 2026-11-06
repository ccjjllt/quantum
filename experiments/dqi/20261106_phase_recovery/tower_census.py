"""Enumerate valid GF(2^24) subfield towers and their bilinear term counts.

The standard construction evaluates the degree-d extension at 2d-1 points of
GF(2^k); it is valid only when 2^k >= 2d-1. The term count is
(2d-1) * rank(GF(2^k) multiplication).  The exact ranks mu_2(4)=9 and
mu_2(6)=15 are used where known; the best known constructions are used for
8 and 12.
"""
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[3]
KIT = WORK / 'artifacts/20261106_phase_recovery/old_build/blocks/dqi/pro-q18-900/source/playbook/kit/decoder'
sys.path.insert(0, str(KIT))
import kickmix as km
sys.modules['circ'] = km
sys.path.insert(0, str(KIT / 'exp/arithmetic'))
import field as ar
from exp.mul99 import kernels as mk


def main():
    t4 = mk.tensor4()
    t8 = mk.extension_tensor(8, 4, 2, t4)
    rows = []
    for k in (1, 2, 3, 4, 6, 8, 12, 24):
        d = 24 // k
        points = 2 * d - 1
        valid = (1 << k) >= points
        if k == 4:
            sub = len(t4)
            sub_name = 'mu_2(4)=9 (exact)'
            terms = mk.extension_tensor(24, 4, 6, t4)
        elif k == 6:
            sub = 15
            # exact rank is 15 (PolyTOF / literature); the tower's own 18 is worse
            sub_name = 'mu_2(6)=15 (exact); field.py tower=18'
            terms = None
        elif k == 8:
            sub = len(t8)
            sub_name = 'best known 27 (tower construct)'
            terms = mk.extension_tensor(24, 8, 3, t8)
        elif k == 12:
            sub = len(ar.tensor(12))
            sub_name = 'best known 42 (PolyTOF / tensor12)'
            terms = mk.extension_tensor(24, 12, 2, ar.tensor(12))
        else:
            sub = None
            sub_name = 'invalid: not enough evaluation points'
            terms = None
        rows.append({
            'k': k,
            'd': d,
            'points': points,
            'field_size': 1 << k,
            'valid_standard_tower': valid,
            'sub_rank': sub,
            'sub_rank_note': sub_name,
            'constructed_terms': len(terms) if terms is not None else None,
            'best_known_terms': (points * sub) if (valid and sub is not None) else None,
        })
    out = {'source': 'field.py extension_tensor', 'rows': rows,
           'best_valid_standard_tower': min(r['best_known_terms'] for r in rows if r['best_known_terms'])}
    target = WORK / 'artifacts/20261106_phase_recovery/tower_census.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
