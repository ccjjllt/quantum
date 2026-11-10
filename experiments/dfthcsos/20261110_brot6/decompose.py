"""brot=6 vs brot=8门失败分解:同U/W在两种字宽下signed编码+evaluate_words精确数.

只做精确算术,无shots,无verify.py调用,不跑验证器.
输入: seed(未训练)与300步探针(连续最优点);树固定b9eced3e log-depth树.
输出: artifacts/20261110_brot6/decompose.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers"))

from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    build_h1_prime,
    reconstruct_u_vectors,
    reconstruct_x,
)
from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

N = 76


def signed_angles(vectors, edges):
    a = np.array(vectors, dtype=np.float64)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    theta = np.zeros((len(a), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        s = np.where(a[:, p] > 0, 1.0, np.where(a[:, p] < 0, -1.0, np.where(a[:, q] > 0, -1.0, 1.0)))
        theta[:, t] = np.arctan2(s * a[:, q], s * a[:, p])
        a[:, p] = s * np.hypot(a[:, p], a[:, q])
        a[:, q] = 0.0
    return theta / np.pi


def signed_words(vectors, edges, brot):
    s = 1 << (brot - 1)
    k = np.clip(np.round(signed_angles(vectors, edges) * s), -s // 2, s // 2 - 1)
    return k.astype(np.int64) % (1 << brot)


def encode_all(inputs, edges, brot):
    U = np.asarray(inputs.params["U"], dtype=np.float64)
    R, B, n = U.shape
    two = signed_words(U.reshape(-1, n), edges, brot)

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([signed_words(vecs.T, edges, brot), two])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree_npz", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("factors", nargs="+", type=Path)
    ap.add_argument("--brots", nargs="+", type=int, default=[8, 6])
    a = ap.parse_args()
    zt = np.load(a.tree_npz, allow_pickle=False)
    edges = np.array(zt["tree_edges"] if "tree_edges" in zt.files else zt["arr_0"])
    out = {"rows": []}
    for f in a.factors:
        inputs = load_inputs(f)
        R, B, C = (int(x) for x in inputs.w.shape)
        for brot in a.brots:
            t0 = time.time()
            words = encode_all(inputs, edges, brot)
            m = evaluate_words(inputs, words, edges, brot)
            row = {
                "factor": str(f),
                "R": R, "B": B, "C": C, "brot": brot,
                "error_1_Ha": float(m["error_1"]),
                "error_2_Ha": float(m["error_2"]),
                "error_1_mHa": float(m["error_1"]) * 1e3,
                "error_2_mHa": float(m["error_2"]) * 1e3,
                "Lambda": float(m["Lambda"]),
                "E_gap": float(m["E_gap"]),
                "lambda_eff": float(m["lambda_eff"]),
                "encode_seconds": round(time.time() - t0, 1),
            }
            out["rows"].append(row)
            print(json.dumps(row), flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote " + str(a.out))


if __name__ == "__main__":
    main()
