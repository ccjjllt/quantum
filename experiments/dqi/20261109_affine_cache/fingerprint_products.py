"""Pass 1: bit-parallel classical simulation of frontier dqi.kmb.

Tracks computational-basis values (qubits + classical bits, batch of NB shots
in Python ints) with a condition stack, records for every unconditional
CCX/CCZ in {unsynthesis, unextract}:
  (line_idx, stage, op, a, b, t, fp_a, fp_b)
plus unconditional HMR/R zeroing events and ancilla (q840..891) occurrences.
Self-check: S qubits restored and ancillas zero at circuit end.

Read-only w.r.t. the repo; writes pkl + summary JSON to artifacts dir.
"""
from __future__ import annotations

import array
import io
import json
import os
import pickle
import random
import tempfile
from pathlib import Path

import kickmix as km

NB = 384
FORCE0 = sum(1 << s for s in range(128, 192))   # HMR outcomes forced 0
FORCE1 = sum(1 << s for s in range(192, 256))   # HMR outcomes forced 1
ALL1 = (1 << NB) - 1
ANC_MIN, ANC_MAX = 840, 891
TARGET_STAGES = ("unsynthesis", "unextract")

SRC = Path("artifacts/20261108_public_frontier/release/dqi.kmb")
OUT_DIR = Path("artifacts/20261109_affine_cache")
TMP_KMX = Path(tempfile.gettempdir()) / "affine_cache_frontier.kmx"


def dump_kmx() -> None:
    if TMP_KMX.exists() and TMP_KMX.stat().st_size > 10**6:
        print(f"reuse cached kmx {TMP_KMX} ({TMP_KMX.stat().st_size/1e9:.2f} GB)")
        return
    print("loading kmb + dumping kmx (one-time, slow)...")
    c = km.Circuit.from_file(str(SRC))
    with open(TMP_KMX, "w") as f:
        c.to_file(f, format="kmx")
    print(f"wrote {TMP_KMX} ({TMP_KMX.stat().st_size/1e9:.2f} GB)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dump_kmx()

    rng = random.Random(0xD91)
    # Valid-syndrome init: S must be a true Reed-Solomon syndrome tuple of some
    # error pattern (uniform-random S breaks algebraic invariants and the
    # circuit legitimately leaves residue). Mirror the official sampler.
    field = km.GF2Field(12)
    prim = field.primitive_element
    order = (1 << 12) - 1
    antilog = [field.pow(prim, k) for k in range(order)]
    log = [0] * (1 << 12)
    for k, v in enumerate(antilog):
        log[v] = k
    qv = {}
    k_of_shot = []
    for s in range(NB):
        k = rng.randint(0, 35)
        k_of_shot.append(k)
        pos = rng.sample(range(4095), k) if k else []
        vals = [rng.randint(1, 4095) for _ in range(k)]
        syn = [0] * 70
        for p, v in zip(pos, vals):
            lv = log[v]
            for i in range(70):
                syn[i] ^= antilog[(lv + (i + 1) * p) % order]
        for i in range(70):
            for bit in range(12):
                if (syn[i] >> bit) & 1:
                    q = 12 * i + bit
                    qv[q] = qv.get(q, 0) | (1 << s)
    for q in range(892):
        qv.setdefault(q, 0)
    qv_init = dict(qv)
    bv: dict[int, int] = {}
    for b in range(49140):  # E registers: random MBUC inputs
        bv[b] = rng.getrandbits(NB)

    def bitval(b: int) -> int:
        return bv.get(b, 0)

    cond_stack: list[int] = []
    stack_and = ALL1

    def eff_of(inline: int | None) -> int:
        m = stack_and
        if inline is not None:
            m &= bitval(inline)
        return m

    sites: list[tuple] = []
    zero_events: list[tuple[int, int]] = []  # (line_idx, q)
    occ: dict[int, array.array] = {q: array.array("I") for q in range(ANC_MIN, ANC_MAX + 1)}

    stage = "header"
    stack: list[str] = []
    n_ops = 0
    unknown: dict[str, int] = {}

    def note_anc(idx: int, *qs: int) -> None:
        seen = set()
        for q in qs:
            if ANC_MIN <= q <= ANC_MAX and q not in seen:
                seen.add(q)
                occ[q].append(idx)

    with open(TMP_KMX) as f:
        for idx, raw in enumerate(f):
            l = raw.strip()
            if not l:
                continue
            if l.startswith("INFO_TAG"):
                tag = l.split('"', 2)[1]
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                    stage = stack[0]
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    stage = stack[0] if stack else "header"
                continue
            if l[0] in "ARS":
                if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
                    continue
            c0 = l[0]
            if c0 == "C" and (l.startswith("CZ ") or l.startswith("CCZ ")):
                pass  # phase-only for values; CCZ handled below
            parts = l.split()
            op = parts[0]
            inline = None
            if len(parts) >= 3 and parts[-2] == "if":
                inline = int(parts[-1][1:])
                args = parts[1:-2]
            else:
                args = parts[1:]

            if op == "CX":
                a, b = int(args[0][1:]), int(args[1][1:])
                m = eff_of(inline)
                if m:
                    qv[b] ^= qv.get(a, 0) & m
                if stage in TARGET_STAGES:
                    note_anc(idx, a, b)
            elif op == "X":
                a = int(args[0][1:])
                m = eff_of(inline)
                if m:
                    qv[a] ^= m
                if stage in TARGET_STAGES:
                    note_anc(idx, a)
            elif op == "SWAP":
                a, b = int(args[0][1:]), int(args[1][1:])
                m = eff_of(inline)
                if m:
                    d = (qv.get(a, 0) ^ qv.get(b, 0)) & m
                    qv[a] ^= d
                    qv[b] ^= d
                if stage in TARGET_STAGES:
                    note_anc(idx, a, b)
            elif op == "CCX":
                a, b, t = int(args[0][1:]), int(args[1][1:]), int(args[2][1:])
                m = eff_of(inline)
                fa, fb = qv.get(a, 0), qv.get(b, 0)
                if stage in TARGET_STAGES:
                    note_anc(idx, a, b, t)
                    if m == ALL1:
                        sites.append((idx, stage, "CCX", a, b, t, fa, fb))
                if m:
                    qv[t] ^= fa & fb & m
            elif op == "CCZ":
                a, b, t = int(args[0][1:]), int(args[1][1:]), int(args[2][1:])
                if stage in TARGET_STAGES:
                    note_anc(idx, a, b, t)
                    if eff_of(inline) == ALL1:
                        sites.append((idx, stage, "CCZ", a, b, t,
                                      qv.get(a, 0), qv.get(b, 0)))
            elif op == "CSWAP":
                c_, a, b = int(args[0][1:]), int(args[1][1:]), int(args[2][1:])
                m = eff_of(inline) & qv.get(c_, 0)
                if m:
                    d = (qv.get(a, 0) ^ qv.get(b, 0)) & m
                    qv[a] ^= d
                    qv[b] ^= d
                if stage in TARGET_STAGES:
                    note_anc(idx, c_, a, b)
            elif op == "HMR":
                a, b = int(args[0][1:]), int(args[1][1:])
                m = eff_of(inline)
                if m:
                    r = rng.getrandbits(NB)
                    forced = (r & ~FORCE0) | FORCE1
                    bv[b] = (bitval(b) & ~m) | (forced & m)
                    qv[a] &= ~m
                if stage in TARGET_STAGES:
                    note_anc(idx, a)
                    if m == ALL1:
                        zero_events.append((idx, a))
            elif op == "R":
                a = int(args[0][1:])
                m = eff_of(inline)
                if m:
                    qv[a] &= ~m
                if stage in TARGET_STAGES:
                    note_anc(idx, a)
                    if m == ALL1:
                        zero_events.append((idx, a))
            elif op == "BIT_STORE0":
                b = int(args[0][1:])
                m = eff_of(inline)
                bv[b] = bitval(b) & ~m
            elif op == "BIT_STORE1":
                b = int(args[0][1:])
                m = eff_of(inline)
                bv[b] = bitval(b) | m
            elif op == "BIT_INVERT":
                b = int(args[0][1:])
                m = eff_of(inline)
                bv[b] = bitval(b) ^ m
            elif op == "PUSH_CONDITION":
                cond_stack.append(bitval(inline) if inline is not None else ALL1)
                stack_and &= cond_stack[-1]
            elif op == "POP_CONDITION":
                cond_stack.pop()
                stack_and = ALL1
                for v in cond_stack:
                    stack_and &= v
            elif op in ("CZ", "Z", "NEG",
                        "INFO_TAG", "APPEND_TO_REGISTER", "REGISTER"):
                pass
            elif op == "CCX_CARRY":
                # carry variant: same computational effect on target + carry
                a, b, t = int(args[0][1:]), int(args[1][1:]), int(args[2][1:])
                m = eff_of(inline)
                fa, fb = qv.get(a, 0), qv.get(b, 0)
                if stage in TARGET_STAGES:
                    note_anc(idx, a, b, t)
                    if m == ALL1:
                        sites.append((idx, stage, "CCX", a, b, t, fa, fb))
                if m:
                    qv[t] ^= fa & fb & m
            else:
                unknown[op] = unknown.get(op, 0) + 1
            n_ops += 1
            if (idx + 1) % 10_000_000 == 0:
                print(f"... {idx+1} lines, sites={len(sites)}")

    # Self-check: shots 0..127 use fully random HMR outcomes; 128..383 force
    # all-0 / all-1 HMR outcomes (possibly unrealizable). Report separately.
    lo_mask = (1 << 128) - 1
    s_lo = sum(1 for q in range(840) if ((qv.get(q, 0) ^ qv_init[q]) & lo_mask) != 0)
    s_hi = sum(1 for q in range(840) if ((qv.get(q, 0) ^ qv_init[q]) & (ALL1 ^ lo_mask)) != 0)
    print(f"self-check S mismatch shots[0:128]={s_lo}/840 shots[128:384]={s_hi}/840")
    # per-shot S residue popcounts + error weight (diagnose rare-fail vs bug)
    import collections as _co
    pershot = _co.Counter()
    badshots = []
    for s in range(NB):
        r = sum((((qv.get(q, 0) ^ qv_init[q]) >> s) & 1) for q in range(840))
        if r:
            pershot[r] += 1
            badshots.append((s, k_of_shot[s], r))
    print(f"shots with S residue: {len(badshots)}/{NB}; residue-size histogram: {sorted(pershot.items())[:10]}")
    print("bad shots (shot,k,residue):", badshots[:20])
    s_bad = sum(1 for q in range(840) if qv.get(q, 0) != qv_init[q])
    a_bad = [q for q in range(840, 892) if qv.get(q, 0) != 0]
    print(f"self-check: S qubits mismatch(all)={s_bad}/840; nonzero ancillas={len(a_bad)} {a_bad[:10]}")
    a_lo = sum(1 for q in range(840, 892) if (qv.get(q, 0) & lo_mask) != 0)
    print(f"self-check ancilla-nonzero shots[0:128]={a_lo}/52")
    print(f"unknown ops: {unknown}")
    print(f"sites in target stages: {len(sites)}; zero events: {len(zero_events)}")

    with open(OUT_DIR / "sim_out.pkl", "wb") as f:
        pickle.dump({"sites": sites, "zero_events": zero_events, "occ": occ,
                     "s_bad": s_bad, "a_bad": a_bad, "unknown": unknown,
                     "s_lo": s_lo, "a_lo": a_lo}, f)
    print("saved sim_out.pkl")


if __name__ == "__main__":
    main()
