"""DQI multiply-block anatomy on tape 575b043f.  Kaggle CPU, read-only, small output.

Reads the tape from the public dataset, decompresses to /tmp, and recovers the EXACT
bilinear interface of the 42-CCX field-multiply blocks:

  * census of CCX blocks (maximal runs sharing a (q1//12, q2//12, q3//12) word triple,
    inter-CCX gap <= 80) in the EEA forward and reverse passes;
  * for sampled blocks: the minimal CLOSED instruction window [s, e) (every qubit
    restored except the accumulator word) found by ANF propagation;
  * the per-AND terms (u_i, v_i, w_i): u_i, v_i are linear forms of the two input
    words, w_i is the set of accumulator bits the product is routed into;
  * the tensor T[k][i][j] of the block, i.e. the exact GF(2)-bilinear map it computes.

No quantum simulation: ANF propagation over classical values, degree <= 2.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

T0 = time.time()
OUT = {}
WORK = pathlib.Path("/kaggle/working")


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def find(pat):
    for p in pathlib.Path("/kaggle/input").rglob(pat):
        return p
    return None


XZ = find("dqi_575b043f.kmb.xz")
IRPY = find("vqcc_ir.py")
say("xz", XZ, "ir", IRPY)
raw = pathlib.Path("/tmp/dqi_575b043f.kmb")
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
OUT["num_ops"] = c.num_ops
OUT["num_qubits"] = c.num_qubits
OUT["static_toffoli"] = c.toffoli_like()
say("read", c.num_ops, c.num_qubits, OUT["static_toffoli"])

t = c.types
tof = np.flatnonzero(ir.LTOF[t])
cczp = np.flatnonzero(ir.L3Q[t] & ((t & 0x7F) == 0x31))
cfun3 = np.cumsum(ir.L3Q[t])
qc = cfun3[cczp + 1] - 1
A, B, C = (c.qqq0[qc].astype(np.int64), c.qqq1[qc].astype(np.int64), c.qqq2[qc].astype(np.int64))
CRA, CRB, CRT = A // 12, B // 12, C // 12
say("ccx", len(cczp))

# condition depth per instruction boundary
ev, clamped = ir._depth_events(t)


def depth(a):
    k = int(np.searchsorted(ev, a, side="left"))
    return int(clamped[k - 1]) if k > 0 else 0


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
for nm, bb in (("fwd", BF), ("rev", BR)):
    sizes = np.array([x[2] for x in bb])
    OUT[f"census_{nm}"] = {
        "blocks": len(bb), "n42": int((sizes == 42).sum()), "max": int(sizes.max()),
        "n_ge12": int((sizes >= 12).sum()),
        "sizes": {int(s): int(v) for s, v in zip(*np.unique(sizes, return_counts=True))},
    }
    b42 = [x for x in bb if x[2] == 42]
    OUT[f"triples_{nm}"] = {
        "distinct_ABC_on_42": len({(x[3], x[4], x[5]) for x in b42}),
        "A_eq_B": sum(1 for x in b42 if x[3] == x[4]),
        "C_in_AB": sum(1 for x in b42 if x[5] in (x[3], x[4])),
        "pool_target": sum(1 for x in b42 if x[5] >= 70),
        "synd_target": sum(1 for x in b42 if x[5] < 70),
        "top": sorted([(f"{x[3]},{x[4]},{x[5]}", sum(1 for y in b42 if (y[3], y[4], y[5]) == (x[3], x[4], x[5])))
                       for x in b42], key=lambda z: -z[1])[:8],
    }
say("census", json.dumps({k: v for k, v in OUT.items() if k.startswith("census")}))

# conditioning of the 42-blocks
cond42 = {"fwd": 0, "rev": 0}
for nm, b42 in (("fwd", [x for x in BF if x[2] == 42]), ("rev", [x for x in BR if x[2] == 42])):
    nn = 0
    for x in b42:
        if depth(x[0]) or depth(x[1] + 1):
            nn += 1
    cond42[nm] = nn
OUT["conditional_42_blocks"] = cond42
say("cond", cond42)


# ------------------------------------------------------------------ ANF engine
def _xor(dst, src):
    out = dict(dst)
    for m, v in src.items():
        if m in out:
            del out[m]
        else:
            out[m] = 1
    return out


def _xor_mul(dst, p, q, cap=2):
    out = dict(dst)
    for m1 in p:
        for m2 in q:
            m = m1 | m2
            if len(m) > cap:
                raise ValueError(f"degree {len(m)} > {cap}")
            if m in out:
                del out[m]
            else:
                out[m] = 1
    return out


def analyse_window(s, e):
    ops = c.decode(s, e)
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    val = {q: {frozenset([lv[q]]): 1} for q in qubits}
    pex = {q: {} for q in qubits}
    ands, conds = [], set()
    for (i, name, qs, tb, cb) in ops:
        base = name.replace("_IF", "")
        if cb is not None:
            conds.add(cb)
        if base == "CX":
            a, b = qs
            val[b] = _xor(val[b], val[a])
            pex[b] = _xor(pex[b], pex[a])
        elif base == "CCX":
            c1, c2, d = qs
            if pex[c1] or pex[c2]:
                raise ValueError(f"AND result used as a control at {i}")
            for v in (c1, c2):
                if any(len(m) > 1 for m in val[v]):
                    raise ValueError(f"non-linear CCX control at {i}")
            tid = len(ands)
            ands.append((i, c1, c2, d,
                         tuple(sorted(next(iter(m)) for m in val[c1])),
                         tuple(sorted(next(iter(m)) for m in val[c2]))))
            val[d] = _xor_mul(val[d], val[c1], val[c2])
            pex[d] = _xor(pex[d], {tid: 1})
        elif base == "SWAP":
            a, b = qs
            val[a], val[b] = val[b], val[a]
            pex[a], pex[b] = pex[b], pex[a]
        elif base == "X":
            val[qs[0]] = _xor(val[qs[0]], {frozenset(): 1})
        else:
            raise ValueError(f"unsupported {name} at {i} {qs}")
    out = {}
    for q in qubits:
        lin = {next(iter(m)): 1 for m in val[q] if len(m) == 1}
        pairs = sorted(tuple(sorted(m)) for m in val[q] if len(m) == 2)
        out[q] = (lin, pairs, 1 if frozenset() in val[q] else 0)
    return {"ands": ands, "out": out, "pex": pex, "conds": conds, "qubits": qubits}


def closure(res):
    ident, acc, bad = [], [], []
    for q, (lin, pairs, const) in res["out"].items():
        if lin == {q: 1} and not pairs and not const:
            ident.append(q)
        elif lin == {q: 1} and not const and pairs:
            acc.append(q)
        else:
            bad.append(q)
    return ident, acc, bad


def anatomy(x, npad_max=192, ntries=18):
    """Locate the minimal closed window around a block and extract its terms."""
    first, last, n, wa, wb, wc = x
    best = None
    for pad in [0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 64, 80, 96, 128, 160, npad_max][:ntries]:
        s, e = first - pad, last + 1 + pad
        if s < 0 or e > c.num_ops or depth(s) or depth(e):
            continue
        try:
            res = analyse_window(s, e)
        except ValueError as ex:
            continue
        ident, acc, bad = closure(res)
        if bad:
            continue
        if len({q // 12 for q in acc}) != 1:
            continue
        accw = acc[0] // 12
        # the two control words: every pair must join word wa' and wb'
        if best is None or pad < best[0]:
            best = (pad, s, e, res, ident, acc, accw)
    if best is None:
        return None
    pad, s, e, res, ident, acc, accw = best
    # tensor: accumulator bit k x (bit of wordA) x (bit of wordB)
    words = {}
    for q in res["qubits"]:
        words.setdefault(q // 12, []).append(q)
    accbits = {q % 12: q for q in acc}
    T = np.zeros((12, 12, 12), dtype=np.uint8)   # T[k][i][j]
    pairwords = set()
    for q in acc:
        k = q % 12
        for (p1, p2) in res["out"][q][1]:
            pairwords.add((p1 // 12, p2 // 12))
            for (u, v) in ((p1, p2), (p2, p1)):
                if u // 12 == wa and v // 12 == wb:
                    T[k, u % 12, v % 12] ^= 1
    terms = []
    for tid, (i, c1, c2, d, uu, vv) in enumerate(res["ands"]):
        wm = 0
        for q in acc:
            if tid in res["pex"][q]:
                wm |= 1 << (q % 12)
        terms.append({"op": i, "u": [f"{x // 12}.{x % 12}" for x in uu],
                      "v": [f"{x // 12}.{x % 12}" for x in vv], "w": wm})
    return {"pad": pad, "s": s, "e": e, "n_ops": e - s, "n_and": len(res["ands"]),
            "ident": len(ident), "acc": sorted(acc), "accw": accw,
            "pairwords": sorted(pairwords), "conds": sorted(res["conds"]),
            "T": T, "terms": terms,
            "n_cx": int(sum(1 for op in c.decode(s, e) if op[1].startswith("CX")))}


def pick(bb, frac):
    b42 = [y for y in bb if y[2] == 42]
    return b42[min(len(b42) - 1, int(frac * len(b42)))]


SAMPLES = [("fwd0", pick(BF, 0.0)), ("fwd_mid", pick(BF, 0.4)),
           ("rev0", pick(BR, 0.0)), ("rev_mid", pick(BR, 0.5))]
ab = [y for y in BF if y[2] == 42 and y[3] == y[4]]
if ab:
    SAMPLES.append(("fwd_Asq", ab[0]))
small = [y for y in BF if y[2] in (24, 34, 36)]
if small:
    SAMPLES.append((f"fwd_{small[0][2]}", small[0]))

OUT["blocks"] = {}
for nm, x in SAMPLES:
    say("anatomy", nm, x)
    r = anatomy(x)
    if r is None:
        OUT["blocks"][nm] = {"block": x, "status": "not closed"}
        say("  not closed")
        continue
    T = r.pop("T")
    r["block"] = x
    r["T_rows"] = [[int(sum(int(T[k, i, j]) << j for j in range(12))) for i in range(12)] for k in range(12)]
    r["T_bits"] = int(T.sum())
    r["T_by_out"] = [int(x) for x in T.sum(axis=(1, 2))]
    OUT["blocks"][nm] = r
    say("  pad", r["pad"], "window", r["s"], r["e"], "nops", r["n_ops"], "and", r["n_and"],
        "accw", r["accw"], "pairwords", r["pairwords"], "conds", r["conds"], "T_bits", r["T_bits"])
    print("   T rows (out bit k: 12 ints over i, value = mask over j):", flush=True)
    for k in range(12):
        print(f"     k={k:2d} {r['T_rows'][k]}", flush=True)

# print one block's full term list
first_nm = SAMPLES[0][0]
if first_nm in OUT["blocks"] and "terms" in OUT["blocks"][first_nm]:
    print(f"\n== full AND term list of {first_nm} ==", flush=True)
    for t_, tm in enumerate(OUT["blocks"][first_nm]["terms"]):
        print(f"  and{t_:2d} op={tm['op']:>9} u={tm['u']} v={tm['v']} w=0b{tm['w']:012b}", flush=True)

# uniformity: do the sample tensors agree?
tb = {nm: v.get("T_rows") for nm, v in OUT["blocks"].items()}
ref = tb.get("fwd0")
OUT["tensor_agreement"] = {nm: (v == ref) for nm, v in tb.items()}
say("agreement", OUT["tensor_agreement"])

with open(WORK / "anatomy.json", "w") as f:
    json.dump(OUT, f, indent=1)
say("wrote anatomy.json", (WORK / "anatomy.json").stat().st_size)
