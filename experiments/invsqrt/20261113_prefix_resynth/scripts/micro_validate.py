"""Micro-validation of qsim against km.Simulator on valid hand-written circuits.

Every case is a *well-formed* kickmix circuit (each HMR kickback is exactly
corrected), so both the values and the tracked phase are deterministic and can be
compared.  Cases cover every instruction kind used by the invsqrt lineage.
"""

from __future__ import annotations

import io
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from qsim import HMR_MODE, Sim, op_table, run  # noqa: E402

HDR = "".join(f"APPEND_TO_REGISTER q{i} r0\n" for i in range(6))
XS = np.array([0, 1, 2, 3, 4, 5, 7, 8, 13, 21, 32, 41, 62, 63], dtype=np.uint64)

CASES = {
    "z_cz_ccz": "Z q0\nCZ q0 q1\nCCZ q0 q1 q2\n",
    "zpow": "Z_POW q0 1.5\nZ_POW q1 0.0009765625\nZ_POW q2 -0.5\n",
    "zpow_cond_cancel": ("X q4\nHMR q4 b4\nNEG if b4\n"
                         "Z_POW q3 0.25 if b4\nZ_POW q3 0.25 if b4\n"),
    "neg": "NEG\nNEG if b0\n",
    "hmr_neg": "X q0\nHMR q0 b0\nNEG if b0\n",
    "hmr_cz": "CCX q0 q1 q2\nHMR q2 b0\nCZ q0 q1 if b0\n",
    "hmr_two": ("CCX q0 q1 q2\nCCX q1 q2 q3\nHMR q2 b0\nHMR q3 b1\n"
                "CZ q0 q1 if b0\nCZ q0 q1 if b1\n"),
    "classical": ("BIT_STORE1 b1\nBIT_INVERT b1\nBIT_INVERT b1\n"
                  "X q5 if b1\nBIT_STORE0 b2\nBIT_INVERT b2 if b1\nZ q4 if b2\n"),
    "stacked_snapshot": ("BIT_STORE1 b2\nPUSH_CONDITION if b2\nBIT_STORE0 b2\nZ q3\n"
                         "POP_CONDITION\n"),
    "swap_family": "SWAP q0 q1\nCSWAP q2 q0 q3\nCSWAP q1 q4 q5\n",
}


def km_phase_all(text, xs):
    import kickmix as km

    c = km.Circuit.from_file(io.StringIO(HDR + text), format="kmx")
    n = len(xs)
    sim = km.Simulator(batch_size=n, debug_print=False, seed=1)
    sim.clear_for_shot()
    bits = ((xs[None, :] >> np.arange(6, dtype=np.uint64)[:, None]) & 1) == 1
    sim.write_across_shots(km.array([km.q(i) for i in range(6)]), bits)
    sim.do(c)
    ph = []
    for i in range(n):
        n_, d_ = Fraction(sim.read_shot_phase(i)).as_integer_ratio()
        ph.append(((n_ << 63) // d_) % (1 << 64))
    q = sim.read_across_shots(km.array([km.q(i) for i in range(6)]))
    return np.array(ph, dtype=np.uint64), q


def main() -> None:
    ok = True
    with tempfile.NamedTemporaryFile("w", suffix=".kmx", delete=False) as f:
        tmp = Path(f.name)
    for name, body in CASES.items():
        tmp.write_text(HDR + body)
        table, nq = op_table(tmp)
        sim = Sim(len(XS), n_qubits=6)
        sim.v = XS.copy()
        run(sim, table)
        ph, q = km_phase_all(body, XS)
        mine_q = np.stack([(sim.v >> np.uint64(i)) & np.uint64(1) for i in range(6)]).astype(bool)
        dq = int(np.count_nonzero(mine_q != q))
        dp = int(np.count_nonzero(sim.phase != ph))
        status = "OK  " if (dq == 0 and dp == 0) else "FAIL"
        ok &= status == "OK  "
        print(f"{status} {name:>16}  value-diff {dq}  phase-diff {dp}  (of {len(XS)})")
    tmp.unlink(missing_ok=True)
    print("ALL OK" if ok else "SOME FAILED")


if __name__ == "__main__":
    main()
