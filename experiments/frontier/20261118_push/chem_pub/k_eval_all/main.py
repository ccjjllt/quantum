"""Evaluate every public DF-THC factorization that ships angle_words, official metrics.

Extends chem_pub/k_eval to both public datasets.  For each .npz with U/W/H2_I +
angle_words + tree_edges: official evaluate_words -> error_1/error_2/Lambda/E_gap/
lambda_eff; official heuristic_costs -> T_h/Q; T = 2*4022 + T_h (the shipped loader
density held fixed, which is optimistic for files with more rows); score =
lambda_eff * T * Q.  CPU only, nothing submitted.
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
    paths.setdefault(p.name, p)
cands = sorted(n for n, p in paths.items()
               if n != "submission.npz")
say("npz found:", len(paths), cands)

out = {}
for name in cands:
    p = paths[name]
    try:
        with np.load(p) as d:
            if not {"U", "W", "H2_I", "angle_words", "tree_edges"} <= set(d.files):
                continue
            brot = int(d["brot"]) if "brot" in d.files else 8
            U, W, aw = d["U"], d["W"], d["angle_words"]
            R, B, C = U.shape[0], U.shape[1], W.shape[2]
            say(name, "U", U.shape, "W", W.shape, "rows", 76 + R * B,
                "words", aw.shape, "brot", brot)
            inputs = load_inputs(p)
            m = evaluate_words(inputs, d["angle_words"], d["tree_edges"], brot)
            hc = heuristic_costs(76, R, B, C, brot)
            T = 2 * 4022 + hc["toffoli"]
            Q = hc["qubits"] + 40
            score = m["lambda_eff"] * T * Q
            out[name] = {k: m[k] for k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")} | {
                "R": R, "B": B, "C": C, "brot": brot, "rows": 76 + R * B,
                "T": T, "Q": Q, "TQ": T * Q, "score": score,
                "vs_ours": score / 294643137.73357135}
            say(name, {k: out[name][k] for k in ("Lambda", "lambda_eff", "TQ", "score")})
    except Exception as e:
        out[name] = {"error": repr(e)[:300]}
        say(name, "ERROR", repr(e)[:300])

ordered = dict(sorted(out.items(), key=lambda kv: kv[1].get("score", 1e30)))
with open("/kaggle/working/pub_chem_all.json", "w") as f:
    json.dump(ordered, f, indent=1)
print(json.dumps(ordered, indent=1))
