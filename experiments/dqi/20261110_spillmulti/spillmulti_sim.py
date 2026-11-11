"""DQI spillmulti: borrow-reroute TAIL=0 slice verification for blocks D and E.

Full-window replay shape (unconditional, dead-after victim):
  orig: R qV ; ... all qV touches (compute+controls+targets+SWAPs) ... ; HMR qV bX
  new : R qB ; ... same lines with token qV->qB ...                    ; HMR qB bX
Borrow qB: HMR-born, strict zero touches in [birth..kill] (verified in-script
by backward scan to birth + forward gap scan; cf. borrow_strict_check.py).
HMR stream order/positions unchanged (only kill line's qubit operand swaps);
paid (CCX/CCZ/CSWAP) identical by construction (pure rename).

Slice protocol (s7_broadcast/spillfrag): header + [ENTRY..kill], 4-shot,
sim seed 99, init rng 0xD91; compare ALL qubits + ALL bits; determinism rerun.
Writes artifacts/20261110_spillmulti/spill{D,E}.{diff,json}.
"""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import numpy as np

import kickmix as km

KMX = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillmulti")
HEADER_END = 54146
ENTRY_CONVERT = 12006935
W = 892
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")

BLOCKS = {
    # D: M_at block head; victim q863 full window [R..HMR]; borrow q845 (strict q20)
    "D": {"victim": "q863", "borrow": "q845", "F_B": 52299461, "F_K": 52299746,
          "ENTRY": ENTRY_CONVERT, "expect_uses": 41, "birth_op": 52030323,
          "birth_kind": "HMR"},
    # E: short block span 5; victim q878 full window; borrow q875 (strict q20)
    "E": {"victim": "q878", "borrow": "q875", "F_B": 41258103, "F_K": 41258109,
          "ENTRY": ENTRY_CONVERT, "expect_uses": 7, "birth_op": 41176959,
          "birth_kind": "HMR"},
}


def qtok(line):
    p = line.split()
    return p[0], p[1:]


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


def verify_block(lines, tag, cfg):
    qv, qb = cfg["victim"], cfg["borrow"]
    F_B, F_K, ENTRY = cfg["F_B"], cfg["F_K"], cfg["ENTRY"]
    assert lines[F_B].strip() == f"R {qv}", lines[F_B][:40]
    assert lines[F_K].strip().startswith(f"HMR {qv} b"), lines[F_K][:40]
    killbit = lines[F_K].split()[2]
    # window: no conditionals at all
    for i in range(F_B, F_K + 1):
        assert " if " not in lines[i], (i, lines[i][:60])
    # victim-touching lines in window
    vlines = [i for i in range(F_B, F_K + 1) if has_qtok(lines[i], qv)]
    assert len(vlines) == cfg["expect_uses"], (len(vlines), cfg["expect_uses"])
    assert vlines[0] == F_B and vlines[-1] == F_K
    # role census of victim touches
    roles = {}
    for i in vlines:
        roles[lines[i].split()[0]] = roles.get(lines[i].split()[0], 0) + 1
    assert set(roles) <= {"R", "CCX", "CX", "SWAP", "HMR"}, roles
    # borrow: zero touches in orig window
    for i in range(F_B, F_K + 1):
        assert not has_qtok(lines[i], qb), (i, lines[i][:60])
    # borrow birth: backward scan for last qb touch, must be R/HMR birth (strict q20)
    F_birth = None
    for i in range(F_B - 1, -1, -1):
        if has_qtok(lines[i], qb):
            F_birth = i
            break
    assert F_birth is not None
    bt = lines[F_birth].strip()
    assert bt == f"R {qb}" or bt.startswith(f"HMR {qb} b"), bt[:60]
    assert cfg["birth_kind"] in bt
    # strict gap: zero touches in (birth..F_B)
    for i in range(F_birth + 1, F_B):
        assert not has_qtok(lines[i], qb), (i, lines[i][:60])
    gap = F_B - F_birth
    # paid census (orig window vs renamed window: identical by rename)
    def paid(i0, i1, ren):
        n = 0
        for i in range(i0, i1 + 1):
            op = lines[i].split()[0]
            if op in PAID:
                n += 1
        return n
    p0 = paid(F_B, F_K, False)
    new_mid = [rename(lines[i], qv, qb) for i in range(F_B, F_K + 1)]
    p1 = sum(1 for l in new_mid if l.split()[0] in PAID)
    assert p0 == p1, (p0, p1)
    # HMR preservation: same count, same relative positions; only kill line differs
    hO = [i for i in range(F_B, F_K + 1) if lines[i].startswith("HMR")]
    assert len(hO) == 1 and hO[0] == F_K, hO
    assert new_mid[-1].strip() == f"HMR {qb} {killbit}", new_mid[-1][:60]
    print(f"[{tag}] victim window roles={roles} paid={p0}->{p1} "
          f"borrow {qb} birth file={F_birth} ({bt.strip()[:40]}) gap={gap} file lines",
          flush=True)
    header = lines[:HEADER_END]
    # diff (s7 style, file coords +-3)
    a = [f"{i}:{lines[i]}" for i in range(F_B - 3, F_K + 4)]
    b = ([f"{F_B - 3}:{lines[F_B - 3]}", f"{F_B - 2}:{lines[F_B - 2]}",
          f"{F_B - 1}:{lines[F_B - 1]}"]
         + [f"{F_B}+:{l}" for l in new_mid]
         + [f"{F_K + 1}:{lines[F_K + 1]}", f"{F_K + 2}:{lines[F_K + 2]}",
            f"{F_K + 3}:{lines[F_K + 3]}"])
    (ART / f"spill{tag}.diff").write_text("".join(difflib.unified_diff(
        a, b, fromfile="orig_fragment", tofile="rewritten_fragment")))
    # slice build
    tO = "".join(header + lines[ENTRY:F_K + 1])
    tR = "".join(header + lines[ENTRY:F_B] + new_mid + lines[F_K + 1:F_K + 1])
    cO, cR = km.Circuit(tO), km.Circuit(tR)
    print(f"[{tag}] q/b orig={cO.num_qubits}/{cO.num_bits} "
          f"new={cR.num_qubits}/{cR.num_bits}", flush=True)
    assert cO.num_qubits == cR.num_qubits == W
    assert cO.num_bits == cR.num_bits
    rng = np.random.default_rng(0xD91)
    qb4 = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4 = rng.integers(0, 2, size=(cO.num_bits, 4)).astype(np.bool_)
    print(f"[{tag}] sim orig...", flush=True)
    simO, _ = sim_sized(tO, 99, qb4, bb4)
    print(f"[{tag}] sim rewritten...", flush=True)
    simR, _ = sim_sized(tR, 99, qb4, bb4)
    print(f"[{tag}] sim rewritten again...", flush=True)
    simR2, _ = sim_sized(tR, 99, qb4, bb4)
    qmis, nbits, bmis = compare(simO, cO, simR, cR)
    qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    res = {
        "block": tag, "victim": qv, "borrow": qb,
        "window_files": [F_B, F_K], "kill_bit": killbit,
        "victim_roles": roles, "n_retargeted": len(vlines),
        "static_paid_orig": p0, "static_paid_new": p1, "static_paid_delta": p1 - p0,
        "added_gates": [f"R {qb} (free, at victim-R position)"],
        "removed_gates": [f"R {qv} (free)"],
        "borrow_birth": {"file": F_birth, "text": bt.strip()[:60],
                         "gap_file_lines": gap, "census_birth_op": cfg["birth_op"]},
        "hmr_stream": "positions unchanged; only kill-line qubit operand swapped",
        "tail_file_lines": 0,
        "qubits_compared": W, "qubits_equal": len(qmis) == 0,
        "qubit_mismatches": qmis, "qubits_deterministic": qR == qR2,
        "bits_compared": nbits, "bit_mismatches": bmis,
    }
    (ART / f"spill{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"[{tag}] qubits_equal={res['qubits_equal']} det={res['qubits_deterministic']} "
          f"bits={nbits} bmis={bmis[:20]}", flush=True)
    return res


def main():
    only = sys.argv[1:] or ["D", "E"]
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)
    out = {}
    for tag in only:
        out[tag] = verify_block(lines, tag, BLOCKS[tag])
    print(json.dumps({k: {"qubits_equal": v["qubits_equal"],
                           "det": v["qubits_deterministic"],
                           "bmis": v["bit_mismatches"]} for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
