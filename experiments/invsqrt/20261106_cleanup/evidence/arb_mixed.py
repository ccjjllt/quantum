import io, re, json, subprocess, sys, time
from pathlib import Path
import kickmix as km
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')
c = km.Circuit.from_file(ROOT / 'artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb')
buf = io.StringIO(); c.to_file(buf, format='kmx')
lines = buf.getvalue().splitlines()
hdr = [l for l in lines if l.startswith(('APPEND', 'REGISTER'))]
ops = [l for l in lines if not l.startswith(('APPEND', 'REGISTER'))]
triples = [(16005,16030,16005,16018,16029),(16018,16039,16018,16029,16038),
           (16029,16046,16029,16038,16045),(16038,16051,16038,16045,16050),
           (16045,16061,16045,16050,16060),(16174,16191,16174,16189,16190),
           (16189,16207,16189,16190,16206),(16190,16253,16190,16206,16252)]
cands = [(0,'del-16005'),(0,'del16005-mod16018p3->q41'),(2,'del-16029'),
         (4,'del16050-mod16060p2->q26'),(3,'del16038-mod16045p3->q57')]
def support(a,b):
    s=set()
    for i in range(a,b):
        for t in ops[i].split()[1:]:
            if re.fullmatch(r'q\d+',t): s.add(t)
    return sorted(s)
for wid,kind in cands:
    a,b,p0,p1,p2 = triples[wid]
    m = re.match(r'del-?(\d+)(?:-mod(\d+)p(\d+)->(q\d+))?', kind)
    dpos = int(m.group(1))
    new=[]
    for i,l in enumerate(ops):
        if i==dpos: continue
        if m.group(2) and i==int(m.group(2)):
            pp=l.split(); pos=int(m.group(3)); tgt=m.group(4)
            parts=pp[1:4]
            assert parts[pos-1].startswith('q'), (i,l)
            l=' '.join([pp[0]]+[tgt if j+1==pos else t for j,t in enumerate(parts)])
        new.append(l)
    cand = km.Circuit.from_file(io.StringIO('\n'.join(hdr+new)+'\n'), format='kmx')
    out = ROOT/'artifacts/20261105_rotlp/proto_mix.kmb'
    cand.to_file(out, format='kmb')
    t0=time.time()
    r=subprocess.run([sys.executable,str(ROOT/'scripts/manual_verify.py'),'invsqrt',str(out),
                      '--salt','mix-%d'%dpos],capture_output=True,text=True,cwd=str(ROOT))
    try:
        js=json.loads(r.stdout); st,sc,er=js.get('status'),js.get('score'),js.get('error','')
    except Exception: st,sc,er='PARSE',None,r.stdout[-80:]
    print('%-34s %s score=%s %.1fs %s'%(kind,st,sc,time.time()-t0,er[:60]),flush=True)
