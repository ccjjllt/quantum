"""Independent audit for Kirill-V5 nofallback migration (actual bytes).

Reads the real Kirill baseline KMB and the migrated candidate KMB.
Does NOT import the migration generator. Verifies:
 1. byte audit: 62Q, header, Z_POW order, window-only replacement, fresh-bit lifecycle;
 2. exact branch ANF (output restore, 1 CCX, HMR cancel, q21-phases) + negative control;
 3. affine failure forms: f2=f0^f1, rank 2, triple-failure UNSAT, per-branch residuals;
 4. generic semantics of the two original selectors (Z3, 60s each);
 5. new-prefix 65-claim contract (Z3, 60s each);
 6. exact affine-rank billing: old window 2-2^-18, new window 1.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.metadata, io, json, platform, sys, time
from fractions import Fraction
from pathlib import Path
import kickmix as km
import z3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261103_one_ccx"))
import audit_phase_cache as AP

BASE = ROOT / "artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb"
BASE_SHA = "ed77292a0e4a267e62235055cc2ab7faaa30b15d8a150bab79f34e5c1b8f172b"
CAND = ROOT / "artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb"
ART = ROOT / "artifacts/20261104_public62_optimization/invsqrt"
LO, MID, LO2, HI = 27745, 28183, 28315, 28753
PRE1 = (27613, 27745)
PRE2 = (28183, 28315)
F_BITS = [42006, 42007, 42008]
S_BITS = [42009, 42010, 42011]
H_BITS = [42012, 42013, 42014]
WORDS = [14, 16, 17, 19, 20, 22, 29, 30, 31, 25, 26, 45, 46, 47, 48, 52, 55, 56, 58]


def load(path):
    raw = path.read_bytes()
    c = km.Circuit.from_file(path)
    buf = io.StringIO(); c.to_file(buf, format="kmx")
    hdr, ops = [], []
    for line in buf.getvalue().splitlines():
        (hdr if line.startswith(("APPEND", "REGISTER")) else ops).append(line)
    return c, hdr, ops, hashlib.sha256(raw).hexdigest()


def mul(a, b):
    out = set()
    for x in a:
        for y in b:
            z = x | y
            if z in out: out.remove(z)
            else: out.add(z)
    return out


def branch_anf(lines):
    entry = [{1 << q} if q not in (28, 40) else set() for q in range(62)]
    q = [set(v) for v in entry]; phase = {}; measurements = []; ccx = 0
    for line in lines:
        p = line.split(); k = p[0]; qs = [int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k in ('X', 'CX', 'CCX', 'HMR'):
            assert 'if' not in p, ('conditional data in successful branch', line)
        if k == 'CX': q[qs[1]] ^= q[qs[0]]
        elif k == 'CCX': q[qs[2]] ^= mul(q[qs[0]], q[qs[1]]); ccx += 1
        elif k == 'HMR':
            key = 'NEW_OUT_' + p[2]; measurements.append(p[2]); phase[key] = phase.get(key, set()) ^ q[qs[0]]
            q[qs[0]] = set()
        elif k in ('Z', 'CZ'):
            assert 'if' in p
            bit = p[-1]; key = 'NEW_OUT_' + bit if bit in measurements else bit
            poly = {0}
            for wire in qs: poly = mul(poly, q[wire])
            phase[key] = phase.get(key, set()) ^ poly
        else: raise ValueError(('unexpected success-branch operation', line))
    assert q == entry, 'successful branch failed exact output restoration'
    assert len(measurements) == 1 and ccx == 1
    assert all(not poly for key, poly in phase.items() if key.startswith('NEW_OUT_')), 'HMR phase not cancelled'
    phase = {k: v for k, v in phase.items() if v and not k.startswith('NEW_OUT_')}
    assert all(m & (1 << 21) for poly in phase.values() for m in poly), 'phase may remain when q21=0'
    return phase, {'all_62_output_ANFs_identical': True,
                   'new_HMR_phase_coefficients_zero': True,
                   'all_phase_monomials_contain_q21': True,
                   'executed_Toffoli_like_if_selected': 1,
                   'new_measurement_bits': measurements,
                   'phase_monomials_per_source': {k: len(v) for k, v in phase.items()}}


def eval_poly(poly, columns):
    ans = 0
    for monomial in poly:
        term = (1 << 63) - 1
        while monomial:
            bit = monomial & -monomial; term &= columns[bit.bit_length() - 1]; monomial ^= bit
        ans ^= term
    return ans


def check_residuals(phase, failure, sources, columns, target):
    residual = None
    for source in sorted(sources):
        diff = eval_poly(phase.get(source, set()), columns) ^ target[source]
        if source not in failure:
            assert diff == 0, ('unexpected phase residual', source)
        elif residual is None: residual = diff
        else: assert diff == residual, ('inconsistent residual', source)
    assert residual is not None
    return residual


def affine_rank(rows):
    basis = {}
    for mask, rhs in rows:
        while mask:
            pivot = mask.bit_length() - 1
            if pivot not in basis: basis[pivot] = (mask, rhs); break
            other, value = basis[pivot]; mask ^= other; rhs ^= value
        if not mask and rhs: return None
    return len(basis)


def probability(rows):
    r = affine_rank(rows); return Fraction(0) if r is None else Fraction(1, 2 ** r)


def classical_cost(lines, initial, nvars):
    bits, stack, charges = dict(initial), [], []
    for i, line in enumerate(lines):
        p = line.split(); kind = p[0]
        cond = bits[int(p[-1][1:])] if "if" in p else (0, 1)
        if kind == "PUSH_CONDITION": stack.append(cond)
        elif kind == "POP_CONDITION": stack.pop()
        elif kind.startswith("BIT_"):
            assert not stack, (i, line, stack)
            target = int(p[1][1:])
            if kind == "BIT_INVERT":
                old = bits.get(target, (0, 0)); bits[target] = (old[0] ^ cond[0], old[1] ^ cond[1])
            else:
                assert "if" not in p; bits[target] = (0, int(kind == "BIT_STORE1"))
        elif kind == "HMR":
            target = int(p[2][1:]); assert target not in bits; bits[target] = (1 << nvars, 0); nvars += 1
        elif kind in ("CCX", "CCZ"):
            forms = stack + ([cond] if "if" in p else [])
            rows = [(mask, 1 ^ const) for mask, const in forms]
            prob = probability(rows)
            charges.append({"offset": i, "instruction": line,
                            "rank": affine_rank(rows), "probability": str(prob)})
        else: assert kind in ("CX", "CZ", "X", "Z"), (i, line)
    assert not stack
    return bits, charges, sum((Fraction(c["probability"]) for c in charges), Fraction(0))


def find_subseq(hay, needle, start=0):
    n = len(needle)
    for i in range(start, len(hay) - n + 1):
        if hay[i:i + n] == needle: return i
    return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, default=CAND)
    ap.add_argument("--baseline", type=Path, default=BASE)
    ap.add_argument("--baseline-sha", type=str, default=BASE_SHA)
    args = ap.parse_args()
    started = time.monotonic()
    bc, bh, base, bsha = load(args.baseline)
    cc, ch, cand, csha = load(args.candidate)
    assert bsha == args.baseline_sha == BASE_SHA, bsha
    assert bc.num_qubits == cc.num_qubits == 62 and bh == ch
    assert [l for l in base if l.startswith("Z_POW")] == [l for l in cand if l.startswith("Z_POW")]
    assert len(base) == 48088
    # fresh bits unused in baseline; old b42002..b42005 present
    import re
    base_big = {int(m) for l in base for m in re.findall(r"b(\d+)", l) if int(m) >= 42006}
    assert not base_big, sorted(base_big)
    # locate joint via anchor base[HI:HI+10]
    anchor = base[HI:HI + 10]
    joint_end = find_subseq(cand, anchor, LO)
    assert joint_end > LO, "joint_end not found"
    joint_new = cand[LO:joint_end]
    assert cand[:LO] == base[:LO], "prefix mismatch"
    assert cand[joint_end:] == base[HI:], "suffix mismatch"
    print(f"WINDOW_REPLACED old_len {HI-LO} new_len {len(joint_new)} joint_end {joint_end}", flush=True)
    assert joint_new[:PRE2[1] - PRE2[0]] == base[PRE2[0]:PRE2[1]], "second prep not preserved"
    first_push = next(i for i, l in enumerate(joint_new) if l.startswith("PUSH_CONDITION"))
    classical = joint_new[:first_push]
    assert all(l.startswith("BIT_") for l in classical)
    pos = first_push
    branches = []
    for j in range(3):
        assert joint_new[pos] == f"PUSH_CONDITION if b{S_BITS[j]}", (j, joint_new[pos])
        end = next(i for i in range(pos + 1, len(joint_new)) if joint_new[i] == "POP_CONDITION")
        body = joint_new[pos + 1:end]
        assert not any(l.startswith("PUSH_CONDITION") for l in body)
        branches.append(body)
        assert joint_new[end + 1] == f"PUSH_CONDITION if b{F_BITS[j]}", (j, joint_new[end + 1])
        pos = end + 2
    assert joint_new[pos:] == ["POP_CONDITION"] * 3, joint_new[pos:pos + 5]
    print("STRUCTURE_OK 3 branches no fallback", flush=True)
    # simulator truth on new prefix
    prefix = km.Circuit.from_file(io.StringIO("\n".join(bh + base[:LO]) + "\n"), format="kmx")
    sim = km.Simulator(batch_size=63, seed=314159); sim.use_same_registers_as(prefix)
    for i in range(63): sim.write_within_shot('x', i, i + 1)
    sim.do(prefix)
    columns = [sum(int(v) << i for i, v in enumerate(sim.read_across_shots(km.q(q)))) for q in range(62)]
    assert columns[21] == (1 << 63) - 1 and columns[28] == columns[40] == 0
    prep1 = AP.affine_classical(base[PRE1[0]:LO])
    forms = AP.affine_classical(classical, prep1)
    coeffs = [[f'b{24256+i}' for i in range(19)], [f'b{24320+i}' for i in range(19)]]
    word_groups = [[int(l.split()[3][1:]) for l in base[a:b] if l.startswith('CCZ ')]
                   for a, b in ((LO, MID), (LO2, HI))]
    assert all(len(w) == 19 for w in word_groups), word_groups
    sources = set().union(*(forms[c] for group in coeffs for c in group))
    assert 'ONE' not in sources
    guards = [columns[18] & columns[21], columns[27] & columns[21]]
    target = {s: 0 for s in sources}
    for group, words, guard in zip(coeffs, word_groups, guards):
        for c, w in zip(group, words):
            for s in forms[c]: target[s] ^= guard & columns[w]
    failure_forms = []
    for j in range(3):
        f = forms[f'b{F_BITS[j]}']
        assert f <= sources
        assert forms[f'b{S_BITS[j]}'] == f ^ {'ONE'}
        failure_forms.append(f)
    assert (failure_forms[0] ^ failure_forms[1] ^ failure_forms[2]) == set(), "xor not zero"
    assert AP.gf2_rank(failure_forms) == 2, "expected rank 2"
    print("FAILURE_XOR_ZERO rank 2", flush=True)
    branch_records = []
    for j, body in enumerate(branches):
        failure = forms[f'b{F_BITS[j]}']
        phase, proof = branch_anf(body)
        assert set(phase) <= sources
        residual = check_residuals(phase, failure, sources, columns, target)
        proof.update({'branch': j, 'failure_parity_sources': sorted(failure),
                      'residual_x': [i + 1 for i in range(63) if residual >> i & 1]})
        branch_records.append(proof)
    print("BRANCH_PHASES_OK", flush=True)
    # negative control: drop one correction gate from branch 0 -> full check must fail
    drop = next(k for k, m in enumerate(branches[0]) if m.startswith("CZ q21"))
    neg_ok = False
    try:
        phase_b, _ = branch_anf([l for k, l in enumerate(branches[0]) if k != drop])
        check_residuals(phase_b, forms['b42006'], sources, columns, target)
    except (AssertionError, ValueError):
        neg_ok = True
    assert neg_ok, "negative control did not fail"
    print("NEGATIVE_CONTROL_OK broken correction rejected", flush=True)
    # generic selector semantics on original window
    selector_records = []
    for j, (start, stop, cstart, guardwire) in enumerate(((LO, MID, 24256, 18), (LO2, HI, 24320, 27))):
        qs = [z3.Bool(f'generic{j}_q{k}') for k in range(62)]
        cbits = {f'b{cstart+i}': z3.Bool(f'generic{j}_coef{i}') for i in range(19)}
        cbits.update({f'b{cstart+19+i}': z3.Not(cbits[f'b{cstart+i}']) for i in range(19)})
        cbits[f'b{cstart+38}'] = z3.BoolVal(False)
        q, bits, stack, phase, cost, _ = AP.execute(base[start:stop], qs, cbits)
        assert not stack
        wanted = z3.BoolVal(False)
        for i, w in enumerate(word_groups[j]): wanted = z3.Xor(wanted, z3.And(cbits[f'b{cstart+i}'], qs[w]))
        wanted = z3.And(qs[guardwire], qs[21], wanted)
        fail = z3.Or([a != b for a, b in zip(q, qs)] + [phase != wanted, cost != z3.If(
            z3.Or([cbits[f'b{cstart+i}'] for i in range(19)]), 1, 0)])
        solver = z3.Solver(); solver.set(timeout=60000)
        selector_records.append(AP.check(solver, fail, f'original selector {j}'))
    # prefix audit: 65 claims
    def prefix_audit():
        solver = z3.Solver(); solver.set(timeout=60000)
        x = z3.BitVec('joint_ssa_input_x', 22)
        solver.add(z3.UGE(x, 1), z3.ULE(x, 3133452))
        q0 = [z3.Extract(i, i, x) == 1 for i in range(22)] + [z3.BoolVal(False)] * 40
        count = 0
        def define(e):
            nonlocal count
            e = z3.simplify(e)
            if z3.is_true(e) or z3.is_false(e): return e
            b = z3.Bool(f'joint_ssa_{count}'); count += 1; solver.add(b == e); return b
        q, bits, stack, _, _, events = AP.execute(base[:LO], q0, definition=define, prefix=True)
        assert not stack
        claims = [AP.check(solver, z3.And(q[21], z3.UGE(x, 64)), 'q21 implies x<=63', x),
                  AP.check(solver, z3.Or(q[28], q[40]), 'q28/q40 zero', x)]
        for value in range(1, 64):
            mismatch = z3.Or([q[w] != z3.BoolVal(bool(columns[w] >> (value - 1) & 1)) for w in range(62)])
            claims.append(AP.check(solver, z3.And(x == value, mismatch), f'x={value}', x))
        return {'ssa_nodes': count, 'measurement_variables': events, 'claims': claims,
                'status': 'PASS' if all(r['result'] == 'unsat' for r in claims) else 'NOT_PROVEN'}
    pref = prefix_audit()
    print("PREFIX", pref['status'], flush=True)
    # triple failure impossible
    src_vars = {s: z3.Bool(f'src_{s}') for s in sources}
    def parity(form):
        v = z3.BoolVal(False)
        for s in form: v = z3.Xor(v, src_vars[s])
        return v
    s = z3.Solver(); s.add(parity(failure_forms[0]), parity(failure_forms[1]), parity(failure_forms[2]))
    assert str(s.check()) == "unsat", "triple failure reachable"
    print("TRIPLE_FAILURE_UNSAT", flush=True)
    # exact billing
    KNOWN_29 = ["b350", "b351", "b358", "b359", "b363", "b364", "b371", "b372", "b366",
                "b367", "b374", "b375", "b610", "b368", "b365", "b373", "b353", "b354",
                "b361", "b362", "b355", "b357", "b369", "b356", "b360", "b370", "b352",
                "b611", "b612"]
    init = {int(b[1:]): (1 << j, 0) for j, b in enumerate(KNOWN_29)}
    tmp, _, _ = classical_cost(base[PRE1[0]:LO], dict(init), len(KNOWN_29))
    _, old_charges, old_cost = classical_cost(base[LO:HI], dict(tmp), len(KNOWN_29))
    _, new_charges, new_cost = classical_cost(joint_new, dict(tmp), len(KNOWN_29))
    print(f"BILLING old {old_cost} new {new_cost} saving {old_cost - new_cost}", flush=True)
    assert old_cost == Fraction(2, 1) - Fraction(1, 2 ** 18), old_cost
    assert new_cost == Fraction(1, 1), new_cost
    status = 'PASS' if all(r['result'] == 'unsat' for r in selector_records) and pref['status'] == 'PASS' else 'NOT_PROVEN'
    out = ART / "audit_migrated.json"
    result = {'status': status, 'baseline_sha256': bsha, 'candidate_sha256': csha,
              'qubits': 62, 'replaced_window': [LO, HI], 'joint_new_len': len(joint_new),
              'fresh_bits': {'failure': F_BITS, 'select': S_BITS, 'hmr': H_BITS},
              'branch_records': branch_records, 'selector_semantics': selector_records,
              'prefix_audit': pref, 'triple_failure': 'unsat',
              'negative_control': 'PASS' if neg_ok else 'FAIL',
              'billing': {'old_window_cost': str(old_cost), 'new_window_cost': str(new_cost),
                          'saving_C': str(old_cost - new_cost),
                          'saving_decimal': float(old_cost - new_cost),
                          'old_charge_count': len(old_charges), 'new_charge_count': len(new_charges)},
              'metadata': {'seconds': time.monotonic() - started, 'python': platform.python_version(),
                           'kickmix': importlib.metadata.version('kickmix'),
                           'z3': z3.get_version_string()}}
    out.write_text(json.dumps(result, indent=2) + "\n")
    print('FINAL_RESULT ' + json.dumps({'status': result['status'], 'path': str(out)}), flush=True)
    return 0 if status == 'PASS' else 1


if __name__ == "__main__":
    raise SystemExit(main())
