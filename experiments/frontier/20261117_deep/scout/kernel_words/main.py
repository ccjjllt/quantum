"""Screen every public chemistry factorization for OUR exact angle-word table.

Why: our 15 ANGLE loaders are fixed circuits; they load exactly one (1220, 75) word
table (the maoxin123 v27 C44 table, file 93326853, 14,706 Toffolis total). A public
`submission.npz` whose `angle_words` and `tree_edges` are identical to ours is therefore a
drop-in replacement: the official score becomes lambda_eff(that npz) * 14,706 * 427.
Everything else would need its own loaders and is out of scope for a swap.

CPU-only Kaggle kernel; datasets are mounted read-only, nothing is downloaded, nothing is
submitted. Uses the unchanged official `evaluate_words` / `verify` code paths.

Pinned (computed locally with numpy on our shipped npz):
  our submission.npz file sha256  93326853f42800cc5bb6cf8cac44cce456ebf20e01986ae4b1edc13b485b9c9e
  our angle_words bytes sha256    33e671e4a00ae869a151710d76100081f9fafe6db06cff6ac6e2b78eb553c66c
  our tree_edges bytes sha256     3f7a12e756b2e0490f8b3300192454512852e4226ad6d465a4491aba5ce52c26
"""
import hashlib
import json
import pathlib
import shutil
import sys

import numpy as np

OUR_WORDS = "33e671e4a00ae869a151710d76100081f9fafe6db06cff6ac6e2b78eb553c66c"
OUR_TREE = "3f7a12e756b2e0490f8b3300192454512852e4226ad6d465a4491aba5ce52c26"
OUR_T = 14706.0
OUR_Q = 427
OUR_LAMBDA = 46.92171681802858
OUR_CHEM_COST = 294643137.73357135


def digest(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main() -> None:
    comp = next(p.parents[2] for p in pathlib.Path("/kaggle/input").rglob("verifiers/dfthcsos/verify.py"))
    sys.path.insert(0, str(comp / "verifiers"))
    for p in pathlib.Path("/kaggle/input").rglob("kickmix/kickmix.so"):
        sys.path.insert(0, str(p.parent))
        break
    import kickmix  # noqa: F401
    from dfthcsos.verify import evaluate_words, load_inputs, load_tree_edges, verify

    # our loaders (the ratnachand dataset carries them byte-for-byte) and our words
    loaders = next(p.parent for p in pathlib.Path("/kaggle/input").rglob("angle_k_0.kmb")
                   if p.parent.name == "dfthcsos")
    ref_npz = loaders / "submission.npz"
    with np.load(ref_npz) as z:
        ref_words = np.asarray(z["angle_words"])
        ref_tree = np.asarray(z["tree_edges"])
    assert digest(ref_words) == OUR_WORDS, "reference words are not ours"
    assert digest(ref_tree) == OUR_TREE, "reference tree is not ours"

    out = {"our_loaders": str(loaders), "reference_npz": str(ref_npz), "scanned": 0,
           "with_our_words": [], "best_other": None}
    roots = [p for p in pathlib.Path("/kaggle/input").iterdir() if p.is_dir()]
    out["roots"] = [str(r) for r in roots]
    seen = set()
    cands = []
    for r in roots:
        for f in r.rglob("*.npz"):
            cands.append(f)
    out["npz_found"] = len(cands)

    for f in cands:
        try:
            h = hashlib.sha256()
            with f.open("rb") as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    h.update(block)
            key = h.hexdigest()
            if key in seen:
                continue
            seen.add(key)
            try:
                with np.load(f) as z:
                    if "angle_words" not in z.files or "tree_edges" not in z.files:
                        continue
                    w = z["angle_words"]
                    t = z["tree_edges"]
                    if w.shape != ref_words.shape:
                        continue
                    if not (np.array_equal(w, ref_words) and np.array_equal(t, ref_tree)):
                        continue
                inp = load_inputs(f)
                edges = np.asarray(t, dtype=np.int64)
                met = evaluate_words(inp, w, edges, 8)
                cost = float(met["lambda_eff"]) * OUR_T * OUR_Q
                out["with_our_words"].append({
                    "path": str(f),
                    "file_sha256": key,
                    "lambda_eff": float(met["lambda_eff"]),
                    "Lambda": float(met["Lambda"]),
                    "E_gap": float(met["E_gap"]),
                    "error_1": float(met["error_1"]),
                    "error_2": float(met["error_2"]),
                    "cost_with_our_loaders": cost,
                    "delta_vs_our_chem": cost - OUR_CHEM_COST,
                    "delta_pct": 100.0 * (cost / OUR_CHEM_COST - 1.0),
                })
            except Exception as ex:  # noqa: BLE001 - a broken public npz must not stop the scan
                out.setdefault("errors", []).append(f"{f}: {type(ex).__name__}: {ex}")
            out["scanned"] += 1
        except OSError:
            continue
    out["with_our_words"].sort(key=lambda r: r["cost_with_our_loaders"])
    print(json.dumps({k: out[k] for k in ("scanned", "factorization_dirs")}, indent=1), flush=True)
    print(json.dumps(out["with_our_words"], indent=1), flush=True)

    # official-verifier receipt for the cheapest word-exact drop-in, if it beats ours
    if out["with_our_words"] and out["with_our_words"][0]["cost_with_our_loaders"] < OUR_CHEM_COST:
        best = out["with_our_words"][0]
        work = pathlib.Path("/kaggle/working/dfthcsos")
        work.mkdir(parents=True, exist_ok=True)
        for k in range(15):
            shutil.copy(loaders / f"angle_k_{k}.kmb", work / f"angle_k_{k}.kmb")
        shutil.copy(best["path"], work / "submission.npz")
        res = verify(work)
        out["verified_best"] = {
            "source_npz": best["path"],
            "score": float(res["score"]),
            "lambda_eff": float(res["lambda_eff"]),
            "toffoli_count": float(res["toffoli_count"]),
            "num_qubits": int(res["num_qubits"]),
            "status": res["status"],
            "delta_vs_our_chem": float(res["score"]) - OUR_CHEM_COST,
            "delta_pct": 100.0 * (float(res["score"]) / OUR_CHEM_COST - 1.0),
        }
        print(json.dumps({"verified_best": out["verified_best"]}, indent=1), flush=True)

    pathlib.Path("/kaggle/working/word_screen.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
