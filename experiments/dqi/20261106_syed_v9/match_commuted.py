"""Match the proven Leo templates with arbitrary wire renaming/control swaps."""
import gc, json, re, time
from pathlib import Path
from inspect_migration import ROOT,OUT,export,truth

def bind(template,actual):
    pairs=[(a.split(),b.split()) for a,b in zip(template,actual)]
    states=[{}]
    for a,b in pairs:
        nxt=[]
        variants=[b]
        if b[0]=='CCX':variants.append([b[0],b[2],b[1],b[3]])
        if b[0]=='SWAP':variants.append([b[0],b[2],b[1]])
        for state in states:
            for bb in variants:
                d=dict(state);ok=True
                for old,new in zip(a[1:],bb[1:]):
                    if (old in d and d[old]!=new) or (old not in d and new in d.values()):ok=False;break
                    d[old]=new
                if ok:nxt.append(d)
        states=nxt
        if not states:return None
    return states[0]

def main():
    t0=time.monotonic();wins=json.loads((OUT/'leo_windows.json').read_text())
    c,raw=export(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb')
    results=[]
    for template,w in enumerate(wins[:2]):
        for kind in ('old','new'):
            pat=rb'(?m)^'+b'\n'.join(l.split()[0].encode()+rb'(?: q\d+){'+str(len(l.split())-1).encode()+b'}' for l in w[kind])+b'\n'
            matches=[];skeletons=0
            for m in re.finditer(pat,raw):
                skeletons+=1;lines=m.group().decode().splitlines();mapping=bind(w[kind],lines)
                if mapping:matches.append({'byte_start':m.start(),'byte_end':m.end(),'wire_map':mapping,'lines':lines})
            results.append({'template':template,'kind':kind,'op_skeletons':skeletons,'matches':matches})
    (OUT/'commuted_matches.json').write_text(json.dumps({'scope':'Exact gate order, arbitrary injective wire renaming and CCX control/SWAP symmetry; no claim about other algebraic schedules','results':results,'seconds':time.monotonic()-t0},indent=2)+'\n')
    print([(r['template'],r['kind'],r['op_skeletons'],len(r['matches'])) for r in results],flush=True)
    selected=[(r,m) for r in results if r['kind']=='old' for m in r['matches']]
    if not selected:return
    selected.sort(key=lambda x:x[1]['byte_start']);last=0;parts=[];records=[]
    for r,m in selected:
        assert m['byte_start']>=last
        new=[' '.join(m['wire_map'].get(p,p) for p in line.split()) for line in wins[r['template']]['new']]
        assert truth(m['lines'])==truth(new)
        parts.extend((raw[last:m['byte_start']],('\n'.join(new)+'\n').encode()));last=m['byte_end']
        records.append({'position':m['byte_start'],'old':m['lines'],'new':new})
    parts.append(raw[last:]);import io
    newc=__import__('kickmix').Circuit.from_file(io.BytesIO(b''.join(parts)),format='kmx')
    newc.to_file(OUT/'syed_leo_port.kmb',format='kmb')
    (OUT/'port_candidate.json').write_text(json.dumps({'replacements':records,'old_static_T':c.operation_statistics().num_toffoli_like,'new_static_T':newc.operation_statistics().num_toffoli_like,'Q':newc.num_qubits},indent=2)+'\n')
    print('candidate generated',len(selected),'windows',flush=True)

if __name__=='__main__':main()
