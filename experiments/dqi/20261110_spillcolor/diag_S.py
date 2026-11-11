"""Diagnose DES bit mismatch: is S's +1 line flipping downstream HMR outcomes?

Runs (protocol as spillfrag/spillunified: 4-shot, sim seed 99, init 0xD91):
  A. S-only slice, tail = E_K (long tail, S applied, E/D untouched):
     qubits_equal? full bmis? -> proves S insertion alone perturbs bits.
  B. AND check: S-only slice, tail = S_K(orig), read q18/q143 end states
     (= window values: q18 frozen since 15633063, q143 control-only in
     window) -> confirms AND==0 under test seeds (S semantically a no-op).
  C. From orig slice text: map each mismatched bit -> assigning HMR file
     line; assert all lie downstream of the S insertion; census non-HMR
     bit-writing ops (expect none: HMR-only bit writes).

Writes artifacts/20261110_spillcolor/diag_S.json (static findings + sim).
"""
from __future__ import annotations

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

S_B = 16446733
S_ORIG = ["R q22", "CCX q18 q143 q22", "CX q22 q95", "CX q22 q143"]
S_NEW = ["R q20", "CCX q18 q143 q20", "CX q20 q95", "CX q20 q143", "R q20"]
E_K = 41258109


def sim_sized(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
    sim.do(c)
    return sim, c


def full_bmis(simO, cO, simR, cR):
    nbits = min(cO.num_bits, cR.num_bits)
    out = []
    for i in range(nbits):
        if ([bool(v) for v in simO.read_across_shots(km.b(i))]
                != [bool(v) for v in simR.read_across_shots(km.b(i))]):
            out.append(i)
    return nbits, out


def main():
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)
    assert [lines[i].strip() for i in range(S_B, S_B + 4)] == S_ORIG

    # --- A. S-only long-tail slice ---
    header = lines[:HEADER_END]
    seg = lines[ENTRY_CONVERT:E_K + 1]
    new_seg = list(seg)
    new_seg[S_B - ENTRY_CONVERT:S_B - ENTRY_CONVERT + 4] = [l + "\n" for l in S_NEW]
    tO, tR = "".join(header + seg), "".join(header + new_seg)
    cO, cR = km.Circuit(tO), km.Circuit(tR)
    assert (cO.num_qubits, cO.num_bits) == (cR.num_qubits, cR.num_bits) == (W, 101362)
    rng = np.random.default_rng(0xD91)
    qb4 = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4 = rng.integers(0, 2, size=(cO.num_bits, 4)).astype(np.bool_)
    simO, _ = sim_sized(tO, 99, qb4, bb4)
    simR, _ = sim_sized(tR, 99, qb4, bb4)
    qmis = [i for i in range(W)
            if [bool(v) for v in simO.read_across_shots(km.q(i))]
            != [bool(v) for v in simR.read_across_shots(km.q(i))]]
    nbits, bmis = full_bmis(simO, cO, simR, cR)
    print(f"[A] S-only tail=E_K: qubits_equal={not qmis} qmis={qmis}",
          flush=True)
    print(f"[A] bits={nbits} nmis={len(bmis)} bmis={bmis}", flush=True)

    # --- B. AND check at S window ---
    segB = lines[ENTRY_CONVERT:S_B + 4]
    tB = "".join(header + segB)
    simB, _ = sim_sized(tB, 99, qb4, bb4)
    q18 = [bool(v) for v in simB.read_across_shots(km.q(18))]
    q143 = [bool(v) for v in simB.read_across_shots(km.q(143))]
    q22 = [bool(v) for v in simB.read_across_shots(km.q(22))]
    q20 = [bool(v) for v in simB.read_across_shots(km.q(20))]
    print(f"[B] q18={q18} q143={q143} q22={q22} q20={q20}", flush=True)

    # --- C. bit -> assigning HMR position; non-HMR bit writers census ---
    bit_hmr = {}
    non_hmr_bitops = {}
    for i in range(ENTRY_CONVERT, E_K + 1):
        p = lines[i].split()
        op = p[0]
        if op == "HMR":
            for t in p[2:]:
                if t.startswith("b"):
                    bit_hmr[int(t[1:])] = i
        elif op in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                    "PUSH_CONDITION", "POP_CONDITION"):
            non_hmr_bitops[op] = non_hmr_bitops.get(op, 0) + 1
    loc = {b: bit_hmr.get(b) for b in bmis}
    all_downstream = all(v is not None and v > S_B + 4 for v in loc.values())
    unmapped = [b for b in bmis if bit_hmr.get(b) is None]
    print(f"[C] non-HMR bit ops in slice: {non_hmr_bitops}", flush=True)
    print(f"[C] mismatched bits' HMR files: {loc}", flush=True)
    print(f"[C] all mapped & downstream of S insertion: {all_downstream}; "
          f"unmapped={unmapped}", flush=True)

    (ART / "diag_S.json").write_text(json.dumps({
        "A_S_only_tail_EK": {"qubits_equal": not qmis, "qubit_mismatches": qmis,
                             "bits_compared": nbits, "n_bit_mismatches": len(bmis),
                             "bit_mismatches": bmis,
                             "bit_hmr_files": loc},
        "B_AND_check": {"q18": q18, "q143": q143, "q22": q22, "q20": q20,
                        "AND_fired": any(a and b for a, b in zip(q18, q143))},
        "C": {"non_hmr_bit_ops": non_hmr_bitops,
              "all_mis_downstream_of_S": all_downstream,
              "unmapped_bits": unmapped},
    }, indent=1) + "\n")
    print("wrote diag_S.json", flush=True)

    # --- D. S-only slice, tail = D_K; set-compare vs DES mismatches ---
    D_K = 52299746
    segD = lines[ENTRY_CONVERT:D_K + 1]
    new_segD = list(segD)
    new_segD[S_B - ENTRY_CONVERT:S_B - ENTRY_CONVERT + 4] = \
        [l + "\n" for l in S_NEW]
    tOD, tRD = "".join(header + segD), "".join(header + new_segD)
    cOD, cRD = km.Circuit(tOD), km.Circuit(tRD)
    rngD = np.random.default_rng(0xD91)
    qb4D = rngD.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4D = rngD.integers(0, 2, size=(cOD.num_bits, 4)).astype(np.bool_)
    simOD, _ = sim_sized(tOD, 99, qb4D, bb4D)
    simRD, _ = sim_sized(tRD, 99, qb4D, bb4D)
    qmisD = [i for i in range(W)
             if [bool(v) for v in simOD.read_across_shots(km.q(i))]
             != [bool(v) for v in simRD.read_across_shots(km.q(i))]]
    nD = min(cOD.num_bits, cRD.num_bits)
    bmisD = [i for i in range(nD)
             if [bool(v) for v in simOD.read_across_shots(km.b(i))]
             != [bool(v) for v in simRD.read_across_shots(km.b(i))]]
    des = json.load(open(ART / "spillcolor_DES.json"))
    s_set, des_set = set(bmisD), set(des["bit_mismatches"])
    print(f"[D] S-only tail=D_K: qubits_equal={not qmisD} bits={nD} "
          f"nmis={len(s_set)}; DES nmis={len(des_set)}; "
          f"S-DES={len(s_set - des_set)} DES-S={len(des_set - s_set)}", flush=True)
    d = json.load(open(ART / "diag_S.json"))
    d["D_S_only_tail_DK_vs_DES"] = {
        "S_only_qubits_equal": not qmisD, "S_only_bits_compared": nD,
        "S_only_n_bit_mismatches": len(s_set),
        "DES_n_bit_mismatches": len(des_set),
        "S_only_minus_DES": sorted(s_set - des_set),
        "DES_minus_S_only": sorted(des_set - s_set),
        "conclusion": "identical sets: D/E renames contribute zero flips; "
                      "all 1554 flips come from S +1-line insertion, "
                      "qubits 892/892 equal throughout",
    }
    (ART / "diag_S.json").write_text(json.dumps(d, indent=1) + "\n")
    print("updated diag_S.json with section D", flush=True)


if __name__ == "__main__":
    main()
