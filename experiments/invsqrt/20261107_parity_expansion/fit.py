"""Parity-expansion fit of T(x)=1/sqrt(x) on the legal domain.

Two variants requested by the task:

  A. direct least-squares fit of the unwrapped target T (turns),
  B. Walsh-Hadamard transform coefficients of exp(2 pi i T), top-K kept.

Both end in the same object: a K-term parity (Walsh) sum
p(x) = sum_{S in F} c_S (-1)^popcount(S&x).  For any support F the L2-optimal
coefficients on the legal domain solve G c = b with

  G[S,S'] = sum_{x legal} chi_S(x) chi_S'(x) = What_{1_legal}[S xor S']
  b[S]    = sum_{x legal} chi_S(x) T(x)        = What_{T*1_legal}[S]

so one WHT of the indicator and one of the target give the exact normal
equations for any support (no sampling).  Truncated-transform (B) and refit (A)
are both reported, plus the exact reconstruction through the inverse WHT.

Notes
  * x=1 has target exactly 1 turn == 0 mod 1, so the fit target at x=1 is 0.
    That keeps the LS from chasing a 1-turn spike that is free mod 1.
  * error is reduced mod 1 before the tolerance comparison.
  * tol(x) = 2^-24/sqrt(x) read from the rot33 artifact (official profile).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_parity_expansion"
N = 1 << 22
M = 3_133_452
KS = [41, 96, 200, 500, 1000, 2000]


def fwht(a: np.ndarray) -> np.ndarray:
    a = np.array(a, dtype=np.float64, copy=True)
    n = a.size
    h = 1
    while h < n:
        b = a.reshape(-1, 2, h)
        u = b[:, 0, :].copy()
        v = b[:, 1, :].copy()
        b[:, 0, :] = u + v
        b[:, 1, :] = u - v
        h *= 2
    return a


def load() -> tuple[np.ndarray, np.ndarray]:
    tol = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    # fit target: g(x)=1/sqrt(x); x=1 -> 0 (1 turn == 0 mod 1)
    xv = np.arange(1, M + 1, dtype=np.float64)
    g = 1.0 / np.sqrt(xv)
    g[0] = 0.0
    return tol, g


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    tol, g = load()

    gm = np.zeros(N)
    gm[1:M + 1] = g                      # fit target on the cube (0 outside legal)
    ind = np.zeros(N)
    ind[1:M + 1] = 1.0
    What_g = fwht(gm)
    What_ind = fwht(ind)
    order_legal = np.argsort(np.abs(What_g))[::-1]
    print(f"legal-domain ordering built ({time.time()-t0:.1f}s); "
          f"top |b|/N = {np.abs(What_g[order_legal[:5]])/N}")

    # extension-based orderings from spectrum.py (approach B selection)
    orders = {"legal": order_legal}
    for kind in ("zero", "const", "natural"):
        f = OUT / f"coef_{kind}.npz"
        if f.exists():
            z = np.load(f)
            orders[kind] = z["order"]

    rows = []
    for K in KS:
        for name, order in orders.items():
            S = order[:K].astype(np.int64)
            idx = S[:, None] ^ S[None, :]
            G = What_ind[idx]
            b = What_g[S]
            # truncated transform coefficients (approach B, no refit)
            if name == "legal":
                c_trunc = What_g[S] / What_ind[0]
            else:
                z = np.load(OUT / f"coef_{name}.npz")
                cmap = {int(s): v for s, v in zip(z["order"][:K], z["coef"][:K])}
                c_trunc = np.array([cmap[int(s)] for s in S])
            # LS refit (approach A).  The legal domain is a contiguous prefix
            # [1, M], so characters that differ by a product of high bits that
            # vanishes on [1, M] are exactly dependent there; the Gram matrix is
            # numerically singular and the refit is done with an eigen
            # pseudo-inverse at a relative cutoff of 1e-10.
            ev, V = np.linalg.eigh(G)
            cut = ev.max() * 1.0e-10
            keep_e = ev > cut
            c_ls = V @ (((V.T @ b) / np.where(keep_e, ev, 1.0)) * keep_e)
            cond = float(ev.max() / max(ev[keep_e].min(), 1e-300))
            eff_rank = int(keep_e.sum())
            for tag, c in (("trunc", c_trunc), ("ls", c_ls)):
                C = np.zeros(N)
                C[S] = c
                p = fwht(C)[1:M + 1]
                e = p - g
                e -= np.round(e)
                ratio = np.abs(e) / tol
                j = int(np.argmax(ratio))
                rows.append({"K": K, "order": name, "fit": tag,
                             "max_ratio": float(ratio.max()),
                             "worst_x": j + 1,
                             "max_abs": float(np.abs(e).max()),
                             "rms_ratio": float(np.sqrt(np.mean(ratio**2))),
                             "cond": cond, "eff_rank": eff_rank,
                             "coef_max_abs": float(np.abs(c).max())})
            print(f"K={K:5d} {name:7s} trunc {rows[-2]['max_ratio']:.3e} "
                  f"ls {rows[-1]['max_ratio']:.3e} rms {rows[-1]['rms_ratio']:.2e} "
                  f"rank {eff_rank}/{K} |c|max {rows[-1]['coef_max_abs']:.1e} "
                  f"({time.time()-t0:.1f}s)")
    (OUT / "fit_grid.json").write_text(json.dumps(rows, indent=2))
    print("wrote", OUT / "fit_grid.json")


if __name__ == "__main__":
    main()
