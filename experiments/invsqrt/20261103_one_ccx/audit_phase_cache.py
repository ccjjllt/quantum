"""Independent manual proof of the actual last-phase-selector KMB patch.

No imports from phase_cache.py or the older symbolic proof code. Reads the two
KMBs, reconstructs the actual change, builds a separate full-prefix SSA model,
and checks an exact all-branch local phase/data/cost contract. No official
verifier runs here. Artifacts include executable command, versions and hashes.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import importlib.metadata
import io
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import kickmix as km
import z3

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
CAND = ART / "phase_last_selector.kmb"
BASE_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
CAND_SHA = "e30937769d6245c405e9933336e57e8d1701aeb0d67e42dc0133f490a4fbbabe"
PREP, LO, HI = 28213, 28345, 28783
COEFF = [f"b{24320+i}" for i in range(19)]
AGG = ["b41000", "b41001", "b41002"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    raw = path.read_bytes(); c = km.Circuit.from_file(path)
    buf = io.StringIO(); c.to_file(buf, format="kmx")
    header, ops = [], []
    for line in buf.getvalue().splitlines():
        (header if line.startswith(("APPEND", "REGISTER")) else ops).append(line)
    canonical = io.BytesIO(); c.to_file(canonical, format="kmb")
    assert sha(raw) == sha(canonical.getvalue())
    return c, header, ops, sha(raw)


def initial_bit(name):
    return z3.Bool("local_entry_" + name)


def execute(lines, initial_q, initial_bits=None, definition=None, prefix=False):
    """Independent Boolean data interpreter, with pi-phase parity in local mode."""
    q = list(initial_q); bits = dict(initial_bits or {}); stack = []
    phase = z3.BoolVal(False); cost = z3.IntVal(0)
    versions = collections.Counter()
    def define(value):
        return definition(value) if definition else value
    def bit(name):
        return bits.setdefault(name, z3.BoolVal(False) if prefix else initial_bit(name))
    for index, line in enumerate(lines):
        p = line.split(); kind = p[0]
        if kind == "PUSH_CONDITION":
            stack.append(bit(p[-1])); continue
        if kind == "POP_CONDITION":
            assert stack, (index, "condition underflow")
            stack.pop(); continue
        active = z3.And(stack + ([bit(p[-1])] if "if" in p else []))
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        if kind == "X":
            q[qs[0]] = define(z3.If(active, z3.Not(q[qs[0]]), q[qs[0]]))
        elif kind == "CX":
            q[qs[1]] = define(z3.Xor(q[qs[1]], z3.And(active, q[qs[0]])))
        elif kind == "CCX":
            q[qs[2]] = define(z3.Xor(q[qs[2]], z3.And(active, q[qs[0]], q[qs[1]])))
            if not prefix: cost += z3.If(active, 1, 0)
        elif kind in ("SWAP", "CSWAP"):
            a, b = qs[-2:]; ctl = active if kind == "SWAP" else z3.And(active, q[qs[0]])
            oa, ob = q[a], q[b]
            q[a], q[b] = define(z3.If(ctl, ob, oa)), define(z3.If(ctl, oa, ob))
            if not prefix and kind == "CSWAP": cost += z3.If(active, 1, 0)
        elif kind in ("HMR", "R"):
            assert prefix, "local window must contain no measurement"
            if kind == "HMR":
                name = p[2]; version = versions[name]; versions[name] += 1
                outcome = z3.Bool(f"prefix_out_{name}_v{version}")
                bits[name] = define(z3.If(active, outcome, bit(name)))
            q[qs[0]] = define(z3.If(active, z3.BoolVal(False), q[qs[0]]))
        elif kind in ("BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
            old = bit(p[1])
            new = z3.Not(old) if kind == "BIT_INVERT" else z3.BoolVal(kind == "BIT_STORE1")
            bits[p[1]] = define(z3.If(active, new, old))
        elif kind in ("Z", "CZ", "CCZ", "NEG", "Z_POW"):
            if not prefix:
                assert kind != "Z_POW", "exact parity only supports local pi phases"
                phase = z3.Xor(phase, z3.And([active] + [q[j] for j in qs]))
                if kind == "CCZ": cost += z3.If(active, 1, 0)
        elif kind != "INFO_TAG":
            raise ValueError((index, line))
    return q, bits, stack, phase, cost, sum(versions.values())


def check(solver, negated_claim, label, x=None):
    start = time.monotonic(); solver.push(); solver.add(negated_claim)
    verdict = solver.check()
    row = {"label": label, "result": str(verdict), "seconds": time.monotonic()-start}
    if verdict == z3.unknown: row["reason"] = solver.reason_unknown()
    if verdict == z3.sat:
        row["counterexample"] = str(solver.model()) if x is None else int(solver.model().eval(x).as_long())
    solver.pop(); print(json.dumps(row), flush=True)
    return row


def prefix_claims(base, words, truth):
    solver = z3.Solver(); solver.set(timeout=60000)
    x = z3.BitVec("audit_input_x", 22)
    solver.add(z3.UGE(x, 1), z3.ULE(x, 3133452))
    q0 = [z3.Extract(i, i, x) == 1 for i in range(22)] + [z3.BoolVal(False)] * 40
    serial = 0
    def define(expression):
        nonlocal serial
        expression = z3.simplify(expression)
        if z3.is_true(expression) or z3.is_false(expression): return expression
        out = z3.Bool(f"audit_ssa_{serial}"); serial += 1
        solver.add(out == expression); return out
    q, bits, stack, _, _, events = execute(base[:LO], q0, definition=define, prefix=True)
    assert not stack
    claims = []
    claims.append(check(solver, z3.And(q[27], q[21], z3.UGE(x, 4)), "actual prefix guard implies x in {1,2,3}", x))
    for value in (1, 2, 3):
        mismatch = z3.Or([q[w] != z3.BoolVal(bool(truth[w] >> (value-1) & 1)) for w in words])
        claims.append(check(solver, z3.And(x == value, mismatch), f"all word values fixed for x={value}, arbitrary prefix measurement outcomes", x))
    invalid_coeff = [bits[f"b{24339+i}"] != z3.Not(bits[COEFF[i]]) for i in range(19)]
    invalid_coeff.append(bits["b24358"])
    claims.append(check(solver, z3.Or(invalid_coeff), "actual prefix complements and b24358=0", x))
    return {"input_domain": [1, 3133452], "input_encoding": "22-bit unsigned bit-vector",
            "ssa_nodes": serial, "free_measurement_events": events, "claims": claims}


def affine_classical(lines, initial=None):
    """Exact affine classical BIT operations; leaves are bit-name strings."""
    forms = {k: set(v) for k, v in (initial or {}).items()}; stack = []
    for line in lines:
        p=line.split(); kind=p[0]
        if kind == "PUSH_CONDITION": stack.append(p[-1]); continue
        if kind == "POP_CONDITION": stack.pop(); continue
        if not kind.startswith("BIT_"): continue
        assert not stack, "this candidate's aggregation writes must be unconditional"
        target=p[1]
        if kind == "BIT_STORE0":
            assert "if" not in p; forms[target]=set()
        elif kind == "BIT_STORE1":
            assert "if" not in p; forms[target]={"ONE"}
        elif kind == "BIT_INVERT":
            assert "if" in p and target in forms
            forms[target] ^= forms.get(p[-1], {p[-1]})
        else: raise ValueError(line)
    assert not stack
    return forms


def gf2_rank(rows):
    basis={}
    for row in rows:
        row=set(row)
        while row:
            pivot=max(row)
            if pivot not in basis:
                basis[pivot]=row;break
            row ^= basis[pivot]
    return len(basis)


def mask_distribution(base,new):
    forms=affine_classical(base[PREP:LO])
    for i,c in enumerate(COEFF): assert forms[f"b{24339+i}"] == forms[c] ^ {"ONE"}
    assert forms["b24358"] == set()
    rows=[forms[c] for c in COEFF]
    assert all("ONE" not in row for row in rows)
    leaves=set().union(*rows)
    stack=[];last={}
    for i,line in enumerate(base[:PREP]):
        p=line.split();k=p[0]
        if k=="PUSH_CONDITION":stack.append(p[-1])
        elif k=="POP_CONDITION":stack.pop()
        elif k=="HMR":last[p[2]]={"op":i,"kind":k,"unconditional":not stack and "if" not in p}
        elif k.startswith("BIT_"):last[p[1]]={"op":i,"kind":k,"unconditional":not stack and "if" not in p}
    assert not stack
    assert all(last[b]["kind"]=="HMR" and last[b]["unconditional"] for b in leaves)
    assert len({last[b]["op"] for b in leaves})==len(leaves)
    transformed=affine_classical(new,forms)
    new_rows=[transformed["b41001"],transformed["b41002"]]
    assert all("ONE" not in row for row in new_rows)
    old_rank,new_rank=gf2_rank(rows),gf2_rank(new_rows)
    return {"old_rank":old_rank,"new_rank":new_rank,
            "old_masks":{c:sorted(forms[c]) for c in COEFF},
            "new_masks":{b:sorted(transformed[b]) for b in AGG},
            "independent_unconditional_HMR_sources":{b:last[b] for b in sorted(leaves)},
            "expected_old_toffoli_like":1-2.0**(-old_rank),
            "expected_new_toffoli_like":1-2.0**(-new_rank),
            "expected_saving":2.0**(-new_rank)-2.0**(-old_rank),
            "probability_assumption":"independent unbiased HMR outcomes conditional on each legal x"}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--prove",action="store_true",required=True);ap.parse_args()
    started=time.monotonic()
    bc,bh,base,bsha=read(BASE);cc,ch,cand,csha=read(CAND)
    assert bsha==BASE_SHA and csha==CAND_SHA
    assert bc.num_qubits==cc.num_qubits==62 and bh==ch
    cut=len(cand)-(len(base)-HI)
    assert base[:LO]==cand[:LO] and base[HI:]==cand[cut:]
    old,new=base[LO:HI],cand[LO:cut]
    assert not any(l.startswith(("HMR ","R ","Z_POW ")) for l in old+new)
    zpow_equal=[l for l in base if l.startswith("Z_POW ")]==[l for l in cand if l.startswith("Z_POW ")]
    assert zpow_equal
    old_bits={t for l in base for t in l.split() if t.startswith('b') and t[1:].isdigit()}
    new_bits={t for l in cand for t in l.split() if t.startswith('b') and t[1:].isdigit()}
    assert new_bits-old_bits == {"b41000","b41001","b41002","b41003"}
    words=[int(l.split()[3][1:]) for l in old if l.startswith("CCZ ")]
    assert len(words)==len(set(words))==19
    assert all(l.split()[1:3]==["q27","q21"] for l in old if l.startswith('CCZ '))
    # Independently obtain only the three proposed rows, then prove each for
    # all prefix measurement outcomes below. A sample never serves as proof.
    prefix=km.Circuit.from_file(io.StringIO('\n'.join(bh+base[:LO])+'\n'),format='kmx')
    sim=km.Simulator(batch_size=3,seed=20261103);sim.use_same_registers_as(prefix)
    for i,value in enumerate((1,2,3)):sim.write_within_shot('x',i,value)
    sim.do(prefix)
    truth={w:sum(int(v)<<i for i,v in enumerate(sim.read_across_shots(km.q(w)))) for w in words}
    agg=affine_classical(new,{c:{c} for c in COEFF})
    assert all(agg[b]<=set(COEFF) for b in AGG)
    reps={w:sum((1<<j) for j,b in enumerate(AGG) if c in agg[b]) for w,c in zip(words,COEFF)}
    basis=(14,16)
    for w,mask in reps.items():
        row=(7 if mask&1 else 0) ^ (truth[14] if mask&2 else 0) ^ (truth[16] if mask&4 else 0)
        assert row==truth[w],(w,mask,truth[w],row)
    pref=prefix_claims(base,words,truth)
    q0=[z3.Bool(f'local_q{j}') for j in range(62)]
    bits={c:z3.Bool(c) for c in COEFF}
    bits.update({f'b{24339+i}':z3.Not(bits[c]) for i,c in enumerate(COEFF)})
    bits['b24358']=z3.BoolVal(False)
    qo,bo,so,po,co,_=execute(old,q0,bits)
    qn,bn,sn,pn,cn,_=execute(new,q0,bits)
    assert not so and not sn
    relations=[];guard=z3.And(q0[27],q0[21])
    for w,mask in reps.items():
        rhs=z3.BoolVal(bool(mask&1))
        if mask&2:rhs=z3.Xor(rhs,q0[basis[0]])
        if mask&4:rhs=z3.Xor(rhs,q0[basis[1]])
        relations.append(z3.Implies(guard,q0[w]==rhs))
    solver=z3.Solver();solver.set(timeout=60000);solver.add(relations)
    diffs=[z3.Xor(a,b) for a,b in zip(qo,qn)]+[z3.Xor(po,pn)]
    diffs += [z3.Xor(bo.get(b,initial_bit(b)),bn.get(b,initial_bit(b))) for b in (set(bo)|set(bn))&old_bits]
    local=check(solver,z3.Or(diffs),'actual local KMB window: all qubits, old classical bits, exact phase and balanced stack')
    solver=z3.Solver();solver.set(timeout=60000)
    expected_old=z3.If(z3.Or([bits[c] for c in COEFF]),1,0)
    expected_new=z3.If(z3.Or(bn['b41001'],bn['b41002']),1,0)
    cost=check(solver,z3.Or(co!=expected_old,cn!=expected_new),'exact execution count formula for every classical coefficient assignment')
    distribution=mask_distribution(base,new)
    pass_all=all(x['result']=='unsat' for x in pref['claims']) and local['result']==cost['result']=='unsat'
    result={"status":"PASS" if pass_all else "NOT_PROVEN", "scope":"independent full-prefix contract plus local all-branch composition; not official verification",
            "baseline_sha256":bsha,"candidate_sha256":csha,"qubits":62,"extra_qubits":0,
            "baseline_window":[LO,HI],"candidate_window":[LO,cut],"unchanged_prefix_and_suffix":True,
            "all_zpow_instructions_identical":zpow_equal,"added_measurements":0,
            "actual_old_window":old,"actual_new_window":new,"word_truth_proposals":truth,"word_representations":reps,
            "prefix_proof":pref,"local_equivalence":local,"cost_formula":cost,"distribution":distribution,
            "metadata":{"timestamp":datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),"python":platform.python_version(),
                        "kickmix":importlib.metadata.version('kickmix'),"z3":z3.get_version_string(),
                        "command":"uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/audit_phase_cache.py --prove",
                        "cwd":str(ROOT),"argv":sys.argv,"script_sha256":sha(Path(__file__).read_bytes()),
                        "seconds":time.monotonic()-started,"official_verifier_shots":0,"discovery_sample_shots":3}}
    ART.mkdir(parents=True,exist_ok=True);out=ART/'audit_phase_cache.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({"status":result['status'],"candidate_sha256":csha,"expected_saving":distribution['expected_saving'],"artifact":str(out)}),flush=True)
    return 0 if pass_all else 1


if __name__=='__main__':raise SystemExit(main())
