"""s6_guard_verify.py: scan per-position mask-guard unit, slice verification.

Window: scan region-1 mask prologue + guarded block (0-based
[17974728, 17974954]): 12x BIT_STORE0 masks, INVERT chains, STORE0/STORE1 guard
accumulation, PUSH b101254 ... 105-line guarded block ... POP.

Variants: G (guarded, as-is) vs U (PUSH/POP stripped).
Inits (batch 4, rng 0xD91): Z (all bits 0 -> all masks 0 -> guard 0; qubits
random) and R (all bits+qubits random -> guard ~always 1).
Sim seed 99. Compares qubit+bit reads at window end.
Questions: (1) G1==U1 (pass-through)? (2) G0==input (true skip)?
(3) U0==input (V11 'identity otherwise' on the bare block)?
Plus determinism rerun.

Writes artifacts/20261109_dqi_decoder_struct/s6_guard.json
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import kickmix as km

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
OUT = Path("artifacts/20261109_dqi_decoder_struct/s6_guard.json")
HEADER_END = 54145
W0, W1 = 17974728, 17974954  # inclusive, 0-based
PUSH, POP = 17974849, 17974954
QWATCH = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
          841, 849, 859, 874, 875, 880, 881, 885, 890, 878]
BWATCH = [101254, 101267, 101268, 101269, 101270, 101271, 101272, 101273,
          101274, 101275, 101276, 101277, 101278, 99126]


def sim_slice(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb)
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb)
    sim.do(c)
    return sim, c


def reads(sim):
    q = {x: [bool(v) for v in sim.read_across_shots(km.q(x))] for x in QWATCH}
    b = {x: [bool(v) for v in sim.read_across_shots(km.b(x))] for x in BWATCH}
    return {"q": q, "b": b}


def main() -> None:
    print("loading lines...", flush=True)
    with open(KMX) as f:
        lines = f.readlines()
    header = lines[:HEADER_END]
    win = lines[W0:W1 + 1]
    assert win[0].strip() == "BIT_STORE0 b101278", win[0][:40]
    assert win[PUSH - W0].strip() == "PUSH_CONDITION if b101254"
    assert win[POP - W0].strip() == "POP_CONDITION"
    winU = [l for i, l in enumerate(win) if W0 + i not in (PUSH, POP)]
    tG = "".join(header + win)
    tU = "".join(header + winU)
    c0 = km.Circuit(tG)
    nq, nb = c0.num_qubits, c0.num_bits
    print(f"slice circuit: qubits={nq} bits={nb} window_lines={len(win)}", flush=True)
    rng = np.random.default_rng(0xD91)
    qb = rng.integers(0, 2, size=(nq, 4)).astype(np.bool_)
    bbR = rng.integers(0, 2, size=(nb, 4)).astype(np.bool_)
    bbZ = np.zeros((nb, 4), dtype=np.bool_)
    res = {"window": [W0, W1], "qubits": nq, "bits": nb,
           "paid_G": sum(1 for l in win for k in ("CCX", "CCZ", "CSWAP") if l.startswith(k)),
           "runs": {}}
    # Z init
    simG0, _ = sim_slice(tG, 99, qb, bbZ)
    simU0, _ = sim_slice(tU, 99, qb, bbZ)
    # R init
    simG1, _ = sim_slice(tG, 99, qb, bbR)
    simU1, _ = sim_slice(tU, 99, qb, bbR)
    # determinism
    simG1b, _ = sim_slice(tG, 99, qb, bbR)
    rG0, rU0, rG1, rU1, rG1b = map(reads, (simG0, simU0, simG1, simU1, simG1b))
    res["runs"] = {"G0": rG0, "U0": rU0, "G1": rG1, "U1": rU1, "G1b": rG1b}
    # input reads for identity checks
    qin = {x: [bool(v) for v in qb[x, :]] for x in QWATCH}
    res["input_q"] = qin
    eq = lambda a, b: a == b
    res["verdicts"] = {
        "G1_eq_U1_passthrough": eq(rG1, rU1),
        "G1b_eq_G1_deterministic": eq(rG1b, rG1),
        "G0_guard_bit": rG0["b"]["101254"] if "101254" in rG0["b"] else rG0["b"][101254],
        "G0_eq_input": all(rG0["q"][x] == qin[x] for x in QWATCH),
        "U0_eq_input": all(rU0["q"][x] == qin[x] for x in QWATCH),
        "U0_eq_G0": eq(rU0, rG0),
    }
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res["verdicts"], indent=1, default=str))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
