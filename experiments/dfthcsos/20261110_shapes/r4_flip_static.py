"""R4/B131/C83 等价翻转降T空间静态分析(零训练,不跑验证器).

1. SpinFreeData_V1 精确heuristic(R4在brot 6/8下).
2. 规范翻转机制演示:在R5种子U上随机翻转部分行符号->重编码->
   evaluate_words精确metrics对比(P0已在(8,143,44)实表证明逐位不变;
   本演示在(5,135,70)复现机制;代码路径与形状无关,故R4同理)。
3. 结论只看数字,不做loader重综合(那是P0式campaign,需先有过门R4表)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers"))

from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    build_h1_prime,
    reconstruct_u_vectors,
    reconstruct_x,
)
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402

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


def encode_from_U(U, inputs, edges, brot):
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


def tree_angles(vectors, edges):
    u = np.array(vectors, dtype=np.float64, ndmin=2)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    theta = np.zeros((len(u), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        theta[:, t] = np.arctan2(u[:, q], u[:, p])
    return np.mod(theta / np.pi, 2.0)


def unsigned_words(vectors, edges, brot):
    scaled = np.mod(tree_angles(vectors, edges), 2.0) * (1 << (brot - 1))
    return np.floor(scaled + 0.5).astype(np.int64) % (1 << brot)


def encode_unsigned_from_U(U, inputs, edges, brot):
    R, B, n = U.shape
    two = unsigned_words(U.reshape(-1, n), edges, brot)

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([unsigned_words(vecs.T, edges, brot), two])


def main():
    outdir = Path("artifacts/20261110_shapes")
    outdir.mkdir(parents=True, exist_ok=True)
    rep: dict = {}

    # 1. R4 heuristic精确值(brot 6/8)
    rep["r4_heuristic"] = {}
    for brot in (6, 8):
        hc = heuristic_costs(N, 4, 131, 83, brot)
        rep["r4_heuristic"][str(brot)] = {
            "toffoli": int(hc["toffoli"]),
            "outer": int(hc["outer_state_prep_toffoli"]),
            "inner": int(hc["inner_state_prep_toffoli"]),
            "givens": int(hc["givens_rotations_toffoli"]),
            "persist": int(hc["persistent_qubits"]),
            "temp_max": int(hc["temporary_qubits"]),
        }
    print("R4 heuristic:", json.dumps(rep["r4_heuristic"], indent=1))

    # 2. 翻转机制演示(R5种子U,形状无关代码路径)
    inputs = load_inputs("artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz")
    zt = np.load("artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz", allow_pickle=False)
    edges = np.array(zt["tree_edges"])
    brot = 8
    U0 = np.asarray(inputs.params["U"], dtype=np.float64)
    w0 = encode_from_U(U0, inputs, edges, brot)
    m0 = evaluate_words(inputs, w0, edges, brot)

    rng = np.random.default_rng(20261110)
    R, B, _ = U0.shape
    nrows = R * B
    flip = np.zeros(nrows, dtype=bool)
    flip[rng.choice(nrows, size=150, replace=False)] = True  # 翻转150/675 two-body行
    U1 = U0.copy().reshape(-1, N)
    U1[flip] *= -1.0
    U1 = U1.reshape(R, B, N)
    w1 = encode_from_U(U1, inputs, edges, brot)
    m1 = evaluate_words(inputs, w1, edges, brot)

    keys = ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")
    rep["flip_demo"] = {
        "shape": [R, B, 70], "n_two_body_rows": nrows, "n_flipped": 150, "brot": brot,
        "signed_gauge": {
            "n_word_entries_changed": int(np.sum(w0 != w1)),
            "metrics_base": {k: float(m0[k]) for k in keys},
            "metrics_flipped": {k: float(m1[k]) for k in keys},
            "bitwise_identical": bool(all(m0[k] == m1[k] for k in keys)),
        },
    }

    # unsigned规范对照:同一翻转在unsigned编码下是否产生不同字表(仍应metrics不变)
    u0 = encode_unsigned_from_U(U0, inputs, edges, brot)
    u1 = encode_unsigned_from_U(U1, inputs, edges, brot)
    mu0 = evaluate_words(inputs, u0, edges, brot)
    mu1 = evaluate_words(inputs, u1, edges, brot)
    rep["flip_demo"]["unsigned_gauge"] = {
        "n_word_entries_changed": int(np.sum(u0 != u1)),
        "metrics_base": {k: float(mu0[k]) for k in keys},
        "metrics_flipped": {k: float(mu1[k]) for k in keys},
        "bitwise_identical": bool(all(mu0[k] == mu1[k] for k in keys)),
    }
    print("flip demo:", json.dumps(rep["flip_demo"], indent=1))

    (outdir / "r4_flip_static.json").write_text(json.dumps(rep, indent=2) + "\n")
    print("wrote artifacts/20261110_shapes/r4_flip_static.json")


if __name__ == "__main__":
    main()
