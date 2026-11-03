"""Kickmix ground-truth probes v2 (fixed bit alloc). Manual run only."""
import json
from pathlib import Path
from fractions import Fraction
import kickmix as km

OUT = Path("artifacts/20261103_baseline_patch_round2/invsqrt/probe_kickmix.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
res = {}

def build(add):
    b = km.CircuitBuilder()
    x = b.create_quantum_register(3, name="x")
    c = b.create_classical_register(2, name="c")
    add(b, x, c)
    return b.finish_circuit()

def stats(c):
    st = c.operation_statistics()
    return {"toffoli_like": st.num_toffoli_like, "t_like": st.num_t_like,
            "ops": {str(k): v for k, v in dict(st).items()}}

res["ccx"] = stats(build(lambda b, x, c: b.ccx(x[0], x[1], x[2])))
res["ccz"] = stats(build(lambda b, x, c: b.ccz(x[0], x[1], x[2])))
res["cswap"] = stats(build(lambda b, x, c: b.cswap(x[0], x[1], x[2])))
res["hmr"] = stats(build(lambda b, x, c: b.hmr(x[0], c[0])))
res["r"] = stats(build(lambda b, x, c: b.reset(x[0])))
res["z"] = stats(build(lambda b, x, c: b.z(x[0])))
res["cz"] = stats(build(lambda b, x, c: b.cz(x[0], x[1])))
res["neg"] = stats(build(lambda b, x, c: b.neg()))
res["zpow_half"] = stats(build(lambda b, x, c: b.z_pow(x[0], Fraction(1, 2))))
res["zpow_quarter"] = stats(build(lambda b, x, c: b.z_pow(x[0], Fraction(1, 4))))
res["zpow_tenth"] = stats(build(lambda b, x, c: b.z_pow(x[0], Fraction(1, 10))))
print(json.dumps(res, indent=1))
OUT.write_text(json.dumps(res, indent=1) + "\n")
