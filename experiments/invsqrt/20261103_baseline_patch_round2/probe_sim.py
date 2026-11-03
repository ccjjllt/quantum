"""Simulator ground truth probes. Manual run only."""
import json, io
from pathlib import Path
import kickmix as km
import numpy as np

OUT = Path("artifacts/20261103_baseline_patch_round2/invsqrt/probe_sim.json")
N = 400
res = {}
HDR = ("APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n"
       "APPEND_TO_REGISTER q2 r0\nAPPEND_TO_REGISTER q3 r0\n"
       "REGISTER r0 \"x\"\n"
       "APPEND_TO_REGISTER b0 r1\nAPPEND_TO_REGISTER b1 r1\n"
       "APPEND_TO_REGISTER b2 r1\nAPPEND_TO_REGISTER b3 r1\n"
       "REGISTER r1 \"c\"\n")


def run_kmx(lines, seed=7):
    circ = km.Circuit.from_file(io.StringIO(HDR + "\n".join(lines) + "\n"),
                                format="kmx")
    sim = km.Simulator(N, counting_operations=True, seed=seed)
    sim.do(circ)
    return circ, sim


def bits(sim, b):
    return np.array([sim.read_shot_phase(i) for i in range(N)])  # placeholder


# E1: conditional CCX executed-counting
circ, sim = run_kmx(["X q0", "HMR q0 b0", "X q1",
                     "CCX q0 q1 q2 if b0", "CCX q1 q2 q3"])
st = circ.operation_statistics()
est = sim.operation_statistics()
res["E1_static_toff"] = st.num_toffoli_like
res["E1_exec_toff"] = est.num_toffoli_like
print("E1 static:", st.num_toffoli_like, "exec total:", est.num_toffoli_like,
      "per-shot:", est.num_toffoli_like / N)

print("has km.b:", hasattr(km, "b"), "has km.q:", hasattr(km, "q"))
# try bit readout
try:
    v = sim.read_across_shots(km.b(0))
    print("bit readout ok, mean:", np.asarray(v).mean())
    res["bit_readout"] = "km.b works"
except Exception as e:
    print("bit readout fail:", e)
    res["bit_readout"] = "fail: %s" % e
OUT.write_text(json.dumps(res, indent=1) + "\n")
