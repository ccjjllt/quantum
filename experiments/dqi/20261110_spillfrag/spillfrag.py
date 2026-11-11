"""DQI Q-1 unified-spill first candidate fragment (borrow-reroute) + slice check.

Cut: min exact-live clique witness [16391916,16391920] (op coords):
  R q22 ; CCX q18 q143 q22 ; CX q22 q95 ; CX q22 q143 ; CX q17 q84 ; HMR q24 b101243
Spill rule under test (borrow-reroute, 0 new paid):
  victim q22's window R dropped; compute+uses retargeted onto q20, which is
  proven |0> at the borrow point (HMR q20 b101249 @op16391778 + zero q20
  touches until restore; punch.json cone_touch_ub=0, uses_in_block=0);
  R q20 (borrow, no-op) + CCX q18 q143 q20 + CX q20 q95 + CX q20 q143
  + R q20 (restore, kills only dead scratch AND).
  Paid 1 -> 1 (delta 0); added gates all free (+2 R); removed 1 free R.
  Placement: borrow-R at dropped-R position; compute immediately after;
  each CX retargeted 1:1 in order; restore-R immediately after last use.

Slice (s7_broadcast.py protocol): header + [convert-entry .. rewrite point],
4-shot, sim seed 99, init rng 0xD91; TAIL=0 and TAIL=8000 (file lines);
compare 892 qubits + all bits; determinism rerun. No scratch bits added.
Static check included: victim q22's next touch after the window (read vs kill).

Writes artifacts/20261110_spillfrag/spillfrag.{diff,json} (+tail json).
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

import numpy as np

import kickmix as km

KMX = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillfrag")
OUT_JSON = ART / "spillfrag.json"
OUT_TAIL = ART / "spillfrag_tail.json"
DIFF = ART / "spillfrag.diff"

HEADER_END = 54146          # first counted line (BIT_STORE0 b49140)
ENTRY = 12006935            # file line of INFO_TAG @enter:convert
F_R = 16446733              # R q22            (op 16391915)
F_CCX = 16446734            # CCX q18 q143 q22 (op 16391916)
F_CX1 = 16446735            # CX q22 q95       (op 16391917)
F_CX2 = 16446736            # CX q22 q143      (op 16391918)
F_CXU = 16446737            # CX q17 q84       (op 16391919)
F_HMR = 16446738            # HMR q24 b101243 (op 16391920)
TAIL2 = 8000
W = 892

SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


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


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    assert lines[F_R].strip() == "R q22", lines[F_R][:40]
    assert lines[F_CCX].strip() == "CCX q18 q143 q22", lines[F_CCX][:40]
    assert lines[F_CX1].strip() == "CX q22 q95", lines[F_CX1][:40]
    assert lines[F_CX2].strip() == "CX q22 q143", lines[F_CX2][:40]
    assert lines[F_CXU].strip() == "CX q17 q84", lines[F_CXU][:40]
    assert lines[F_HMR].strip() == "HMR q24 b101243", lines[F_HMR][:40]

    # static: victim q22 next touch after window (read vs R-kill)
    nxt = None
    op_idx = -1
    for ln in range(len(lines)):
        l = lines[ln].rstrip("\n")
        if not l or l.startswith(SKIP):
            continue
        op_idx += 1
        if op_idx <= 16391918:
            continue
        p = l.split()
        if p[0] in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                     "PUSH_CONDITION", "POP_CONDITION"):
            continue
        toks = [t for t in p[1:] if t.startswith("q") and t[1:].replace(",", "").isdigit()]
        if "q22" in toks:
            nxt = {"op": op_idx, "fileline": ln, "text": l[:60]}
            break
    print("next q22 touch after window:", nxt, flush=True)

    # static: no q20 touch in [16391778(HMR birth), F_HMR] except the birth
    op_idx = -1
    q20hits = []
    for ln in range(len(lines)):
        l = lines[ln].rstrip("\n")
        if not l or l.startswith(SKIP):
            continue
        op_idx += 1
        if op_idx < 16391778 or op_idx > 16391920:
            continue
        p = l.split()
        if p[0] in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                     "PUSH_CONDITION", "POP_CONDITION"):
            continue
        toks = [t for t in p[1:] if t.startswith("q")]
        if "q20" in toks:
            q20hits.append((op_idx, l[:60]))
    print("q20 touches in [birth..window-end]:", q20hits, flush=True)
    assert len(q20hits) == 1 and q20hits[0][0] == 16391778, q20hits

    new_mid = ["R q20\n", "CCX q18 q143 q20\n", "CX q20 q95\n",
               "CX q20 q143\n", "R q20\n"]
    header = lines[:HEADER_END]

    # fragment diff (s7 style, file-line coords, +-3 context)
    a = [f"{i}:{lines[i]}" for i in range(F_R - 3, F_CX2 + 4)]
    b = ([f"{F_R - 3}:{lines[F_R - 3]}", f"{F_R - 2}:{lines[F_R - 2]}",
          f"{F_R - 1}:{lines[F_R - 1]}"]
         + [f"{F_R}+:{l}" for l in new_mid]
         + [f"{F_CX2 + 1}:{lines[F_CX2 + 1]}", f"{F_CX2 + 2}:{lines[F_CX2 + 2]}",
            f"{F_CX2 + 3}:{lines[F_CX2 + 3]}"])
    DIFF.write_text("".join(difflib.unified_diff(a, b, fromfile="orig_fragment",
                                                 tofile="rewritten_fragment")))
    print(f"wrote {DIFF}", flush=True)

    rng = np.random.default_rng(0xD91)
    c0 = km.Circuit("".join(header + lines[ENTRY:F_R]))
    qb = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb = rng.integers(0, 2, size=(c0.num_bits, 4)).astype(np.bool_)

    def build(tail):
        tO = "".join(header + lines[ENTRY:F_R]
                     + lines[F_R:F_CX2 + 1] + lines[F_CX2 + 1:F_CX2 + 1 + tail])
        tR = "".join(header + lines[ENTRY:F_R]
                     + new_mid + lines[F_CX2 + 1:F_CX2 + 1 + tail])
        return tO, tR

    for tag, tail, out in (("TAIL0", 0, OUT_JSON), ("TAIL8000", TAIL2, OUT_TAIL)):
        tO, tR = build(tail)
        cO, cR = km.Circuit(tO), km.Circuit(tR)
        print(f"{tag}: orig q/b={cO.num_qubits}/{cO.num_bits} "
              f"rewritten q/b={cR.num_qubits}/{cR.num_bits}", flush=True)
        assert cO.num_qubits == cR.num_qubits == W
        assert cO.num_bits == cR.num_bits
        bbx = bb[:cO.num_bits]
        print(f"{tag}: sim original...", flush=True)
        simO, cO2 = sim_sized(tO, 99, qb, bbx)
        print(f"{tag}: sim rewritten...", flush=True)
        simR, cR2 = sim_sized(tR, 99, qb, bbx)
        print(f"{tag}: sim rewritten again (determinism)...", flush=True)
        simR2, _ = sim_sized(tR, 99, qb, bbx)
        qmis, nbits, bmis = compare(simO, cO2, simR, cR2)
        qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
        qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
        res = {
            "fragment": {"borrow": "R q22@op16391915 -> R q20",
                         "compute": "CCX q18 q143 q22 -> CCX q18 q143 q20",
                         "uses": ["CX q22 q95 -> CX q20 q95",
                                  "CX q22 q143 -> CX q20 q143"],
                         "restore": "R q20 after last use",
                         "tail_file_lines": tail,
                         "static_paid_orig": 1, "static_paid_new": 1,
                         "static_paid_delta": 0,
                         "added_gates": ["R q20 x2 (free)"],
                         "removed_gates": ["R q22 (free)"]},
            "qubits_compared": W, "qubits_equal": len(qmis) == 0,
            "qubit_mismatches": qmis,
            "qubits_deterministic": qR == qR2,
            "bits_compared": nbits, "bit_mismatches": bmis,
            "static_next_q22_touch": nxt,
            "q20_borrow_safety": q20hits,
        }
        out.write_text(json.dumps(res, indent=1) + "\n")
        print(f"{tag}: qubits_equal={res['qubits_equal']} qmis={qmis} "
              f"det={res['qubits_deterministic']} bits={nbits} bmis={bmis[:20]}",
              flush=True)
        print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    main()
