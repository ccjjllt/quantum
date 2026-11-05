"""Static Maoxin V2 invsqrt audit and bounded local symbolic diagnostics.

Reads literal public gate data, never executes notebook Python. No hashes,
full official verification, submission, or claim of a global lower bound.
"""
from __future__ import annotations
import ast
import bisect
import collections
import io
import json
import re
from pathlib import Path
import kickmix as km

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/20261105_maoxin_v2/invsqrt'
BASE=ROOT/'artifacts/20261105_maoxin_v2/release/invsqrt.kmb'


def load(path):
    c=km.Circuit.from_file(path);b=io.StringIO();c.to_file(b,format='kmx')
    return c,[l for l in b.getvalue().splitlines() if not l.startswith(('APPEND','REGISTER'))]


def literals():
    nb=json.loads((ART/'sources/kirill_four_v10.ipynb').read_text())
    wanted={'OLD_GATE_DATA','NEW_GATE_DATA','QIU_INTEGRATION','FULL_REPORTS','V7_REPORTS','V8_REPORTS','V9_REPORTS'}
    out={}
    for c in nb['cells']:
        if c['cell_type']!='code':continue
        for n in ast.parse(c['source']).body:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in wanted:
                out[n.targets[0].id]=ast.literal_eval(n.value)
    return out


def mul(a,b):
    result=set()
    for x in a:
        for y in b:
            m=x|y
            if m in result:result.remove(m)
            else:result.add(m)
    return result


def anf(lines):
    q=[{1<<i} for i in range(62)];peak=1
    for line in lines:
        p=line.split();assert 'if' not in p
        w=[int(t[1:]) for t in p[1:]]
        if p[0]=='X':q[w[0]]^={0}
        elif p[0]=='CX':q[w[1]]^=q[w[0]]
        elif p[0]=='CCX':q[w[2]]^=mul(q[w[0]],q[w[1]])
        else:raise ValueError(line)
        peak=max(peak,*(len(x) for x in q))
    return q,peak


def find(ops,part):
    return [i for i,l in enumerate(ops) if l==part[0] and ops[i:i+len(part)]==part]


def zero_hmr_scan(ops):
    # Conservative affine expressions with opaque nonlinear products. Equal
    # symbolic expressions imply equal functions; missed equalities are allowed.
    # This follows the public free-coin idea, reimplemented locally for a census.
    serial=62;products={};one=frozenset({0});zero=frozenset()
    def unknown():
        nonlocal serial
        serial+=1;return frozenset({serial})
    def product(a,b):
        if not a or not b:return zero
        if a==one:return b
        if b==one or a==b:return a
        key=frozenset((a,b))
        if key not in products:products[key]=unknown()
        return products[key]
    q=[frozenset({i+1}) if i<22 else zero for i in range(62)]
    stack=[];found=[]
    for i,line in enumerate(ops):
        p=line.split();k=p[0]
        if k=='PUSH_CONDITION':stack.append(q.copy());continue
        if k=='POP_CONDITION':
            before=stack.pop();q=[a if a==b else unknown() for a,b in zip(before,q)];continue
        w=[int(t[1:]) for t in p[1:] if re.fullmatch(r'q\d+',t)]
        if k=='HMR' and not q[w[0]] and not stack and 'if' not in p:
            found.append(dict(index=i,instruction=line,next_instruction=ops[i+1],already_forced_zero=ops[i+1]=='BIT_STORE0 '+p[2]))
        before=q.copy()
        if k=='X':q[w[0]]^=one
        elif k=='CX':q[w[1]]^=q[w[0]]
        elif k=='CCX':q[w[2]]^=product(q[w[0]],q[w[1]])
        elif k in ('HMR','R'):q[w[0]]=zero
        elif k=='SWAP':q[w[0]],q[w[1]]=q[w[1]],q[w[0]]
        elif k=='CSWAP':
            a,b=w[-2:];d=product(q[w[0]],q[a]^q[b]);q[a]^=d;q[b]^=d
        elif k not in ('Z','CZ','CCZ','NEG','Z_POW','BIT_STORE0','BIT_STORE1','BIT_INVERT','INFO_TAG'):raise ValueError(line)
        if 'if' in p:q=[a if a==b else unknown() for a,b in zip(before,q)]
    assert not stack
    return found


def census(ops):
    gates=[l.split() for l in ops];paid=[i for i,p in enumerate(gates) if p[0] in ('CCX','CCZ','CSWAP')]
    stack=[];stacks=[]
    for p in gates:
        stacks.append(tuple(stack))
        if p[0]=='PUSH_CONDITION':stack.append(p[-1])
        elif p[0]=='POP_CONDITION':stack.pop()
    rows=[]
    for a,b,c in zip(paid,paid[1:],paid[2:]):
        win=gates[a:c+1]
        if sum(p[0]=='HMR' for p in win)!=1:continue
        if any(p[0] in ('Z_POW','R','BIT_STORE0','BIT_STORE1','BIT_INVERT','PUSH_CONDITION','POP_CONDITION') for p in win):continue
        if any(s!=stacks[a] for s in stacks[a:c+1]):continue
        wires={int(t[1:]) for p in win for t in p[1:] if re.fullmatch(r'q\d+',t)}
        if len(wires)>10:continue
        rows.append(dict(window=[a,c+1],paid_indices=[a,b,c],types=[gates[j][0] for j in (a,b,c)],wire_count=len(wires),unconditional=not stacks[a] and all('if' not in gates[j] for j in (a,b,c)),instructions=ops[a:c+1]))
    rows.sort(key=lambda r:(r['window'][1],r['window'][0]));ends=[r['window'][1] for r in rows];dp=[(0,0,[])]
    for i,row in enumerate(rows):
        prev=dp[bisect.bisect_right(ends,row['window'][0],0,i)]
        take=(prev[0]+1,prev[1]+int(row['unconditional']),prev[2]+[i]);skip=dp[-1]
        dp.append(take if take[:2]>skip[:2] else skip)
    selected=[rows[i] for i in dp[-1][2]]
    return dict(scope='Geometric 3-paid-gate/one-HMR/<=10-wire census; no synthesis or gain proof',qualified=len(rows),nonoverlapping=len(selected),unconditional=sum(r['unconditional'] for r in selected),guarded=sum(not r['unconditional'] for r in selected),selected_type_histogram=dict(collections.Counter('/'.join(r['types']) for r in selected)),template_ceiling_C=len(selected),selected=selected)


def coin_dependencies(ops,row):
    bit=row['instruction'].split()[2];reads=[];paid=[];stack=[];next_write=None
    for i in range(row['index']+1,len(ops)):
        p=ops[i].split();k=p[0]
        if (k=='HMR' and p[2]==bit) or (k in ('BIT_STORE0','BIT_STORE1','BIT_INVERT') and p[1]==bit):
            next_write=i;break
        if bit in p:reads.append(dict(index=i,instruction=ops[i]))
        # No transfers from these particular free coins to another classical bit.
        assert not (bit in p and k.startswith('BIT_'))
        if k=='PUSH_CONDITION':stack.append(p[-1]);continue
        if k=='POP_CONDITION':
            if stack:stack.pop()
            continue
        depends=bit in stack or ('if' in p and p[-1]==bit)
        if depends and k in ('CCX','CCZ','CSWAP','Z_POW'):paid.append(dict(index=i,instruction=ops[i]))
    return dict(bit=bit,next_write=next_write,read_count=len(reads),reads=reads,dependent_paid_operations=paid,dependent_paid_count=len(paid),scope='Exact reads until next write; no classical transfers observed. Z/CZ/NEG are free in this metric.')


def main():
    c,ops=load(BASE);d=literals();stats=c.operation_statistics();audit={}
    for name,before,after in [('syed_decode',d['OLD_GATE_DATA'],d['NEW_GATE_DATA']),('qiu_quadratic',d['QIU_INTEGRATION']['old_gate_data'],d['QIU_INTEGRATION']['new_gate_data'])]:
        old,po=anf(before);new,pn=anf(after)
        same=old==new
        audit[name]=dict(arbitrary_62_wire_ANF_equal=same,old_ops=len(before),new_ops=len(after),old_CCX=sum(l.startswith('CCX') for l in before),new_CCX=sum(l.startswith('CCX') for l in after),peak_terms=max(po,pn))
        if name=='qiu_quadratic':
            assert same
            neg=[l for i,l in enumerate(after) if i!=next(j for j,x in enumerate(after) if x.startswith('CCX'))]
            broken,_=anf(neg);assert broken!=old
            audit[name]['negative_dropped_CCX_rejected']=True
        else:
            assert not same
            diff={str(i):len(a^b) for i,(a,b) in enumerate(zip(old,new)) if a!=b}
            witness=1<<15
            differences=[i for i,(a,b) in enumerate(zip(old,new)) if sum((m&witness)==m for m in a^b)%2]
            assert differences==[50]
            audit[name].update(differing_ANF_term_counts=diff,arbitrary_boundary_counterexample='q15=1, all other boundary qubits=0; output q50 differs',scope='This is not an arbitrary-dirty-input identity. Does not show a reachable competition input failure; its prefix contract needs separate proof.')
    syed=d['NEW_GATE_DATA'];qold=d['QIU_INTEGRATION']['old_gate_data'];qnew=d['QIU_INTEGRATION']['new_gate_data']
    hits=find(syed,qold);assert len(hits)==1
    j=hits[0];combined=syed[:j]+qnew+syed[j+len(qold):]
    locations=find(ops,combined);assert len(locations)==1
    audit['combined_public_window']=dict(location=locations[0],length=len(combined),old_CCX=5,new_CCX=2,already_in_maoxin=True)
    rotations=[l for l in ops if l.startswith('Z_POW')]
    zero=zero_hmr_scan(ops)
    for row in zero:row['cost_dependencies']=coin_dependencies(ops,row)
    assert all(not row['cost_dependencies']['dependent_paid_count'] for row in zero if not row['already_forced_zero'])
    target_index=next(row['index'] for row in zero if row['instruction']=='HMR q21 b417')
    negative_ops=ops[:target_index]+['X q21']+ops[target_index:]
    assert not any(row['instruction']=='HMR q21 b417' for row in zero_hmr_scan(negative_ops))
    report=d['FULL_REPORTS']['invsqrt']
    effective=report['toffoli_equivalent'];direct=report['toffoli_count'];small=report['t_count']/4;rot=effective-direct-small
    predicted=report['score']-61.99976348876953
    summary=dict(scope='Actual Maoxin V2 static/local diagnostics; author full report quoted separately; no hashes or full official run',actual=dict(qubits=c.num_qubits,bits=c.num_bits,ops=len(ops),statistics=dict(stats),static_toffoli_like=stats.num_toffoli_like,Z_POW_count=len(rotations)),author_full_report=report,phase_free_window_proofs=audit,conservative_zero_HMR=zero,zero_scan_negative_control_rejected=True,unforced_proven_zero_HMR=sum(not r['already_forced_zero'] for r in zero),remaining_proven_zero_coin_paid_savings=0,census=census(ops),cost_composition_from_author_report=dict(direct_Toffoli=direct,T_over_4=small,general_rotation_equivalent=rot,general_rotation_fraction=rot/effective),selector_projection=dict(cost=predicted,subtask_reduction_percent=61.99976348876953/report['score']*100,overall_GM_increase_percent=((report['score']/predicted)**(1/3)-1)*100,scope='Exact local expectation saving applied to a different authors sample cost; projection only'))
    (ART/'research_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('census','author_full_report')},indent=2))
    print(json.dumps({k:v for k,v in summary['census'].items() if k!='selected'},indent=2))


if __name__=='__main__':main()
