"""Read-only structure dump of the DQI tape (no simulation, no verification).

Locates the 42-CCX multiply blocks in the EEA forward/reverse passes exactly as the
dqi_algo census does (maximal runs of CCX with identical (q1//12, q2//12, q3//12)
register triple and inter-CCX gap <= 80) and prints one block's full instruction
window plus the qubit->register map.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
spec = importlib.util.spec_from_file_location("vqcc_ir", ROOT / "artifacts/20261118_push_dqi/ds/vqcc_ir.py")
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

PATH = "/private/tmp/dqid/dqi_575b043f.kmb"
c = ir.Circuit.read(PATH)
t = c.types
tof = np.flatnonzero(ir.LTOF[t])
ccxp = np.flatnonzero(ir.L2Q[t] & ((t & 0x7F) == 0x21))   # CX
cczp = np.flatnonzero(ir.L3Q[t] & ((t & 0x7F) == 0x31))   # CCX

# operand index of each CCX in qqq arrays
cfun3 = np.cumsum(ir.L3Q[t])
qc = cfun3[cczp + 1] - 1
A, B, C = (c.qqq0[qc].astype(np.int64), c.qqq1[qc].astype(np.int64), c.qqq2[qc].astype(np.int64))
CRA, CRB, CRT = A // 12, B // 12, C // 12

# register name map
qmap = {}
for nm, ids in c.registers:
    q = ids[ids >> 31 == 1] & 0x7FFFFFFF
    b = ids[ids >> 31 == 0]
    if len(q):
        qmap[nm] = [int(x) for x in q]
print("num_registers", len(c.registers), "num_qubits", c.num_qubits)
print("qubit registers:", [(nm, len(v)) for nm, v in qmap.items()][:8], "...")
print("all qubit reg names:", [nm for nm in qmap][:20])

FWD = (17576206, 30335416)
REV = (35627262, 52910631)


def blocks(lo, hi, gapmax=80):
    sel = np.flatnonzero((cczp >= lo) & (cczp < hi))
    P = cczp[sel]
    a, b, d = CRA[sel], CRB[sel], CRT[sel]
    out = []
    i = 0
    while i < len(P):
        j = i
        while j + 1 < len(P) and (P[j + 1] - P[j] <= gapmax and a[j + 1] == a[j] and b[j + 1] == b[j] and d[j + 1] == d[j]):
            j += 1
        out.append((int(P[i]), int(P[j]), j - i + 1, int(a[i]), int(b[i]), int(d[i])))
        i = j + 1
    return out


bf = blocks(*FWD)
br = blocks(*REV)
for nm, bb in (("fwd", bf), ("rev", br)):
    sizes = np.array([x[2] for x in bb])
    print(nm, "blocks", len(bb), "max", sizes.max(), "n42", int((sizes == 42).sum()))

print("\n== first 42-blocks fwd ==")
for x in [y for y in bf if y[2] == 42][:6]:
    print(x)
print("== 42-blocks rev ==")
for x in [y for y in br if y[2] == 42][:6]:
    print(x)

np.save("/tmp/ccxp.npy", ccxp)
json.dump({"fwd": bf[:2000], "rev": br[:2000]}, open(str(ROOT / "experiments/frontier/20261118_push/dqi_mult/work/blocks.json"), "w"))
print("saved")
