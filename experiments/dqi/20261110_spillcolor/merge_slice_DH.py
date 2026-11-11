"""DQI spillcolor merge+slice: {D,H} combined rewrite + TAIL=0 slice.

Subset choice: {D,H} is strict-clean (colorgraph.json: no window touches
either direction, no gap intrusion, kills distinct, no introduced cross),
length-preserving on both cuts (1:1 full-window renames, no HMR stream
change), and covers the last block D. E is excluded: Hwin touches q878(Ev)
x24 (strict edge E-H); S is excluded: its +1-line shape perturbs downstream
HMR-outcome bits in this simulator (diag_S.json), so no S-bearing subset can
pass the bit-exact gate -- recorded separately, not retried here.

Rewrites (1:1 renames, orig file coords):
  H: files [52088951..52089238] q861->q849 (spillH)
  D: files [52299461..52299746] q863->q845 (spillD)
Slice: header[:54146] + [12006935..D_K=52299746], 4-shot, sim seed 99,
init seed 0xD91; 892Q + all bits + determinism rerun.
Writes artifacts/20261110_spillcolor/spillcolor_DH.{diff,json}.
No full kmb; no official verifier.
"""
from __future__ import annotations

import difflib
import json
import os
from pathlib import Path

import numpy as np

import kickmix as km

TMP = os.environ.get("TMPDIR", "/tmp/")
KMX = os.path.join(TMP, "dqi_e9diff", "e9.kmx")
ART = Path("artifacts/20261110_spillcolor")
HEADER_END = 54146
ENTRY_CONVERT = 12006935
W = 892
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}

BLOCKS = [
    {"tag": "H", "victim": "q861", "borrow": "q849",
     "F_B": 52088951, "F_K": 52089238, "kill_bit": "b99619"},
    {"tag": "D", "victim": "q863", "borrow": "q845",
     "F_B": 52299461, "F_K": 52299746, "kill_bit": "b99524"},
]


def has_qtok(line, q):
    for t in line.split()[1:]:
        if t == "if":
            break
        if t == q:
            return True
    return False


def rename(line, qv, qb):
    p = line.split()
    return " ".join([p[0]] + [qb if t == qv else t for t in p[1:]]) + "\n"


def sim_sized(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
    sim.do(c)
    return sim, c


def compare(simO, cO, simR, cR):
    qmis = [i for i in range(W)
            if [bool(v) for v in simO.read_across_shots(km.q(i))]
            != [bool(v) for v in simR.read_across_shots(km.q(i))]]
    nbits = min(cO.num_bits, cR.num_bits)
    bmis = []
    for i in range(nbits):
        if ([bool(v) for v in simO.read_across_shots(km.b(i))]
                != [bool(v) for v in simR.read_across_shots(km.b(i))]):
            bmis.append(i)
            if len(bmis) > 20:
                break
    return qmis, nbits, bmis


def main():
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)

    new_mids, paid = {}, {}
    for cfg in BLOCKS:
        t, qv, qb = cfg["tag"], cfg["victim"], cfg["borrow"]
        F_B, F_K = cfg["F_B"], cfg["F_K"]
        assert lines[F_B].strip() == f"R {qv}", (t, lines[F_B][:60])
        assert lines[F_K].strip() == f"HMR {qv} {cfg['kill_bit']}", (t, lines[F_K][:60])
        new = [rename(lines[i], qv, qb) for i in range(F_B, F_K + 1)]
        assert new[-1].strip() == f"HMR {qb} {cfg['kill_bit']}", new[-1][:60]
        new_mids[t] = new
        p0 = sum(1 for i in range(F_B, F_K + 1) if lines[i].split()[0] in PAID)
        p1 = sum(1 for l in new if l.split()[0] in PAID)
        assert p0 == p1, (t, p0, p1)
        paid[t] = [p0, p1]
        print(f"[{t}] paid {p0}->{p1}", flush=True)
    kb = [c["kill_bit"] for c in BLOCKS]
    assert len(set(kb)) == len(kb), kb
    # strict-clean re-assert (mirrors colorgraph census for this pair)
    H, D = BLOCKS
    for a, b in ((H, D), (D, H)):
        for role in ("victim", "borrow"):
            n = sum(1 for i in range(a["F_B"], a["F_K"] + 1)
                    if has_qtok(lines[i], b[role]))
            assert n == 0, (a["tag"], b["tag"], role, n)
    print("[DH] strict-clean re-assert passed", flush=True)

    diff_parts = []
    for cfg in BLOCKS:
        t, F_B, F_K = cfg["tag"], cfg["F_B"], cfg["F_K"]
        a = [f"{i}:{lines[i]}" for i in range(F_B - 3, F_K + 4)]
        b = ([f"{F_B - 3}:{lines[F_B - 3]}", f"{F_B - 2}:{lines[F_B - 2]}",
              f"{F_B - 1}:{lines[F_B - 1]}"]
             + [f"{F_B}+:{l}" for l in new_mids[t]]
             + [f"{F_K + 1}:{lines[F_K + 1]}", f"{F_K + 2}:{lines[F_K + 2]}",
                f"{F_K + 3}:{lines[F_K + 3]}"])
        frag = "".join(difflib.unified_diff(
            a, b, fromfile=f"orig_fragment_{t}", tofile=f"rewritten_fragment_{t}"))
        diff_parts.append(f"# block {t}: files [{F_B}..{F_K}] "
                          f"{cfg['victim']}->{cfg['borrow']}\n" + frag)
    (ART / "spillcolor_DH.diff").write_text("\n".join(diff_parts))
    print("wrote merged diff", flush=True)

    ENTRY = ENTRY_CONVERT
    tail = D["F_K"]
    header = lines[:HEADER_END]
    seg = lines[ENTRY:tail + 1]
    new_seg = list(seg)
    for cfg in BLOCKS:
        for i in range(cfg["F_B"], cfg["F_K"] + 1):
            new_seg[i - ENTRY] = rename(lines[i], cfg["victim"], cfg["borrow"])
    tO = "".join(header + seg)
    tR = "".join(header + new_seg)
    cO, cR = km.Circuit(tO), km.Circuit(tR)
    print(f"q/b orig={cO.num_qubits}/{cO.num_bits} new={cR.num_qubits}/{cR.num_bits}",
          flush=True)
    assert cO.num_qubits == cR.num_qubits == W
    assert cO.num_bits == cR.num_bits
    rng = np.random.default_rng(0xD91)
    qb4 = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4 = rng.integers(0, 2, size=(cO.num_bits, 4)).astype(np.bool_)
    print("sim orig...", flush=True)
    simO, _ = sim_sized(tO, 99, qb4, bb4)
    print("sim rewritten...", flush=True)
    simR, _ = sim_sized(tR, 99, qb4, bb4)
    print("sim rewritten again...", flush=True)
    simR2, _ = sim_sized(tR, 99, qb4, bb4)
    qmis, nbits, bmis = compare(simO, cO, simR, cR)
    qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    res = {
        "design": "{D,H}: independent-borrow pair (H:q861->q849, D:q863->q845); "
                  "strict-clean, length-preserving 1:1 renames",
        "windows_files": {c["tag"]: [c["F_B"], c["F_K"]] for c in BLOCKS},
        "kill_bits": {c["tag"]: c["kill_bit"] for c in BLOCKS},
        "paid_per_block": {c["tag"]: {"orig": paid[c["tag"]][0],
                                      "new": paid[c["tag"]][1], "delta": 0}
                           for c in BLOCKS},
        "paid_total_delta": 0,
        "hmr_stream": "positions unchanged; only kill-line qubit operands swapped",
        "slice": {"header_end": HEADER_END, "entry": ENTRY, "tail_file": tail,
                  "tail_len": 0, "shots": 4, "sim_seed": 99, "init_seed": "0xD91"},
        "qubits_compared": W, "qubits_equal": len(qmis) == 0,
        "qubit_mismatches": qmis, "qubits_deterministic": qR == qR2,
        "bits_compared": nbits, "bit_mismatches": bmis,
        "verdict": ("MERGE_EQUAL" if (len(qmis) == 0 and not bmis)
                    else "MERGE_MISMATCH"),
    }
    (ART / "spillcolor_DH.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"qubits_equal": res["qubits_equal"],
                      "det": res["qubits_deterministic"], "bmis": bmis,
                      "verdict": res["verdict"]}, indent=1), flush=True)


if __name__ == "__main__":
    main()
