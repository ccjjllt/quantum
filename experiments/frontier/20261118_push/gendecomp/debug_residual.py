"""Debug: residual ANF cells between target and the plan.json rectangle reconstruction."""
import sys, json
from collections import Counter
import common as C
from probe_products import bitinds


def recon(ps, k):
    got = Counter()
    for p in ps:
        for lm, hm in ((p['l1'], p['h2']), (p['l2'], p['h1'])):
            for h in bitinds(hm):
                for l in [i + 1 for i in bitinds(lm)]:
                    got[(h, l)] ^= p['out']
    return got


if __name__ == '__main__':
    d = json.loads(open(sys.argv[1]).read())
    ps = d['products']
    k = d['report']['k']
    W, Wc, target, cl = C.build(k)
    got = recon(ps, k)
    diff = {}
    for c in set(cl) | set(got):
        x = cl.get(c, 0) ^ got.get(c, 0)
        if x:
            diff[c] = x
    print('residual cells', len(diff))
    print('by h:', sorted(Counter(h for h, l in diff).items()))
    print('by l:', sorted(Counter(l for h, l in diff).items()))
    print('values', sorted(set(diff.values())) == sorted(set(diff.values())))
    print('distinct residual values', len(set(diff.values())))
    print('rank of residual values', C.gf2_rank(list(diff.values())))
    print('slices', {(h, l): hex(v) for (h, l), v in sorted(diff.items())[:20]})
