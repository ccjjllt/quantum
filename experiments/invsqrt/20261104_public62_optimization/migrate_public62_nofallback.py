"""Migrate stage1 nofallback selector onto Kirill V5 62Q baseline.

Baseline (true construction input): artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb
  SHA ed77292a0e4a267e62235055cc2ab7faaa30b15d8a150bab79f34e5c1b8f172b
Replaces window [27745,28753) with trial1/2/40 three-branch no-fallback selector.
Window-exterior instructions are copied verbatim. Fresh classical bits 42006..42014
(baseline max is 42005; b42002..b42005 stay untouched).
Expected gain: exactly-one-branch covering at 1 CCX/shot vs two-selector window.
"""
from __future__ import annotations
import argparse, hashlib, io, json, random
from pathlib import Path

import numpy as np, kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb"
BASE_SHA = "ed77292a0e4a267e62235055cc2ab7faaa30b15d8a150bab79f34e5c1b8f172b"
ART = ROOT / "artifacts/20261104_public62_optimization/invsqrt"
LO, MID, PREP2_LO, LO2, HI = 27745, 28183, 28183, 28315, 28753
PRE1 = (27613, 27745)
PRE2 = (28183, 28315)
WORDS = [14, 16, 17, 19, 20, 22, 29, 30, 31, 25, 26, 45, 46, 47, 48, 52, 55, 56, 58]
F_BITS = [42006, 42007, 42008]
S_BITS = [42009, 42010, 42011]
H_BITS = [42012, 42013, 42014]


def load(path: Path):
    c = km.Circuit.from_file(path)
    buf = io.StringIO(); c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]
    return c, hdr, ops


def discover(hdr, ops, c):
    import sys
    sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
    from invsqrt import verify_submission_invsqrt as official
    xs = np.arange(1, 64, dtype=np.uint64)
    xr, _ = official.validate_registers(c, official.ProblemSpecInvSqrt.for_n_p(10))
    prefix = km.Circuit.from_file(io.StringIO("\n".join(hdr + ops[:LO]) + "\n"), format="kmx")
    sim = km.Simulator(batch_size=63, seed=113)
    sim.write_across_shots(xr, official.to_bits(xs, 22))
    sim.do(prefix)
    mat = np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(62)])))
    truth = [sum(int(b) << i for i, b in enumerate(row)) for row in mat]
    one = (1 << 63) - 1
    assert truth[21] == one and truth[28] == 0 and truth[40] == 0
    leaves: dict[int, int] = {}; forms: dict[int, int] = {}
    for lo, hi in [PRE1, PRE2]:
        for line in ops[lo:hi]:
            p = line.split(); target = int(p[1][1:]); kind = p[0]
            if kind == "BIT_STORE0": forms[target] = 0
            elif kind == "BIT_STORE1": forms[target] = 1 << 128
            elif kind == "BIT_INVERT":
                source = int(p[-1][1:])
                if source in forms: value = forms[source]
                else:
                    if source not in leaves: leaves[source] = 1 << len(leaves)
                    value = leaves[source]
                forms[target] ^= value
    targets = []
    for source, bit in leaves.items():
        val = 0
        for start, ctrl in [(24256, 18), (24320, 27)]:
            for j, w in enumerate(WORDS):
                if forms[start + j] & bit: val ^= truth[ctrl] & truth[w]
        targets.append(val)

    def make_basis(columns):
        basis = {}
        for j, vec in enumerate(columns):
            comb = 1 << j
            while vec:
                pivot = vec.bit_length() - 1
                if pivot not in basis: basis[pivot] = (vec, comb); break
                vv, cc = basis[pivot]; vec ^= vv; comb ^= cc
        return basis

    def partial(vec, basis):
        comb = rem = 0
        while vec:
            pivot = vec.bit_length() - 1
            if pivot in basis:
                vv, cc = basis[pivot]; vec ^= vv; comb ^= cc
            else: rem ^= 1 << pivot; vec ^= 1 << pivot
        return comb, rem

    rng = random.Random(8121)
    wanted = {1, 2, 40}
    branches = {}
    for trial in range(100):
        sel = rng.getrandbits(62) & ~((1 << 28) | (1 << 40))
        u = 0
        for j in range(62):
            if sel >> j & 1: u ^= truth[j]
        columns = [one] + truth + [u & t for t in truth]
        basis = make_basis(columns)
        if len(basis) != 62: continue
        solutions = [partial(t, basis) for t in targets]
        residuals = {r for _, r in solutions if r}
        if len(residuals) != 1: continue
        failure = sum(bool(r) << j for j, (_, r) in enumerate(solutions))
        if trial in wanted:
            branches[trial] = {
                "trial": trial,
                "u_wires": [j for j in range(62) if sel >> j & 1],
                "span_rank": len(basis), "failure_mask": failure,
                "residual_vector": next(iter(residuals)),
                "solutions": [
                    {"source_bit": b, "column_mask": comb, "residual": bool(rem)}
                    for b, (comb, rem) in zip(leaves, solutions)],
            }
            for (comb, rem), t in zip(
                    [(s["column_mask"], 1 if s["residual"] else 0)
                     for s in branches[trial]["solutions"]], targets):
                rep = branches[trial]["residual_vector"] if rem else 0
                for col, value in enumerate(columns):
                    if comb >> col & 1: rep ^= value
                assert rep == t
        if len(branches) == 3: break
    assert set(branches) == {1, 2, 40}
    assert branches[1]["failure_mask"] == 0x1CBC6090
    assert branches[2]["failure_mask"] == 0x0185ECD3
    assert branches[40]["failure_mask"] == 0x1D398C43
    assert (branches[1]["failure_mask"] ^ branches[2]["failure_mask"]
            ^ branches[40]["failure_mask"]) == 0
    return {"truth_63x62": truth, "source_bits": list(leaves),
            "branches": [branches[1], branches[2], branches[40]]}


def joint_replacement(ops, doc):
    out = list(ops[PRE2[0]:PRE2[1]])
    for j, br in enumerate(doc["branches"]):
        out.append(f"BIT_STORE0 b{F_BITS[j]}")
        for b in doc["source_bits"]:
            k = doc["source_bits"].index(b)
            if br["failure_mask"] >> k & 1: out.append(f"BIT_INVERT b{F_BITS[j]} if b{b}")
        out += [f"BIT_STORE1 b{S_BITS[j]}", f"BIT_INVERT b{S_BITS[j]} if b{F_BITS[j]}"]
    for j, br in enumerate(doc["branches"]):
        out.append(f"PUSH_CONDITION if b{S_BITS[j]}")
        computes = [f"CX q{w} q28" for w in br["u_wires"]]
        out += computes + ["CCX q21 q28 q40"]
        for row in br["solutions"]:
            mask = row["column_mask"]; b = row["source_bit"]
            if mask & 1: out.append(f"Z q21 if b{b}")
            for q in range(62):
                if mask >> (q + 1) & 1:
                    out.append(("Z q21" if q == 21 else f"CZ q21 q{q}") + f" if b{b}")
                if mask >> (q + 63) & 1:
                    out.append(f"CZ q40 q{q} if b{b}")
        out += [f"HMR q40 b{H_BITS[j]}", f"CZ q21 q28 if b{H_BITS[j]}"] + computes[::-1]
        out.append("POP_CONDITION")
        out.append(f"PUSH_CONDITION if b{F_BITS[j]}")
    out += ["POP_CONDITION"] * 3
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(BASE))
    ap.add_argument("--baseline-sha", default=BASE_SHA)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    raw = Path(args.baseline).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == BASE_SHA, f"baseline SHA mismatch {sha}"
    assert sha == args.baseline_sha, "baseline-sha arg mismatch"
    c, hdr, ops = load(Path(args.baseline))
    assert c.num_qubits == 62, c.num_qubits
    assert len(ops) == 48088, len(ops)
    assert ops[LO] == "CZ q18 q21 if b24294", ops[LO]
    assert ops[LO2] == "CZ q27 q21 if b24358", ops[LO2]
    doc = discover(hdr, ops, c)
    joint_new = joint_replacement(ops, doc)
    full = ops[:LO] + joint_new + ops[HI:]
    nc = km.Circuit.from_file(io.StringIO("\n".join(hdr + full) + "\n"), format="kmx")
    assert nc.num_qubits == 62
    assert [l for l in full if l.startswith("Z_POW")] == [l for l in ops if l.startswith("Z_POW")]
    ART.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else ART / "public62_nofallback.kmb"
    nc.to_file(out_path, format="kmb")
    cand_sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
    window_sha = hashlib.sha256("\n".join(joint_new).encode()).hexdigest()
    result = {
        "parent_baseline_sha256": sha,
        "parent_baseline_path": str(args.baseline),
        "replaced_window": [LO, HI],
        "kept_second_prep": list(PRE2),
        "fresh_bits": {"failure": F_BITS, "select": S_BITS, "hmr": H_BITS},
        "candidate_sha256": cand_sha,
        "candidate_window_sha256": window_sha,
        "qubits": 62, "operations": len(full), "joint_len": len(joint_new),
        "branches": [{"trial": b["trial"], "failure_mask": hex(b["failure_mask"]),
                      "u_pop": len(b["u_wires"])} for b in doc["branches"]],
        "failure_xor_zero": True,
        "source_bits": doc["source_bits"],
        "status": "built; audit/proof/official pending",
    }
    (out_path.with_suffix(".json")).write_text(json.dumps(result, indent=2) + "\n")
    print("MIGRATED_BUILT " + cand_sha + " Q62 ops " + str(len(full)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
