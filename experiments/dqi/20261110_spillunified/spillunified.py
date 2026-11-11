"""DQI spillunified: D+E independent-borrow merge + combined-slice verification.

Design (see experiments/dqi/20261110_spillunified/README.md):
  E: R q878..HMR q878 b99126  @files [41258103..41258109] -> q875 (borrow)
  D: R q863..HMR q863 b99524  @files [52299461..52299746] -> q845 (borrow)
Shared-borrow rejected structurally: q845 is born (file 52101869) AFTER E's
window, and q875 is written inside D's window (19 touches incl. CCX-target).
So each block keeps its own borrow line (verified disjoint: E win touches
neither q845/q863; D win touches no q878; renames introduce no cross-touches).

Slice protocol (s7_broadcast/spillfrag/spillmulti): header + [ENTRY..D_K]
with BOTH renames applied, 4-shot, sim seed 99, init rng 0xD91; compare ALL
qubits + ALL bits; determinism rerun.
Writes artifacts/20261110_spillunified/spillunified.{diff,json}.
"""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import numpy as np

import kickmix as km

KMX = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillunified")
HEADER_END = 54146
ENTRY_CONVERT = 12006935
W = 892
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}

# (victim, borrow, F_B, F_K), file coords; cf. spillmulti_sim.py BLOCKS
BLOCKS = [
    {"tag": "E", "victim": "q878", "borrow": "q875",
     "F_B": 41258103, "F_K": 41258109, "kill_bit": "b99126"},
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

    interference = {}
    # --- interference census: each window vs the other block's victim/borrow
    for a, b in ((BLOCKS[0], BLOCKS[1]), (BLOCKS[1], BLOCKS[0])):
        for q in (b["victim"], b["borrow"]):
            hits = [i for i in range(a["F_B"], a["F_K"] + 1) if has_qtok(lines[i], q)]
            interference[f"{a['tag']}win_touches_{q}"] = hits
            print(f"[{a['tag']}win] touches {q}: n={len(hits)} first={hits[:5]}", flush=True)
    # renames introduce no new cross-touches
    for cfg in BLOCKS:
        qv, qb = cfg["victim"], cfg["borrow"]
        other = [q for blk in BLOCKS if blk["tag"] != cfg["tag"]
                 for q in (blk["victim"], blk["borrow"])]
        new = [rename(lines[i], qv, qb) for i in range(cfg["F_B"], cfg["F_K"] + 1)]
        cfg["new_mid"] = new
        intro = [(i, q) for i, l in zip(range(cfg["F_B"], cfg["F_K"] + 1), new)
                 for q in other if has_qtok(l, q) and not has_qtok(lines[i], q)]
        interference[f"{cfg['tag']}_introduced_cross"] = intro
        print(f"[{cfg['tag']}] introduced cross-touches: {intro}", flush=True)
        # static asserts (same as spillmulti per-block verification)
        assert lines[cfg["F_B"]].strip() == f"R {qv}"
        assert lines[cfg["F_K"]].strip() == f"HMR {qv} {cfg['kill_bit']}"
        p0 = sum(1 for i in range(cfg["F_B"], cfg["F_K"] + 1)
                 if lines[i].split()[0] in PAID)
        p1 = sum(1 for l in new if l.split()[0] in PAID)
        assert p0 == p1, (p0, p1)
        cfg["paid"] = [p0, p1]
        print(f"[{cfg['tag']}] paid {p0}->{p1}", flush=True)

    # q875-in-D-window is sequential third-party use AFTER E kill (not a gap
    # intrusion); the real no-go conditions are decided explicitly below.
    no_go = (
        interference["Ewin_touches_q845"] or interference["Ewin_touches_q863"]
        or interference["Dwin_touches_q878"]
        or interference["E_introduced_cross"] or interference["D_introduced_cross"]
    )
    print(f"hard conflict (merge-blocking): {bool(no_go)}", flush=True)
    if no_go:
        (ART / "spillunified.json").write_text(json.dumps(
            {"verdict": "CONFLICT", "interference": interference}, indent=1) + "\n")
        print("CONFLICT: aborting merge, no combined slice run", flush=True)
        sys.exit(2)

    # --- merged diff: per-block fragments concatenated, orig file coords
    ENTRY = ENTRY_CONVERT
    D_K = BLOCKS[1]["F_K"]
    diff_parts = []
    for cfg in BLOCKS:
        F_B, F_K = cfg["F_B"], cfg["F_K"]
        a = [f"{i}:{lines[i]}" for i in range(F_B - 3, F_K + 4)]
        b = ([f"{F_B - 3}:{lines[F_B - 3]}", f"{F_B - 2}:{lines[F_B - 2]}",
              f"{F_B - 1}:{lines[F_B - 1]}"]
             + [f"{F_B}+:{l}" for l in cfg["new_mid"]]
             + [f"{F_K + 1}:{lines[F_K + 1]}", f"{F_K + 2}:{lines[F_K + 2]}",
                f"{F_K + 3}:{lines[F_K + 3]}"])
        frag = "".join(difflib.unified_diff(
            a, b, fromfile=f"orig_fragment_{cfg['tag']}",
            tofile=f"rewritten_fragment_{cfg['tag']}"))
        diff_parts.append(f"# block {cfg['tag']}: files [{F_B}..{F_K}] "
                          f"{cfg['victim']}->{cfg['borrow']}\n" + frag)
    (ART / "spillunified.diff").write_text("\n".join(diff_parts))
    print("wrote merged diff", flush=True)

    # --- combined slice: header + [ENTRY..D_K] with BOTH renames
    header = lines[:HEADER_END]
    seg = lines[ENTRY:D_K + 1]
    E, D = BLOCKS
    new_seg = list(seg)
    for i in range(E["F_B"], E["F_K"] + 1):
        new_seg[i - ENTRY] = rename(lines[i], E["victim"], E["borrow"])
    for i in range(D["F_B"], D["F_K"] + 1):
        new_seg[i - ENTRY] = rename(lines[i], D["victim"], D["borrow"])
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
        "design": "independent-borrow merge (E:q878->q875, D:q863->q845); "
                  "shared-borrow rejected structurally",
        "windows_files": {c["tag"]: [c["F_B"], c["F_K"]] for c in BLOCKS},
        "kill_bits": {c["tag"]: c["kill_bit"] for c in BLOCKS},
        "paid_per_block": {c["tag"]: {"orig": c["paid"][0], "new": c["paid"][1],
                                       "delta": c["paid"][1] - c["paid"][0]}
                            for c in BLOCKS},
        "paid_total_delta": sum(c["paid"][1] - c["paid"][0] for c in BLOCKS),
        "hmr_stream": "positions unchanged in both windows; only kill-line "
                      "qubit operands swapped",
        "interference": {k: (v if len(v) < 8 else {"n": len(v), "first": v[:5]})
                         for k, v in interference.items()},
        "note_q875_in_D": "19 third-party touches (CX/CCX incl. CCX-target) "
                          "AFTER E kill+HMR reset; sequential reuse, not a gap "
                          "intrusion; covered by combined slice",
        "slice": {"header_end": HEADER_END, "entry": ENTRY, "tail_file": D_K,
                  "tail_len": 0, "shots": 4, "sim_seed": 99, "init_seed": "0xD91"},
        "qubits_compared": W, "qubits_equal": len(qmis) == 0,
        "qubit_mismatches": qmis, "qubits_deterministic": qR == qR2,
        "bits_compared": nbits, "bit_mismatches": bmis,
        "verdict": ("MERGE_EQUAL" if (len(qmis) == 0 and not bmis) else "MERGE_MISMATCH"),
    }
    (ART / "spillunified.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"qubits_equal": res["qubits_equal"],
                      "det": res["qubits_deterministic"], "bmis": bmis,
                      "verdict": res["verdict"]}, indent=1), flush=True)


if __name__ == "__main__":
    main()
