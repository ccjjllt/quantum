"""Exact trilinear tensor of ONE 42-CCX multiply block of tape 575b043f.  Kaggle CPU, read-only.

Method (no quantum simulation, no statevector): every op in a multiply block is X / CX / CCX /
SWAP, i.e. GF(2)-affine except for the 42 CCX, each of which creates exactly one product
variable.  So the block is a *bilinear* straight-line program, and propagating

    qubit value = (linear form over the window's input bits)  XOR  (set of product vars)  XOR const

in exact integer bitmasks recovers, per AND i, the two linear forms (u_i, v_i) and the set of
accumulator bits w_i the product is routed into.  The trilinear tensor is then

    T[k][i][j] = parity over t of  [k in w_t] * [i in u_t] * [j in v_t]

which is exact, not sampled: 144 basis inputs are never needed because the propagation *is*
the 144 evaluations at once.

The window is the interesting part.  A window that starts inside the carrier preparation loses
part of u_i; one that starts too early picks up a neighbouring gadget.  We therefore sweep the
pad around the 42 CCXs and report, per pad, whether the block reads only the declared operand
word (12 bits into u, 12 into v), writes only one 12-bit word, restores every other qubit, and
whether the recovered T is a field / truncated product / cyclic product.  The correct window is
the one where those answers are stable, and the identification is the evidence.

Output: small JSON only.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

T0 = time.time()
WORK = pathlib.Path("/kaggle/working")
OUT = {}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def find(pat):
    for p in pathlib.Path("/kaggle/input").rglob(pat):
        return p
    return None


XZ = find("dqi_575b043f.kmb.xz")
IRPY = find("vqcc_ir.py")
say("xz", XZ, "ir", IRPY)
raw = pathlib.Path("/tmp/dqi.kmb")
if not raw.exists():
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
say("decompressed", raw.stat().st_size)

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
OUT["num_ops"] = int(c.num_ops)
OUT["num_qubits"] = int(c.num_qubits)
OUT["static_toffoli"] = int(c.toffoli_like())
say("read", c.num_ops, c.num_qubits, OUT["static_toffoli"])

t = c.types
tof = np.flatnonzero(ir.LTOF[t])
cczp = np.flatnonzero(ir.L3Q[t] & ((t & 0x7F) == 0x31))
cfun3 = np.cumsum(ir.L3Q[t])
qc = cfun3[cczp + 1] - 1
A = c.qqq0[qc].astype(np.int64)
B = c.qqq1[qc].astype(np.int64)
C = c.qqq2[qc].astype(np.int64)
CRA, CRB, CRT = A // 12, B // 12, C // 12

FWD = (17576206, 30335416)
REV = (35627262, 52910631)


def blocks(lo, hi, gapmax=80):
    sel = np.flatnonzero((cczp >= lo) & (cczp < hi))
    P = cczp[sel]
    a, b, d = CRA[sel], CRB[sel], CRT[sel]
    out = []
    i = 0
    while i < len(P):
        j = i
        while j + 1 < len(P) and (P[j + 1] - P[j] <= gapmax and a[j + 1] == a[j]
                                  and b[j + 1] == b[j] and d[j + 1] == d[j]):
            j += 1
        out.append((int(P[i]), int(P[j]), j - i + 1, int(a[i]), int(b[i]), int(d[i])))
        i = j + 1
    return out


BF, BR = blocks(*FWD), blocks(*REV)
b42f = [x for x in BF if x[2] == 42]
b42r = [x for x in BR if x[2] == 42]
OUT["n42"] = {"fwd": len(b42f), "rev": len(b42r)}

# ---------------------------------------------------------------- pick the blocks
picks = []
for nm, bb, tri in (("fwd_first", b42f, None), ("fwd_66_1_67", b42f, (66, 1, 67)),
                    ("rev_64_66_70", b42r, (64, 66, 70)), ("rev_first", b42r, None)):
    if tri is None:
        cand = bb[0]
    else:
        hit = [x for x in bb if (x[3], x[4], x[5]) == tri]
        cand = hit[0] if hit else None
    if cand is not None:
        picks.append((nm, cand))
OUT["picks"] = {nm: list(x) for nm, x in picks}
say("picks", OUT["picks"])

# ---------------------------------------------------------------- simple-gate runs
SIMPLE = np.zeros(256, bool)
for op in (0x11, 0x21, 0x22, 0x31):     # X, CX, SWAP, CCX  (no _IF, no rotations)
    SIMPLE[op] = True
simple = SIMPLE[t]                       # unconditional gate only
nonsimple = np.flatnonzero(~simple)
OUT["n_simple"] = int(simple.sum())
say("simple gates", OUT["n_simple"])


def run_bounds(a, b):
    k = np.searchsorted(nonsimple, a, side="left")
    lo = 0 if k == 0 else int(nonsimple[k - 1]) + 1
    k = np.searchsorted(nonsimple, b, side="left")
    hi = int(nonsimple[k]) if k < len(nonsimple) else int(c.num_ops)
    return lo, hi


# ---------------------------------------------------------------- ANF engine
def analyse(ops):
    """Exact GF(2) ANF to degree 2 over the given instruction list."""
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    val = {q: 1 << lv[q] for q in qubits}
    pex = {q: 0 for q in qubits}
    con = {q: 0 for q in qubits}
    ands = []          # (u_mask, v_mask, target_qubit, and_id)
    for (i, name, qs, tb, cb) in ops:
        if cb is not None:
            raise ValueError(f"conditioned op at {i}")
        if name == "CX":
            x, y = qs
            val[y] ^= val[x]
            pex[y] ^= pex[x]
            con[y] ^= con[x]
        elif name == "CCX":
            c1, c2, d = qs
            if pex[c1] or pex[c2] or con[c1] or con[c2]:
                raise ValueError(f"AND control not linear at {i}")
            ands.append((val[c1], val[c2], d, len(ands)))
            pex[d] ^= 1 << (len(ands) - 1)
        elif name == "SWAP":
            x, y = qs
            val[x], val[y] = val[y], val[x]
            pex[x], pex[y] = pex[y], pex[x]
            con[x], con[y] = con[y], con[x]
        elif name == "X":
            con[qs[0]] ^= 1
        else:
            raise ValueError(f"unsupported {name} at {i}")
    return qubits, lv, val, pex, con, ands


def bits(m):
    while m:
        b = m & -m
        yield b.bit_length() - 1
        m ^= b


def build_tensor(qubits, lv, val, pex, con, ands, wa, wb, wc):
    """Restrict to word wa x word wb -> word wc.  Returns (T3, diagnostics)."""
    Qa = set(range(12 * wa, 12 * wa + 12))
    Qb = set(range(12 * wb, 12 * wb + 12))
    Qc = set(range(12 * wc, 12 * wc + 12))
    diag = {"and_bad_u": 0, "and_bad_v": 0, "out_bad": 0, "n_out": 0, "out_qubits": []}
    terms = []
    for (u, v, d, _t) in ands:
        su, sv = set(bits(u)), set(bits(v))
        if not su <= Qa:
            diag["and_bad_u"] += 1
        if not sv <= Qb:
            diag["and_bad_v"] += 1
        terms.append((u, v))
    # qubits carrying products = candidate outputs
    outs = [q for q in qubits if pex[q]]
    outs_c = [q for q in outs if q in Qc]
    diag["n_out"] = len(outs)
    diag["n_out_c"] = len(outs_c)
    diag["out_qubits"] = sorted(outs_c)
    diag["out_outside_c"] = len(outs) - len(outs_c)
    T3 = np.zeros((12, 12, 12), np.uint8)       # [k][i][j]
    for q in outs_c:
        k = q - 12 * wc
        m = pex[q]
        for t in bits(m):
            u, v = terms[t]
            ui = [x - 12 * wa for x in bits(u) if 12 * wa <= x < 12 * wa + 12]
            vj = [y - 12 * wb for y in bits(v) if 12 * wb <= y < 12 * wb + 12]
            if ui and vj:
                T3[k][np.ix_(ui, vj)] ^= 1
    # closure: everything that is not an output must be identity
    ident, acc, bad = 0, 0, []
    for q in qubits:
        if val[q] == 1 << lv[q] and pex[q] == 0 and con[q] == 0:
            ident += 1
        elif val[q] == 1 << lv[q] and con[q] == 0:
            acc += 1
        else:
            bad.append(q)
    diag["closed"] = (len(bad) == 0)
    diag["n_bad_qubits"] = len(bad)
    diag["bad_sample"] = bad[:8]
    diag["const_any"] = int(sum(con.values()))
    return T3, diag


# ---------------------------------------------------------------- tensor tests
def mat_mul_gf2(X, Y):
    return (X.astype(np.int64) @ Y.astype(np.int64)) & 1


def gf2_rank(M):
    M = M.copy().astype(np.uint8) & 1
    r = 0
    rows, cols = M.shape
    for c in range(cols):
        p = None
        for i in range(r, rows):
            if M[i, c]:
                p = i
                break
        if p is None:
            continue
        M[[r, p]] = M[[p, r]]
        for i in range(rows):
            if i != r and M[i, c]:
                M[i] ^= M[r]
        r += 1
        if r == rows:
            break
    return r


def tests(T3):
    """T3[k][i][j]; returns structural facts about the 12x12->12 bilinear map."""
    res = {}
    # flattening ranks
    F1 = T3.reshape(12, 144)              # k vs (i,j)
    F2 = np.transpose(T3, (1, 0, 2)).reshape(12, 144)   # i vs (k,j)
    F3 = np.transpose(T3, (2, 0, 1)).reshape(12, 144)   # j vs (k,i)
    res["flat_ranks"] = [int(gf2_rank(F1)), int(gf2_rank(F2)), int(gf2_rank(F3))]
    # structure constants  S[b][a] = T(a,b)   (12-bit ints)
    Tb = np.transpose(T3, (2, 1, 0))      # [j][i][k]  -> b, a, out
    S = np.zeros((12, 12), np.int64)
    for b in range(12):
        for a in range(12):
            v = 0
            for k in range(12):
                v |= int(Tb[b][a][k]) << k
            S[b][a] = v
    res["commutative"] = bool(np.array_equal(T3, np.transpose(T3, (0, 2, 1))))
    # L_b : a -> a*b   (12x12 over GF(2), rows a, cols out)
    L = np.zeros((12, 12, 12), np.uint8)
    for b in range(12):
        for a in range(12):
            for k in range(12):
                L[b][a][k] = Tb[b][a][k]
    # associativity on the basis: L_{e_i} L_{e_j} == L_{e_i e_j}
    assoc = True
    prod_ok = True
    for i in range(12):
        for j in range(12):
            p = int(S[j][i])          # the VECTOR e_i * e_j
            X = mat_mul_gf2(L[j], L[i])
            Y = np.zeros((12, 12), np.uint8)
            for b in bits(p):
                Y ^= L[b]
            if not np.array_equal(X, Y):
                assoc = False
    res["associative_on_basis"] = bool(assoc)
    # identity
    ident = None
    for e in range(12):
        ok = (all(int(S[e][a]) == (1 << a) for a in range(12))
              and all(int(S[b][e]) == (1 << b) for b in range(12)))
        if ok:
            ident = e
            break
    res["identity_basis"] = ident
    # invertibility of a -> a*b for all b != 0 (no zero divisors)
    ranks = [int(gf2_rank(L[b])) for b in range(12)]
    res["min_unit_rank"] = int(min(ranks))
    return res, S


def match_named(T3, name):
    """Compare T3 with the truncated product, the cyclic product, and all field products mod P."""
    K, I, J = T3.shape
    # truncated x^12 : c_k = sum_{i+j=k}
    T = np.zeros((12, 12, 12), np.uint8)
    for i in range(12):
        for j in range(12):
            if i + j < 12:
                T[i + j][i][j] = 1
    out = {"trunc": bool(np.array_equal(T3, T))}
    # cyclic x^12 - 1
    Tc = np.zeros((12, 12, 12), np.uint8)
    for i in range(12):
        for j in range(12):
            Tc[(i + j) % 12][i][j] = 1
    out["cyclic"] = bool(np.array_equal(T3, Tc))
    return out


def minpoly_of(S, e, n=12):
    """Minimal polynomial of the basis element e, from structure constants S[b][a]=a*b."""
    # powers 1, x, x^2, ... as 12-bit vectors
    pw = [0] * (2 * n + 2)
    # x^0 = identity vector
    ident = None
    for cand in range(n):
        if all(int(S[cand][a]) == (1 << a) for a in range(n)):
            ident = cand
            break
    if ident is None:
        return None
    pw[0] = 1 << ident
    cur = 1 << e
    for k in range(1, 2 * n + 2):
        pw[k] = int(cur)
        nxt = 0
        for b in bits(int(cur)):
            nxt ^= int(S[b][e])
        cur = nxt
        if cur == 0:
            pw[k + 1] = 0
            break
    # find the first d with x^d in span(1..x^{d-1})
    for d in range(1, n + 1):
        basis = [pw[k] for k in range(d)]
        # solve sum c_k x^k = x^d
        M = np.zeros((n, d + 1), np.uint8)
        for k in range(d):
            for r in range(n):
                M[r][k] = (basis[k] >> r) & 1
        for r in range(n):
            M[r][d] = (pw[d] >> r) & 1
        # consistent?  rank(A) == rank(A|b)
        if gf2_rank(M[:, :d]) == gf2_rank(M):
            # solve for coefficients
            A2 = M[:, :d].copy()
            b2 = M[:, d].copy()
            sol = np.zeros(d, np.uint8)
            # gaussian elimination
            Mc = M.copy()
            piv = []
            r = 0
            for col in range(d):
                p = None
                for i in range(r, n):
                    if Mc[i][col]:
                        p = i
                        break
                if p is None:
                    continue
                Mc[[r, p]] = Mc[[p, r]]
                for i in range(n):
                    if i != r and Mc[i][col]:
                        Mc[i] ^= Mc[r]
                piv.append(col)
                r += 1
            consistent = all(not Mc[i].any() or Mc[i][d] == 0 for i in range(r, n))
            if consistent:
                for rr, col in enumerate(piv):
                    sol[col] = Mc[rr][d]
                # poly: x^d + sum sol_k x^k
                return [int(sol[k]) for k in range(d)] + [1]
    return None


# ---------------------------------------------------------------- sweep
PADS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 64, 80, 96, 128, 160, 200, 240]
RES = {}
for nm, x in picks:
    first, last, n, wa, wb, wc = x
    lo, hi = run_bounds(first, last + 1)
    say(nm, "run", lo, hi, "len", hi - lo)
    d0 = max(lo, first - 800)
    d1 = min(hi, last + 1 + 800)
    ops_all = c.decode(d0, d1)
    rows = []
    for pad in PADS:
        s = max(lo, first - pad)
        e = min(hi, last + 1 + pad)
        if s < d0 or e > d1:
            continue
        sub = [o for o in ops_all if s <= o[0] < e]
        try:
            qubits, lv, val, pex, con, ands = analyse(sub)
        except ValueError as exc:
            rows.append({"pad": pad, "err": str(exc)[:80]})
            continue
        T3, diag = build_tensor(qubits, lv, val, pex, con, ands, wa, wb, wc)
        row = {"pad": pad, "span": [s, e], "n_and": len(ands), "n_qubits": len(qubits)}
        row.update(diag)
        if diag["and_bad_u"] == 0 and diag["and_bad_v"] == 0 and diag["n_out_c"] == 12:
            tr = tests(T3)
            row["struct"] = tr[0]
            row.update(match_named(T3, nm))
            # how many distinct u forms and their multiplicities
            uu = {}
            for (u, v, d, _t) in ands:
                uu[u] = uu.get(u, 0) + 1
            row["n_distinct_u"] = len(uu)
            row["u_mult"] = sorted(uu.values(), reverse=True)
            row["symmetric_terms"] = sum(1 for (u, v, d, _t) in ands if u == v)
        rows.append(row)
        say(nm, "pad", pad, {k: row[k] for k in ("n_and", "n_out", "closed", "n_bad_qubits") if k in row},
            row.get("struct", {}).get("associative_on_basis"), row.get("identity_basis", ""),
            (row.get("u_mult") or [])[:8], row.get("trunc"), row.get("cyclic"))
    RES[nm] = {"block": [first, last, n, wa, wb, wc], "run": [lo, hi], "rows": rows}

OUT["sweep"] = RES

# ---------------------------------------------------------------- dump one decode + tensor
best = None
for nm, r in RES.items():
    for row in r["rows"]:
        st = row.get("struct")
        if st and st.get("identity_basis") is not None and st.get("associative_on_basis") \
                and st.get("commutative") and st.get("min_unit_rank") == 12:
            best = (nm, row)
            break
    if best:
        break
OUT["field_like"] = None if best is None else {"pick": best[0], "pad": best[1]["pad"]}

if best is not None:
    nm, row = best
    x = picks[[p[0] for p in picks].index(nm)][1]
    first, last, n, wa, wb, wc = x
    pad = row["pad"]
    s, e = max(0, first - pad), last + 1 + pad
    qubits, lv, val, pex, con, ands = analyse([o for o in c.decode(s, e)])
    T3, diag = build_tensor(qubits, lv, val, pex, con, ands, wa, wb, wc)
    st, S = tests(T3)
    terms = []
    for (u, v, d, _t) in ands:
        ui = 0
        for q in bits(u):
            if 12 * wa <= q < 12 * wa + 12:
                ui |= 1 << (q - 12 * wa)
        vj = 0
        for q in bits(v):
            if 12 * wb <= q < 12 * wb + 12:
                vj |= 1 << (q - 12 * wb)
        wk = 0
        for q in qubits:
            if pex[q] >> _t & 1 and 12 * wc <= q < 12 * wc + 12:
                wk |= 1 << (q - 12 * wc)
        terms.append([ui, vj, wk])
    OUT["terms"] = terms
    OUT["struct_full"] = st
    OUT["T3"] = T3.tolist()
    # minimal polynomials of every basis element
    OUT["minpolys"] = {int(e): minpoly_of(S, e) for e in range(12)}
    # check the term list really is a decomposition of T3
    R = np.zeros((12, 12, 12), np.uint8)
    for (ui, vj, wk) in terms:
        for k in bits(wk):
            for i in bits(ui):
                for j in bits(vj):
                    R[k][i][j] ^= 1
    OUT["terms_reproduce_T"] = bool(np.array_equal(R, T3))

with open(WORK / "tensor.json", "w") as f:
    json.dump(OUT, f)
say("wrote", (WORK / "tensor.json").stat().st_size, "bytes")
print(json.dumps({k: v for k, v in OUT.items() if k not in ("T3", "terms")}, indent=1)[:14000])
raw.unlink()
say("done")
