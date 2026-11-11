"""Stage-1 static anatomy of ANGLE loader phase-2 (no synthesis, no verifier).

Usage: uv run python experiments/dfthcsos/20261112_synth/analyze_products.py
Reads artifacts/20261111_maoxin303 + artifacts/20261111_lera11x, prints:
  1. prefix-69 identity check across loaders/versions
  2. per-loader CCX accounting: prefix / setup(q120+) / loads, pairs, CX
  3. k1 block-hypothesis tests (contiguity gaps, delta rank, k-means-5,
     setup-seed signatures) - all static, kmx topology only.
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np

WORK = Path(__file__).resolve().parents[3]
MAO = WORK / "artifacts/20261111_maoxin303"
LERA = WORK / "artifacts/20261111_lera11x"


def kmx_lines(path: Path):
    import kickmix

    c = kickmix.Circuit.from_file(str(path), format="auto")
    c.to_file("/tmp/synth_stage1.kmx", format="kmx")
    lines = [
        l.strip()
        for l in open("/tmp/synth_stage1.kmx").read().splitlines()
        if l.strip() and not l.strip().startswith(("REGISTER", "APPEND"))
    ]
    return c, lines


def ccx_of(lines):
    return [l for l in lines if l.startswith("CCX")]


def accounting(path: Path):
    c, lines = kmx_lines(path)
    ccx = ccx_of(lines)
    pre, rest = ccx[:69], ccx[69:]
    setup = [l for l in rest if l.split()[3] in
             ("q120", "q121", "q122", "q123", "q124", "q125", "q126", "q127")]
    loads = [l for l in rest if l not in setup]
    ab = Counter((l.split()[1], l.split()[2]) for l in loads)
    tg = Counter(l.split()[3] for l in loads)
    n_cx = sum(1 for l in lines if l.startswith("CX"))
    return {"n": len(ccx), "nq": c.num_qubits, "ncx": n_cx,
            "nsetup": len(setup), "setup": setup, "nloads": len(loads),
            "npairs": len(ab), "top": ab.most_common(4), "tg": dict(tg),
            "pre": pre, "loads_seq": loads}


def gfrank_int(vecs):
    basis = {}
    for v in vecs:
        x = v
        while x:
            b = x.bit_length() - 1
            if b in basis:
                x ^= basis[b]
            else:
                basis[b] = x
                break
    return len(basis)


def main():
    # 1. prefix identity
    prefs = {}
    for tag, p in [("Mao-k1", MAO / "angle_k_1.kmb"),
                   ("Lera-k1", LERA / "angle_k_1.kmb"),
                   ("Mao-k0", MAO / "angle_k_0.kmb")]:
        prefs[tag] = accounting(p)["pre"]
    print("prefix69 Mao-k1==Lera-k1:", prefs["Mao-k1"] == prefs["Lera-k1"],
          " Mao-k1==Mao-k0:", prefs["Mao-k1"] == prefs["Mao-k0"])

    # 2. accounting table
    for ver, base in [("Lera", LERA), ("Mao ", MAO)]:
        rows = []
        for k in range(15):
            a = accounting(base / f"angle_k_{k}.kmb")
            rows.append(f"k{k}:{a['n']}=69+{a['nsetup']}+{a['nloads']}/pairs{a['npairs']}")
        print(ver, " ".join(rows))

    # 3. k1 deep dive (Mao vs Lera)
    m1 = accounting(MAO / "angle_k_1.kmb")
    l1 = accounting(LERA / "angle_k_1.kmb")
    print("Mao-k1 setup:", m1["setup"])
    print("Lera-k1 setup:", l1["setup"])
    print("Mao-k1 targets:", m1["tg"], " CX:", m1["ncx"])
    print("Lera-k1 targets:", l1["tg"], " CX:", l1["ncx"], " top:", l1["top"])

    # 4. block tests on Mao-k1 215 loads (single pair q126,q127)
    _, lines = kmx_lines(MAO / "angle_k_1.kmb")
    nq = 128
    idx = [i for i, l in enumerate(lines)
           if l.startswith("CCX q126 q127") or l.startswith("CCX q127 q126")]
    assert len(idx) == 215, len(idx)
    gaps = [idx[j + 1] - idx[j] - 1 for j in range(len(idx) - 1)]
    print(f"gaps: mean={sum(gaps) / len(gaps):.1f} min={min(gaps)} max={max(gaps)}")
    M = np.zeros((215, 2 * nq), dtype=np.uint8)
    prev = 0
    for j, i in enumerate(idx):
        for l in lines[prev:i]:
            p = l.split()
            if p[0] == "CX" and p[2] in ("q126", "q127"):
                M[j, int(p[1][1:]) + (0 if p[2] == "q126" else nq)] ^= 1
        prev = i
    print("delta-rank acc126/acc127/stacked:",
          gfrank_int([int("".join(map(str, row[:nq][::-1])), 2) for row in M]),
          "(ref: full-matrix ranks 92/92/93; combined-row rank 184 - see README)")

    # linearized factor rank (fresh var per CCX)
    vals = [1 << q for q in range(nq)]
    loads, nccx = [], 0
    for l in lines:
        p = l.split()
        if p[0] == "CX":
            vals[int(p[2][1:])] ^= vals[int(p[1][1:])]
        elif p[0] == "CCX":
            if (p[1], p[2]) in (("q126", "q127"), ("q127", "q126")):
                loads.append((vals[126], vals[127], p[3]))
            vals[int(p[3][1:])] ^= (1 << (nq + nccx))
            nccx += 1
    facs = [v for a, b, _ in loads for v in (a, b)]
    print("linearized factor rank (430 rows):", gfrank_int(facs))
    tg = [t for _, _, t in loads]
    for ch in range(5):
        print(f"chunk{ch} targets:", dict(Counter(tg[ch * 43:(ch + 1) * 43])))


if __name__ == "__main__":
    sys.exit(main())
