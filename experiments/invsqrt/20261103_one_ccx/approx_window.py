"""Manual one-CCX research: actual-prefix bit-packed discovery, no verifier.

Pinned bce baseline. Discovery identities are hypotheses until separately proved.
No file mutation on import; `--scan` writes only this experiment's JSON evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_baseline_patch"))
import patch62 as P

ART = ROOT / "artifacts/20261103_one_ccx"


def linear_representation(values, target, exclude, active):
    """Exact GF(2) span solve on the sampled columns; returns wire mask or None."""
    basis = {}
    for q, val in enumerate(list(values) + [active]):
        if q == exclude:
            continue
        val &= active
        mask = 1 << q
        while val:
            pivot = val.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (val, mask)
                break
            v, m = basis[pivot]
            val ^= v; mask ^= m
    val = target & active
    mask = 0
    while val:
        pivot = val.bit_length() - 1
        if pivot not in basis:
            return None
        v, m = basis[pivot]
        val ^= v; mask ^= m
    return [q if q < 62 else -1 for q in range(63) if mask >> q & 1]


def packed_inputs(n, seed):
    rng = random.Random(seed)
    xs = list(range(1, min(n + 1, 128)))
    xs += [161, 888, 3133452, 2097151, 2097152]
    xs += [rng.randrange(1, 3133453) for _ in range(max(0, n - len(xs)))]
    xs = xs[:n]
    return xs, [sum(((x >> q) & 1) << j for j, x in enumerate(xs))
                for q in range(22)] + [0] * 40


def vector_rank(vectors):
    basis = {}
    for v in vectors:
        while v:
            k = v.bit_length() - 1
            if k not in basis:
                basis[k] = v
                break
            v ^= basis[k]
    return len(basis)


def scan(n=4096, seed=20261103, lo=32283, hi=43927, zero_events=False):
    header, ops = P.load_baseline()
    xs, wire = packed_inputs(n, seed)
    allbits = (1 << len(xs)) - 1
    rng = random.Random(seed ^ 0x6D5A)
    bits, stack = {}, []
    hits = []
    checkpoints = {}
    entries, lower_bounds = {}, {}
    for index, line in enumerate(ops[:hi]):
        if index in (35485, 35557):
            entries[index] = [allbits] + list(wire)
        if index in (35543, 35609, 35544, 35610):
            start = 35485 if index in (35543, 35544) else 35557
            old = entries[start]
            lower_bounds[str(start) + ("_after_HMR" if index in (35544, 35610) else "")] = {
                "stop_before_HMR": index,
                "input_affine_rank": vector_rank(old),
                "input_output_rank": vector_rank(old + wire),
                "new_independent_functions": vector_rank(old + wire) - vector_rank(old),
                "claim": "CCX lower bound only for X/CX/SWAP/CCX implementation of all pre-HMR outputs, same fixed classical branch; not a bound allowing changed measurement or phase correction",
            }
        p = line.split(); k = p[0]
        active = allbits
        for c in stack:
            active &= c
        if "if" in p:
            active &= bits.get(int(p[p.index("if") + 1][1:]), 0)
        def q(j):
            return int(p[j][1:])
        if k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0)); continue
        if k == "POP_CONDITION":
            stack.pop(); continue
        if k in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            b = int(p[1][1:]); old = bits.get(b, 0)
            new = 0 if k == "BIT_STORE0" else allbits if k == "BIT_STORE1" else old ^ allbits
            bits[b] = old ^ ((old ^ new) & active)
        elif k == "CX":
            wire[q(2)] ^= wire[q(1)] & active
        elif k == "CCX":
            a, b, t = q(1), q(2), q(3)
            prod = wire[a] & wire[b]
            if lo <= index < hi:
                reps = []
                if (prod & active) == 0:
                    reps.append([])
                for u in range(62):
                    if u != t and ((prod ^ wire[u]) & active) == 0:
                        reps.append([u])
                lookup = {}
                for u in range(62):
                    if u == t:
                        continue
                    masked = wire[u] & active
                    for v in lookup.get((prod & active) ^ masked, []):
                        reps.append([v, u])
                    lookup.setdefault(masked, []).append(u)
                rep = linear_representation(wire, prod, t, active)
                if rep is not None and rep not in reps:
                    reps.append(rep)
                if reps:
                    hits.append({"op": index, "line": line, "active_samples": active.bit_count(),
                                 "representations": reps, "stack_depth": len(stack)})
            wire[t] ^= prod & active
        elif k == "X":
            wire[q(1)] ^= active
        elif k in ("SWAP", "CSWAP"):
            a, b = (q(1), q(2)) if k == "SWAP" else (q(2), q(3))
            cond = active if k == "SWAP" else active & wire[q(1)]
            d = (wire[a] ^ wire[b]) & cond
            wire[a] ^= d; wire[b] ^= d
        elif k in ("R", "HMR"):
            outcome = 0 if zero_events else rng.getrandbits(len(xs))
            if len(p) > 2 and p[2].startswith("b"):
                b = int(p[2][1:]); old = bits.get(b, 0)
                bits[b] = old ^ ((old ^ outcome) & active)
            wire[q(1)] &= allbits ^ active
        elif k not in ("Z", "CZ", "CCZ", "NEG", "Z_POW", "INFO_TAG"):
            raise ValueError((index, line))
        if index in (35489, 35508, 35537, 35560, 35577, 35604):
            checkpoints[str(index)] = {
                "constant_zero": [q for q in range(62) if wire[q] == 0],
                "constant_one": [q for q in range(62) if wire[q] == allbits],
            }
    return {"baseline_sha256": P.BASELINE_SHA, "seed": seed, "n": len(xs),
            "lo": lo, "hi": hi, "hits": hits, "checkpoints": checkpoints,
            "zero_events": zero_events, "window_rank_witnesses": lower_bounds,
            "scope": "actual legal x prefix; independent sampled measurement outcomes; discovery only"}


def anf_mul(a, b):
    out = set()
    for x in a:
        for y in b:
            z = x | y
            if z in out:
                out.remove(z)
            else:
                out.add(z)
    return out


def anf_run(ops, initial=None):
    wire = [set(p) for p in initial] if initial is not None else [{1 << q} for q in range(62)]
    for line in ops:
        p = line.split(); qs = [int(t[1:]) for t in p[1:]]
        if p[0] == "CCX":
            a, b, t = qs; wire[t] ^= anf_mul(wire[a], wire[b])
        elif p[0] == "CX":
            a, b = qs; wire[b] ^= wire[a]
        elif p[0] == "X":
            wire[qs[0]] ^= {0}
        elif p[0] == "SWAP":
            a, b = qs; wire[a], wire[b] = wire[b], wire[a]
        else:
            raise ValueError(line)
    return wire


def nonlinear_rank(ops):
    """Exact free-entry Boolean ANF, including all output wires, no prefix assumptions."""
    wire = anf_run(ops)
    nonlinear = [{m for m in poly if m.bit_count() >= 2} for poly in wire]
    basis = {}
    for poly in nonlinear:
        poly = set(poly)
        while poly:
            pivot = max(poly)
            if pivot not in basis:
                basis[pivot] = poly
                break
            poly ^= basis[pivot]
    quadratic_rank = None
    if len(basis) == 1:
        poly = next(iter(basis.values()))
        if all(m.bit_count() == 2 for m in poly):
            rows = [0] * 62
            for m in poly:
                low = m & -m; high = m ^ low
                i, j = low.bit_length() - 1, high.bit_length() - 1
                rows[i] ^= high; rows[j] ^= low
            rb = {}
            for row in rows:
                while row:
                    k = row.bit_length() - 1
                    if k not in rb:
                        rb[k] = row; break
                    row ^= rb[k]
            quadratic_rank = len(rb)
    return len(basis), quadratic_rank


def rank_scan(lo=0, hi=47258):
    _, ops = P.load_baseline()
    runs, start = [], lo
    for i in range(lo, hi):
        p = ops[i].split()
        if p[0] not in ("CCX", "CX", "X", "SWAP") or "if" in p:
            if start < i:
                runs.append((start, i))
            start = i + 1
    if start < hi:
        runs.append((start, hi))
    found, count = [], 0
    for a, b in runs:
        gates = [i for i in range(a, b) if ops[i].startswith("CCX ")]
        for n in (2, 3, 4):
            for j in range(len(gates) - n + 1):
                x, y = gates[j], gates[j + n - 1] + 1
                rank, qr = nonlinear_rank(ops[x:y]); count += 1
                if rank == 0 or (qr is not None and qr // 2 < n):
                    found.append({"lo": x, "hi": y, "ccx": n, "nonlinear_rank": rank,
                                  "quadratic_rank": qr, "ops": ops[x:y]})
    return {"checked": count, "hits": found,
            "scope": "exact free-entry ANF nonlinear dimension; lower bound only, no physical synthesis yet"}


def prefix_frame(state, target):
    """Exact XOR relations at the true prefix; AND atoms stay independent.

    Independent variables are actual entry qubit values, not arbitrary vid IDs.
    Constants remain constants. Target is last, so controls never need it.
    """
    basis, physical, frame = {}, [], [None] * 62
    for q in [q for q in range(62) if q != target] + [target]:
        fs = set(state.values.fs[state.wire[q]])
        constant = -1 in fs
        fs.discard(-1)
        expr = 0
        while fs:
            atom = max(fs)
            if atom not in basis:
                bit = 1 << len(physical)
                physical.append(q)
                # New formal variable denotes actual wire[q], including its constant.
                basis[atom] = (set(fs), expr ^ bit, constant)
                expr = bit
                constant = False
                break
            other, mask, const = basis[atom]
            fs ^= other; expr ^= mask; constant ^= const
        frame[q] = {1 << k for k in range(len(physical)) if expr >> k & 1}
        if constant:
            frame[q].add(0)
    return frame, physical


def factor_quadratic(poly):
    """Exact Boolean quadratic factorization; returns products and affine residual."""
    residual = set(poly)
    products = []
    while True:
        quadratic = [m for m in residual if m.bit_count() == 2]
        if any(m.bit_count() > 2 for m in residual):
            return None
        if not quadratic:
            return products, residual
        edge = min(quadratic)
        bi = edge & -edge; bj = edge ^ bi
        l1 = {m ^ bi for m in quadratic if m & bi}
        l2 = {m ^ bj for m in quadratic if m & bj}
        products.append((bi.bit_length() - 1, bj.bit_length() - 1, l1, l2))
        residual ^= anf_mul(l1, l2)


def prefix_quadratic_scan(lo=0, hi=47258):
    sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261103_baseline_patch_round2"))
    import patch62r2 as R2
    header, ops = P.load_baseline()
    state = R2.Sym2()
    checked, hits = 0, []
    covered = -1
    for index, line in enumerate(ops[:hi]):
        p = line.split()
        if lo <= index and index > covered and p[0] == "CCX" and "if" not in p:
            target = int(p[3][1:]); end = index; n = 0
            for j in range(index, hi):
                w = ops[j].split(); k = w[0]
                if "if" in w or k not in ("CCX", "CX", "X", "SWAP"):
                    break
                qs = [int(t[1:]) for t in w[1:]]
                if (k == "CCX" and (qs[2] != target or target in qs[:2])) or \
                   (k == "CX" and qs[0] == target) or (k == "SWAP" and target in qs):
                    break
                if k == "CCX":
                    n += 1; end = j + 1
            if n >= 2:
                checked += 1
                frame, physical = prefix_frame(state, target)
                original = ops[index:end]
                linear = [l for l in original if not l.startswith("CCX ")]
                want = anf_run(original, frame)
                free = anf_run(linear, frame)
                poly = want[target] ^ free[target]
                factored = factor_quadratic(poly)
                if factored is not None and len(factored[0]) < n:
                    products, affine = factored
                    synth = []
                    for i, j, l1, l2 in products:
                        qi, qj = physical[i], physical[j]
                        assert target not in (qi, qj)
                        before = []
                        for bit in sorted(l1 - {1 << j}):
                            before.append(f"CX q{physical[bit.bit_length()-1]} q{qj}")
                        for bit in sorted(l2 - {1 << i}):
                            before.append(f"CX q{physical[bit.bit_length()-1]} q{qi}")
                        synth += before + [f"CCX q{qi} q{qj} q{target}"] + list(reversed(before))
                    for bit in sorted(affine):
                        synth.append(f"X q{target}" if bit == 0 else f"CX q{physical[bit.bit_length()-1]} q{target}")
                    candidate = synth + linear
                    assert anf_run(candidate, frame) == want, (index, end, "exact ANF mismatch")
                    rec = {"lo": index, "hi": end, "target": target, "old_ccx": n,
                           "new_ccx": len(products), "old_ops": original, "new_ops": candidate,
                           "physical_basis": physical, "prefix_vids": list(state.wire),
                           "frame": [sorted(poly) for poly in frame],
                           "proof": "all 62 outputs exactly equal as Boolean ANFs under exact prefix XOR identities; no phase/events inside"}
                    hits.append(rec)
                    covered = end - 1
        state.step(line, index)
    return header, ops, {"checked": checked, "hits": hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--rank-scan", action="store_true")
    ap.add_argument("--prefix-quad", action="store_true")
    ap.add_argument("--zero-events", action="store_true")
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--lo", type=int, default=32283)
    ap.add_argument("--hi", type=int, default=43927)
    a = ap.parse_args()
    if a.prefix_quad:
        header, ops, out = prefix_quadratic_scan(a.lo, a.hi)
        ART.mkdir(parents=True, exist_ok=True)
        dest = ART / "approx_window_prefix_quad.json"
        dest.write_text(json.dumps(out, indent=2) + "\n")
        for h in out["hits"]:
            P.splice_kmb(header, ops, h["lo"], h["hi"], h["new_ops"], ART / f"approx_window_{h['lo']}.kmb")
        print(json.dumps({"checked": out["checked"], "hits": [{k:h[k] for k in ("lo","hi","old_ccx","new_ccx")} for h in out["hits"]]}, indent=2))
        return
    if a.rank_scan:
        out = rank_scan(a.lo, a.hi)
        ART.mkdir(parents=True, exist_ok=True)
        dest = ART / "approx_window_rank.json"
        dest.write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps({"checked": out["checked"], "hits": [{k:v for k,v in h.items() if k != "ops"} for h in out["hits"]]}, indent=2))
        return
    if a.scan:
        out = scan(a.n, a.seed, a.lo, a.hi, a.zero_events)
        ART.mkdir(parents=True, exist_ok=True)
        dest = ART / f"approx_window_scan_{a.seed}.json"
        dest.write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps({"path": str(dest), "n": out["n"], "hits": out["hits"],
                          "window_rank_witnesses": out["window_rank_witnesses"],
                          "checkpoints": out["checkpoints"]}, indent=2))


if __name__ == "__main__":
    main()
