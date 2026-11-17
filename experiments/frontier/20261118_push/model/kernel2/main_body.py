"""Kernel #2: two free-degree-of-freedom checks on the shipped chem submission.

B2  joint (w, u) row permutation inside each rho block  -> metrics invariant?
B3  one-body row permutation only                        -> metrics invariant?
B4  ANGLE circuits padded to 128 qubits with idle qubits -> Q_total unchanged?
"""

import base64
import importlib.util
import json
import pathlib
import sys
import tempfile
import traceback
import zlib

import numpy as np


def decode(b64, dtype, shape):
    return np.frombuffer(zlib.decompress(base64.b64decode(b64)), dtype=dtype).reshape(shape).copy()


M = META
WORDS = decode(WORDS_B64, np.uint8, tuple(M["words_shape"])).astype(np.int64)
W = decode(W_B64, np.float32, tuple(M["W_shape"]))
H2 = decode(H2I_B64, np.float32, tuple(M["H2_shape"]))
TREE = decode(TREE_B64, np.int8, tuple(M["tree_shape"])).astype(np.int64)
R, B, C = W.shape

COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for up in (p.parents[1], p.parents[2], p.parents[3]):
        if (up / "kickmix").is_dir():
            COMP = up
            break
    if COMP:
        break
sys.path.insert(0, str(COMP / "verifiers"))
sys.path.insert(0, str(COMP / "kickmix"))
import kickmix as km  # noqa: E402
import dfthcsos.verify as V  # noqa: E402

U0 = np.zeros((R, B, 76), dtype=np.float32)
SHIFT = np.zeros((76 * 77 // 2,), dtype=np.float32)


def inputs_for(w):
    return V.load_inputs({"U": U0, "W": w, "H2_I": H2, "H1_I": np.float32(0.0), "Hsym_lower": SHIFT})


BASE = inputs_for(W)
ref = V.evaluate_words(BASE, WORDS, TREE, 8)
KEYS = ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")
OUT = {"reference": {k: float(ref[k]) for k in KEYS}}
print("reference", OUT["reference"], flush=True)


def compare(tag, words, w):
    m = V.evaluate_words(inputs_for(w), words, TREE, 8)
    d = {k: float(m[k]) - float(ref[k]) for k in KEYS}
    rel = {k: abs(d[k]) / max(abs(float(ref[k])), 1e-30) for k in KEYS}
    out = {"tag": tag, "passes": bool(V.passes_accuracy(m)),
           "max_rel_delta": max(rel.values()), "delta": d,
           "lambda_eff": float(m["lambda_eff"]), "err2_mHa": 1e3 * m["error_2"]}
    print("EXP", out, flush=True)
    return out


# ---- B2: joint permutation of (b within rho, words) --------------------------
perm = np.arange(WORDS.shape[0])
permW = np.arange(W.shape[0])
permW[:] = np.arange(W.shape[0])
w_perm = W.copy()
for r in range(R):
    s = 76 + r * B
    blk = np.arange(s, s + B)
    order = np.lexsort(WORDS[blk].T[::-1])
    perm[s:s + B] = blk[order]
    w_perm[r] = W[r][order]
OUT["B2_joint_block_perm"] = compare("joint (w,u) within rho", WORDS[perm], w_perm)

# ---- B3: one-body rows only -------------------------------------------------
perm1 = np.arange(WORDS.shape[0])
perm1[:76] = np.lexsort(WORDS[:76].T[::-1])
OUT["B3_onebody_perm"] = compare("one-body rows only", WORDS[perm1], W)

# ---- B3b: the WRONG permutation (words only) documents the constraint -------
OUT["B3b_words_only"] = compare("words only, w untouched", WORDS[perm], W)

# ---- B4: idle qubits up to 128 are free ------------------------------------
spec = importlib.util.spec_from_file_location(
    "akrc", COMP / "verifiers/dfthcsos/example_submission/angle_k_reference_circuit.py")
akrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(akrc)


def family_with_width(words, brot, J, width):
    out = []
    for c in akrc.build_angle_k_family(words, brot, J):
        text = str(c).rstrip("\n")
        extra = []
        nq = c.num_qubits
        for j in range(nq, width):
            extra.append(f"X q{j}")
            extra.append(f"X q{j}")
        out.append(km.Circuit(text + "\n" + "\n".join(extra) + "\n") if extra else c)
    return out


def score_family(width, tag):
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"w{width}_"))
    fam = family_with_width(WORDS, 8, 5, width)
    for k, c in enumerate(fam):
        c.to_file(d / f"angle_k_{k}.kmb", format="kmb")
    np.savez(d / "submission.npz", U=U0, W=W, H2_I=H2, H1_I=np.float32(0.0), Hsym_lower=SHIFT,
             tree_edges=TREE)
    res = V.evaluate_circuits(BASE, str(d), TREE)
    rr = res["resources"]
    out = {"tag": tag, "max_circuit_qubits": rr["angles_qubits"], "angles_temp": rr["angles_temporary_qubits"],
           "heur_temp": rr["heuristic_temporary_qubits"], "Q_total": rr["qubits"],
           "T_total": rr["toffoli"], "score": float(res["score"]),
           "rejected": V.rejection_reason(res["metrics"], rr)}
    print("EXP-B4", out, flush=True)
    return out


for width, tag in ((61, "reference width"), (128, "padded to the 128-qubit cap")):
    try:
        OUT[f"B4_{width}"] = score_family(width, tag)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        OUT[f"B4_{width}"] = {"error": f"{type(exc).__name__}: {exc}"}

print("RESULT_JSON " + json.dumps(OUT), flush=True)
