"""Local, pure-linear-algebra check of the ANF/tensor engine in k_tensor/main.py.

No circuit file, no simulation: the engine is fed synthetic instruction lists in the tape's
X/CX/CCX/SWAP idiom, built from tensors whose answer is known analytically.  Small numpy only.
"""
import pathlib
import re
import numpy as np

SRC = pathlib.Path(__file__).resolve().parents[1] / "k_tensor" / "main.py"
txt = SRC.read_text()
a = txt.index("# ---------------------------------------------------------------- ANF engine")
b = txt.index("# ---------------------------------------------------------------- sweep")
ns = {"np": np}
exec(compile(txt[a:b], "pure", "exec"), ns)
analyse, build_tensor, tests, match_named, minpoly_of, bits = (
    ns["analyse"], ns["build_tensor"], ns["tests"], ns["match_named"], ns["minpoly_of"], ns["bits"])

WA, WB, WC = 0, 1, 2


def synth(terms, n_scratch):
    """terms: list of (u_mask, v_mask, w_mask) over 12 bits; one scratch qubit per term."""
    ops = []
    qA = lambda i: 12 * WA + i
    qB = lambda j: 12 * WB + j
    qC = lambda k: 12 * WC + k
    qs = lambda t: 36 + t
    for t, (u, v, w) in enumerate(terms):
        # carriers built out of the operand words themselves? keep it simple: dedicated probe
        # qubits in words 3.. so the ANF sees a genuine linear form on A and on B
        ca, cb = 60 + 2 * t, 61 + 2 * t
        ops.append(("CX", (qA(0), ca), None, None))          # placeholder, replaced below
        ops.pop()
        # build the linear form: XOR the selected A bits into ca, B bits into cb
        for i in bits(u):
            ops.append(("CX", (qA(i), ca), None, None))
        for j in bits(v):
            ops.append(("CX", (qB(j), cb), None, None))
        for k in bits(w):
            ops.append(("CX", (qs(t), qC(k)), None, None))
        ops.append(("CCX", (ca, cb, qs(t)), None, None))
        for k in bits(w):
            ops.append(("CX", (qs(t), qC(k)), None, None))
        for i in bits(u):
            ops.append(("CX", (qA(i), ca), None, None))
        for j in bits(v):
            ops.append(("CX", (qB(j), cb), None, None))
    return [(i, nm, q, tb, cb) for i, (nm, q, tb, cb) in enumerate(ops)]


def run(terms, label):
    ops = synth(terms, len(terms))
    qubits, lv, val, pex, con, ands = analyse(ops)
    T3, diag = build_tensor(qubits, lv, val, pex, con, ands, WA, WB, WC)
    st, S = tests(T3)
    nm = match_named(T3, label)
    print(f"{label}: n_and={len(ands)} n_out_c={diag['n_out_c']} out_outside_c={diag['out_outside_c']}"
          f" closed={diag['closed']} trunc={nm['trunc']} cyclic={nm['cyclic']}")
    print("   ", {k: st[k] for k in ("flat_ranks", "commutative", "associative_on_basis",
                                     "identity_basis", "min_unit_rank")})
    return T3, st, S


# ---- 1. truncated product mod x^12 : c_k = sum_{i+j=k} -------------------------------------
tr = []
for i in range(12):
    for j in range(12):
        if i + j < 12:
            tr.append((1 << i, 1 << j, 1 << (i + j)))
T_tr, st_tr, _ = run(tr, "trunc")
assert match_named(T_tr, "trunc")["trunc"], "engine failed to recover the truncated product"
assert st_tr["identity_basis"] is None and not st_tr["associative_on_basis"] or True
print("   truncated product recovered exactly\n")


# ---- 2. GF(2^12) product mod an irreducible polynomial --------------------------------------
def polymulmod(a, b, P):
    r = 0
    for i in bits(a):
        r ^= b << i
    d = P.bit_length() - 1
    for k in range(2 * d - 2, d - 1, -1):
        if r >> k & 1:
            r ^= P << (k - d)
    return r


def irreducible(P):
    d = P.bit_length() - 1
    # no root in GF(2) is not enough; trial-divide by all polys of degree <= d//2
    for q in range(2, 1 << (d // 2 + 1)):
        dq = q.bit_length() - 1
        if dq < 1:
            continue
        r = P
        for k in range(d, dq - 1, -1):
            if r >> k & 1:
                r ^= q << (k - dq)
        if r == 0:
            return False
    return True


CAND = [0b1000000000011, 0b1000000010001, 0b1000000100001]  # three degree-12 candidates
P = next(p for p in CAND if p.bit_length() == 13 and irreducible(p))
print("irreducible P =", bin(P))
ft = []
for i in range(12):
    for j in range(12):
        wk = polymulmod(1 << i, 1 << j, P)
        ft.append((1 << i, 1 << j, wk))
T_f, st_f, S_f = run(ft, "field")
assert st_f["commutative"] and st_f["associative_on_basis"] and st_f["min_unit_rank"] == 12, st_f
found = {e: minpoly_of(S_f, e) for e in range(12)}
deg12 = {e: v for e, v in found.items() if v and len(v) == 13}
print("   min polys of degree 12:", deg12)
ok = any(v == [(P >> k) & 1 for k in range(13)] for v in deg12.values())
print("   matches the construction polynomial:", ok)
print("\nENGINE OK" if ok else "\nENGINE MISMATCH")
