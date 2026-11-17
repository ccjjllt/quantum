"""Build the Kaggle CPU kernel dir for the general-GF(2)-product line.

The kernel is self-contained: the shipped 1220x75 angle table is embedded as base64
(sha256 checked), the two shipped reconstruction functions are re-implemented, and the
target matrix is checked against precomputed sha256 digests so a porting bug cannot
silently change the object of study.
"""
import base64, hashlib, json, pathlib, sys
import numpy as np

REPO = pathlib.Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(REPO / 'experiments/frontier/20261117_deep/chem/work/ds/code2'))
sys.path.insert(0, str(REPO / 'experiments/frontier/20261117_deep/chem/work/ds/code2/compiler'))
OUT = REPO / 'experiments/frontier/20261118_push/gendecomp/k_spanrep'
OUT.mkdir(parents=True, exist_ok=True)

TABLE = pathlib.Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz')
W = np.asarray(np.load(TABLE, allow_pickle=False)['angle_words'], np.uint8)
assert W.shape == (1220, 75)

from planner import complete_words, cross_tensor   # noqa: E402

Wc = complete_words(W)
digests = {}
for k in (2, 4):
    t = cross_tensor(Wc, k)
    flat = np.zeros((len(t), 525), dtype=np.uint8)
    for h, x in enumerate(t):
        for i in range(15):
            v = (int(x) >> (35 * i)) & ((1 << 35) - 1)
            for b in range(35):
                flat[h, 35 * i + b] = (v >> b) & 1
    digests[k] = hashlib.sha256(np.ascontiguousarray(flat).tobytes()).hexdigest()

b64 = base64.b64encode(W.tobytes()).decode()
tbl_sha = hashlib.sha256(W.tobytes()).hexdigest()

MAIN = '''"""Kaggle CPU: general GF(2) product decomposition of the chem angle-loader target.

Pure GF(2) linear algebra on the shipped 1220x75 angle table.  No circuit is simulated
and no submission is produced.  CPU only.

Question: the closed cut/pairing line puts the loader at 188 products (k4..k8).  The
brief's rank bound says >= 38.  This kernel measures where the truth is.

A product column is always  outer(L, v)  = the 35-bit label v replicated on the
low-monomial subset L.  {target[h]} is a subset sum of those columns, so
    R = span{target[h]}  must be INSIDE span{columns}.
Three measurements:
  A. census of chunk vectors inside R (|L| <= 2, 3)                        -> 0 or not
  B. per-block projection dims pi_B(R) and in-block chunk-vector pools     -> term floor
  C. bounded greedy rectangle cover (h-mask x l-mask x label) on the cells -> where it stalls
"""
import base64, hashlib, itertools, json, random, sys
import numpy as np

TBL_SHA = "__TBL_SHA__"
DIGEST = __DIGESTS__
B64 = "__B64__"

NOUT = 35
M35 = (1 << NOUT) - 1
FREE = {(76, l) for l in range(4, 16)}          # padding cells: unconstrained


def log(**kw):
    print(json.dumps(kw, sort_keys=True), flush=True)


def gf2_rank(xs):
    d = {}
    for x in xs:
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p]
            else:
                d[p] = x
                break
    return len(d)


def add_to(x, d):
    while x:
        p = x.bit_length() - 1
        if p in d:
            x ^= d[p]
        else:
            d[p] = x
            return True
    return False


def reduce_to(x, d):
    for p in sorted(d, reverse=True):
        if x & (1 << p):
            x ^= d[p]
    return x


def complete_words(words):
    words = np.asarray(words, dtype=np.uint8)
    rows = len(words)
    nh = (rows + 15) // 16
    rem = rows - 16 * (nh - 1)
    hbits = (nh - 1).bit_length()
    a = np.zeros((nh * 16, 75), dtype=np.uint8)
    a[:rows] = words
    f = a.reshape(nh, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(hbits):
        for h in range(nh):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    f[nh - 1, rem:] = 0
    for b in range(hbits):
        for h in range(nh):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    assert np.array_equal(a[:rows], words)
    return a


def cross_tensor(words, k):
    words = np.asarray(words)
    rows = len(words)
    nh = (rows + 15) // 16
    hbits = (nh - 1).bit_length()
    delta = words[:, 5 * k:5 * k + 5].copy()
    if k:
        delta ^= words[:, 5 * k - 5:5 * k]
    packed = np.zeros(nh * 16, dtype=np.uint64)
    for j in range(5):
        packed[:len(delta)] |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(nh, 16).copy()
    for b in range(4):
        for lo in range(16):
            if lo & (1 << b):
                f[:, lo] ^= f[:, lo ^ (1 << b)]
    for b in range(hbits):
        for hi in range(nh):
            if hi & (1 << b):
                f[hi] ^= f[hi ^ (1 << b)]
    return [sum(int(f[h, l]) << ((l - 1) * NOUT) for l in range(1, 16)) for h in range(nh)]


def target_cells(t):
    """(h,l) -> 35-bit ANF coefficient, h in 1..76, l in 1..15, padding cells dropped."""
    out = {}
    for h in range(1, 77):
        x = int(t[h])
        if not x:
            continue
        for i in range(15):
            v = (x >> (NOUT * i)) & M35
            if v and (h, i + 1) not in FREE:
                out[(h, i + 1)] = v
    return out


def slice_space(cells):
    R = {}
    for h in range(1, 77):
        x = 0
        for l in range(1, 16):
            x ^= cells.get((h, l), 0) << (NOUT * (l - 1))
        if x:
            add_to(x, R)
    return R


def outer(L, v, base):
    out = 0
    for i, c in enumerate(base):
        if (L >> i) & 1:
            out ^= v << (NOUT * c)
    return out


def kernel_basis(imgs, n):
    piv, out = {}, []
    for j in range(n):
        x, co = imgs[j], 1 << j
        while x:
            p = x.bit_length() - 1
            if p in piv:
                x ^= piv[p][0]
                co ^= piv[p][1]
            else:
                piv[p] = (x, co)
                break
        if not x:
            out.append(co)
    return out


def projection(R, base):
    mask = 0
    for i in base:
        mask |= M35 << (NOUT * i)
    proj = {}
    for x in R.values():
        y = x & mask
        if y:
            add_to(y, proj)
    return proj


def census(proj, base):
    pool, per_L = [], {}
    for L in range(1, 1 << len(base)):
        imgs = [reduce_to(outer(L, 1 << j, base), proj) for j in range(NOUT)]
        vs = kernel_basis(imgs, NOUT)
        per_L[bin(L)] = len(vs)
        for v in vs:
            z = outer(L, v, base)
            assert z and reduce_to(z, proj) == 0
            pool.append((L, v, z))
    return pool, per_L


def main():
    W = np.frombuffer(base64.b64decode(B64), dtype=np.uint8).reshape(1220, 75)
    assert hashlib.sha256(W.tobytes()).hexdigest() == TBL_SHA, 'embedded table changed'
    log(step='table', sha=TBL_SHA, shape=list(W.shape))
    Wc = complete_words(W)
    for k in (4, 2):
        t = cross_tensor(Wc, k)
        flat = np.zeros((len(t), 525), dtype=np.uint8)
        for h, x in enumerate(t):
            for i in range(15):
                v = (int(x) >> (NOUT * i)) & M35
                for b in range(NOUT):
                    flat[h, NOUT * i + b] = (v >> b) & 1
        got = hashlib.sha256(np.ascontiguousarray(flat).tobytes()).hexdigest()
        assert got == DIGEST[k], 'target rebuild differs from the local run'
        log(step='target_ok', k=k, sha=got)

    for k in (4, 2):
        cells = target_cells(cross_tensor(Wc, k))
        vals = list(cells.values())
        R = slice_space(cells)
        log(step='cells', k=k, nonzero=len(cells), distinct=len(set(vals)),
            rank_values=gf2_rank(vals), dimR=len(R),
            row_ranks=sorted({gf2_rank([cells.get((h, l), 0) for l in range(1, 16)]) for h in range(1, 77)}))
        colr = [gf2_rank([cells.get((h, l), 0) for h in range(1, 77)]) for l in range(1, 16)]
        log(step='column_ranks', k=k, ranks=colr, sum=sum(colr))

        # A. chunk vectors inside R
        for lmax in (1, 2, 3):
            found = 0
            for size in range(1, lmax + 1):
                for Lc in itertools.combinations(range(15), size):
                    L = sum(1 << i for i in Lc)
                    imgs = [reduce_to(outer(L, 1 << j, list(range(15))), R) for j in range(NOUT)]
                    found += len(kernel_basis(imgs, NOUT))
            log(step='chunk_census_R', k=k, lmax=lmax, chunk_vectors_in_R=found)

        # B. block projections and in-block pools
        blocks = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11], [12, 13, 14]]
        dims, pools, used = [], [], []
        for base in blocks:
            proj = projection(R, base)
            pool, per_L = census(proj, base)
            span = {}
            n_used = 0
            for L, v, z in pool:
                if reduce_to(z, span):
                    add_to(z, span)
                    n_used += 1
                    if len(span) == len(proj):
                        break
            dims.append(len(proj)); pools.append(len(pool)); used.append(n_used)
            log(step='block3', k=k, base=base, dim=len(proj), pool=len(pool),
                per_L=per_L, covered=len(span), greedy_terms=n_used)
        log(step='block3_total', k=k, dims=dims, pools=pools, covered=used,
            sum_dims=sum(dims), term_floor=sum(dims), products_floor=(sum(dims) + 1) // 2)

        for b in (4, 5):
            bl = [list(range(i, min(i + b, 15))) for i in range(0, 15, b)]
            if len(bl[-1]) != b:
                bl[-2] += bl[-1]; bl.pop()
            dims2, pools2 = [], []
            for base in bl:
                proj = projection(R, base)
                pool, _ = census(proj, base)
                dims2.append(len(proj)); pools2.append(len(pool))
            log(step='block_b', k=k, b=b, dims=dims2, pools=pools2)

        # B2. attainable non-cut product set: 2-coord blocks (every pool is large
        #     enough to span its own projection, so the union really covers R)
        bl2 = [list(range(i, min(i + 2, 15))) for i in range(0, 15, 2)]
        if len(bl2[-1]) != 2:
            bl2[-2] += bl2[-1]; bl2.pop()
        pool2, per2 = [], []
        for base in bl2:
            proj = projection(R, base)
            pl, _ = census(proj, base)
            sp = {}
            n = 0
            for L, v, z in pl:
                if reduce_to(z, sp):
                    add_to(z, sp); n += 1
            per2.append({'base': base, 'dim': len(proj), 'pool': len(pl), 'covered': n})
            pool2 += pl
        sp2, used2 = {}, []
        for L, v, z in pool2:
            if reduce_to(z, sp2):
                add_to(z, sp2); used2.append((L, v))
        covers2 = all(reduce_to(x, sp2) == 0 for x in R.values())
        log(step='block2_attainable', k=k, blocks=per2, pool=len(pool2),
            terms=len(sp2), covers_R=covers2)

        # C1. why a "greedy rectangle cover" cannot start: all residual values distinct
        vals0 = list(cells.values())
        log(step='cover_start', k=k, cells=len(vals0), distinct=len(set(vals0)))
        rng = random.Random(11)
        keys = list(cells)
        best_gain, best_area = None, None
        for _ in range(400):
            h0, l0 = keys[rng.randrange(len(keys))]
            v0 = cells[(h0, l0)]
            hm = 1 << h0
            for _ in range(rng.randrange(0, 4)):
                hm |= 1 << rng.randrange(1, 77)
            lm = 1 << (l0 - 1)
            for _ in range(rng.randrange(0, 3)):
                lm |= 1 << rng.randrange(0, 15)
            area = bin(hm).count('1') * bin(lm).count('1')
            gain = 0
            for hh in range(1, 77):
                if hm >> hh & 1:
                    for l in range(1, 16):
                        if lm >> (l - 1) & 1:
                            gain += 1 if cells.get((hh, l), 0) == v0 else -1
            if best_gain is None or gain > best_gain:
                best_gain, best_area = gain, area
        log(step='cover_probe', k=k, best_gain=best_gain, best_area=best_area,
            note='max gain over 400 sampled rectangles; only 1x1 rectangles have gain 1')

        # C2. bounded algebraic attempt: minimal irredundant product set from the
        #     measured in-block chunk-vector pool (all 5 blocks), then prune.
        pool = []
        for base in blocks:
            proj = projection(R, base)
            pl, _ = census(proj, base)
            pool += pl
        order = list(range(len(pool)))
        rng.shuffle(order)
        span = {}
        chosen = []
        for i in order:
            L, v, z = pool[i]
            if reduce_to(z, span):
                add_to(z, span)
                chosen.append(pool[i])
        ok = all(reduce_to(x, span) == 0 for x in R.values())
        log(step='pool_greedy', k=k, pool=len(pool), chosen=len(chosen), covers_R=ok,
            span=len(span))
        improved = True
        while improved:
            improved = False
            for i in range(len(chosen) - 1, -1, -1):
                trial = chosen[:i] + chosen[i + 1:]
                sp = {}
                for L, v, z in trial:
                    add_to(z, sp)
                if all(reduce_to(x, sp) == 0 for x in R.values()):
                    chosen = trial
                    improved = True
        labels = {}
        for L, v, z in chosen:
            labels[v] = labels.get(v, 0) + 1
        log(step='pruned', k=k, terms=len(chosen), distinct_labels=len(labels),
            products=sum((c + 1) // 2 for c in labels.values()))


main()
'''

src = MAIN.replace('__TBL_SHA__', tbl_sha).replace('__DIGESTS__', repr(digests)).replace('__B64__', b64)
(OUT / 'main.py').write_text(src)
print('wrote', OUT / 'main.py', len(src), 'bytes')
print('table sha', tbl_sha)
print('digests', digests)
