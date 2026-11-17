"""DQI 575b043f: per-wire census of the 50 scratch wires 840..889 (Q-axis evidence).

Which of the 50 pool wires are long-lived EEA working words and which are product accumulators
(one value per reset-window)?  Counts, per wire: touches, reads, writes, Toffoli writes, resets
(R/HMR) and R/HMR-delimited windows, from the operand arrays directly.

Fix vs the first attempt in k_find: an operand array's index is NOT the global op index.  Each
group's k-th entry belongs to the k-th op of that group, so the global index is
`flatnonzero(L3Q/L2Q/L1Q[types])[k]`.  Without that map the op kinds were misattributed.

Read-only.
"""
from __future__ import annotations

import json
import lzma
import pathlib
import shutil
import sys
import time

import numpy as np

T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)


DS = None
for p in sorted(pathlib.Path("/kaggle/input").rglob("vqcc_measure_out.py")):
    DS = p.parent
    break
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi")
TMP.mkdir(parents=True, exist_ok=True)
TOOLS = pathlib.Path("/tmp/tools")
(TOOLS / "qc" / "passes").mkdir(parents=True, exist_ok=True)
for p in (TOOLS / "qc" / "__init__.py", TOOLS / "qc" / "passes" / "__init__.py"):
    p.write_text("")
for src, dst in (("vqcc_ir.py", "qc/ir.py"), ("vqcc_measure_out.py", "qc/passes/measure_out.py")):
    shutil.copyfile(DS / src, TOOLS / dst)
sys.path.insert(0, str(TOOLS))
from qc import ir                                        # noqa: E402

TAPE = TMP / "dqi_575b043f.kmb"
if not TAPE.exists():
    with lzma.open(DS / "dqi_575b043f.kmb.xz", "rb") as f, open(TAPE, "wb") as g:
        shutil.copyfileobj(f, g, 1 << 24)
c = ir.Circuit.read(TAPE)
types = np.asarray(c.types)
log(f"ops {c.num_ops:,} Q {c.num_qubits} staticT {c.toffoli_like():,} sha {c.sha256()[:16]}")

LO, HI = 840, 890
groups = ((np.flatnonzero(ir.L3Q[types]), (c.qqq0, 0), (c.qqq1, 0), (c.qqq2, 1)),
          (np.flatnonzero(ir.L2Q[types]), (c.qq0, 0), (c.qq1, 1)),
          (np.flatnonzero(ir.L1Q[types]), (c.q0, 1)))
parts = []
for opsidx, *slots in groups:
    log(f"  group ops {len(opsidx):,}")
    for arr, kind in slots:
        a = np.asarray(arr)
        assert len(a) == len(opsidx), (len(a), len(opsidx))
        for s in range(0, len(a), 1 << 23):
            blk = a[s:s + (1 << 23)]
            k = np.flatnonzero((blk >= LO) & (blk < HI))
            if len(k):
                parts.append(np.stack([blk[k].astype(np.int64),
                                       opsidx[k + s].astype(np.int64),
                                       np.full(len(k), kind, np.int64)], 1))
    del opsidx
tab = np.concatenate(parts)
del parts
base = types[tab[:, 1]] & 0x7F
tab[(base == 0x30) & (tab[:, 2] == 1), 2] = 0            # CCZ: diagonal
tab[(base == 0x20) & (tab[:, 2] == 1), 2] = 0            # CZ: diagonal
tab[np.isin(base, [0x31, 0x32]) & (tab[:, 2] == 1), 2] = 2   # Toffoli target
tab[np.isin(base, [0x12, 0x50]) & (tab[:, 2] >= 1), 2] = 3   # R / HMR
o = np.lexsort((tab[:, 1], tab[:, 0]))
tab = tab[o]
del o
out = {}
for w in range(LO, HI):
    a, b = np.searchsorted(tab[:, 0], [w, w + 1])
    seg = tab[a:b]
    k, pos = seg[:, 2], seg[:, 1]
    rst = pos[k == 3]
    win = int(len(rst) + (1 if len(pos) and (not len(rst) or pos.min() < rst.min()) else 0))
    out[w] = {"touches": int(len(seg)), "reads": int((k == 0).sum()), "writes": int((k >= 1).sum()),
              "toffoli_writes": int((k == 2).sum()), "resets": int((k == 3).sum()),
              "windows": win,
              "first": int(pos.min()) if len(pos) else -1, "last": int(pos.max()) if len(pos) else -1}
# cross-check against the whole tape
tot = {key: sum(out[w][key] for w in out) for key in ("touches", "reads", "writes",
                                                     "toffoli_writes", "resets", "windows")}
whole = {"R": int((base == 0x12).sum()), "HMR": int((base == 0x50).sum()),
         "toffoli": int((types & 0x7F == 0x31).sum()), "ops": int(c.num_ops)}
log("pool totals:", json.dumps(tot))
log("whole tape  :", json.dumps(whole))
log("wires 840-851:", json.dumps({str(w): out[w] for w in range(840, 852)}))
log("wires 852-863:", json.dumps({str(w): out[w] for w in range(852, 864)}))
log("wires 864-875:", json.dumps({str(w): out[w] for w in range(864, 876)}))
log("wires 876-887:", json.dumps({str(w): out[w] for w in range(876, 888)}))
log("wires 888-889:", json.dumps({str(w): out[w] for w in range(888, 890)}))
(WORK / "pool_census.json").write_text(json.dumps({"totals": tot, "whole_tape": whole,
                                                   "wires": {str(k): v for k, v in out.items()}},
                                                  indent=1))
log("DONE")
