"""Manual exact affine-frame resynthesis on the pinned 62Q baseline.

Each window contains 2--4 nonlinear gates and otherwise only X/CX/SWAP.
CCX/CSWAP are conjugated into affine-control transvections. Commuting
transvections can merge by their output direction or by rank-two quadratic
factorization. Candidate circuits are certified by exact Boolean ANFs on
all 62 independent entry wires. No validator or submission is invoked.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
from collections import Counter
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
N = 62
ONE = 1 << N
MASK = ONE - 1
ALLOWED = {"X", "CX", "SWAP", "CCX", "CSWAP"}


def bits(v):
    while v:
        k = (v & -v).bit_length() - 1
        yield k
        v &= v - 1


def parity(v):
    return v.bit_count() & 1


def xor(a, b):
    return a ^ b


def mul(a, b):
    out = set()
    for x in a:
        for y in b:
            z = x | y
            if z in out:
                out.remove(z)
            else:
                out.add(z)
    return frozenset(out)


def affine(v):
    return frozenset(0 if i == N else 1 << i for i in bits(v))


def product(g):
    u, v, _ = g
    return mul(affine(u), affine(v))


def decode(line):
    p = line.split()
    return p[0], [int(v[1:]) for v in p[1:]]


def expanded(lines):
    for line in lines:
        k, q = decode(line)
        if k == "CSWAP":
            c, a, b = q
            yield "CX", [a, b]
            yield "CCX", [c, b, a]
            yield "CX", [a, b]
        else:
            yield k, q


def canonical(lines):
    rows = [1 << i for i in range(N)]
    cols = rows.copy()
    gs, cliff = [], []
    for k, q in expanded(lines):
        if k == "CCX":
            a, b, t = q
            gs.append((rows[a], rows[b], cols[t]))
        else:
            cliff.append(k + " " + " ".join(f"q{i}" for i in q))
            if k == "X":
                rows[q[0]] ^= ONE
            elif k == "CX":
                a, b = q
                rows[b] ^= rows[a]
                cols[a] ^= cols[b]
            elif k == "SWAP":
                a, b = q
                rows[a], rows[b] = rows[b], rows[a]
                cols[a], cols[b] = cols[b], cols[a]
    return gs, cliff


def commute(a, b):
    return all(not parity(u & w) for u, w in
               [(a[0], b[2]), (a[1], b[2]), (b[0], a[2]), (b[1], a[2])])


def factor(poly, w):
    """poly = u*v XOR linear; None when its quadratic rank exceeds two."""
    quad = {m for m in poly if m.bit_count() == 2}
    if any(m.bit_count() > 2 for m in poly):
        return None
    if not quad:
        lin = sum(ONE if m == 0 else m for m in poly)
        return [], [(lin, w)] if lin else []
    a, b = list(bits(next(iter(quad))))
    u = sum(m ^ (1 << a) for m in quad if m & (1 << a))
    v = sum(m ^ (1 << b) for m in quad if m & (1 << b))
    rem = poly ^ product((u, v, w))
    if any(m.bit_count() > 1 for m in rem):
        return None
    lin = sum(ONE if m == 0 else m for m in rem)
    if parity(u & w) or parity(v & w) or parity(lin & w):
        return None
    return [(u, v, w)], [(lin, w)] if lin else []


def merge(a, b):
    if product(a) == product(b):
        w = a[2] ^ b[2]
        return ([(a[0], a[1], w)] if w else []), []
    if a[2] == b[2]:
        return factor(product(a) ^ product(b), a[2])
    return None


def emit_linear(lin, w):
    if not lin or not w:
        return []
    t = next(bits(w))
    ds = [f"CX q{t} q{j}" for j in bits(w & ~(1 << t))]
    assert parity(lin & w) == 0
    middle = [f"CX q{j} q{t}" for j in bits(lin & MASK & ~(1 << t))]
    if lin & ONE:
        middle.append(f"X q{t}")
    return ds + middle + ds[::-1]


def emit_gate(g):
    u, v, w = g
    if not w:
        return []
    t = next(bits(w))
    assert not parity(u & w) and not parity(v & w)
    ds = [f"CX q{t} q{j}" for j in bits(w & ~(1 << t))]
    # Conjugation by ds removes the t coordinate from both controls.
    uc, vc = u & ONE, v & ONE
    u, v = u & MASK & ~(1 << t), v & MASK & ~(1 << t)
    if not u or not v or u == v:
        poly = mul(affine(u | uc), affine(v | vc))
        assert all(m.bit_count() <= 1 for m in poly)
        lin = sum(ONE if m == 0 else m for m in poly)
        return ds + emit_linear(lin, 1 << t) + ds[::-1]
    a = next(bits(u))
    ps = [f"CX q{j} q{a}" for j in bits(u & ~(1 << a))]
    vp = v ^ ((u ^ (1 << a)) if v & (1 << a) else 0)
    b = next(bits(vp & ~(1 << a)))
    ps += [f"CX q{j} q{b}" for j in bits(vp & ~(1 << b))]
    xs = ([f"X q{a}"] if uc else []) + ([f"X q{b}"] if vc else [])
    return ds + ps + xs + [f"CCX q{a} q{b} q{t}"] + xs[::-1] + ps[::-1] + ds[::-1]


def anf_run(lines):
    q = [frozenset([1 << i]) for i in range(N)]
    for k, qs in expanded(lines):
        if k == "X":
            q[qs[0]] ^= frozenset([0])
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]]
        elif k == "SWAP":
            a, b = qs
            q[a], q[b] = q[b], q[a]
        elif k == "CCX":
            a, b, t = qs
            q[t] ^= mul(q[a], q[b])
        if max(map(len, q)) > 200000:
            raise OverflowError("ANF budget")
    return q


def linear_solve(polys, target):
    """Return a bit mask of columns whose exact ANFs XOR to target."""
    basis = {}
    for j, poly in enumerate(polys):
        v, comb = set(poly), 1 << j
        while v:
            pivot = max(v)
            if pivot not in basis:
                basis[pivot] = (v, comb)
                break
            vv, cc = basis[pivot]
            v.symmetric_difference_update(vv); comb ^= cc
    v, comb = set(target), 0
    while v:
        pivot = max(v)
        if pivot not in basis: return None
        vv, cc = basis[pivot]
        v.symmetric_difference_update(vv); comb ^= cc
    return comb


def availability_search(header, ops):
    """Exact local ANFs retain Boolean idempotence and distributivity.

    Measurements/resets remain in place. All phase gates are untouched.
    Only a CCX whose product already equals an affine combination of the
    other live wires is replaced, so data and all later measurement phases
    are identical even on dirty, unconstrained entry states.
    """
    hits, attempted, capped = [], 0, 0
    block_start, nonlinear = 0, []
    for at, line in enumerate(ops):
        k = line.split()[0]
        if k in {"PUSH_CONDITION", "POP_CONDITION", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            block_start, nonlinear = at + 1, []
            continue
        if k in {"Z", "CZ", "CCZ", "Z_POW", "NEG"}: continue
        if k not in ALLOWED | {"HMR", "R"} or " if " in line:
            block_start, nonlinear = at + 1, []
            continue
        if k not in {"CCX", "CSWAP"}: continue
        if k == "CCX":
            lo = max(block_start, nonlinear[-8] if len(nonlinear) >= 8 else block_start, at - 350)
            attempted += 1
            q = [frozenset([1 << i]) for i in range(N)]
            over = False
            for ll in ops[lo:at]:
                pp = ll.split(); kind = pp[0]
                if kind in {"Z", "CZ", "CCZ", "Z_POW", "NEG"}: continue
                if kind in {"HMR", "R"}:
                    q[int(pp[1][1:])] = frozenset(); continue
                for kind, qs in expanded([ll]):
                    if kind == "X": q[qs[0]] ^= frozenset([0])
                    elif kind == "CX": q[qs[1]] ^= q[qs[0]]
                    elif kind == "SWAP":
                        a,b=qs; q[a],q[b]=q[b],q[a]
                    elif kind == "CCX":
                        a,b,t=qs
                        if len(q[a])*len(q[b]) > 100000:
                            over=True;break
                        q[t] ^= mul(q[a],q[b])
                if over or max(map(len,q))>10000: over=True;break
            if over: capped+=1;nonlinear.append(at);continue
            _,(a,b,t)=decode(line)
            if len(q[a])*len(q[b])>100000: capped+=1;nonlinear.append(at);continue
            want=mul(q[a],q[b]); wires=[j for j in range(N) if j!=t]
            cols=[frozenset([0])]+[q[j] for j in wires]
            sol=linear_solve(cols,want)
            clear = q[t] == want
            if sol is not None or clear:
                cand=([f"X q{t}"] if sol is not None and sol&1 else [])+[f"CX q{wires[j-1]} q{t}" for j in bits(sol or 0) if j]
                if clear:
                    cand=[f"HMR q{t} b{40000+at}",f"CZ q{a} q{b} if b{40000+at}"]
                got=frozenset()
                for j in bits(sol or 0):got ^= cols[j]
                assert clear or got==want
                tag=f"availability_{at}"
                rec={"baseline_sha256":SHA,"lo":at,"hi":at+1,"entry_proof_start":lo,
                     "old":[line],"new":cand,"saved_static":1,
                     "proof":"exact ANF at replacement point on all 62 unconstrained entry bits; prior HMR/R reset values modeled", "anf_terms":len(want),
                     "clear_by_mbu":clear,"phase":"HMR outcome times a*b canceled exactly by conditional CZ" if clear else "all phase gates unchanged"}
                ART.mkdir(parents=True,exist_ok=True)
                (ART/(tag+".json")).write_text(json.dumps(rec,indent=2)+"\n")
                nc=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:at]+cand+ops[at+1:])+"\n"),format="kmx")
                nc.to_file(ART/(tag+".kmb"),format="kmb")
                rec.update(candidate_sha256=hashlib.sha256((ART/(tag+".kmb")).read_bytes()).hexdigest(),num_qubits=nc.num_qubits)
                (ART/(tag+".json")).write_text(json.dumps(rec,indent=2)+"\n")
                hits.append(rec)
                print("AVAILABILITY",at,"from",lo,"Q",nc.num_qubits,"new",cand,flush=True)
            nonlinear.append(at)
    summary={"attempted":attempted,"capped":capped,"hits":len(hits)}
    print("AVAILABILITY_SUMMARY",json.dumps(summary),flush=True)
    return summary


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO(); c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    header = [l for l in lines if l.startswith(("REGISTER", "APPEND_TO_REGISTER"))]
    ops = [l for l in lines if not l.startswith(("REGISTER", "APPEND_TO_REGISTER"))]
    blocks, cur = [], []
    for i, line in enumerate(ops):
        if line.split()[0] in ALLOWED and " if " not in line:
            cur.append(i)
        else:
            if cur: blocks.append(cur)
            cur = []
    if cur: blocks.append(cur)
    nwin, nmerge, proofs = 0, 0, []
    seen = set()
    for block in blocks:
        nn = [i for i in block if ops[i].split()[0] in ("CCX", "CSWAP")]
        for count in (2, 3, 4):
            for k in range(len(nn) - count + 1):
                lo, hi = nn[k], nn[k + count - 1] + 1
                if hi - lo > 500: continue
                nwin += 1
                old = ops[lo:hi]; gs, cliff = canonical(old)
                for a in range(len(gs)):
                    for b in range(a + 1, len(gs)):
                        if not all(commute(gs[b], gs[j]) for j in range(a + 1, b)):
                            continue
                        merged = merge(gs[a], gs[b])
                        if merged is None: continue
                        nmerge += 1
                        repl, linear = merged
                        ng = gs[:a] + repl + gs[a+1:b] + gs[b+1:]
                        cand = []
                        for j, g in enumerate(ng):
                            cand += emit_gate(g)
                            if j == a + len(repl) - 1:
                                for l, w in linear: cand += emit_linear(l, w)
                        if not repl:
                            cand = []
                            for j in range(len(gs)):
                                if j == a:
                                    for l, w in linear: cand += emit_linear(l, w)
                                if j not in (a,b): cand += emit_gate(gs[j])
                        cand += cliff
                        save = count - sum(l.startswith("CCX ") for l in cand)
                        if save <= 0: continue
                        key = (lo, hi, tuple(cand))
                        if key in seen: continue
                        seen.add(key)
                        try: equal = anf_run(old) == anf_run(cand)
                        except OverflowError: continue
                        if not equal:
                            print("INTERNAL_MISMATCH",lo,hi,a,b,flush=True)
                            continue
                        tag = f"affine_{lo}_{hi}_{len(proofs)}"
                        rec = {"baseline_sha256":SHA,"lo":lo,"hi":hi,"saved_static":save,
                               "old":old,"new":cand,"proof":"exact ANF, all 62 independent entry bits", "phase":"no phase or measurement gates in window"}
                        ART.mkdir(parents=True,exist_ok=True)
                        (ART/(tag+".json")).write_text(json.dumps(rec,indent=2)+"\n")
                        (ART/(tag+".kmx")).write_text("\n".join(cand)+"\n")
                        nc=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:lo]+cand+ops[hi:])+"\n"),format="kmx")
                        nc.to_file(ART/(tag+".kmb"),format="kmb")
                        rec.update(candidate_sha256=hashlib.sha256((ART/(tag+".kmb")).read_bytes()).hexdigest(),num_qubits=nc.num_qubits)
                        (ART/(tag+".json")).write_text(json.dumps(rec,indent=2)+"\n")
                        proofs.append(rec)
                        print("FOUND",tag,"saved",save,"Q",nc.num_qubits,"ops",len(old),"->",len(cand),flush=True)
                        if len(proofs)>=20:break
                    if len(proofs)>=20:break
                if len(proofs)>=20:break
            if len(proofs)>=20:break
        if len(proofs)>=20:break
    summary={"windows":nwin,"algebraic_merges":nmerge,"certified":len(proofs)}
    print("SUMMARY",json.dumps(summary),flush=True)
    availability=availability_search(header,ops)
    ART.mkdir(parents=True,exist_ok=True)
    (ART/"window_search.json").write_text(json.dumps({
        "baseline_sha256":SHA,"affine_transvection_search":summary,
        "local_anf_availability_search":availability,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope":"Exact local ANF/affine-frame identities; arbitrary independent entry wires. Capped ANFs are unknown. No lower bound on the original legal-input circuit.",
        "official_validation":"not run", "gain_claimed":False,
    },indent=2)+"\n")


if __name__ == "__main__":
    main()
