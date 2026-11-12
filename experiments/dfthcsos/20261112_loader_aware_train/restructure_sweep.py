"""Cheapest possible loader-friendly restructuring of the current signed word table.

For each chosen output bit (rotation j, bit k) enforce bit(a) == bit(a ^ 8) inside every
16-address block by flipping the single cheapest bit of each disagreeing pair.  That kills every
mixed ANF monomial containing the top low bit, halving the per-output product rank.  Sweep how many
output bits are structured and report the official metrics and the loader proxies.
"""
from __future__ import annotations
import sys, math, json
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import encode
import tensorqrom as tq
from dfthcsos.verify import load_inputs, evaluate_words
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

NPZ = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT, J, LB = 8, 5, 4
OUT = ROOT/'.worktree/dfthcsos/artifacts/20261112_loader_aware_train'


def deltas(words):
    out = []; prev = None
    for k in range(15):
        b = words[:, k*J:(k+1)*J]
        out.append(b if prev is None else b ^ prev); prev = b
    return out


def per_output_proxy(words):
    return sum(tq.cost(tq.per_output(tq.anf_tensor(d, BROT, LB)), 1 << LB, tq.anf_tensor(d, BROT, LB).shape[1])
               for d in deltas(words))


def rank_model(words):
    """cache (mixed high monomials) + sum_o ceil(rank/2), the Maoxin-style cost structure."""
    n_sel = max(1, (len(words)-1).bit_length())
    caches, prods = [], []
    for d in deltas(words):
        L = 1 << LB; H = -(-len(d)//L); O = d.shape[1]*(BROT-1)
        pad = np.zeros((1 << n_sel, O), np.uint8)
        for j in range(d.shape[1]):
            for i in range(BROT-1):
                pad[:len(d), j*(BROT-1)+i] = (d[:, j] >> i) & 1
        x = tq.mobius(pad.reshape(1 << (n_sel-LB), L, O), 1)
        C = tq.mobius(x, 0)[:H].transpose(1, 0, 2)
        mixed = C[1:, 1:]
        caches.append(int(np.any(mixed.any(axis=0), axis=1).sum()))
        pr = 0
        for o in range(O):
            rr = [int(sum(int(v) << i for i, v in enumerate(mixed[m, :, o]))) for m in range(L-1)]
            pr += (len(tq.rank_factor(rr)[0]) + 1)//2
        prods.append(pr)
    return int(sum(caches)), int(sum(prods))


def force_pair_bit(words, theta, cols, bit):
    """Flip the cheapest single bit so bit(a) == bit(a ^ 8) in every 16-address block."""
    w = words.copy(); th = theta.copy()
    A = len(w)
    nblk = -(-A // 16)
    flips = 0
    for c in cols:
        for b in range(nblk):
            s = 16*b
            for lo in range(8):
                a, a2 = s + lo, s + lo + 8
                if a2 >= A:
                    continue
                if ((w[a, c] >> bit) & 1) != ((w[a2, c] >> bit) & 1):
                    best = None
                    for r in (a, a2):
                        v = int(w[r, c]); nv = v ^ (1 << bit)
                        d = abs(th[r, c] - nv)
                        if best is None or d < best[1]:
                            best = (nv, d, r)
                    w[best[2], c] = best[0]
                    flips += 1
    return w, th, flips


def main():
    inp = load_inputs(NPZ)
    with np.load(NPZ) as z:
        base_words = np.asarray(z['angle_words'], np.int64); tree = np.asarray(z['tree_edges'], np.int64)
    u = reconstruct_u_vectors(base_words[76:] / 128.0, tree)
    u = u / np.linalg.norm(u, axis=1, keepdims=True)
    th = encode.signed_angles(u, tree) * 128.0       # word units, signed gauge
    words = base_words.copy()
    words[76:] = np.mod(np.round(th).astype(np.int64), 1 << BROT)
    th_full = np.concatenate([base_words[:76].astype(np.float64), th])
    m0 = evaluate_words(inp, words, tree, BROT)
    print('control (signed re-encode): e1 %.4f e2 %.4f lambda_eff %.3f | proxy %d | rank-model cache %d prods %d'
          % (1e3*m0['error_1'], 1e3*m0['error_2'], m0['lambda_eff'], per_output_proxy(words),
             *rank_model(words)), flush=True)
    rows = []
    rng = np.random.default_rng(20261112)
    cols_all = list(range(75))
    for bit in (0, 1, 2):
        for ncol in (5, 15, 30, 75):
            cols = cols_all[:ncol]
            w2, th2, flips = force_pair_bit(words, th_full, cols, bit)
            m = evaluate_words(inp, w2, tree, BROT)
            cache, prod = rank_model(w2)
            rows.append(dict(bit=bit, ncol=ncol, flips=flips, e1=float(m['error_1']), e2=float(m['error_2']),
                             lambda_eff=float(m['lambda_eff']), proxy=per_output_proxy(w2),
                             cache=cache, prods=prod))
            print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in rows[-1].items()}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'restructure_sweep.json').write_text(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
