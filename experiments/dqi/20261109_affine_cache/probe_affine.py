"""Probe: affine-canonical product repeat census (read-only, no circuit edit)."""
import kickmix as km, io, collections, json, sys

c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/dqi.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
lines=buf.getvalue().splitlines()
stack=[]; stage_of=[None]*len(lines)
for i,l in enumerate(lines):
    if l.startswith('INFO_TAG '):
        tag=l.strip().split('"',2)[1]
        if tag.startswith('@enter:'): stack.append(tag[7:])
        elif tag.startswith('@exit:') and stack: stack.pop()
        continue
    stage_of[i]=stack[0] if stack else 'header'

def pq(t): return int(t[1:])

for stage in ['unextract','unsynthesis']:
    mask={}; const={}; dirty=set()
    # init basis at stage entry: all 892 qubits symbolic
    for q in range(892):
        mask[q]=1<<q; const[q]=0
    n_ccx=0; n_bothclean=0; n_cond=0
    key_count=collections.Counter()   # strict (with const)
    keymask_count=collections.Counter() # ignoring consts (complement-folded)
    lit_count=collections.Counter()
    first_seen={}; first_seen_m={}
    for i,l in enumerate(lines):
        if stage_of[i]!=stage: continue
        if not l or l.startswith(('APPEND','REGISTER','INFO_TAG','SEMANTIC','ANNOTATION')): continue
        cond = ' if ' in l
        p=l.split()
        op=p[0]
        if op=='X' and len(p)>=2 and p[1][0]=='q' and 'if' not in p:
            q=pq(p[1])
            if q in dirty: pass
            else: const[q]^=1
        elif op=='CX' and len(p)>=3 and p[1][0]=='q':
            a=pq(p[1]); b=pq(p[2])
            has_if = 'if' in p
            if has_if:
                dirty.add(b)
                mask.pop(b,None)
            else:
                if a in dirty or b in dirty:
                    dirty.add(b); mask.pop(b,None)
                else:
                    mask[b]^=mask[a]; const[b]^=const[a]
        elif op=='SWAP' and len(p)>=3:
            a=pq(p[1]); b=pq(p[2])
            mask[a],mask[b]=mask.get(b,1<<b),mask.get(a,1<<a)
            const[a],const[b]=const.get(b,0),const.get(a,0)
            da=a in dirty; db=b in dirty
            if da and not db: dirty.add(b)
            elif db and not da: dirty.add(a)
            elif not da and not db:
                dirty.discard(a); dirty.discard(b)
        elif op in ('HMR',) and len(p)>=2 and p[1][0]=='q':
            q=pq(p[1]); mask[q]=0; const[q]=0; dirty.discard(q)
        elif op=='R' and len(p)>=2 and p[1][0]=='q':
            q=pq(p[1]); mask[q]=0; const[q]=0; dirty.discard(q)
        elif op=='CCX' and len(p)>=4 and p[1][0]=='q':
            a=pq(p[1]); b=pq(p[2]); t=pq(p[3])
            has_if='if' in p
            if has_if:
                n_cond+=1
                dirty.add(t); mask.pop(t,None)
                continue
            n_ccx+=1
            lit_count[tuple(sorted((a,b)))]+=1
            if a not in dirty and b not in dirty:
                n_bothclean+=1
                ka=(mask[a],const[a]); kb=(mask[b],const[b])
                key=tuple(sorted((ka,kb)))
                key_count[key]+=1
                km_=(mask[a],mask[b])
                km_=tuple(sorted(km_))
                keymask_count[km_]+=1
            # target becomes nonlinear
            dirty.add(t); mask.pop(t,None)
        elif op=='CSWAP':
            # conservative: mark swapped targets dirty
            try:
                cc=pq(p[1]); aa=pq(p[2]); bb=pq(p[3])
                dirty.add(aa); dirty.add(bb); mask.pop(aa,None); mask.pop(bb,None)
            except: pass
        # CZ/CCZ/Z/BIT/NEG/PUSH/POP: no computational effect
    print(f"== {stage}: unconditional CCX={n_ccx} bothclean={n_bothclean} condCCX={n_cond}")
    print(f"   distinct strict keys={len(key_count)} repeated(strict,>=2): {sum(1 for k,v in key_count.items() if v>=2)} occ={sum(v for k,v in key_count.items() if v>=2)}")
    print(f"   distinct mask keys={len(keymask_count)} repeated(mask,>=2): {sum(1 for k,v in keymask_count.items() if v>=2)} occ={sum(v for k,v in keymask_count.items() if v>=2)}")
    print(f"   literal repeats: distinct={len(lit_count)} repkeys={sum(1 for k,v in lit_count.items() if v>=2)} occ={sum(v for k,v in lit_count.items() if v>=2)}")
    # top repeated
    print("   top-10 mask-key repeats:", keymask_count.most_common(10))
