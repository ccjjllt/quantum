"""Inspect an emitted plan.json: product rectangle structure and cell coverage.

plan.json products carry (l1,l2,out,h1,h2) where h1/h2 are row-set masks over
h=1..76 and l1/l2 are low-monomial masks (bit i <-> low monomial i+1).
The ANF contribution of a product is exactly the two rectangles
(h2 x l1) and (h1 x l2), each carrying the 35-bit vector `out`.
"""
import sys, json
from collections import Counter
import common as C


def bitinds(x):
    out = []
    while x:
        b = x & -x
        x ^= b
        out.append(b.bit_length() - 1)
    return out


def main(path, k=None):
    d = json.loads(open(path).read())
    rep = d['report']
    ps = d['products']
    k = rep['k'] if k is None else k
    print('k', k, 'products', len(ps), 'toffoli', rep['toffoli_count'])
    nl1 = Counter(len(bitinds(p['l1'])) for p in ps)
    nl2 = Counter(len(bitinds(p['l2'])) for p in ps)
    nh1 = Counter(len(bitinds(p['h1'])) for p in ps)
    nh2 = Counter(len(bitinds(p['h2'])) for p in ps)
    print('|l1|', dict(sorted(nl1.items())), '|l2|', dict(sorted(nl2.items())))
    print('|h1|', dict(sorted(nh1.items())), '|h2|', dict(sorted(nh2.items())))
    areas = [len(bitinds(p['l1'])) * len(bitinds(p['h1'])) +
             len(bitinds(p['l2'])) * len(bitinds(p['h2'])) for p in ps]
    print('product cell-area: min', min(areas), 'max', max(areas), 'mean', sum(areas) / len(areas),
          'hist', dict(sorted(Counter(areas).items())))
    print('rows shared between the two rects (h1 & h2 != 0):',
          sum(1 for p in ps if p['h1'] & p['h2']), ' l overlap:',
          sum(1 for p in ps if p['l1'] & p['l2']))
    # coverage
    cov = Counter()
    for p in ps:
        for lm, hm in ((p['l1'], p['h2']), (p['l2'], p['h1'])):
            for h in bitinds(hm):
                for l in [i + 1 for i in bitinds(lm)]:
                    cov[(h, l)] += 1
    W, Wc, target, cl = C.build(k)
    cells = set(cl)
    print('cells', len(cells), 'avg coverage', sum(cov[c] for c in cells) / len(cells),
          'coverage hist', dict(sorted(Counter(cov[c] for c in cells).items())))
    got = Counter()
    for p in ps:
        for lm, hm in ((p['l1'], p['h2']), (p['l2'], p['h1'])):
            for h in bitinds(hm):
                for l in [i + 1 for i in bitinds(lm)]:
                    got[(h, l)] ^= p['out']
    print('value mismatches', sum(1 for c in cells if got.get(c, 0) != cl[c]))
    print('spurious nonzero cells', len([c for c in got if got[c] and c not in cells]))


if __name__ == '__main__':
    main(sys.argv[1])
