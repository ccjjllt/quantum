"""Extract the exact ANF (degree <= 2) of one multiply block. Pure symbolic arithmetic.

Each qubit's value is an ANF polynomial over GF(2) in the *input* values of the window's
qubits: dict {monomial: 1} with monomial a frozenset of local variable ids, degree <= 2.
The block should come out as out_k = in_k + sum_{i,j} T[i,j,k] x_i y_j (a bilinear map).
"""
import importlib.util
import itertools
import pathlib
import sys
import collections

import numpy as np

ROOT = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
spec = importlib.util.spec_from_file_location("vqcc_ir", ROOT / "artifacts/20261118_push_dqi/ds/vqcc_ir.py")
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read("/private/tmp/dqid/dqi_575b043f.kmb")

EMPTY = frozenset()


def anf_xor(p, q):
    out = dict(p)
    for m, v in q.items():
        if m in out:
            del out[m]
        else:
            out[m] = 1
    return out


def anf_mul(p, q, cap=3):
    out = {}
    for m1 in p:
        for m2 in q:
            m = m1 | m2
            if len(m) > cap:
                raise ValueError(f"degree > {cap}: {m}")
            if m in out:
                del out[m]
            else:
                out[m] = 1
    return out


def deg2_count(p):
    return sum(1 for m in p if len(m) == 2)


def extract(a, b, label):
    ops = c.decode(a, b)
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    val = {q: {frozenset([lv[q]]): 1} for q in qubits}   # identity ANF
    maxdeg = 0
    for (i, name, qs, tb, cb) in ops:
        base = name.replace("_IF", "")
        if base == "CX":
            s, d = qs
            val[d] = anf_xor(val[d], val[s])
        elif base == "CCX":
            c1, c2, d = qs
            val[d] = anf_xor(val[d], anf_mul(val[c1], val[c2]))
        elif base == "SWAP":
            val[qs[0]], val[qs[1]] = val[qs[1]], val[qs[0]]
        elif base == "X":
            val[qs[0]] = anf_xor(val[qs[0]], {EMPTY: 1})
        else:
            print(f"   !! unsupported {name} at {i} {qs}")
    print(f"\n===== {label} [{a},{b}) {len(ops)} ops, {len(qubits)} qubits, vars {qubits[0]}..{qubits[-1]}")
    for q in qubits:
        p = val[q]
        ident = p == {frozenset([lv[q]]): 1}
        d2 = deg2_count(p)
        if not ident or d2:
            terms = sorted((tuple(sorted(m)) for m in p), key=lambda m: (len(m), m))
            print(f"  q{q:<4} deg2={d2:<3} terms={len(p):<3} {'IDENT' if ident else ''} "
                  f"{[tuple(qubits[j] for j in m) for m in terms][:14]}")
    return qubits, lv, val


qubits, lv, val = extract(17576206, 17577498, "fwd0")
qubits1, lv1, val1 = extract(17579104, 17580396, "fwd1")
qubits2, lv2, val2 = extract(36295669, 36296961, "rev0")
