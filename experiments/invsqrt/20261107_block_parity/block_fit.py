"""Block / wavelet parity expansion of T(x) = 1/sqrt(x) on the legal domain.

Basis.  Split the 22-bit input into high bits H (block index h = x >> b) and
low bits L = x & (2^b - 1), block size 2^b.  The model is

    p(x) = sum_h I_h(h(x)) * sum_{S subseteq [b]} c_{h,S} chi_S(L(x)),
    chi_S(L) = (-1)^popcount(S & L)                                   (1)

i.e. a local parity (Walsh) expansion inside every block with a
block-dependent coefficient vector.  Cost structure (counted in kernels.py and
priced in ledger.py): the block indicator is an AND of the 22-b high bits with
X-flips for zero controls, the local parity is a free CX fan-in, and every
nonzero c_{h,S} needs its own rotation double-controlled by
(block indicator, local parity).

Fit.  Blocks are disjoint and chi is orthonormal on a full block, so the
legal-domain least-squares problem is *block diagonal* and exact:

    G_h[S,S'] = sum_{L legal in h} chi_S(L) chi_S'(L) = WHT(mask_h)[S xor S']
    b_h[S]    = sum_{L legal in h} chi_S(L) g(L)      = WHT(mask_h * g)[S]

Only block 0 (x = 0 illegal) and the last block (x > M illegal) are partial;
there G_h = 2^b I - J, so the solve is a tiny pinv.  Coefficients come from the
official `target_units` array (x=1 -> 1 turn == 0) and the error is measured
against the official `tol_units`.

Because the blocks are independent, "K terms" is allocated by water-filling:
for a threshold t every block takes the fewest local terms whose measured
max |error|/tol over that block is <= t; K(t) = sum_h k_h(t).  Every reported
worst ratio is the *measured* full-domain value for the allocation actually
used (never a bound).

Variants
  * water-fill     : per-block term counts that minimise the full-domain
                     max |error|/tol for a given total K (the best this family
                     can do with K terms),
  * shared support : one local subset set {S_1..S_K_L} used in every block with
                     block-dependent angles (the cheapest circuit variant,
                     because the K_L parity ancillas can be prepared once),
  * haar           : the block constants re-expressed as a coarse value plus
                     adjacent-block differences (telescoping prefix
                     indicators); the residual is identical by orthogonality,
                     only detail sparsity and cost change,
  * chebyshev      : exact per-block min-max LP on the worst blocks, to measure
                     how far LS is from the L-infinity optimum.

Output: artifacts/20261107_block_parity/block_fit.json (+ printed log).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_block_parity"
N = 1 << 22
M = 3_133_452
BS = [6, 7, 8, 9, 10, 11, 12]
KS = [41, 96, 200, 500, 1000, 2000]
LP_B = (8, 12)


def fwht_axis1(a: np.ndarray) -> np.ndarray:
    """Unnormalised WHT on the last axis, in place (self-inverse up to n)."""
    squeeze = a.ndim == 1
    if squeeze:
        a = a.reshape(1, -1)
    n = a.shape[-1]
    h = 1
    while h < n:
        z = a.reshape(a.shape[0], -1, 2, h)
        u = z[:, :, 0, :].copy()
        v = z[:, :, 1, :].copy()
        z[:, :, 0, :] = u + v
        z[:, :, 1, :] = u - v
        h *= 2
    return a.reshape(-1) if squeeze else a


def kgrid(nb: int) -> list[int]:
    base = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48,
            56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 448, 512,
            640, 768, 896, 1024, 1280, 1536, 1792, 2048, 2560, 3072, 3584, 4096]
    return sorted(k for k in base if k <= nb)


def solve_block(mask: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Sparse exact interpolation inside one partial block.

    A partial block (block 0 without x=0, the last block truncated at M) has
    n_p legal points.  The min-norm LS solution spreads the value over all 2^b
    characters, so truncating it to k terms is terrible; instead use the n_p
    characters of lowest order (popcount, then index) and solve the square
    system, which is exact on the legal points with only n_p terms.
    """
    nb = mask.size
    off = np.flatnonzero(mask)
    npts = off.size
    key = np.bitwise_count(np.arange(nb)).astype(np.int64) * nb + np.arange(nb)
    sel = np.argsort(key)[:npts]
    A = np.array([[(-1.0) ** int(np.bitwise_count(int(S) & int(o)))
                   for S in sel] for o in off])
    try:
        csel = np.linalg.solve(A, g[off])
    except np.linalg.LinAlgError:
        csel = np.linalg.pinv(A, rcond=1e-12) @ g[off]
    c = np.zeros(nb)
    c[sel] = csel
    return c


def load_blocks(b: int):
    """Arrays indexed by x itself, so block h covers x in [h*2^b, (h+1)*2^b).

    The official arrays are indexed by x-1 (tol_units[j] is tol(x=j+1)); they
    are re-indexed here so that the block index is exactly the high bits of x,
    which is what the circuit's AND-of-high-bits indicator implements.
    """
    nb = 1 << b
    hb = (M >> b) + 1                      # blocks with at least one legal x
    n = hb * nb
    tol = np.zeros(n)
    tgt = np.zeros(n)
    tol[1:M + 1] = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    tgt[1:M + 1] = np.load(ROT33 / "target_units.npy").astype(np.float64) / 2.0**64
    g2 = tgt.reshape(hb, nb)
    t2 = tol.reshape(hb, nb)
    m2 = t2 > 0
    c = np.empty((hb, nb), dtype=np.float64)
    for h in range(hb):
        mh = m2[h]
        if mh.all() or int(mh.sum()) >= nb - 1:
            # full block, or the single puncture at x = 0: the full-block WHT
            # (with target 0 at x = 0, which is outside the domain) is exact on
            # every legal point of the block.
            c[h] = fwht_axis1(np.where(mh, g2[h], 0.0)) / nb
        else:
            c[h] = solve_block(mh, g2[h])
    rec = fwht_axis1(c.copy())
    err = np.abs(rec - g2)[m2].max()
    order = np.argsort(-np.abs(c), axis=1)
    rank = np.empty_like(order)
    np.put_along_axis(rank, order, np.broadcast_to(np.arange(nb), (hb, nb)), axis=1)
    return dict(b=b, nb=nb, hb=hb, g2=g2, tol2=t2, mask2=m2, c=c,
                order=order, rank=rank, full_basis_err=float(err))


def evaluate(bl: dict, kk: np.ndarray):
    """Exact residual for per-block keep-counts kk."""
    keep = bl["rank"] < kk[:, None]
    ck = np.where(keep, bl["c"], 0.0)
    p = fwht_axis1(ck)
    e = p - bl["g2"]
    e = e - np.round(e)
    m = bl["mask2"]
    ratio = np.where(m, np.abs(e) / np.where(m, bl["tol2"], 1.0), 0.0)
    return ratio, e, float(kk.sum()), float(ratio.max())


def refine(bl: dict, kk: np.ndarray, gain: float = 1.0, rounds: int = 3):
    """Shrink every block's keep-count while the block still passes."""
    nb = bl["nb"]
    for _ in range(rounds):
        moved = False
        for delta in (-1024, -512, -256, -128, -64, -32, -16, -12, -8, -6, -5,
                      -4, -3, -2, -1):
            cand = np.clip(kk + delta, 0, nb)
            ratio, _, _, _ = evaluate(bl, cand)
            ok = ratio.max(axis=1) <= gain
            better = ok & (cand < kk)
            if better.any():
                kk = np.where(better, cand, kk)
                moved = True
        if not moved:
            break
    return kk


def bessel_lb(bl: dict) -> tuple[int, list[dict]]:
    """Method-independent lower bound on K for this block-parity basis.

    Any approximation with k characters in a block has L2 error at least the
    sum of squares of the (2^b - k) *smallest* local Walsh coefficients
    (Bessel).  Since max|x| >= rms and tol is smallest at the block's top x,
        max_i |e_i|/tol_i >= sqrt(tail_min(k)) * 2^24 * sqrt(x_max) / sqrt(n).
    A block with this bound > 1 cannot pass with k terms whatever the fitting
    method, so the sum of the per-block minimal k is a lower bound on K.
    """
    nb = bl["nb"]
    a = np.sort(np.abs(bl["c"]), axis=1)               # ascending
    sq = a ** 2
    # tail_min(k) = sum of the (nb-k) smallest = prefix sum of the ascending
    pre = np.concatenate([np.zeros((bl["hb"], 1)), np.cumsum(sq, axis=1)], axis=1)
    kk = np.arange(nb + 1)[None, :]
    # x_max of each block: last legal x
    xmax = np.array([np.max(np.arange(nb)[bl["mask2"][h]]) + h * nb
                     for h in range(bl["hb"])], dtype=np.float64)
    bound = np.sqrt(pre[:, ::-1]) * 2.0**24 * np.sqrt(xmax)[:, None] / math.sqrt(nb)
    rows = []
    for h in range(bl["hb"]):
        ok = np.flatnonzero(bound[h] <= 1.0)
        rows.append(int(ok[0]) if ok.size else nb)
    rows = np.array(rows, dtype=np.int64)
    return int(rows.sum()), [{"hmax": int(rows.max()), "hmean": float(rows.mean())}]


def lawson_minimax(A: np.ndarray, g: np.ndarray, tol: np.ndarray,
                   iters: int = 300) -> tuple[float, np.ndarray]:
    """Lawson's algorithm: weighted LS iterations converging to the min-max fit."""
    B = A / tol[:, None]
    y = g / tol
    n, k = B.shape
    w = np.full(n, 1.0 / n)
    best = (np.inf, np.zeros(k))
    for _ in range(iters):
        G = B.T @ (w[:, None] * B)
        c = np.linalg.solve(G + 1e-14 * np.eye(k), B.T @ (w * y))
        r = np.abs(B @ c - y)
        if r.max() < best[0]:
            best = (float(r.max()), c)
        w = w * r
        s = w.sum()
        if s <= 0:
            break
        w = w / s + 1e-12 / n
    return best


def chebyshev_block(bl: dict, h: int, k: int) -> dict:
    """Exact-enough min-max (Lawson) vs LS on one block, same support size."""
    nb = bl["nb"]
    idx = bl["order"][h, :k]
    L = np.arange(nb, dtype=np.int64)
    chi = 1.0 - 2.0 * (np.bitwise_count(idx[:, None] & L[None, :]) & 1)
    m = bl["mask2"][h]
    A, g, tol = chi.T[m], bl["g2"][h][m], bl["tol2"][h][m]
    ls_ratio = float(np.max(np.abs(A @ bl["c"][h][idx] - g) / tol))
    mm_ratio, _ = lawson_minimax(A, g, tol)
    return {"h": int(h), "k": int(k), "ls_ratio": ls_ratio,
            "minimax_ratio": mm_ratio,
            "gain": ls_ratio / mm_ratio if mm_ratio > 0 else float("inf")}


def evaluate_restricted(bl: dict, keep_idx: np.ndarray):
    """Keep a fixed local subset in every block (block-dependent angles)."""
    ck = np.zeros_like(bl["c"])
    ck[:, keep_idx] = bl["c"][:, keep_idx]
    p = fwht_axis1(ck)
    e = p - bl["g2"]
    e = e - np.round(e)
    m = bl["mask2"]
    ratio = np.where(m, np.abs(e) / np.where(m, bl["tol2"], 1.0), 0.0)
    return ratio, e, float(keep_idx.size * bl["hb"]), float(ratio.max())


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "N": N, "M": M, "legal_x": M,
        "target": "T(x)=1/sqrt(x) turns, official target_units (x=1 -> 0)",
        "tol": "tol(x)=2^-24/sqrt(x), official tol_units",
        "bs": {}, "ks": KS,
    }
    for b in BS:
        tb = time.time()
        bl = load_blocks(b)
        nb, hb = bl["nb"], bl["hb"]
        print(f"\n=== b={b}  block size {nb}  blocks {hb}  "
              f"full-basis max err {bl['full_basis_err']:.2e} turns  "
              f"({time.time()-tb:.1f}s)")
        garr = np.array(kgrid(nb), dtype=np.int64)
        curves = np.empty((garr.size, hb))
        for i, k in enumerate(garr):
            ratio, _, _, _ = evaluate(bl, np.full(hb, int(k)))
            curves[i] = ratio.max(axis=1)
        curves = np.minimum.accumulate(curves, axis=0)     # monotone envelope

        # ---- water-fill over thresholds t --------------------------------
        lo = max(curves[-1].max(), 1e-6)
        ts = np.geomspace(max(lo, 1e-3), 3e7, 400)
        allocs: dict[bytes, dict] = {}
        for t in ts:
            i = np.argmax(curves <= t, axis=0)
            ok = curves[i, np.arange(hb)] <= t
            i = np.where(ok, i, garr.size - 1)
            kk = garr[i]
            key = kk.astype(np.int32).tobytes()
            a = allocs.get(key)
            if a is None:
                _, _, K, worst = evaluate(bl, kk)
                a = {"K": int(K), "worst": worst, "kmin": int(kk.min()),
                     "kmax": int(kk.max()), "nz": int((kk > 0).sum()),
                     "kmean": float(kk.mean())}
                allocs[key] = a
        steps = sorted(allocs.values(), key=lambda r: r["K"])
        best_at = {}
        for Kreq in KS:
            cand = [s for s in steps if s["K"] <= Kreq]
            if cand:
                best_at[Kreq] = min(cand, key=lambda s: s["worst"])
        for Kreq in KS:
            s = best_at.get(Kreq)
            if s:
                print(f"  K<={Kreq:5d}: best worst={s['worst']:.4e} "
                      f"(uses K={s['K']}, k_h {s['kmin']}..{s['kmax']}, "
                      f"{s['nz']}/{hb} blocks)")

        # ---- minimum passing K, refined to +-1 per block ------------------
        coarse = garr[np.argmax(curves <= 1.0, axis=0)]
        coarse = np.where(curves[np.argmax(curves <= 1.0, axis=0),
                                 np.arange(hb)] <= 1.0, coarse, nb)
        rat0, _, K0, w0 = evaluate(bl, coarse.astype(np.int64))
        kk = refine(bl, coarse.astype(np.int64))
        rat, err, Kpass, worst = evaluate(bl, kk)
        margin = float((bl["tol2"] - np.abs(err))[bl["mask2"]].min())
        fail = int((rat.max(axis=1) > 1.0).sum())
        print(f"  MIN PASSING K = {int(Kpass)}  worst={worst:.4f} "
              f"margin={margin:.3e} turns (coarse {int(K0)} -> refined, "
              f"k_h {kk.min()}..{kk.max()}, failing blocks {fail}, "
              f"block0 k={int(kk[0])})")
        # design allocation with headroom: smallest grid allocation whose
        # measured worst ratio is <= 0.5 (then margin >= 0.5*tol_min)
        cand = [s for s in steps if s["worst"] <= 0.5]
        dstep = min(cand, key=lambda r: r["K"]) if cand else None
        if dstep:
            print(f"  design (ratio<=0.5): K={dstep['K']} "
                  f"worst={dstep['worst']:.4f} -> margin >= "
                  f"{0.5*float(np.load(ROT33/'tol_units.npy')[-1])/2.0**64:.3e} turns")
        # min-max fitting sensitivity: allow a G-times larger per-block ratio
        gains = {}
        for G in (1.16, 1.43, 1.71, 2.0, 4.0):
            kg = refine(bl, kk.copy(), gain=G, rounds=2)
            _, _, Kg, wg = evaluate(bl, kg)
            gains[str(G)] = {"K": int(Kg), "worst": wg,
                             "dK": int(Kg - Kpass)}
            print(f"  minimax-equivalent threshold {G:4.2f}: K={int(Kg):7d} "
                  f"({100.0*(Kg-Kpass)/Kpass:+5.1f}%) worst={wg:.4f}")
        # Bessel method-independent lower bound
        Klb, lbinfo = bessel_lb(bl)
        print(f"  Bessel lower bound on K (any k-term approximation): {Klb}"
              f"  ({100.0*(Klb-Kpass)/Kpass:+.1f}% vs water-filled LS K)")

        # allocation profile by octave of the block index
        prof = []
        hs = np.arange(hb)
        buckets = [(0, 1)] + [(1 << j, 1 << (j + 1)) for j in range(0, 24)]
        for j, (lo_h, hi_h) in enumerate(buckets):
            sel = (hs >= lo_h) & (hs < hi_h)
            if not sel.any():
                continue
            prof.append({"octave": (j - 1), "blocks": int(sel.sum()),
                         "x_center": float((lo_h + 0.5) * nb),
                         "k_mean": float(kk[sel].mean()),
                         "k_min": int(kk[sel].min()), "k_max": int(kk[sel].max()),
                         "K": int(kk[sel].sum())})

        # ---- shared support ---------------------------------------------
        energy = (bl["c"] ** 2).sum(axis=0)
        shared_order = np.argsort(-energy)
        shared = []
        for KL in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64):
            if KL > nb:
                break
            _, _, K, w = evaluate_restricted(bl, np.sort(shared_order[:KL]))
            shared.append({"KL": KL, "K": int(K), "worst": w})
            print(f"  shared support K_L={KL:3d} (K={K:7.0f}): worst={w:.4e}")

        # ---- haar --------------------------------------------------------
        A = bl["c"][:, 0]
        d = np.abs(np.diff(A))
        tblock = bl["tol2"].min(axis=1)
        thr = 0.5 * np.minimum(tblock[:-1], tblock[1:])
        n_above = int((d > thr).sum())
        rel = d / np.maximum(A[:-1], 1e-300)
        pc = np.abs(A[:, None] - bl["g2"]) / np.where(bl["mask2"], bl["tol2"], 1)
        pc = np.where(bl["mask2"], pc, 0.0)
        haar = {"n_pairs": int(d.size), "n_above_tol": n_above,
                "frac_above": n_above / max(d.size, 1),
                "rel_detail_min": float(rel.min()),
                "rel_detail_max": float(rel.max()),
                "pc_const_worst": float(pc.max())}
        print(f"  haar: {n_above}/{d.size} adjacent-block differences above "
              f"tolerance; rel detail {rel.min():.2e}..{rel.max():.2e}; "
              f"pure piecewise-constant worst = {pc.max():.3e}")

        # ---- chebyshev (min-max) check on the worst blocks ---------------
        lp = []
        if b in LP_B:
            for h in np.argsort(-rat.max(axis=1))[:5]:
                k = int(kk[h])
                if 2 <= k <= 400:
                    lp.append(chebyshev_block(bl, int(h), k))
            for r in lp:
                print(f"  min-max block h={r['h']:5d} k={r['k']:4d}: "
                      f"LS ratio {r['ls_ratio']:.4f} -> Lawson "
                      f"{r['minimax_ratio']:.4f} (gain {r['gain']:.2f}x)")

        result["bs"][str(b)] = {
            "nb": nb, "hb": hb, "full_basis_err": bl["full_basis_err"],
            "curves": {"grid": [int(v) for v in garr],
                       "pct_at_grid": {str(int(k)): [
                           float(np.percentile(curves[i], q))
                           for q in (0, 50, 90, 100)]
                           for i, k in enumerate(garr)}},
            "waterfill": steps, "best_at_K": {str(k): v for k, v in best_at.items()},
            "Kpass": int(Kpass), "Kpass_coarse": int(K0), "worst_at_Kpass": worst,
            "worst_coarse": w0, "failing_blocks": fail, "block0_k": int(kk[0]),
            "kmin": int(kk.min()), "kmax": int(kk.max()),
            "margin_at_Kpass": margin,
            "design": dstep,
            "gains": gains, "K_lower_bound": Klb, "lb_info": lbinfo,
            "profile": prof, "shared": shared, "haar": haar, "lp": lp,
            "K_at_K_L_1": hb,
        }
        print(f"  ({time.time()-tb:.1f}s)")
    (OUT / "block_fit.json").write_text(
        json.dumps(result, indent=1, default=float))
    print(f"\nwrote {OUT/'block_fit.json'}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
