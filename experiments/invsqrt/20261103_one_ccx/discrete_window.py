"""Manual bit-packed screen for exact cheap gate replacements in public invsqrt.

Screen output is hypotheses only, never an equivalence certificate. No verifier
or submission is invoked. Keep the public input immutable.
"""
from __future__ import annotations
import argparse, hashlib, io, json, random
from pathlib import Path
import kickmix

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"

def load():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    c = kickmix.Circuit.from_file(BASE)
    f = io.StringIO(); c.to_file(f, format="kmx")
    return [s for s in f.getvalue().splitlines() if not s.startswith(("APPEND", "REGISTER"))]

def screen(n=4096, seed=107, cache=False):
    rng = random.Random(seed)
    xs = list(range(1, min(n//4, 1024)+1))
    xs += [x for k in range(22) for x in ((1<<k)-1,1<<k,(1<<k)+1) if 1<=x<=3133452]
    xs += [rng.randint(1,3133452) for _ in range(n-len(xs))]
    n = len(xs); allbits=(1<<n)-1
    q=[sum(((x>>j)&1)<<i for i,x in enumerate(xs)) for j in range(22)]+[0]*40
    bits={}; stack=[]; found=[]; ops=load();records=[];mentions=[];exec_masks=[];phase_records=[]
    for i,line in enumerate(ops):
        p=line.split(); k=p[0]
        mentions.append(set(int(t[1:]) for t in p[1:] if t.startswith('q')))
        exec_masks.append(0)
        if k=='PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),0));continue
        if k=='POP_CONDITION':
            if stack:stack.pop()
            continue
        active=allbits
        for a in stack:active &= a
        if 'if' in p:active &= bits.get(int(p[p.index('if')+1][1:]),0)
        exec_masks[-1]=active
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if cache and k=='CCX' and active and not active&q[qs[2]]:
            records.append({'op':i,'pair':tuple(sorted(qs[:2])),'target':qs[2],
                            'active':active,'prod':q[qs[0]]&q[qs[1]],'q':list(q),'depth':len(stack)})
        if cache and k=='CCZ' and active:
            for a,b,c in ((qs[0],qs[1],qs[2]),(qs[0],qs[2],qs[1]),(qs[1],qs[2],qs[0])):
                phase_records.append({'op':i,'pair':tuple(sorted((a,b))),'target':c,
                                      'active':active,'prod':q[a]&q[b],'q':list(q),'depth':len(stack)})
        if k in ('CCX','CCZ','CSWAP') and active:
            a,b,c=qs
            options=[]
            if k=='CCX':
                prod=q[a]&q[b]
                if not active&prod:options.append('delete')
                if not active&(prod^q[c]):options.append('HMR_UNCOMPUTE')
                if active.bit_count()>=min(1024,n//2):
                    basis={}; cols=[j for j in range(62) if j!=c]+[-1]
                    for ci,j in enumerate(cols):
                        v=(q[j] if j>=0 else allbits)&active; combo=1<<ci
                        while v:
                            pivot=v.bit_length()-1
                            if pivot not in basis:basis[pivot]=(v,combo);break
                            bv,bc=basis[pivot];v^=bv;combo^=bc
                    v=(prod^q[c])&active;combo=0
                    while v:
                        pivot=v.bit_length()-1
                        if pivot not in basis:break
                        bv,bc=basis[pivot];v^=bv;combo^=bc
                    if not v and combo.bit_count()<=6:
                        linear=[str(cols[j]) for j in range(len(cols)) if (combo>>j)&1]
                        options.append('HMR_LINEAR:'+','.join(linear))
                for w in range(62):
                    if w==c:continue
                    if not active&(prod^q[w]):options.append(f'CX q{w} q{c}')
            elif k=='CCZ':
                prod=q[a]&q[b]&q[c]
                if not active&prod:options.append('delete')
                for u in range(62):
                    if not active&(prod^q[u]):options.append(f'Z q{u}')
                    for v in qs:
                        if u!=v and not active&(prod^(q[u]&q[v])):options.append(f'CZ q{u} q{v}')
            elif not active&q[a]&(q[b]^q[c]):options.append('delete')
            if options:found.append({'op':i,'line':line,'active_samples':active.bit_count(),'options':options})
        if k=='X':q[qs[0]]^=active
        elif k=='CX':q[qs[1]]^=active&q[qs[0]]
        elif k=='CCX':q[qs[2]]^=active&q[qs[0]]&q[qs[1]]
        elif k in ('SWAP','CSWAP'):
            a,b=qs[-2:];m=active if k=='SWAP' else active&q[qs[0]]
            d=(q[a]^q[b])&m;q[a]^=d;q[b]^=d
        elif k in ('R','HMR'):
            q[qs[0]]&=allbits^active
            if k=='HMR':
                b=int(p[2][1:]);bits[b]=(bits.get(b,0)&(allbits^active))|(rng.getrandbits(n)&active)
        elif k.startswith('BIT_'):
            b=int(p[1][1:]);old=bits.get(b,0)
            bits[b]=old^active if k=='BIT_INVERT' else ((old&~active) if k=='BIT_STORE0' else old|active)
    if cache:
        pairs=[]
        def busy_under_source(r,t):
            return set().union(*(mentions[ii] for ii in range(r['op']+1,t['op']+1)
                                 if r['active']&exec_masks[ii]))
        for i,r in enumerate(records):
            for t in records[i+1:]:
                if t['op']-r['op']>10000:break
                common=r['active']&t['active']
                if common.bit_count()<n/64 or common&(r['prod']^t['prod']):continue
                if (common&r['prod']).bit_count()<8:continue
                busy=busy_under_source(r,t);busy|=set(r['pair']);busy.add(r['target'])
                free=[j for j in range(62) if j not in busy and not r['active']&r['q'][j]]
                if free:pairs.append({'src':r['op'],'copy':t['op'],'pair':r['pair'],'copy_pair':t['pair'],'src_target':r['target'],'copy_target':t['target'],'fraction':common.bit_count()/n,'free':free,'depths':[r['depth'],t['depth']]})
        phase_pairs=[]
        for r in phase_records:
            for t in records:
                if t['op']<=r['op'] or t['op']-r['op']>10000:continue
                common=r['active']&t['active']
                if common.bit_count()<n/256 or common&(r['prod']^t['prod']):continue
                if (common&r['prod']).bit_count()<8:continue
                busy=busy_under_source(r,t);busy|=set(r['pair']);busy.add(r['target'])
                free=[j for j in range(62) if j not in busy and not r['active']&r['q'][j]]
                if free:phase_pairs.append({'src':r['op'],'copy':t['op'],'pair':r['pair'],'copy_pair':t['pair'],'src_third':r['target'],'copy_target':t['target'],'fraction':common.bit_count()/n,'free':free,'depths':[r['depth'],t['depth']]})
        pairs += [{'phase_source':True,**r} for r in phase_pairs]
        for r in records:
            for t in phase_records:
                if t['op']<=r['op'] or t['op']-r['op']>10000:continue
                common=r['active']&t['active']
                if common.bit_count()<n/256 or common&(r['prod']^t['prod']):continue
                if (common&r['prod']).bit_count()<8:continue
                busy=busy_under_source(r,t);busy|=set(r['pair']);busy.add(r['target'])
                free=[j for j in range(62) if j not in busy and not r['active']&r['q'][j]]
                if free:pairs.append({'phase_destination':True,'src':r['op'],'copy':t['op'],'pair':r['pair'],'copy_pair':t['pair'],'src_target':r['target'],'copy_third':t['target'],'fraction':common.bit_count()/n,'free':free,'depths':[r['depth'],t['depth']]})
        for r in phase_records:
            for t in phase_records:
                if t['op']<=r['op'] or t['op']-r['op']>10000:continue
                common=r['active']&t['active']
                if common.bit_count()<n/256 or common&(r['prod']^t['prod']):continue
                if (common&r['prod']).bit_count()<8:continue
                busy=busy_under_source(r,t);busy|=set(r['pair']);busy.add(r['target'])
                free=[j for j in range(62) if j not in busy and not r['active']&r['q'][j]]
                if free:pairs.append({'both_phase':True,'src':r['op'],'copy':t['op'],'pair':r['pair'],'copy_pair':t['pair'],'src_third':r['target'],'copy_third':t['target'],'fraction':common.bit_count()/n,'free':free,'depths':[r['depth'],t['depth']]})
        return {'seed':seed,'samples':n,'baseline_sha256':SHA,'status':'cache_screen_only','hypotheses':pairs}
    return {'seed':seed,'samples':n,'baseline_sha256':SHA,'status':'screen_only','hypotheses':found}

def prove_gate(op, replacement, timeout_ms=60000):
    """Exact legal-prefix SAT miter for changing just one Boolean/phase gate.

    Fresh SSA values constrain each update. Every HMR receives an independent
    symbolic outcome; saved PUSH values are expressions captured at PUSH.
    Phase-changing candidates here only change one diagonal gate, so proving
    its phase predicate identical suffices for all later trajectories.
    """
    import z3,time
    start=time.monotonic();ops=load();s=z3.Solver();s.set(timeout=timeout_ms)
    q=[z3.Bool(f'x{j}') for j in range(22)]+[z3.BoolVal(False)]*40
    bits={};stack=[];serial=0
    xv=z3.Sum([z3.If(q[j],1<<j,0) for j in range(22)])
    s.add(xv>=1,xv<=3133452)
    def fresh(expr):
        nonlocal serial
        ex=z3.simplify(expr)
        if z3.is_true(ex) or z3.is_false(ex):return ex
        out=z3.Bool(f't{serial}');serial+=1;s.add(out==ex);return out
    for i,line in enumerate(ops[:op+1]):
        p=line.split();k=p[0]
        if k=='PUSH_CONDITION':stack.append(bits.get(int(p[-1][1:]),z3.BoolVal(False)));continue
        if k=='POP_CONDITION':
            if stack:stack.pop()
            continue
        active=z3.And(*stack) if stack else z3.BoolVal(True)
        if 'if' in p:active=z3.And(active,bits.get(int(p[p.index('if')+1][1:]),z3.BoolVal(False)))
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if i==op:
            old=z3.And(*(q[j] for j in (qs if k=='CCZ' else qs[:2])))
            new=z3.BoolVal(False)
            if replacement=='HMR_UNCOMPUTE':new=q[qs[2]]
            elif replacement.startswith('HMR_LINEAR:'):
                new=q[qs[2]]
                for jj in replacement.split(':')[1].split(','):
                    if jj:new=z3.Xor(new,z3.BoolVal(True) if jj=='-1' else q[int(jj)])
            elif replacement!='delete':
                for part in replacement.split(';'):
                    rp=part.split();rqs=[int(t[1:]) for t in rp[1:] if t.startswith('q')]
                    term=z3.And(*(q[j] for j in (rqs if rp[0] in ('CZ','Z') else rqs[:1])))
                    new=z3.Xor(new,term)
            s.add(active,z3.Xor(old,new));break
        if k=='X':q[qs[0]]=fresh(z3.Xor(q[qs[0]],active))
        elif k=='CX':q[qs[1]]=fresh(z3.Xor(q[qs[1]],z3.And(active,q[qs[0]])))
        elif k=='CCX':q[qs[2]]=fresh(z3.Xor(q[qs[2]],z3.And(active,q[qs[0]],q[qs[1]])))
        elif k in ('SWAP','CSWAP'):
            a,b=qs[-2:];ctl=active if k=='SWAP' else z3.And(active,q[qs[0]])
            oa,ob=q[a],q[b];q[a]=fresh(z3.If(ctl,ob,oa));q[b]=fresh(z3.If(ctl,oa,ob))
        elif k in ('HMR','R'):
            q[qs[0]]=fresh(z3.And(q[qs[0]],z3.Not(active)))
            if k=='HMR':
                b=int(p[2][1:]);out=z3.Bool(f'm{i}');bits[b]=fresh(z3.If(active,out,bits.get(b,z3.BoolVal(False))))
        elif k.startswith('BIT_'):
            b=int(p[1][1:]);old=bits.get(b,z3.BoolVal(False))
            new=z3.Not(old) if k=='BIT_INVERT' else z3.BoolVal(k=='BIT_STORE1')
            bits[b]=fresh(z3.If(active,new,old))
    res=s.check();record={'op':op,'original':ops[op],'replacement':replacement,'verdict':str(res),'ssa_nodes':serial,'seconds':time.monotonic()-start,'baseline_sha256':SHA}
    if res==z3.sat:
        model=s.model();record['counterexample_x']=sum((1<<j) for j in range(22) if z3.is_true(model.eval(z3.Bool(f'x{j}'),model_completion=True)))
    return record

def tail_cache_candidate(extended=False):
    """Cache two ANDs on already-clean q34/q35 across two tail fixups."""
    B=load(); lo,hi=47113,47186
    tagged=[]
    for i in range(lo,hi):
        if i==47123 and extended:
            tagged += [(i,'CCX q19 q11 q36'),(None,'CZ q36 q10')]
        elif i==47160 and extended:
            tagged += [(None,'CX q36 q20 if b320'),(i,'CCX q19 q11 q20 if b90001')]
        elif i==47158:
            tagged += [(None,'BIT_STORE1 b90001'),(None,'BIT_INVERT b90001 if b320'),
                       (None,'CX q34 q32 if b320'),(i,'CCX q18 q13 q32 if b90001')]
        elif i==47159:
            tagged += [(None,'CX q35 q19 if b320'),(i,'CCX q32 q12 q19 if b90001')]
        else:tagged.append((i,B[i]))
        if i==47122:tagged += [(None,'CX q32 q34'),(None,'CX q19 q35')]
    cleanup=['PUSH_CONDITION if b320','X q13','X q12']
    if extended:cleanup+=['X q11','HMR q36 b90004','CZ q35 q11 if b90004','X q11']
    cleanup += [
                                 'HMR q35 b90002','CZ q34 q12 if b90002',
                                 'HMR q34 b90003','CZ q18 q13 if b90003',
                                 'X q12','X q13','POP_CONDITION']
    tagged += [(None,l) for l in cleanup]
    assert not any(f'b{b}' in l.split() for b in (90001,90002,90003,90004) for l in B)
    return lo,hi,tagged

def prove_tail_cache(extended=False):
    """All-input/all-measurement local proof, with four explicit clean wires.

    q34/q35 last touched by unconditional HMR at 44933/45347. q32 last
    unconditional reset 44506, then only three CCX/HMR pairs under identical
    saved conditions. q19 is unconditionally HMR-reset at 46869; both later
    blocks begin with R and end with HMR under the same saved outer condition.
    The separate zero-entry proof covers these mechanical preconditions.
    """
    import z3,time
    B=load();lo,hi,tagged=tail_cache_candidate(extended); started=time.monotonic()
    inputs=[z3.Bool(f'entry_q{j}') for j in range(62)]
    for j in ((19,32,34,35,36) if extended else (19,32,34,35)):inputs[j]=z3.BoolVal(False)
    binputs={b:z3.Bool(f'entry_b{b}') for b in (320,8045,8046)}
    def run(items,entryq,entrystack=()):
        q=list(entryq);bits=dict(binputs);stack=list(entrystack);phase=z3.BoolVal(False);cost=[];newserial=0
        for origid,line in items:
            p=line.split();k=p[0]
            def bit(b):return bits.setdefault(b,z3.Bool(f'entry_b{b}'))
            if k=='PUSH_CONDITION':stack.append(bit(int(p[-1][1:])));continue
            if k=='POP_CONDITION':
                if stack:stack.pop()
                continue
            active=z3.And(*stack) if stack else z3.BoolVal(True)
            if 'if' in p:active=z3.And(active,bit(int(p[p.index('if')+1][1:])))
            qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
            if k in ('CCX','CCZ','CSWAP'):cost.append(active)
            if k=='X':q[qs[0]]=z3.Xor(q[qs[0]],active)
            elif k=='CX':q[qs[1]]=z3.Xor(q[qs[1]],z3.And(active,q[qs[0]]))
            elif k=='CCX':q[qs[2]]=z3.Xor(q[qs[2]],z3.And(active,q[qs[0]],q[qs[1]]))
            elif k in ('Z','CZ','CCZ','NEG'):
                phase=z3.Xor(phase,z3.And(active,*(q[j] for j in qs)))
            elif k in ('HMR','R'):
                ev=z3.Bool(f'm_{origid}') if origid is not None else z3.Bool(f'new_m_{newserial}')
                if origid is None:newserial+=1
                phase=z3.Xor(phase,z3.And(active,q[qs[0]],ev))
                q[qs[0]]=z3.And(q[qs[0]],z3.Not(active))
                if k=='HMR':
                    b=int(p[2][1:]);bits[b]=z3.If(active,ev,bit(b))
            elif k in ('BIT_STORE0','BIT_STORE1','BIT_INVERT'):
                b=int(p[1][1:]);old=bit(b);nv=z3.Not(old) if k=='BIT_INVERT' else z3.BoolVal(k=='BIT_STORE1')
                bits[b]=z3.If(active,nv,old)
            else:raise ValueError(line)
        return q,bits,stack,phase,cost
    initialstack=[binputs[8045],binputs[8046]]
    qo,bo,so,po,co=run(list(enumerate(B[lo:hi],lo)),inputs,initialstack)
    qn,bn,sn,pn,cn=run(tagged,inputs,initialstack)
    differences=[z3.Xor(a,b) for a,b in zip(qo,qn)]+[z3.Xor(po,pn)]
    differences += [z3.Xor(v,bn[b]) for b,v in bo.items()]
    differences += [z3.Xor(a,b) for a,b in zip(so,sn)]
    solver=z3.Solver();solver.set(timeout=60000);solver.add(z3.Or(*differences));result=solver.check()
    # Check the four clean-entry assumptions independently over suffixes from
    # the respective unconditional HMR, using arbitrary other wire/bit values.
    zeros={}
    clean_sites=[(19,46869),(32,44506),(34,44933),(35,45347)]
    if extended:
        stack=[];last=None
        for ii,line in enumerate(B[:lo]):
            pp=line.split()
            if pp[0]=='PUSH_CONDITION':stack.append(pp[-1])
            elif pp[0]=='POP_CONDITION':
                if stack:stack.pop()
            elif pp[0]=='HMR' and pp[1]=='q36' and not stack and 'if' not in pp:last=ii
        assert last is not None
        clean_sites.append((36,last))
    for wire,start in clean_sites:
        assert B[start].startswith(f'HMR q{wire} ')
        # q32/q34/q35 have no writes until the short tail; the read-only phase
        # correction region may alter other wires but cannot dirty them.
        boundary=46869
        if wire!=19:
            for ii in range(start+1,boundary):
                pp=B[ii].split();kk=pp[0];w=[int(t[1:]) for t in pp[1:] if t.startswith('q')]
                writes=w[-1:] if kk in ('X','CX','CCX','HMR','R') else w if kk in ('SWAP','CSWAP') else []
                assert wire not in writes,(wire,ii,B[ii])
        init=[z3.Bool(f'zero{wire}_q{j}') for j in range(62)];init[wire]=z3.BoolVal(False)
        # Start after the outer-independent q19 HMR. Other scratch values may
        # be arbitrary; reset+same-guard HMR restores the target in each branch.
        qz,_,_,_,_=run(list(enumerate(B[boundary+1:lo],boundary+1)),init)
        zs=z3.Solver();zs.set(timeout=60000);zs.add(qz[wire]);zr=zs.check();zeros[str(wire)]=str(zr)
    stem='tail_cache_three_and' if extended else 'tail_cache_two_and'
    record={'baseline_sha256':SHA,'window':[lo,hi],'local_miter':str(result),'clean_entry_proofs':zeros,'seconds':time.monotonic()-started,'expected_equivalent_saving':0.1875 if extended else 0.125,'status':'local_proof_only'}
    if result==z3.unsat and all(v=='unsat' for v in zeros.values()):
        header=['APPEND_TO_REGISTER q%d r0'%j for j in range(22)]+['REGISTER r0 "x"']
        candidate=B[:lo]+[l for _,l in tagged]+B[hi:]
        c=kickmix.Circuit.from_file(io.StringIO('\n'.join(header+candidate)+'\n'),format='kmx')
        out=ART/(stem+'.kmb');c.to_file(out,format='kmb')
        record.update(candidate=str(out),candidate_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),qubits=c.num_qubits,added_hmr=3 if extended else 2,static_ccx_delta=1 if extended else 0,static_ccz_delta=-1 if extended else 0)
    (ART/(stem+'_proof.json')).write_text(json.dumps(record,indent=2)+'\n')
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--samples',type=int,default=4096);ap.add_argument('--seed',type=int,default=107);ap.add_argument('--prove-op',type=int);ap.add_argument('--replacement');ap.add_argument('--tail-cache',action='store_true');ap.add_argument('--tail-cache-extended',action='store_true');ap.add_argument('--cache-screen',action='store_true');args=ap.parse_args()
    if args.tail_cache or args.tail_cache_extended:
        print(json.dumps(prove_tail_cache(args.tail_cache_extended),indent=2));return
    if args.prove_op is not None:
        result=prove_gate(args.prove_op,args.replacement)
        (ART/f'discrete_proof_{args.prove_op}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return
    result=screen(args.samples,args.seed,args.cache_screen)
    ART.mkdir(parents=True,exist_ok=True)
    (ART/('cache_screen.json' if args.cache_screen else 'discrete_screen.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in result.items() if k!='hypotheses'},
                      'n_hypotheses':len(result['hypotheses']),
                      'first_hypotheses':result['hypotheses'][:5]},indent=2))

if __name__=='__main__':main()
