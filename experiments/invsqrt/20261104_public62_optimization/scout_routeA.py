"""Route A scout: non-contiguous 3CCX->2CCX rewrites (Kirill identity + Syed template).

Parent: migrated public62_nofallback KMB (actual bytes; no generator import).
Method:
 1. abstract the 7 applied templates to role patterns; verify all 5 Kirill share
    one abstract shape and both Syed share one abstract shape;
 2. scan parent for ordered non-contiguous embeddings: span<=48 ops, <=10 wires,
    uniform condition stack (no PUSH/POP/HMR/R/Z_POW/BIT_* inside), sandwiches
    quantum-wire-disjoint from pattern wires;
 3. rank by exact execution-probability upper bound (affine-rank billing over the
    real prefix forms) desc, position asc; dedupe overlapping spans; cap 32;
 4. prove each with Z3 local miter (outputs + phase, symbolic dirty wires and
    symbolic classical guards), 60s each, 30min cumulative; UNKNOWN on timeout.
Only strictly positive proven savings proceed to KMB construction (separate step).
"""
from __future__ import annotations
import argparse, hashlib, io, json, sys, time
from fractions import Fraction
from pathlib import Path
import kickmix as km

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261103_one_ccx"))
import audit_phase_cache as AP

PARENT = ROOT / "artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb"
TEMPL = HERE / "routeA_templates.json"
ART = ROOT / "artifacts/20261104_public62_optimization/invsqrt"
MAX_SPAN = 48
MAX_WIRES = 10
MAX_WINDOWS = 32
PROOF_TIMEOUT_MS = 60000
BUDGET_S = 1800.0
BARRIERS = ("HMR", "R", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
            "PUSH_CONDITION", "POP_CONDITION")


def qset(line):
    p = line.split()
    return {int(t[1:]) for t in p[1:] if t.startswith('q')}


def abstract_shape(gates, role_of):
    out = []
    for g in gates:
        p = g.split(); k = p[0]
        if k in ('CX', 'CCX'):
            out.append((k, tuple(role_of["q" + t[1:]] if False else None for t in [])) )
    return out


def shape_of(gates, wmap):
    """Map concrete gate list to (kind, role-tuple) using wire->role map."""
    out = []
    for g in gates:
        p = g.split(); k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k == 'CX': out.append(('CX', (wmap[qs[0]], wmap[qs[1]])))
        elif k == 'CCX': out.append(('CCX', (wmap[qs[0]], wmap[qs[1]], wmap[qs[2]])))
        elif k == 'X': out.append(('X', (wmap[qs[0]],)))
        elif k == 'Z': out.append(('Z', (wmap[qs[0]], p[-1])))
        else: out.append((k, tuple(qs)))
    return out


def self_test():
    """Positive control: synthetic non-contiguous embedding must match."""
    ref = json.loads(TEMPL.read_text())["kirill_identity"][0]["old"]
    wmap = {"q11": 1, "q40": 3, "q36": 5, "q10": 7, "q28": 9, "q16": 11, "q17": 13}
    syn = []
    for g in ref:
        p = g.split()
        syn.append(" ".join([p[0]] + ["q%d" % wmap[t] for t in p[1:] if t.startswith("q")]))
        syn.append("CX q60 q61")
    inv = {}
    pat = []
    for g in ref:
        p = g.split()
        pat.append((p[0], tuple(inv.setdefault(q, "r%d" % len(inv))
                               for q in [t for t in p[1:] if t.startswith("q")])))
    assign = {}
    pos = []
    si = 0
    for pk, prs in pat:
        found = None
        while si < len(syn):
            p = syn[si].split(); k = p[0]
            if k == pk:
                qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
                tmp = dict(assign)
                good = all(not (r in tmp and tmp[r] != w) for r, w in zip(prs, qs))
                for r, w in zip(prs, qs): tmp[r] = w
                good = good and len(set(tmp.values())) == len(tmp)
                if good:
                    assign.update(tmp); pos.append(si); si += 1; found = True; break
            si += 1
        if found is None: return False
    pw = set(assign.values())
    return all(not ({int(t[1:]) for t in syn[i].split()[1:] if t.startswith("q")} & pw)
               for i in range(pos[-1] + 1) if i not in pos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", type=Path, default=PARENT)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--max-windows", type=int, default=MAX_WINDOWS)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        ok = self_test()
        print("SELF_TEST_POSITIVE_CONTROL", "PASS" if ok else "FAIL", flush=True)
        return
    t0 = time.monotonic()
    raw = args.parent.read_bytes()
    print("PARENT_SHA", hashlib.sha256(raw).hexdigest(), flush=True)
    c = km.Circuit.from_file(args.parent)
    assert c.num_qubits == 62
    buf = io.StringIO(); c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]
    templ = json.loads(TEMPL.read_text())
    kir = templ["kirill_identity"]; sy = templ["syed_conditional"]

    def abstract(gates, roles):
        """gates: concrete template old-list; roles: dict var->rolename. Returns shape."""
        inv = {}
        seq = []
        for g in gates:
            p = g.split(); k = p[0]
            if k == 'CX':
                qs = [t for t in p[1:] if t.startswith('q')]
                seq.append(('CX', tuple(inv.setdefault(q, f"r{len(inv)}") for q in qs)))
            elif k == 'CCX':
                qs = [t for t in p[1:] if t.startswith('q')]
                seq.append(('CCX', tuple(inv.setdefault(q, f"r{len(inv)}") for q in qs)))
            elif k == 'X':
                seq.append(('X', (inv.setdefault(p[1], f"r{len(inv)}"),)))
            elif k == 'Z':
                seq.append(('Z', (inv.setdefault(p[1], f"r{len(inv)}"), 'GUARD')))
            else: raise ValueError(g)
        return seq, inv

    kir_shapes = [abstract(e["old"], e.get("variables") or {}) for e in kir]
    # The 5th Kirill window is the documented symmetric form (f=u(a+b)); group by shape.
    kir_groups = {}
    for (s, inv), e in zip(kir_shapes, kir):
        kir_groups.setdefault(json.dumps(s), []).append((e, inv))
    print("KIRILL_SHAPE_GROUPS", {k: len(v) for k, v in kir_groups.items()}, flush=True)
    sy_shapes = [abstract(e["old"], {}) for e in sy]
    assert sy_shapes[0][0] == sy_shapes[1][0], "syed shapes differ"
    SPAT, SINV = sy_shapes[0]
    print("SYED_PATTERN", SPAT, flush=True)

    # condition-stack tracking + barrier map
    stack_of = []
    st = []
    for l in ops:
        p = l.split()
        stack_of.append(tuple(st))
        if p[0] == 'PUSH_CONDITION': st.append(p[-1])
        elif p[0] == 'POP_CONDITION': st.pop()
    assert not st
    is_bar = [l.split()[0] in BARRIERS for l in ops]

    # prefix classical forms for execution-probability billing (BIT/HMR only)
    init = {}
    nvars = [0]
    forms = {}
    stack = []
    for l in ops:
        p = l.split(); k = p[0]
        if k == 'PUSH_CONDITION': stack.append(p[-1])
        elif k == 'POP_CONDITION': stack.pop()
        elif k in ('BIT_STORE0', 'BIT_STORE1', 'BIT_INVERT') and not stack:
            t = p[1]
            if k == 'BIT_STORE0': forms[t] = set()
            elif k == 'BIT_STORE1': forms[t] = {'ONE'}
            else: forms[t] = forms.get(t, {t}) ^ forms.get(p[-1], {p[-1]})
    print("PREFIX_FORMS bits:", len(forms), flush=True)

    import re
    def form_of(bitname):
        return forms.get(bitname, {bitname})

    def activation_prob(stack_tuple, guard_bit=None):
        rows = []
        for b in list(stack_tuple) + ([guard_bit] if guard_bit else []):
            f = form_of(b)
            # affine form as (mask over leaf index, const)
            assert 'ONE' not in f or len(f) == 1
            rows.append(f)
        # rank over GF2 with ONE as extra coordinate
        leaves = sorted({s for r in rows for s in r if s != 'ONE'})
        idx = {s: i for i, s in enumerate(leaves)}
        basis = {}
        for r in rows:
            mask = 0
            for s in r:
                if s != 'ONE': mask |= 1 << idx[s]
            rhs = 1 if 'ONE' in r else 0
            while mask:
                piv = mask.bit_length() - 1
                if piv not in basis: basis[piv] = (mask, rhs); break
                m2, r2 = basis[piv]; mask ^= m2; rhs ^= r2
            if not mask and rhs: return Fraction(0)
        return Fraction(1, 2 ** len(basis))

    kirill_pats = []  # (name, shape, ref_old, ref_new)
    for gi, (skey, members) in enumerate(kir_groups.items()):
        e0, _ = members[0]
        kirill_pats.append((f"kirill-{'AB'[gi] if gi < 2 else 'X'+str(gi)}",
                            json.loads(skey), e0["old"], e0["new"]))
    patterns = [(name, shape, ref_old, ref_new, 'kirill')
                for name, shape, ref_old, ref_new in kirill_pats]
    patterns.append(('syed', SPAT, sy[0]["old"], sy[0]["new"], 'syed'))
    print("PATTERNS", [(p[0], len(p[1])) for p in patterns], flush=True)

    def match_at(pat, start):
        """Try ordered embedding of pat within [start, start+48). Returns match or None."""
        span_end = min(len(ops), start + MAX_SPAN)
        seg = ops[start:span_end]
        base_stack = stack_of[start]
        # NOTE: barriers/stack are enforced on the actual matched span below,
        # not on the whole 48-block (a barrier beyond the match must not hide it).
        # backtracking embedding
        assign = {}
        used = {}
        pos = []
        si = 0
        need = list(pat)
        guard_name = None
        for pi, (pk, prs) in enumerate(need):
            found = None
            while si < len(seg):
                l = seg[si]; p = l.split(); k = p[0]
                if k == pk:
                    qs = [int(t[1:]) for t in p[1:] if t.startswith('q')]
                    ok = (len(qs) == len([r for r in prs if r != 'GUARD']) or
                          (pk in ('Z',) and len(qs) == 1))
                    if ok:
                        # try extend mapping
                        tmp = dict(assign)
                        good = True
                        for role, w in zip([r for r in prs if r != 'GUARD'], qs):
                            if role in tmp and tmp[role] != w: good = False; break
                            tmp[role] = w
                        # distinctness of pattern wires
                        if len(set(tmp.values())) != len(tmp): good = False
                        if good and pk == 'Z':
                            gb = p[-1]
                            if pi == 0: pass
                        if good:
                            assign.update(tmp); pos.append(si); si += 1
                            found = l; break
                si += 1
            if found is None: return None
        pat_idx = [start + i for i in pos]
        pat_wires = set(assign.values())
        # sandwiches: everything in [start, pat_idx[-1]] not in pat
        lo, hi = start, pat_idx[-1] + 1
        if hi - lo > MAX_SPAN: return None
        if any(is_bar[i] for i in range(lo, hi)): return None
        if any(stack_of[i] != base_stack for i in range(lo, hi)): return None
        sw = set()
        for i in range(lo, hi):
            if i in pat_idx: continue
            g = ops[i]; sw |= qset(g)
            # sandwiches must be phase/data neutral w.r.t. pattern: disjoint wires
            if sw & pat_wires: return None
        allw = set()
        for i in range(lo, hi): allw |= qset(ops[i])
        if len(allw) > MAX_WIRES: return None
        # guards: collect `if b` bits on pattern gates
        guards = {ops[i].split()[-1] for i in pat_idx if 'if' in ops[i].split()}
        return {'lo': lo, 'hi': hi, 'pat_idx': pat_idx, 'wires': sorted(allw),
                'pat_wires': sorted(pat_wires), 'stack': list(base_stack),
                'guards': sorted(guards), 'mapping': {v: k for k, v in assign.items()}}

    # find already-applied (new-form) sites to exclude overlaps
    applied = []
    for e in kir:
        nl = e["new"]
        for i in range(len(ops) - len(nl) + 1):
            if ops[i:i + len(nl)] == nl: applied.append((i, i + len(nl)))
    for e in sy:
        nl = e["new"]
        for i in range(len(ops) - len(nl) + 1):
            if ops[i:i + len(nl)] == nl: applied.append((i, i + len(nl)))
    print("APPLIED_SITES", len(applied), applied, flush=True)

    cands = []
    for name, shape, ref_old, ref_new, family in patterns:
        i = 0
        while i < len(ops):
            m = match_at(shape, i)
            if m is None: i += 1; continue
            # skip if span overlaps an applied site or an already-found candidate
            if any(not (m['hi'] <= a or m['lo'] >= b) for a, b in applied): i = m['lo'] + 1; continue
            if any(not (m['hi'] <= c['lo'] or m['lo'] >= c['hi']) for c in cands):
                i = m['lo'] + 1; continue
            # saving ub: 1 CCX * P(context active)
            p = activation_prob(tuple(m['stack']))
            m.update({'template': name, 'family': family, 'pattern': shape,
                      'ref_old': ref_old, 'ref_new': ref_new,
                      'prob_ub': str(p), 'prob_float': float(p)})
            cands.append(m)
            i = m['hi']
    cands.sort(key=lambda m: (-m['prob_float'], m['lo']))
    cands = cands[:args.max_windows]
    print("CANDIDATES", len(cands), flush=True)
    for m in cands:
        print(json.dumps({k: m[k] for k in ('template', 'lo', 'hi', 'prob_ub', 'stack', 'guards')}), flush=True)

    # prove in rank order
    import z3
    budget = BUDGET_S
    spent = 0.0
    results = []
    for m in cands:
        if spent >= budget: m['proof'] = {'result': 'UNKNOWN', 'reason': 'budget-exhausted'}; results.append(m); continue
        lo, hi = m['lo'], m['hi']
        old_span = ops[lo:hi]
        # build new span: replace pattern gates by template new-form with wire mapping
        wmap = m['mapping']  # wire -> role
        inv = {v: k for k, v in wmap.items()}  # role -> wire
        tmpl_new = m['ref_new']
        ref = m['ref_old']
        shape = m['pattern']
        pat_positions = set(m['pat_idx'])
        refvars = {}
        for rg, pg in zip(ref, shape):
            rp = rg.split()
            for tname, role in zip([t for t in rp[1:] if t.startswith('q')], pg[1]):
                if role == 'GUARD': continue
                refvars[tname] = inv[role]
        zguard = None
        if m['family'] == 'syed':
            # Z guard bit: find from matched old span Z line
            for i in m['pat_idx']:
                pp = ops[i].split()
                if pp[0] == 'Z': zguard = pp[-1]
        concrete = []
        for g in tmpl_new:
            p = g.split(); k = p[0]
            if k in ('CX', 'CCX', 'X'):
                qs = ['q%d' % refvars[t] for t in p[1:] if t.startswith('q')]
                # preserve order: controls then target as in template
                concrete.append(' '.join([k] + qs))
            elif k == 'Z':
                concrete.append(f"Z q{refvars[p[1]]} if {zguard}")
            else: raise ValueError(g)
        new_span_ordered = []
        inserted = False
        for i in range(lo, hi):
            if i in pat_positions and not inserted:
                new_span_ordered.extend(concrete); inserted = True
            elif i not in pat_positions:
                new_span_ordered.append(ops[i])
        assert inserted
        t_start = time.monotonic()
        solver = z3.Solver(); solver.set(timeout=PROOF_TIMEOUT_MS)
        nq = 62
        q0 = [z3.Bool(f'ra_q{w}') for w in range(nq)]
        q_old, b_old, st_old, ph_old, _, _ = AP.execute(old_span, list(q0), {}, prefix=False)
        q_new, b_new, st_new, ph_new, _, _ = AP.execute(new_span_ordered, list(q0), dict(b_old), prefix=False)
        assert not st_old and not st_new
        fail = z3.Or([a != b for a, b in zip(q_old, q_new)] + [ph_old != ph_new])
        row = AP.check(solver, fail, f"routeA {m['template']} [{lo},{hi})")
        dt = time.monotonic() - t_start
        spent += dt
        m['proof'] = row
        m['new_span_len'] = len(new_span_ordered)
        m['budget_spent_s'] = spent
        results.append(m)
        print(json.dumps({'lo': lo, 'hi': hi, 'proof': row, 'spent': spent}), flush=True)

    verdict = 'NEGATIVE' if not any(r.get('proof', {}).get('result') == 'unsat' and
                                    r['prob_float'] > 0 for r in results) else 'HAS_CANDIDATE'
    out = {'parent_sha256': hashlib.sha256(raw).hexdigest(), 'qubits': 62,
           'applied_sites': applied, 'candidates': results, 'verdict': verdict,
           'budget_spent_s': spent, 'seconds': time.monotonic() - t0}
    op = args.output or (ART / "routeA_scout.json")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1) + "\n")
    print("VERDICT", verdict, "spent", round(spent, 1), flush=True)


if __name__ == "__main__":
    main()
