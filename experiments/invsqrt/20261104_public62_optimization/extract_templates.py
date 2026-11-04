"""Extract the 7 public 3->2 templates from the pinned Kirill V5 notebook (data only)."""
import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NB = ROOT / "artifacts/20261104_public_refresh/kirill_v5.ipynb"
nb = json.loads(NB.read_text())
src = "".join(nb["cells"][3]["source"])
for key in ["FIVE_WINDOW_EDITS", "TWO_WINDOW_EDITS"]:
    i = src.find(key + " = [")
    start = src.find("[", i)
    depth = 0
    for k in range(start, len(src)):
        if src[k] == "[": depth += 1
        elif src[k] == "]":
            depth -= 1
            if depth == 0:
                Path("/tmp/" + key + ".py").write_text(src[i:k + 1] + "\n")
                break

out = {"kirill_identity": [], "syed_conditional": []}
for key, name in [("FIVE_WINDOW_EDITS", "kirill_identity"), ("TWO_WINDOW_EDITS", "syed_conditional")]:
    spec = importlib.util.spec_from_file_location(key, "/tmp/" + key + ".py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for e in getattr(mod, key):
        out[name].append({"line": e.get("line", e.get("source_line")),
                          "original_syed_line": e.get("original_syed_line"),
                          "old": e["old"], "new": e["new"],
                          "variables": e.get("variables"),
                          "condition_depth": e.get("condition_depth")})
out["provenance"] = {
    "notebook": "artifacts/20261104_public_refresh/kirill_v5.ipynb",
    "cell": 3,
    "kirill_source": "https://www.kaggle.com/code/kirilltym/quantum-circuits-four-loaders-eight-toffolis?scriptVersionId=365421181",
    "syed_source": "https://www.kaggle.com/code/syed3000/vqcc-24-43-portfolio?scriptVersionId=365359337",
    "note": "Kirill 5-identity: phaseless 12-gate 7-wire 3CCX->2CCX; Syed 2-window: 13-gate w/ Z-if-b kept, 3CCX->2CCX. All 7 already applied in Kirill V5 baseline.",
}
p = ROOT / "experiments/invsqrt/20261104_public62_optimization/routeA_templates.json"
p.write_text(json.dumps(out, indent=1) + "\n")
print("wrote", p)
for name in ["kirill_identity", "syed_conditional"]:
    print(name, len(out[name]))
    print(" old lens:", sorted(set(len(e["old"]) for e in out[name])),
          "new lens:", sorted(set(len(e["new"]) for e in out[name])))
