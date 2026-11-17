"""Probe the ANF cell structure of the loader-k target (pure arithmetic).

For k in 2,4 (and 0..14 in summary mode):
  * number of nonzero non-axial ANF cells (h in 1..76, l in 1..15)
  * number of distinct 35-bit cell values
  * GF(2) rank of the 77 slices, and of the cell vectors
  * multiplicity histogram of equal-valued cells
  * a lower bound on products: ceil(rank/2) and #cells after the greedy
    "equal-value component" argument, i.e. #cells - max components where each
    component's vector XOR is 0.
"""
import sys, json
from collections import Counter, defaultdict
import common as C

ks = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '2,4')]

for k in ks:
    W, Wc, target, cl = C.build(k)
    rank = C.gf2_rank([int(x) for x in target[1:76]])
    vals = list(cl.values())
    rankv = C.gf2_rank(vals)
    hist = Counter(Counter(vals).values())          # (multiplicity -> #values)
    # connected components under the "XOR of a component must be 0" rule:
    # best case pairing = pair equal values greedily.
    byval = defaultdict(list)
    for cell, v in cl.items():
        byval[v].append(cell)
    pairs = sum(len(v) // 2 for v in byval.values())
    singles = sum(len(v) % 2 for v in byval.values())
    # residual singles that could form larger zero-xor components: lower bound
    # ignores that (it can only help), so this is an upper estimate of the floor.
    lb = len(cl) - pairs
    hi_counts = Counter(h for (h, l) in cl)
    lo_counts = Counter(l for (h, l) in cl)
    print(json.dumps({
        'k': k, 'rank_77': rank, 'nonzero_cells': len(cl), 'distinct_values': len(byval),
        'rank_values': rankv, 'mult_hist': dict(sorted(hist.items())),
        'equal_value_pairs': pairs, 'odd_singletons': singles,
        'floor_rank_half': (rank + 1) // 2, 'floor_pairing': lb,
        'h_deg_max': max(hi_counts.values()), 'l_deg_max': max(lo_counts.values()),
    }), flush=True)
