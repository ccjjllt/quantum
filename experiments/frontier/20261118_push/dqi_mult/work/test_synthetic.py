"""Validate the ANF block extractor on a synthetic GF(4) multiply block (no tape read)."""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
spec = importlib.util.spec_from_file_location("vqcc_ir", ROOT / "artifacts/20261118_push_dqi/ds/vqcc_ir.py")
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)
sys.path.insert(0, str(ROOT / "experiments/frontier/20261118_push/dqi_mult/work"))
import multlib

# qubits 0,1 = A word; 2,3 = B word; 4,5 = C word (accumulator), 6 = pad (unused)
OPS = [
    ("CX", (1, 0), ()), ("CX", (3, 2), ()),
    ("CCX", (0, 2, 5), ()),
    ("CX", (3, 2), ()), ("CX", (1, 0), ()),
    ("CCX", (0, 2, 4), ()), ("CCX", (1, 3, 4), ()),
    ("CCX", (0, 2, 5), ()), ("CCX", (1, 3, 5), ()),
    ("CCX", (0, 2, 6), ()),
]
regs = [("A", [0x80000000 | 0, 0x80000000 | 1]), ("B", [0x80000000 | 2, 0x80000000 | 3]),
        ("C", [0x80000000 | 4, 0x80000000 | 5]), ("P", [0x80000000 | 6])]
c = ir.Circuit.from_ops(OPS, regs)
p = "/tmp/synth_gf4.kmb"
print("wrote", c.write(p))
c2 = ir.Circuit.read(p)
res = multlib.analyse_window(c2, 0, c2.num_ops)
ident, acc, bad = multlib.closure_report(res, None)
print("identity qubits:", ident, "accumulators:", acc, "bad:", bad)
terms = multlib.terms_from_tensor(res, {"A": [0, 1], "B": [2, 3], "C": [4, 5]}, acc)
for t in terms:
    print("  AND", t["op"], "u", t["u"], "v", t["v"], "-> w bits", bin(t["w"]))
# expected: c0 = a0b0+a1b1 ; c1 = a0b0+a1b1+(a0+a1)(b0+b1)
T = []
for q in (4, 5):
    lin, pairs, const = res["out"][q]
    m = {}
    for (x, y) in pairs:
        m[(x, y)] = m.get((x, y), 0) ^ 1
    T.append(m)
print("c0 tensor pairs (qubit ids):", T[0])
print("c1 tensor pairs (qubit ids):", T[1])
exp0 = {(0, 2): 1, (1, 3): 1}
exp1 = {(0, 2): 1, (1, 3): 1, (0, 2): 1}
print("c0 ok:", T[0] == exp0)
print("c1 has (0,3),(1,2) from the prepared combo:", sorted(T[1]))
