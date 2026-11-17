"""Scout 2026-11-17: ratnachand/vqcc-verified-public-floor — hash + official chem cost.

CPU-only Kaggle kernel. Two jobs:
  1. sha256 every member of the ratnachand dataset (the DQI member is 479 MB, so the
     local machine does not download it; the dataset is mounted read-only instead).
  2. score its dfthcsos/ directory with the UNCHANGED official verifier
     (`verify()` on the directory), which is the only way to get the exact
     lambda_eff * T * Q for that submission.npz.

Nothing is submitted. No GPU, no TPU.
"""
import hashlib
import json
import pathlib
import sys

EXPECTED = {
    "invsqrt.kmb": "0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b",
    "dqi.kmb": "575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155",
    "dfthcsos/submission.npz": "a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3",
    "dfthcsos/angle_k_0.kmb": "ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538",
    "dfthcsos/angle_k_1.kmb": "8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd",
    "dfthcsos/angle_k_2.kmb": "e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f",
    "dfthcsos/angle_k_3.kmb": "b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e",
    "dfthcsos/angle_k_4.kmb": "ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d",
    "dfthcsos/angle_k_5.kmb": "21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856",
    "dfthcsos/angle_k_6.kmb": "1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1",
    "dfthcsos/angle_k_7.kmb": "8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0",
    "dfthcsos/angle_k_8.kmb": "0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563",
    "dfthcsos/angle_k_9.kmb": "b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71",
    "dfthcsos/angle_k_10.kmb": "41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6",
    "dfthcsos/angle_k_11.kmb": "76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca",
    "dfthcsos/angle_k_12.kmb": "e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f",
    "dfthcsos/angle_k_13.kmb": "9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8",
    "dfthcsos/angle_k_14.kmb": "fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f",
}
OUR_CHEM_COST = 294643137.73357135
OUR_LAMBDA_EFF = 46.92171681802858


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def find_comp() -> pathlib.Path:
    for p in pathlib.Path("/kaggle/input").rglob("verifiers/dfthcsos/verify.py"):
        return p.parents[2]
    raise SystemExit("competition verifiers not mounted")


def find_root() -> pathlib.Path:
    hits = list(pathlib.Path("/kaggle/input").rglob("angle_k_0.kmb"))
    for p in hits:
        d = p.parent
        if (d / "submission.npz").is_file() and d.name == "dfthcsos":
            return d.parent
    listing = [str(p) for p in sorted(pathlib.Path("/kaggle/input").iterdir())]
    raise SystemExit(f"no ratnachand dfthcsos dir; /kaggle/input = {listing}; candidates = {[str(h) for h in hits]}")


def main() -> None:
    out = {}
    root = find_root()
    out["root"] = str(root)

    rows = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(root))
            rows[rel] = {"size": p.stat().st_size, "sha256": sha256(p)}
    out["files"] = rows
    out["expected"] = {
        rel: {"sha256": exp, "match": rows.get(rel, {}).get("sha256") == exp}
        for rel, exp in EXPECTED.items()
    }
    dqi = rows.get("dqi.kmb", {})
    out["dqi_equals_575b043f"] = dqi.get("sha256") == EXPECTED["dqi.kmb"]
    loaders_match = all(
        rows.get(f"dfthcsos/angle_k_{k}.kmb", {}).get("sha256") == EXPECTED[f"dfthcsos/angle_k_{k}.kmb"]
        for k in range(15)
    )
    out["all_15_loaders_equal_ours"] = bool(loaders_match)
    print(json.dumps({"stage": "hash", **{k: out[k] for k in
          ("dqi_equals_575b043f", "all_15_loaders_equal_ours")}}, indent=1), flush=True)
    pathlib.Path("/kaggle/working/ratna_hashes.json").write_text(json.dumps(out, indent=1) + "\n")

    # ---- official chemistry score of the dataset's dfthcsos/ directory ----
    comp = find_comp()
    sys.path.insert(0, str(comp / "verifiers"))
    # The competition ships kickmix as a bare extension module (no __init__.py):
    # put <root>/kickmix itself on the path or `import kickmix` resolves to a
    # namespace package and the verifier dies with no attribute 'Circuit'.
    for p in pathlib.Path("/kaggle/input").rglob("kickmix/kickmix.so"):
        sys.path.insert(0, str(p.parent))
        break
    from dfthcsos.verify import verify  # unchanged official code path

    import kickmix
    assert hasattr(kickmix, "Circuit"), f"bad kickmix: {kickmix.__file__}"

    res = verify(root / "dfthcsos")
    keep = {k: res[k] for k in
            ("status", "score", "lambda_eff", "toffoli_count", "num_qubits", "brot",
             "batch_size", "num_circuits", "verified_shots")}
    keep["metrics"] = {k: float(res["metrics"][k]) for k in
                       ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")}
    keep["resources"] = {k: res["resources"][k] for k in
                         ("angles_toffoli", "angles_qubits", "heuristic_toffoli",
                          "toffoli", "qubits")}
    keep["our_chem_cost"] = OUR_CHEM_COST
    keep["our_lambda_eff"] = OUR_LAMBDA_EFF
    keep["delta_cost"] = float(res["score"]) - OUR_CHEM_COST
    keep["delta_cost_pct"] = 100.0 * (float(res["score"]) / OUR_CHEM_COST - 1.0)
    print(json.dumps({"stage": "chem", **keep}, indent=1), flush=True)
    pathlib.Path("/kaggle/working/ratna_chem.json").write_text(json.dumps(keep, indent=1) + "\n")


if __name__ == "__main__":
    main()
