"""Quantize the loadertrain checkpoints, score them with the official metrics and loader proxies."""
from __future__ import annotations
import sys, json, glob
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tensorqrom as tq
from dfthcsos.verify import load_inputs, evaluate_words

BASE = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
ART = ROOT/'.worktree/dfthcsos/artifacts/20261112_loader_aware_train'
BROT, J, LB = 8, 5, 4


def deltas(words):
    out = []; prev = None
    for k in range(15):
        b = words[:, k*J:(k+1)*J]
        out.append(b if prev is None else b ^ prev); prev = b
    return out


def per_output_proxy(words):
    tot = 0
    for d in deltas(words):
        C = tq.anf_tensor(d, BROT, LB)
        tot += tq.cost(tq.per_output(C), 1 << LB, C.shape[1])
    return tot


def rank_model(words):
    n_sel = max(1, (len(words)-1).bit_length())
    cache = prod = 0
    for d in deltas(words):
        L = 1 << LB; H = -(-len(d)//L); O = d.shape[1]*(BROT-1)
        pad = np.zeros((1 << n_sel, O), np.uint8)
        for j in range(d.shape[1]):
            for i in range(BROT-1):
                pad[:len(d), j*(BROT-1)+i] = (d[:, j] >> i) & 1
        x = tq.mobius(pad.reshape(1 << (n_sel-LB), L, O), 1)
        C = tq.mobius(x, 0)[:H].transpose(1, 0, 2)
        mixed = C[1:, 1:]
        cache += int(np.any(mixed.any(axis=0), axis=1).sum())
        for o in range(O):
            rr = [int(sum(int(v) << i for i, v in enumerate(mixed[m, :, o]))) for m in range(L-1)]
            prod += (len(tq.rank_factor(rr)[0]) + 1)//2
    return cache, prod


def main():
    inp = load_inputs(BASE)
    with np.load(BASE) as z:
        base_words = np.asarray(z['angle_words'], np.int64); tree = np.asarray(z['tree_edges'], np.int64)
    rows = []
    files = sorted(glob.glob(str(ART/'train_lam*.npz')), key=lambda p: float(p.split('lam')[-1][:-4]))
    for f in files:
        z = np.load(f)
        phi = z['phi']; words = base_words.copy(); words[76:] = np.mod(np.round(phi).astype(np.int64), 1 << BROT)
        m = evaluate_words(inp, words, tree, BROT)
        cache, prod = rank_model(words)
        # how many of the 75 two-body columns satisfy bit0(a) == bit0(a^8) inside every block
        paired = 0
        for c in range(75):
            col = words[76:, c]; ok = True
            for s in range(0, 1144, 16):
                for lo in range(8):
                    a, a2 = 76+s+lo, 76+s+lo+8
                    if a2 < len(words) and ((words[a, c] >> 0) & 1) != ((words[a2, c] >> 0) & 1):
                        ok = False; break
                if not ok: break
            paired += ok
        r = dict(file=Path(f).name, lam=float(z['lam']),
                 e1_mHa=1e3*float(m['error_1']), e2_mHa=1e3*float(m['error_2']),
                 Lambda=float(m['Lambda']), E_gap=float(m['E_gap']), lambda_eff=float(m['lambda_eff']),
                 proxy=per_output_proxy(words), cache=cache, prods=prod, paired_cols=paired)
        rows.append(r)
        print(json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
    (ART/'candidates.json').write_text(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
