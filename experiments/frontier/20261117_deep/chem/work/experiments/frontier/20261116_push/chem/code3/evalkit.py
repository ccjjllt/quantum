"""Local (classical) evaluation kit for the shipped dfthcsos chemistry package.

No simulation, no kickmix: the official metric code path (dfthc_math) is pure numpy.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

CHEM = Path(__file__).resolve().parents[1]
REPO = CHEM.parents[3]
REFIT = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_merge/dfthc_refit')
BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
os.environ.setdefault('DFTHC_DATA', str(REPO / 'data' / 'competition'))
sys.path.insert(0, str(REFIT))
sys.path.insert(0, str(Path(os.environ['DFTHC_DATA']) / 'verifiers'))

import encode  # noqa: E402
import paths  # noqa: E402
import refit_weights as rw  # noqa: E402
from dfthcsos.verify import load_inputs  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402

N = 76
R, B, C = 8, 143, 44


def load_pkg(path=BUILD / 'submission.npz'):
    with np.load(path) as z:
        return {k: np.array(z[k]) for k in z.files}


class Eval:
    """Exact metric evaluator for (words, w); offsets W = H2_I - sum_b w follow the weights."""

    def __init__(self, data):
        self.edges = np.asarray(data['tree_edges'], np.int64)
        self.w0 = np.asarray(data['W'], np.float64)
        self.H2_I = np.asarray(data['H2_I'], np.float64)
        self.words = np.asarray(data['angle_words'], np.int64)
        self.brot = 8
        self.inputs = load_inputs(dict(data))
        self.ref = self.inputs.ref
        self.S = self.inputs.S
        self.beta = self.inputs.beta_1
        self.tei = np.asarray(self.ref['tei'], np.float64)
        self.eta = int(self.ref['electrons'])
        self.h1_base = self.ref['h1_thc'] - 0.5 * self.eta * self.S + self.beta * np.eye(N)
        self.energy = float(paths.UPPER_ENERGY - self.ref['ecore'] + self.eta * self.beta)
        self._cache = {}

    # ---- vectors -------------------------------------------------------
    def uvec(self, words=None):
        w = self.words if words is None else np.asarray(words, np.int64)
        two = w[N:]
        u = encode.decode(two, self.edges, self.brot).reshape(R, B, N)
        return u / np.linalg.norm(u, axis=2, keepdims=True)

    def problem(self, words=None):
        key = 'base' if words is None else int(np.asarray(words, np.int64).sum() % (1 << 61))
        if key in self._cache:
            return self._cache[key]
        u = self.uvec(words)
        K, Q, T2 = rw.error_terms(u, self.tei, self.S)
        wp = rw.WeightProblem(u, K, Q, T2, self.h1_base, self.energy)
        if key != 'base':
            self._cache[key] = wp
        return wp

    # ---- metrics -------------------------------------------------------
    def official(self, words=None, w=None):
        """Official metric dict for (words, w) at brot 8."""
        words = self.words if words is None else np.asarray(words, np.int64)
        w = self.w0 if w is None else np.asarray(w, np.float64)
        W = self.H2_I - np.sum(w, axis=1)
        return evaluate_dfthc_angle_words(words, w, W, self.S, self.beta, self.ref,
                                          brot=self.brot, tree_edges=self.edges,
                                          energy_upper=paths.UPPER_ENERGY)

    def e2(self, words=None, w=None):
        """error_2 (Ha) from the exact fixed-vector formula (validated against official)."""
        wp = self.problem(words)
        w = self.w0 if w is None else np.asarray(w, np.float64)
        return wp.evaluate(w, self.H2_I - np.sum(w, axis=1))[0][0]


def fmt(m):
    return (f"e1 {1e3*m['error_1']:.6f} mHa  e2 {1e3*m['error_2']:.7f} mHa  Lambda {m['Lambda']:.6f}  "
            f"E_gap {m['E_gap']:.10f}  lambda_eff {m['lambda_eff']:.8f}")


if __name__ == '__main__':
    import time
    d = load_pkg()
    t0 = time.time()
    ev = Eval(d)
    print('load', round(time.time() - t0, 1), 's')
    t0 = time.time()
    m = ev.official()
    print('official(base):', fmt(m), f'({time.time()-t0:.1f}s)')
    t0 = time.time()
    e2 = ev.e2()
    print('formula e2 (Ha):', e2, 'mHa', 1e3 * e2, f'({time.time()-t0:.1f}s)')
