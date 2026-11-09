"""CZ/CCZ/Z pairing audit on frontier 7c10edba (static, no semantics changed).

1. Census: CZ by guard kind; second-selector window [27486,27976): CZ count,
   CCZ count (expect 0 per Step-1 lineage).
2. Pair-cancellation scan for CZ / CCZ / Z: group by (sorted operands, guard
   key=(push tuple, inline bit)); consecutive pairs cancellable iff every
   intervening op touching involved qubits is diagonal (Z/CZ/CCZ/Z_POW, any
   guard -- diagonal gates commute) AND no classical flip (NEG/BIT_INVERT/
   BIT_STORE*) targets the guard bits in between.
   Savings: CZ/Z pairs are free gates (ops only, dScore=0); CCZ pair = 2
   executed Toffolis (real money, if executed every shot).
3. CCZ degeneracy screen: zero-branch support of each CCZ's 3 qubits at its
   position (const-0 control => never fires).
Writes cz_audit.json.
"""
from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path

import kickmix as km
import numpy as np

KMB = "artifacts/20261108_public_frontier/release/invsqrt.kmb"
OUT = "experiments/invsqrt/20261109_tphase_fusion/cz_audit.json"
N_INPUTS = 3_133_452
N_WORDS = (N_INPUTS + 63) // 64
LAST_MASK = np.uint64((1 << (N_INPUTS % 64)) - 1) if N_INPUTS % 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
SEL = (27486, 27976)
DIAG = {"Z", "CZ", "CCZ", "Z_POW"}
NONDIAG_Q = {"X", "CX", "CCX", "SWAP", "CSWAP", "HMR", "R"}


def load_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines()
           if l and not l.startswith(("APPEND", "REGISTER"))]
    return ops


def parse_guard(line, depth, stack):
    inline = line.split(" if ", 1)[1].strip() if " if " in line else None
    return (tuple(stack), inline)


def qubits_of(op, parts):
    if op in ("X", "Z", "Z_POW", "HMR", "R"):
        return [parts[1]]
    if op in ("CX", "CZ", "SWAP"):
        return [parts[1], parts[2]]
    if op in ("CCX", "CCZ", "CSWAP"):
        return [parts[1], parts[2], parts[3]]
    return []


def main():
    ops = load_ops()
    # annotate depth/guard per line
    depth = 0
    stack: list[str] = []
    info = []  # (op, qubits, guardkey, conditional)
    for line in ops:
        if line.startswith("PUSH_CONDITION"):
            stack.append(line.split("CONDITION", 1)[1].strip())
            depth += 1
            info.append(("PUSH", [], None, True))
            continue
        if line.startswith("POP_CONDITION"):
            depth -= 1
            stack.pop()
            info.append(("POP", [], None, True))
            continue
        p = line.split()
        op = p[0]
        g = parse_guard(line, depth, stack)
        cond = depth > 0 or " if " in line
        info.append((op, qubits_of(op, p), g, cond))

    cz = [(i, info[i]) for i, l in enumerate(ops) if l.split()[0] == "CZ"]
    cz_uncond = sum(1 for _, (_, _, _, c) in cz if not c)
    cz_inline = sum(1 for _, (_, _, g, c) in cz if c and g[0] == () and g[1])
    cz_push = sum(1 for _, (_, _, g, c) in cz if c and g[0] != ())
    sel_cz = sum(1 for i, _ in cz if SEL[0] <= i < SEL[1])
    sel_ccz = sum(1 for i, l in enumerate(ops)
                  if l.split()[0] == "CCZ" and SEL[0] <= i < SEL[1])

    # versioned guard keys: classical bit generations bumped on every write
    # (HMR/BIT_STORE*) or flip (NEG/BIT_INVERT). Same static name + same
    # generation => same coin value; a rewrite between pair members splits groups.
    gen: dict[str, int] = {}
    verkey = [None] * len(ops)
    vgdepth = 0
    vgstack: list[str] = []
    for i, line in enumerate(ops):
        if line.startswith("PUSH_CONDITION"):
            bit = line.split("CONDITION", 1)[1].strip().split()[-1]
            vgstack.append(f"{bit}@{gen.get(bit, 0)}")
            vgdepth += 1
            continue
        if line.startswith("POP_CONDITION"):
            vgdepth -= 1
            vgstack.pop()
            continue
        p = line.split()
        op = p[0]
        if op == "HMR" and len(p) > 2:
            gen[p[2]] = gen.get(p[2], 0) + 1
        elif op in ("BIT_STORE0", "BIT_STORE1"):
            gen[p[1]] = gen.get(p[1], 0) + 1
        elif op in ("NEG", "BIT_INVERT"):
            if len(p) < 2:
                continue  # bare NEG: no attributable bit target
            tgt = p[-1] if "if" in line else p[1]
            if tgt == "if":
                tgt = p[2]
            gen[tgt] = gen.get(tgt, 0) + 1
        inl = line.split(" if ", 1)[1].strip() if " if " in line else None
        inl_v = f"{inl}@{gen.get(inl, 0)}" if inl else None
        verkey[i] = (tuple(vgstack), inl_v)

    # top repeated CZ patterns
    pat = Counter()
    for _, (op, qs, g, c) in cz:
        pat[(tuple(sorted(qs)), g)] += 1

    # pair cancellation scan (versioned guard keys: same coin required)
    def scan(opname, arities):
        groups: dict = {}
        for i, l in enumerate(ops):
            if l.split()[0] != opname:
                continue
            _, qs, _, _ = info[i]
            groups.setdefault((tuple(sorted(qs)), verkey[i]), []).append(i)
        cancellable = []
        for key, idxs in groups.items():
            if len(idxs) < 2:
                continue
            (qs_sorted, vk) = key
            qset = set(qs_sorted)
            for a, b in zip(idxs, idxs[1:]):
                blocked = None
                for j in range(a + 1, b):
                    op2, qs2, _, _ = info[j]
                    if op2 in ("PUSH", "POP"):
                        continue
                    if qset & set(qs2):
                        if op2 not in DIAG:
                            blocked = f"{j}:{ops[j]}"
                            break
                if blocked is None:
                    cancellable.append({"operands": list(qs_sorted),
                                        "guard_versioned": [list(vk[0]), vk[1]],
                                        "pair": [a, b], "span": b - a})
        return {"n_groups": len(groups), "n_repeated_groups": sum(1 for v in groups.values() if len(v) > 1),
                "n_cancellable_pairs": len(cancellable), "pairs_sample": cancellable[:10]}

    cz_scan = scan("CZ", 2)
    z_scan = scan("Z", 1)
    ccz_scan = scan("CCZ", 3)

    # CCZ degeneracy screen (zero-branch supports at each CCZ)
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    qv = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bv = ((xs_pad >> np.uint64(bit)) & np.uint64(1)).astype(np.uint64)
        qv[bit] = np.bitwise_or.reduce(bv.reshape(-1, 64) << shifts, axis=1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = LAST_MASK
    ccz_idx = [i for i, l in enumerate(ops) if l.split()[0] == "CCZ"]
    ccz_want = set(ccz_idx)
    ccz_sup = {}
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
        if op in ("HMR", "R"):
            qv[int(p[1][1:])].fill(0)
        elif op == "X":
            qv[int(p[1][1:])] ^= ones
        elif op == "CX":
            qv[int(p[1][1:])] ^= qv[int(p[2][1:])]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            qv[a], qv[b] = qv[b], qv[a]
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            qv[t] ^= qv[a] & qv[b]
        elif op == "CSWAP":
            cc_, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            prod = qv[cc_] & (qv[a] ^ qv[b])
            qv[a] ^= prod
            qv[b] ^= prod
        if idx in ccz_want:
            qs = [int(t[1:]) for t in p[1:4]]
            sup = {f"q{q}": int(np.sum(np.bitwise_count((qv[q] & ones)))) for q in qs}
            ccz_sup[str(idx)] = {"qubits": [f"q{q}" for q in qs], "support": sup,
                                 "guard": [list(info[idx][2][0]), info[idx][2][1]]}
    degenerate = [k for k, v in ccz_sup.items() if 0 in v["support"].values()]

    result = {
        "cz_total": len(cz),
        "cz_unconditional": cz_uncond,
        "cz_inline_if": cz_inline,
        "cz_push_frame": cz_push,
        "second_selector_window": list(SEL),
        "second_selector_cz": sel_cz,
        "second_selector_ccz": sel_ccz,
        "top_cz_patterns": [[list(k[0]), [list(k[1][0]), k[1][1]], v]
                            for k, v in pat.most_common(8)],
        "cz_pair_scan": {k: v for k, v in cz_scan.items() if k != "pairs_sample"},
        "cz_cancellable_pairs": cz_scan["pairs_sample"],
        "z_pair_scan": {k: v for k, v in z_scan.items() if k != "pairs_sample"},
        "z_cancellable_pairs": z_scan["pairs_sample"],
        "ccz_pair_scan": {k: v for k, v in ccz_scan.items() if k != "pairs_sample"},
        "ccz_cancellable_pairs": ccz_scan["pairs_sample"],
        "ccz_total": len(ccz_idx),
        "ccz_degenerate_zero_branch": degenerate,
        "score_note": "CZ/Z cancellations are free-gate op-count only (dScore=0). "
                      "CCZ pair cancellation would save 2 executed Toffolis.",
    }
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2)[:3000])


if __name__ == "__main__":
    main()
