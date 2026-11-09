"""s7c_phase.py: toy phase check for the broadcast HMR+CZ fixup.

Pattern (a=q0,b=q1,w=q2,t1=q3,t2=q4, m=b0, probe=b1), init a=b=1:
  WITH fixup:    CCX a b w; CX w t1; CX w t2; HMR w m; CZ a b if m; HMR a probe
  WITHOUT (neg): same minus the CZ.
Correct fixup => a ends exactly |1> (pure) => probe outcome independent of m.
Missing fixup => a carries phase (-1)^m => probe correlated with m.
64 shots, seed 7. Also checks t1=t2=1 always.

Writes artifacts/20261109_dqi_decoder_struct/s7c_phase.json
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import kickmix as km

OUT = Path("artifacts/20261109_dqi_decoder_struct/s7c_phase.json")
HDR = ('APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n'
       'APPEND_TO_REGISTER q2 r0\nAPPEND_TO_REGISTER q3 r0\n'
       'APPEND_TO_REGISTER q4 r0\nAPPEND_TO_REGISTER b0 r1\n'
       'APPEND_TO_REGISTER b1 r1\nREGISTER r0 "S0"\nREGISTER r1 "S1"\n')


def body(with_cz: bool) -> str:
    s = "X q0\nX q1\nCCX q0 q1 q2\nCX q2 q3\nCX q2 q4\nHMR q2 b0\n"
    if with_cz:
        s += "CZ q0 q1 if b0\n"
    return s + "HMR q0 b1\n"


def run(with_cz: bool, shots: int, seed: int):
    t = HDR + body(with_cz)
    c = km.Circuit(t)
    sim = km.Simulator(batch_size=shots, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    nq, nb = c.num_qubits, c.num_bits
    qb = np.zeros((nq, shots), dtype=np.bool_)
    bb = np.zeros((nb, shots), dtype=np.bool_)
    sim.write_across_shots(km.array([km.q(i) for i in range(nq)]), qb)
    sim.write_across_shots(km.array([km.b(i) for i in range(nb)]), bb)
    sim.do(c)
    m = [bool(v) for v in sim.read_across_shots(km.b(0))]
    pr = [bool(v) for v in sim.read_across_shots(km.b(1))]
    t1 = [bool(v) for v in sim.read_across_shots(km.q(3))]
    t2 = [bool(v) for v in sim.read_across_shots(km.q(4))]
    return m, pr, t1, t2


def main() -> None:
    res = {}
    for with_cz in (True, False):
        m, pr, t1, t2 = run(with_cz, 64, 7)
        # contingency of probe vs m
        tab = {(a, b): sum(1 for x, y in zip(m, pr) if x == a and y == b)
               for a in (False, True) for b in (False, True)}
        res[str(with_cz)] = {"m1": sum(m), "probe1": sum(pr),
                             "contingency_(m,probe)": {str(k): v for k, v in tab.items()},
                             "t1_all1": all(t1), "t2_all1": all(t2)}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
