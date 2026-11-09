"""DQI dirty-borrow study C: toy semantic proof with km.Simulator.

Shows on 5 qubits (a=q0,b=q1,d=q2/wire,t1=q3,t2=q4), inputs a=b=1, d=1:
 - baseline: CCX a b t1; CCX a b t2  -> t1=t2=1, 2 Toffoli-like
 - naive dirty-hold: CCX a b d; CX d t1; CX d t2; CCX a b d
   -> t1=t2=0 (polluted by d), w restored; 2 Toffoli-like, WRONG values
 - correct per-site identity (single site): CCX a b d; CX d t1; CCX a b d; CX d t1
   -> t1=1 correct, d restored; 2 Toffoli-like vs original 1 => net +1/site
 - clean-hold reference: d=0 initial -> naive hold gives t1=t2=1 (correct),
   2 Toffoli-like for 2 sites vs baseline 2: saves 0 here; with k sites the
   Isabe pattern saves k-1 (first CCX retargeted, rest -> CX, HMR+CZ free).

Writes artifacts/20261109_dqi_dirtyk2/c_semantics.json
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

import kickmix as km

ART = Path("artifacts/20261109_dqi_dirtyk2")

CASES = {
    "baseline_2ccx": "X q0\nX q1\nX q2\nCCX q0 q1 q3\nCCX q0 q1 q4\n",
    "naive_dirty_hold": "X q0\nX q1\nX q2\nCCX q0 q1 q2\nCX q2 q3\nCX q2 q4\nCCX q0 q1 q2\n",
    "clean_hold_d0": "X q0\nX q1\nCCX q0 q1 q2\nCX q2 q3\nCX q2 q4\n",
    "per_site_identity": "X q0\nX q1\nX q2\nCCX q0 q1 q2\nCX q2 q3\nCCX q0 q1 q2\nCX q2 q3\n",
}


def run(name, text):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=7)
    sim.use_same_registers_as(c)
    qb = np.zeros((5, 4), dtype=np.bool_)  # all |0>; X gates in circuit set a=b=d=1
    sim.write_across_shots(km.array([km.q(i) for i in range(5)]), qb)
    sim.do(c)
    t1 = [bool(v) for v in sim.read_across_shots(km.array([km.q(3)]))[0]]
    t2 = [bool(v) for v in sim.read_across_shots(km.array([km.q(4)]))[0]]
    d = [bool(v) for v in sim.read_across_shots(km.array([km.q(2)]))[0]]
    stats = c.operation_statistics()
    return {"t1": t1, "t2": t2, "d_final": d,
            "num_toffoli_like": stats.num_toffoli_like, "n_ops": len(c)}


def main():
    out = {}
    for name, text in CASES.items():
        r = run(name, text)
        # for clean_hold_d0 the X q2 line is absent => q2 starts 0
        out[name] = {"circuit": text, **r}
        print(f"{name}: t1={r['t1']} t2={r['t2']} d={r['d_final']} "
              f"toff={r['num_toffoli_like']} ops={r['n_ops']}", flush=True)
    # verdicts (a=b=1 => p=1; d=1 for dirty cases)
    base = out["baseline_2ccx"]
    assert base["t1"] == [True] * 4 and base["t2"] == [True] * 4
    naive = out["naive_dirty_hold"]
    polluted = (naive["t1"] == [False] * 4 and naive["t2"] == [False] * 4)
    restored = (naive["d_final"] == [True] * 4)
    per = out["per_site_identity"]
    per_ok = (per["t1"] == [True] * 4)
    clean = out["clean_hold_d0"]
    clean_ok = (clean["t1"] == [True] * 4 and clean["t2"] == [True] * 4)
    out["verdict"] = {
        "naive_dirty_hold_polluted": polluted,
        "naive_dirty_hold_wire_restored": restored,
        "per_site_identity_correct": per_ok,
        "per_site_identity_cost_delta_vs_1ccx": per["num_toffoli_like"] - 1,
        "clean_hold_correct": clean_ok,
        "conclusion": ("naive dirty-hold restores the wire but pollutes targets "
                       "(t=0 instead of 1); only the per-site 4-gate identity "
                       "(+1 CCX/site) or a truly clean wire is value-correct."),
    }
    print(json.dumps(out["verdict"], indent=1), flush=True)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "c_semantics.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote c_semantics.json", flush=True)


if __name__ == "__main__":
    main()
