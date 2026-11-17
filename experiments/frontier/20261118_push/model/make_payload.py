"""Build the Kaggle kernel payload: the shipped a73b25d2 chem arrays, compacted.

Writes payload.py with WORDS_B64 (uint8), W_B64, H2I_B64, TREE_B64, META.
"""

from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path

import numpy as np

SUB = Path(
    "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261118_inv_sweep/ds/"
    "junmiaotiao_qcc-frontier-20261117r/dfthcsos/submission.npz"
)
OUT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/model/kernel/payload.py")


def pack(a: np.ndarray) -> str:
    return base64.b64encode(zlib.compress(np.ascontiguousarray(a).tobytes(), 9)).decode()


d = np.load(SUB, allow_pickle=False)
words = d["angle_words"]
assert words.min() >= 0 and words.max() <= 255
words = words.astype(np.uint8)
W = d["W"].astype(np.float32)
H2 = d["H2_I"].astype(np.float32)
tree = d["tree_edges"].astype(np.int8)
meta = {
    "words_shape": list(words.shape),
    "W_shape": list(W.shape),
    "H2_shape": list(H2.shape),
    "tree_shape": list(tree.shape),
}
parts = [
    f"META = {json.dumps(meta)}",
    f"WORDS_B64 = {pack(words)!r}",
    f"W_B64 = {pack(W)!r}",
    f"H2I_B64 = {pack(H2)!r}",
    f"TREE_B64 = {pack(tree)!r}",
]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts) + "\n")
print(OUT, OUT.stat().st_size, "bytes")
