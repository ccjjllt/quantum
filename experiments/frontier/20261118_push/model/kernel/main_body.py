"""Kernel body (payload is prepended by build_kernel.py)."""

import base64
import importlib.util
import json
import math
import pathlib
import sys
import tempfile
import traceback
import zlib

import numpy as np


def decode(b64: str, dtype, shape) -> np.ndarray:
    return np.frombuffer(zlib.decompress(base64.b64decode(b64)), dtype=dtype).reshape(shape).copy()


M = META
WORDS = decode(WORDS_B64, np.uint8, tuple(M["words_shape"])).astype(np.int64)
W = decode(W_B64, np.float32, tuple(M["W_shape"]))
H2 = decode(H2I_B64, np.float32, tuple(M["H2_shape"]))
TREE = decode(TREE_B64, np.int8, tuple(M["tree_shape"])).astype(np.int64)
R, B, C = W.shape
print(f"payload: words={WORDS.shape} max={WORDS.max()} W={W.shape} tree={TREE.shape}", flush=True)

COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for up in (p.parents[1], p.parents[2], p.parents[3]):
        if (up / "kickmix").is_dir():
            COMP = up
            break
    if COMP:
        break
assert COMP is not None
sys.path.insert(0, str(COMP / "verifiers"))
sys.path.insert(0, str(COMP / "kickmix"))
print("COMP =", COMP, flush=True)

import kickmix as km  # noqa: E402
import dfthcsos.verify as V  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_vectors, reconstruct_u_vectors  # noqa: E402

PARAMS = {
    "U": np.zeros((R, B, 76), dtype=np.float32),
    "W": W,
    "H2_I": H2,
    "H1_I": np.float32(0.0),
    "Hsym_lower": np.zeros((76 * 77 // 2,), dtype=np.float32),
}
INPUTS = V.load_inputs(PARAMS)
print("inputs loaded; num_vectors =", INPUTS.num_vectors, flush=True)
OUT = {}


def metrics_row(words, brot, note=""):
    m = V.evaluate_words(INPUTS, words, TREE, brot)
    return {
        "note": note, "brot": brot,
        "err1_mHa": 1e3 * m["error_1"], "err2_mHa": 1e3 * m["error_2"],
        "Lambda": m["Lambda"], "E_gap": m["E_gap"], "lambda_eff": m["lambda_eff"],
        "passes": bool(V.passes_accuracy(m)),
    }


def safe(tag, fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        print(f"{tag} EXCEPTION {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        return {"error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------- EXP-A: brot
def exp_a():
    rows = [metrics_row(WORDS, 8, "shipped 8-bit words (control)")]
    for b in (7, 6):
        w = np.rint(WORDS / 2.0 ** (8 - b)).astype(np.int64)
        w = np.clip(w, 0, 2 ** b - 1)
        rows.append(metrics_row(w, b, "round-to-nearest re-quantisation"))
    # continuous limit of the SAME integers (= brot 8 by definition) is skipped;
    # instead report the decode-equivalent float path once as a cross-check.
    u = reconstruct_u_vectors(WORDS / 2.0 ** 7, TREE)
    m = evaluate_dfthc_vectors(u, INPUTS.w, INPUTS.W, INPUTS.S, INPUTS.beta_1, INPUTS.ref,
                               energy_upper=INPUTS.energy_upper)
    rows.append({"note": "float cross-check of the same words", "brot": "float",
                 "err1_mHa": 1e3 * m["error_1"], "err2_mHa": 1e3 * m["error_2"],
                 "Lambda": m["Lambda"], "E_gap": m["E_gap"],
                 "lambda_eff": m["lambda_eff"], "passes": bool(V.passes_accuracy(m))})
    for r in rows:
        print("EXP-A", r, flush=True)
    return rows


OUT["brot_accuracy"] = safe("EXP-A", exp_a)

# ---------------------------------------------------------------- EXP-B: row permutation
def exp_b():
    perm = np.arange(WORDS.shape[0])
    perm[:76] = np.lexsort(WORDS[:76].T[::-1])
    for r in range(R):
        s = 76 + r * B
        blk = np.arange(s, s + B)
        perm[s:s + B] = blk[np.lexsort(WORDS[blk].T[::-1])]
    permuted = WORDS[perm]
    a = V.evaluate_words(INPUTS, WORDS, TREE, 8)
    b = V.evaluate_words(INPUTS, permuted, TREE, 8)
    keys = ("error_1", "error_2", "Lambda", "E_gap")
    d = {k: float(a[k]) - float(b[k]) for k in keys}
    out = {"moved_rows": int((perm != np.arange(len(perm))).sum()), "deltas": d,
           "lambda_eff_natural": float(a["lambda_eff"]), "lambda_eff_permuted": float(b["lambda_eff"]),
           "passes_permuted": bool(V.passes_accuracy(b))}
    print("EXP-B", out, flush=True)
    return out, permuted


OUT["row_permutation"], PERMUTED = safe("EXP-B", exp_b)

# ---------------------------------------------------------------- EXP-C: Q vs J, cap, brot end-to-end
spec = importlib.util.spec_from_file_location(
    "akrc", COMP / "verifiers/dfthcsos/example_submission/angle_k_reference_circuit.py")
akrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(akrc)


def run_family(words, brot, J, tag):
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"chem_{tag}_"))
    fam = akrc.build_angle_k_family(words, brot, J)
    for k, c in enumerate(fam):
        c.to_file(d / f"angle_k_{k}.kmb", format="kmb")
    np.savez(d / "submission.npz", U=PARAMS["U"], W=W, H2_I=H2, H1_I=PARAMS["H1_I"],
             Hsym_lower=PARAMS["Hsym_lower"], tree_edges=TREE)
    res = V.evaluate_circuits(INPUTS, str(d), TREE)
    reason = V.rejection_reason(res["metrics"], res["resources"])
    R_ = res["resources"]
    rec = {"tag": tag, "J": J, "brot": brot, "K": len(fam),
           "angles_qubits": R_["angles_qubits"], "selection": R_["angles_selection_qubits"],
           "words_qubits": R_["angles_persistent_qubits"], "angles_temp": R_["angles_temporary_qubits"],
           "heur_persist": R_["heuristic_persistent_qubits"], "heur_temp": R_["heuristic_temporary_qubits"],
           "angles_toffoli": R_["angles_toffoli"], "T_total": R_["toffoli"], "Q_total": R_["qubits"],
           "lambda_eff": res["metrics"]["lambda_eff"], "err2_mHa": 1e3 * res["metrics"]["error_2"],
           "score": None if not np.isfinite(res["score"]) else float(res["score"]), "rejected": reason}
    print("EXP-C", rec, flush=True)
    return rec


FAM = []
for J in (5, 8, 13):
    FAM.append(safe(f"J{J}", lambda J=J: run_family(WORDS, 8, J, f"b8_J{J}")))
FAM.append(safe("J14", lambda: run_family(WORDS, 8, 14, "b8_J14_cap")))
W7 = np.clip(np.rint(WORDS / 2.0).astype(np.int64), 0, 127)
FAM.append(safe("b7J5", lambda: run_family(W7, 7, 5, "b7_J5")))
if isinstance(PERMUTED, np.ndarray):
    FAM.append(safe("permJ5", lambda: run_family(PERMUTED, 8, 5, "perm_J5")))
OUT["families"] = FAM

print("RESULT_JSON " + json.dumps(OUT), flush=True)
