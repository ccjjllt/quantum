"""Evaluate public DF-THC factorizations that ship angle_words, with the official metrics.

B239_b8 (R=4,B=239,C=128) and M8x156x60_b8 (R=8,B=156,C=60) come from
marculera/dfthc-merge-pipeline and carry angle_words + tree_edges, so their
error_1/error_2/Lambda/E_gap/lambda_eff can be scored directly (no loaders needed).
CPU only.
"""
import json, pathlib, sys, time
import numpy as np

COMP = "/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation"
sys.path.insert(0, COMP + "/kickmix")
sys.path.insert(0, COMP + "/verifiers")
from dfthcsos.verify import load_inputs, evaluate_words, heuristic_costs  # noqa: E402

T0 = time.time()
def say(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

paths = {}
for p in pathlib.Path("/kaggle/input").rglob("*.npz"):
    paths[p.name] = p
say("npz found:", sorted(paths))

out = {}
for name in ("B239_b8.npz", "M8x156x60_b8.npz"):
    p = paths.get(name)
    if not p:
        continue
    d = np.load(p)
    brot = int(d["brot"]) if "brot" in d else 8
    U, W = d["U"], d["W"]
    R, B, C = U.shape[0], U.shape[1], W.shape[2]
    say(name, "U", U.shape, "W", W.shape, "brot", brot)
    try:
        inputs = load_inputs(p)
        m = evaluate_words(inputs, d["angle_words"], d["tree_edges"], brot)
        hc = heuristic_costs(76, R, B, C, brot)
        T = 2 * 4022 + hc["toffoli"]
        Q = hc["qubits"] + 40
        score = m["lambda_eff"] * T * Q
        out[name] = {k: m[k] for k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")} | {
            "R": R, "B": B, "C": C, "brot": brot, "T": T, "Q": Q,
            "TQ": T * Q, "score": score, "vs_ours": score / 294643137.73357135}
    except Exception as e:
        out[name] = {"error": repr(e)[:400]}
    say(name, out[name])
with open("/kaggle/working/pub_chem.json", "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
