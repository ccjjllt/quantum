"""Shared local infrastructure: reference integrals, pair-space H, official metrics.

Everything here is the competition's own code (`data/competition/verifiers/dfthcsos/scoreinfra`)
plus the pair-space (vech) form of the error_2 target used by the shape fits.
No kickmix, no circuit: lambda_eff / error_2 / E_gap are pure linear algebra on
(U, w, W, angle_words) and the reference FCIDUMP.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
V = ROOT / 'data/competition/verifiers/dfthcsos'
CACHE = ROOT / 'artifacts/20261117_lambda_measure'
CACHE.mkdir(parents=True, exist_ok=True)
N = 76


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


refm = _load('dfthcsos.scoreinfra.reference', str(V / 'scoreinfra/reference.py'))
dfm = _load('dfthcsos.scoreinfra.dfthc_math', str(V / 'scoreinfra/dfthc_math.py'))

E_UPPER = refm.UPPER_ENERGY          # -22140.27335
E_GAP_FLOOR = 3.914898
LAMBDA_FLOOR = 49.0
E2_GATE = 0.020                      # Hartree == 20 mHa


def reference():
    ref = refm.load_reference(refm.check_fcidump())
    sh = refm.load_fixed_shifts()
    S = dfm.symmetric_from_lower(sh['Hsym_lower'], N).astype(np.float64)
    beta1 = float(sh['H1_I']) - 0.5 * float(np.trace(S))
    return ref, S, beta1


def pair_space(ref, S):
    """The (2926, 2926) vech target H of error_2, plus the pair bookkeeping."""
    tei = np.asarray(ref['tei'], dtype=np.float64)
    pairs = [(p, q) for p in range(N) for q in range(p, N)]
    PA = np.array(pairs)
    wgt = np.array([1.0 if p == q else 2.0 for p, q in pairs])
    sqw = np.sqrt(wgt)
    flat = np.array([p * N + q for p, q in pairs])
    isdiag = np.array([p == q for p, q in pairs])
    tei2 = tei.reshape(N * N, N * N)
    Gm = np.empty((len(pairs), len(pairs)))
    for a, (p, q) in enumerate(pairs):
        Gm[a] = (tei2[p * N + q, flat]
                 + 0.5 * S[p, q] * isdiag
                 + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0))
    Gm = 0.5 * (Gm + Gm.T)
    H = sqw[:, None] * Gm * sqw[None, :]
    return dict(H=H, PA=PA, sqw=sqw, isdiag=isdiag, NS=len(pairs))


def cached_pair_space():
    f = CACHE / 'pair_H.npz'
    if f.exists():
        z = np.load(f)
        return dict(H=z['H'], PA=z['PA'], sqw=z['sqw'], isdiag=z['isdiag'],
                    NS=int(z['NS']))
    ref, S, _ = reference()
    ps = pair_space(ref, S)
    np.savez(f, H=ps['H'], PA=ps['PA'], sqw=ps['sqw'], isdiag=ps['isdiag'],
             NS=ps['NS'])
    return ps


def floor_mha(ev, K, neg2):
    return 1e3 * float(np.sqrt(np.sum(np.maximum(ev[K:], 0) ** 2) + neg2))


# ---------------------------------------------------------------- official metrics
def metrics_from_vectors(u_all, w, W, ref, S, beta1):
    """Official `evaluate_dfthc_vectors` (no angle quantization)."""
    return dfm.evaluate_dfthc_vectors(u_all, w, W, S, beta1, ref,
                                      energy_upper=E_UPPER)


def metrics_from_words(words, w, W, tree, ref, S, beta1, brot):
    """Official `evaluate_dfthc_angle_words` (the verifier path)."""
    return dfm.evaluate_dfthc_angle_words(words, w, W, S, beta1, ref,
                                         brot=brot, tree_edges=tree,
                                         energy_upper=E_UPPER)


def decompose(u_all, w, W, ref, S, beta1):
    """The metric breakdown the score is built from."""
    ref = ref
    u = np.asarray(u_all, float)
    u = u / np.linalg.norm(u, axis=1, keepdims=True)
    w = np.asarray(w, float)
    W = np.asarray(W, float)
    one_body, u_b_rho = dfm.split_u_vectors(u, w)
    X = dfm.reconstruct_x(u_b_rho, w)
    X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
    h1_thc = np.asarray(ref['oei'], float) - 0.5 * np.einsum('prrq->pq', ref['tei'])
    h1p = dfm.build_h1_prime(h1_thc, S, beta1, ref['electrons'], W, X)
    ev = np.linalg.eigvalsh(h1p)
    lam_h1 = float(np.abs(ev).sum())
    tr = float(np.trace(h1p))
    a = np.abs(w).sum(axis=1)
    wB = W + w.sum(axis=1)
    lam_h2 = float(0.25 * np.sum((a + np.abs(wB)) ** 2))
    sumW2 = float(np.sum(W ** 2))
    e_sos = float(ref['ecore'] - ref['electrons'] * beta1 - (lam_h1 - tr)
                  - 0.5 * sumW2)
    gap = E_UPPER - e_sos
    Lam = lam_h1 + lam_h2
    le = float(np.sqrt(gap * (2 * Lam - gap))) if 0 < gap < 2 * Lam else float('nan')
    return dict(lam_h1=lam_h1, lam_h2=lam_h2, Lambda=Lam, tr_h1p=tr,
                sum_a2=float(np.sum(a ** 2)), sum_aW=float(np.sum(a * np.abs(wB))),
                sumW2=sumW2, E_SOS=e_sos, E_gap=gap, lambda_eff=le,
                neg_eig_sum=float(2 * np.abs(ev[ev < 0]).sum()), nnzW=int(np.count_nonzero(W)))


def e2_pair(Y, H):
    """error_2 (mHa) from the vech-space factor Y (NS, K): ||YY^T - H||_F."""
    return 1e3 * float(np.linalg.norm(Y @ Y.T - H))
