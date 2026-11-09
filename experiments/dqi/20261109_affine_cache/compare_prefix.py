"""Decisive core-logic check: simulate the HMR-free prefix
(lines 0..end of 'initial' stage) with both my classical loop and km.Simulator
on identical inputs; compare every qubit and bit."""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "data/competition/verifiers")
from dqi.verify_submission_dqi import (  # noqa: E402
    FieldTables,
    ProblemSpecDQI,
    optimal_dqi_weights,
    sample_shots,
    to_bits,
)

import kickmix as km  # noqa: E402

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"
NB = 4


def load_prefix():
    lines = open(KMX).readlines()
    end = next(i for i, l in enumerate(lines) if "@exit:initial" in l)
    return lines[: end + 1]


def main() -> None:
    spec = ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=NB)
    tables = FieldTables(km.GF2Field(12))
    wp = optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    rng = np.random.default_rng(7)
    syndromes, mbuc, _ = sample_shots(spec, tables, rng, NB, wp)
    s_bits = to_bits(syndromes, 12)   # (840, NB)
    e_bits = to_bits(mbuc, 12)        # (49140, NB)

    # --- real sim on prefix ---
    pre = load_prefix()
    print(f"prefix lines: {len(pre)}", flush=True)
    c = km.Circuit("".join(pre))
    sim = km.Simulator(batch_size=NB, debug_print=False, seed=99)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(840)]), s_bits)
    sim.write_across_shots(km.array([km.b(i) for i in range(49140)]), e_bits)
    sim.do(c)
    real_q = {q: sum(bool(v) << s for s, v in enumerate(sim.read_across_shots(km.q(q)))) for q in range(892)}
    maxbit = c.num_bits
    real_b = {b: sum(bool(v) << s for s, v in enumerate(sim.read_across_shots(km.b(b)))) for b in range(maxbit)}

    # --- my loop on prefix ---
    qv = {q: sum(int(s_bits[q, s]) << s for s in range(NB)) for q in range(840)}
    qv.update({q: 0 for q in range(840, 892)})
    bv = {b: sum(int(e_bits[b, s]) << s for s in range(NB)) for b in range(49140)}

    def bitval(b):
        return bv.get(b, 0)

    stack = []
    sand = (1 << NB) - 1
    for raw in pre:
        l = raw.strip()
        if not l or l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
            continue
        if l.startswith("INFO_TAG"):
            continue
        parts = l.split()
        op = parts[0]
        if len(parts) >= 3 and parts[-2] == "if":
            inline = int(parts[-1][1:])
            args = parts[1:-2]
        else:
            inline, args = None, parts[1:]
        m = sand if inline is None else sand & bitval(inline)
        if op == "CX":
            a, b = int(args[0][1:]), int(args[1][1:])
            if m:
                qv[b] ^= qv.get(a, 0) & m
        elif op == "X":
            if m:
                qv[int(args[0][1:])] ^= m
        elif op == "SWAP":
            a, b = int(args[0][1:]), int(args[1][1:])
            if m:
                d = (qv.get(a, 0) ^ qv.get(b, 0)) & m
                qv[a] ^= d
                qv[b] ^= d
        elif op == "BIT_STORE0":
            b = int(args[0][1:])
            bv[b] = bitval(b) & ~m
        elif op == "BIT_STORE1":
            b = int(args[0][1:])
            bv[b] = bitval(b) | m
        elif op == "BIT_INVERT":
            b = int(args[0][1:])
            bv[b] = bitval(b) ^ m
        elif op == "PUSH_CONDITION":
            stack.append(bitval(inline))
            sand &= stack[-1]
        elif op == "POP_CONDITION":
            stack.pop()
            sand = (1 << NB) - 1
            for v in stack:
                sand &= v
        elif op in ("CZ", "Z", "NEG", "HMR", "R", "CCX", "CCZ", "CSWAP"):
            pass
        else:
            raise RuntimeError(f"unexpected {l[:60]}")

    qbad = [(q, real_q[q], qv.get(q, 0)) for q in range(892) if real_q[q] != qv.get(q, 0)]
    bbad = [(b, real_b.get(b, 0), bv.get(b, 0)) for b in range(maxbit) if real_b.get(b, 0) != bv.get(b, 0)]
    print(f"qubit mismatches: {len(qbad)}/892; bit mismatches: {len(bbad)}/{maxbit}")
    for e in qbad[:5]:
        print("Q", e)
    for e in bbad[:5]:
        print("B", e)


if __name__ == "__main__":
    main()
