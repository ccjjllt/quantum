"""Structural analysis of bilinear AND blocks in a kickmix tape.

A block is a CNOT/CCX window whose gates form a *bilinear circuit*: every CCX control is a
linear form of the window's input values, every CCX result flows only through CX, and the
window restores every qubit except the accumulator word.  Then the block is exactly

    C_out[k] = C_in[k] + sum_i w_i[k] * (u_i . x) * (v_i . y)

i.e. a rank-m bilinear map realised with m ANDs.  This module recovers, for a window,
the per-AND terms (u_i, v_i, w_i) and the tensor T[k][i][j].

Nothing here simulates quantum mechanics: it is ANF (product polynomial) propagation,
degree <= 2, over the classical values.
"""
import numpy as np


def _xor(dst, src):
    out = dict(dst)
    for m, v in src.items():
        if m in out:
            del out[m]
        else:
            out[m] = 1
    return out


def _xor_mul(dst, p, q, cap=2):
    """dst ^= p*q (p,q ANFs), degree capped at `cap`."""
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


def analyse_window(c, s, e, verbose=False):
    """Decompose instructions [s, e) as a bilinear circuit.

    Returns a dict:  ands  = [(i, c1, c2, tgt, u_dict, v_dict)]  (u,v: var->1 linear forms)
                     out   = {qubit: (linear_dict, pairs_dict)}  final ANF per qubit
                     pexp  = {qubit: {term_id: 1}}               which ANDs reach each qubit
                     conds = set of condition bits used
    """
    ops = c.decode(s, e)
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    val = {q: {frozenset([lv[q]]): 1} for q in qubits}     # ANF over input values
    pex = {q: {} for q in qubits}                          # which ANDs (by id) reach q
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
            ands.append((i, c1, c2, d, [next(iter(m)) for m in val[c1]], [next(iter(m)) for m in val[c2]]))
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
        pairs = [tuple(sorted(m)) for m in val[q] if len(m) == 2]
        const = 1 if frozenset() in val[q] else 0
        out[q] = (lin, pairs, const)
    return {"ands": ands, "out": out, "pex": pex, "conds": conds, "qubits": qubits, "lv": lv}


def closure_report(res, word_of):
    """Which qubits are restored (identity) and which accumulate bilinear content."""
    ident, acc, bad = [], [], []
    for q, (lin, pairs, const) in res["out"].items():
        is_id = (lin == {q: 1} and not pairs and not const)
        if is_id:
            ident.append(q)
        elif lin == {q: 1} and not const and pairs:
            acc.append(q)
        else:
            bad.append((q, lin, len(pairs), const))
    return ident, acc, bad


def terms_from_tensor(res, word_bits, acc):
    """(u,v,w) terms in word-bit coordinates.  word_bits: {word: [12 qubits]}.
    acc: list of accumulator qubits (all in one word)."""
    qword = {}
    for wname, qs in word_bits.items():
        for k, q in enumerate(qs):
            qword[q] = (wname, k)
    qword = {q: qword.get(q, ("?", q)) for q in res["qubits"]}
    terms = []
    for tid, (i, c1, c2, d, u, v) in enumerate(res["ands"]):
        wmask = 0
        for q in [q for q in acc]:
            if tid in res["pex"][q]:
                wmask |= 1 << qword[q][1]
        terms.append({
            "op": i, "c1": c1, "c2": c2, "tgt": d,
            "u": sorted(qword[x] for x in u if x in qword),
            "v": sorted(qword[x] for x in v if x in qword),
            "u_abs": sorted(u), "v_abs": sorted(v),
            "w": wmask,
        })
    return terms
