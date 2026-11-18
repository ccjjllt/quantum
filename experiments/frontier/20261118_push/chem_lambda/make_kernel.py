"""Build the chem-Lambda Kaggle kernel: embed the factorization arrays, splice analysis.py."""
import base64
import json
import lzma
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SRC = REPO / "artifacts/20261118_inv_sweep/ds/junmiaotiao_qcc-frontier-20261117r/dfthcsos"
NPZ = SRC / "submission.npz"
OUT = HERE / os.environ.get("KERNEL_DIR", "k_lambda")
ANALYSIS = HERE / os.environ.get("ANALYSIS", "analysis.py")


def pack(b: bytes) -> str:
    return base64.b64encode(lzma.compress(b, preset=9 | lzma.PRESET_EXTREME)).decode()


def main() -> None:
    with np.load(NPZ, allow_pickle=False) as z:
        arrs = {"W": np.array(z["W"], np.float64),
                "H2_I": np.array(z["H2_I"], np.float64),
                "H1_I": np.array(z["H1_I"]),
                "Hsym_lower": np.array(z["Hsym_lower"]),
                "tree_edges": np.array(z["tree_edges"]),
                "angle_words": np.array(z["angle_words"]).astype(np.uint8)}
    aw = np.asarray(arrs["angle_words"], np.int64)
    assert aw.max() < 256, "words do not fit uint8"
    buf = Path("/tmp/_chem_lambda_npz.npz")
    np.savez(buf, **arrs)
    npz_bytes = buf.read_bytes()
    head = (
        "#!/usr/bin/env python3\n"
        'PAYLOAD_NPZ_B64 = """' + pack(npz_bytes) + '"""\n'
    )
    analysis = ANALYSIS.read_text()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "main.py").write_text(head + analysis)
    print(json.dumps({"npz_bytes": len(npz_bytes), "main_py_bytes": len(head + analysis),
                      "words_shape": list(arrs["angle_words"].shape)}, indent=1))


if __name__ == "__main__":
    main()
