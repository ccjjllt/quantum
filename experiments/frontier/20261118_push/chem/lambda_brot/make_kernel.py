"""Build the Kaggle kernel: embed the shipped weights + 15 loaders, splice analysis.py."""
import base64
import json
import lzma
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / "artifacts/20261118_inv_sweep/ds/junmiaotiao_qcc-frontier-20261117r/dfthcsos"
NPZ = SRC / "submission.npz"
import os
OUT = HERE / os.environ.get("KERNEL_DIR", "k_brot_trade")
ANALYSIS = os.environ.get("ANALYSIS", "analysis.py")


def pack(b: bytes) -> str:
    return base64.b64encode(lzma.compress(b, preset=9 | lzma.PRESET_EXTREME)).decode()


def main() -> None:
    sys.path.insert(0, str(REPO / "data/competition/verifiers"))
    from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

    with np.load(NPZ, allow_pickle=False) as z:
        W = np.array(z["W"])
        U = np.array(z["U"])
        aw = np.array(z["angle_words"], np.int64)
        tree = np.array(z["tree_edges"])
        arrs = {"W": W, "H2_I": np.array(z["H2_I"]), "H1_I": np.array(z["H1_I"]),
                "Hsym_lower": np.array(z["Hsym_lower"]), "tree_edges": tree,
                "angle_words": aw.astype(np.uint8)}
    v = reconstruct_u_vectors(aw / 128.0, tree)[76:]
    ov = np.sum(v * U.reshape(-1, 76), axis=1)
    assert np.all(np.abs(ov) > 1.0 - 1e-9), "U is not +-decode(angle_words)"
    buf = Path("/tmp/_chem_brot_npz.npz")
    np.savez(buf, **arrs)
    npz_bytes = buf.read_bytes()

    lens, blob = [], b""
    for k in range(15):
        d = (SRC / f"angle_k_{k}.kmb").read_bytes()
        lens.append(len(d))
        blob += d

    head = (
        "#!/usr/bin/env python3\n"
        'PAYLOAD_NPZ_B64 = """' + pack(npz_bytes) + '"""\n'
        'PAYLOAD_KMB_B64 = """' + pack(blob) + '"""\n'
        "PAYLOAD_LENS = " + json.dumps(lens) + "\n"
    )
    analysis = (HERE / ANALYSIS).read_text()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "main.py").write_text(head + analysis)
    print(json.dumps({
        "npz_bytes": len(npz_bytes),
        "kmb_bytes": len(blob),
        "main_py_bytes": len(head + analysis),
        "signs_minus": int((ov < 0).sum()),
        "signs_total": int(len(ov)),
    }, indent=1))


if __name__ == "__main__":
    main()
