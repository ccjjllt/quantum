"""Phase-rotation census on Public Frontier 7c10edba (static only, no semantics changed).

Reads artifacts/20261108_public_frontier/release/invsqrt.kmb, dumps kmx, and:
  1. lists every Z_POW (idx, qubit, exact decimal angle, Clifford/T/rotation class,
     PUSH depth + inline guard);
  2. checks same-wire consecutive-merge possibility: between two consecutive Z_POWs
     on the same qubit, classifies every intervening op touching that qubit as
     RESET (HMR/R), NONDIAG_TOUCH (X/CX/CCX/SWAP/CSWAP, any guard), or DIAGONAL
     (Z/CZ/CCZ/Z_POW, commutes). Mergeable only if no RESET / no NONDIAG_TOUCH
     and identical guard context.
  3. full-domain zero-branch bit-parallel simulation (3,133,452 inputs as 48,961
     uint64 words; conditional/deep ops skipped, diagonal gates no-op) recording
     the target-qubit word vector at each Z_POW (rotation coefficient mask);
     pairwise equality test over the 41 rotation masks.

Output: phase_census.json (this dir). Masks npz -> artifacts/20261109_tphase_fusion/.
Ref: verifier cost model data/competition/verifiers/invsqrt/verify_submission_invsqrt.py
(z_pow_class / rotation_t_count), hierarchy counts via operation_statistics().
"""
from __future__ import annotations

import io
import json
from fractions import Fraction
from pathlib import Path

import kickmix as km
import numpy as np

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
OUT_JSON = Path("experiments/invsqrt/20261109_tphase_fusion/phase_census.json")
OUT_NPZ = Path("artifacts/20261109_tphase_fusion/rotation_masks.npz")
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64
LAST_MASK = np.uint64((1 << (N_INPUTS % 64)) - 1) if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)


def z_pow_class(half_turns: Fraction) -> str:
    if half_turns % Fraction(1, 2) == 0:
        return "clifford"
    if half_turns % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def load_ops() -> tuple[list[str], km.Circuit]:
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines()
           if l and not l.startswith(("APPEND", "REGISTER"))]
    return ops, c


def guard_of(line: str, depth: int, stack: list[str]) -> dict:
    inline = None
    if " if " in line:
        inline = line.split(" if ", 1)[1].strip()
    return {"depth": depth, "push": list(stack), "inline": inline}


def main() -> None:
    ops, circ = load_ops()
    s = circ.operation_statistics()
    hier = {str(k): v for k, v in s.z_pow_clifford_hierarchy_counts.items()}

    # ---- 1. enumerate Z_POWs with guard context ----
    zlist: list[dict] = []
    depth = 0
    stack: list[str] = []
    for idx, line in enumerate(ops):
        if line.startswith("PUSH_CONDITION"):
            stack.append(line.split("CONDITION", 1)[1].strip())
            depth += 1
            continue
        if line.startswith("POP_CONDITION"):
            depth -= 1
            stack.pop()
            continue
        parts = line.split()
        if parts[0] == "Z_POW":
            q = parts[1]
            ang = Fraction(parts[2])  # exact decimal -> Fraction
            g = guard_of(line, depth, stack)
            zlist.append({"idx": idx, "qubit": q,
                          "angle_str": parts[2],
                          "angle_half_turns": str(ang),
                          "angle_turns": str(ang / 2),
                          "class": z_pow_class(ang),
                          "guard": g,
                          "unconditional": depth == 0 and g["inline"] is None})
    assert len(zlist) == 48, len(zlist)

    # ---- 2. same-wire consecutive merge check ----
    NONDIAG = {"X", "CX", "CCX", "SWAP", "CSWAP", "HMR", "R"}
    DIAG = {"Z", "CZ", "CCZ", "Z_POW"}

    def qubits_of(op: str, parts: list[str]) -> list[str]:
        if op in ("X", "Z", "Z_POW", "HMR", "R"):
            return [parts[1]]
        if op in ("CX", "CZ", "SWAP"):
            return [parts[1], parts[2]]
        if op in ("CCX", "CCZ", "CSWAP"):
            return [parts[1], parts[2], parts[3]]
        return []

    by_qubit: dict[str, list[int]] = {}
    for n, z in enumerate(zlist):
        by_qubit.setdefault(z["qubit"], []).append(n)
    pairs: list[dict] = []
    for q, members in sorted(by_qubit.items()):
        for a, b in zip(members, members[1:]):
            ia, ib = zlist[a]["idx"], zlist[b]["idx"]
            reset = False
            nondiag: list[str] = []
            diag_only = True
            for j in range(ia + 1, ib):
                l2 = ops[j]
                if l2.startswith(("PUSH_CONDITION", "POP_CONDITION")):
                    continue
                p2 = l2.split()
                op2 = p2[0]
                if op2 in ("NEG", "BIT_INVERT", "BIT_STORE0", "BIT_STORE1"):
                    continue
                qs = qubits_of(op2, p2)
                if q not in qs:
                    continue
                if op2 in ("HMR", "R"):
                    reset = True
                    diag_only = False
                elif op2 in NONDIAG:
                    diag_only = False
                    if len(nondiag) < 5:
                        nondiag.append(f"{j}:{l2}")
                elif op2 in DIAG:
                    pass
                else:
                    diag_only = False
                    if len(nondiag) < 5:
                        nondiag.append(f"{j}:{l2}(?)")
            ga, gb = zlist[a]["guard"], zlist[b]["guard"]
            same_guard = (ga["depth"] == 0 and gb["depth"] == 0
                          and ga["inline"] is None and gb["inline"] is None)
            mergeable = (not reset) and diag_only and same_guard
            pairs.append({"qubit": q, "pair": [a, b], "idx_pair": [ia, ib],
                          "span": ib - ia, "reset_between": reset,
                          "nondiag_touch_sample": nondiag,
                          "same_uncond_guard": same_guard,
                          "mergeable": mergeable,
                          "angle_sum_half_turns": str(Fraction(zlist[a]["angle_str"]) + Fraction(zlist[b]["angle_str"]))})
    n_mergeable = sum(1 for p in pairs if p["mergeable"])

    # ---- 3. full-domain zero-branch masks at each Z_POW ----
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    qv = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> np.uint64(bit)) & np.uint64(1)).astype(np.uint64)
        qv[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = LAST_MASK

    want = {z["idx"]: n for n, z in enumerate(zlist)}
    masks: list[np.ndarray | None] = [None] * len(zlist)
    depth = 0
    for idx, line in enumerate(ops):
        if line.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if line.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or " if " in line:
            continue
        p = line.split()
        op = p[0]
        if op == "HMR" or op == "R":
            qv[int(p[1][1:])].fill(0)
        elif op == "X":
            qv[int(p[1][1:])] ^= ones
        elif op == "CX":
            qv[int(p[1][1:])] ^= qv[int(p[2][1:])]
        elif op == "SWAP":
            a_, b_ = int(p[1][1:]), int(p[2][1:])
            qv[a_], qv[b_] = qv[b_], qv[a_]
        elif op == "CCX":
            a_, b_, t_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            qv[t_] ^= qv[a_] & qv[b_]
        elif op == "CSWAP":
            c_, a_, b_ = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = qv[c_] & (qv[a_] ^ qv[b_])
            qv[a_] ^= prod
            qv[b_] ^= prod
        if idx in want:
            m = qv[int(zlist[want[idx]]["qubit"][1:])].copy()
            m[-1] &= LAST_MASK
            masks[want[idx]] = m
    assert all(m is not None for m in masks)

    rots = [n for n, z in enumerate(zlist) if z["class"] == "rotation"]
    assert len(rots) == 41, len(rots)
    # pairwise equality among rotation masks
    groups: list[list[int]] = []
    seen = set()
    for i_pos, i in enumerate(rots):
        if i in seen:
            continue
        grp = [i]
        for j in rots[i_pos + 1:]:
            if np.array_equal(masks[i], masks[j]):
                grp.append(j)
                seen.add(j)
        if len(grp) > 1:
            groups.append(grp)
        seen.add(i)
    # support sizes + pairwise XOR popcounts vs nearest neighbour (sample, cheap)
    import math
    pops = {str(n): int(np.sum(np.bitwise_count(masks[n]))) for n in rots}
    # nearest-neighbour distance for each rotation (min over j != i of popcount(mask_i XOR mask_j))
    nn: dict[str, int] = {}
    for i in rots:
        best = N_INPUTS + 1
        for j in rots:
            if j == i:
                continue
            d = int(np.sum(np.bitwise_count(masks[i] ^ masks[j])))
            if d < best:
                best = d
                if best == 0:
                    break
        nn[str(i)] = best

    # angle distribution (by decade of |angle| in turns)
    from collections import Counter
    decades = Counter()
    for n in rots:
        t = abs(Fraction(zlist[n]["angle_str"]) / 2)
        dec = math.floor(math.log10(float(t))) if t > 0 else -999
        decades[dec] += 1

    # T-gate + Clifford detail
    others = [{"n": n, **{k: zlist[n][k] for k in ("idx", "qubit", "angle_str", "class", "unconditional")}} for n, z in enumerate(zlist) if z["class"] != "rotation"]

    result = {
        "kmb": str(KMB),
        "counts": {"Z_POW_total": len(zlist),
                   "rotation": len(rots), "t": sum(1 for z in zlist if z["class"] == "t"),
                   "clifford": sum(1 for z in zlist if z["class"] == "clifford")},
        "hierarchy_counts": hier,
        "num_t_like": int(s.num_t_like),
        "all_zpow_unconditional": all(z["unconditional"] for z in zlist),
        "per_qubit_counts": {q: len(v) for q, v in sorted(by_qubit.items())},
        "same_wire_pairs": pairs,
        "n_mergeable_same_wire_pairs": n_mergeable,
        "rotation_duplicate_mask_groups": groups,
        "rotation_support_popcount": pops,
        "rotation_nearest_neighbour_xor_pop": nn,
        "rotation_angle_decades_turns": {str(k): v for k, v in sorted(decades.items())},
        "non_rotation_gates": others,
        "rotations": [{"n": n, "idx": zlist[n]["idx"], "qubit": zlist[n]["qubit"],
                       "angle_str": zlist[n]["angle_str"],
                       "support": pops[str(n)], "nn_xor": nn[str(n)]} for n in rots],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    np.savez_compressed(OUT_NPZ, **{f"rot_{n}": masks[n] for n in rots})
    print(json.dumps({k: result[k] for k in ("counts", "all_zpow_unconditional",
                                            "per_qubit_counts", "n_mergeable_same_wire_pairs",
                                            "rotation_duplicate_mask_groups",
                                            "rotation_angle_decades_turns")}, indent=2))
    print("wrote", OUT_JSON, "and", OUT_NPZ)


if __name__ == "__main__":
    main()
