"""Manual exact-window migration census and Boolean proof; no full verification."""
import gc
import io
import json
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET
import kickmix as km

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/20261106_syed_v9/dqi'

class Sink:
    def write(self,x): self.data=x.encode() if isinstance(x,str) else x
    def flush(self): pass

def export(path):
    c=km.Circuit.from_file(path,format='kmb');s=Sink();c.to_file(s,format='kmx')
    return c,s.data

def truth(lines):
    wires=sorted({int(x) for x in re.findall(r'q(\d+)', '\n'.join(lines))})
    results=[]
    for value in range(1<<len(wires)):
        q={w:(value>>j)&1 for j,w in enumerate(wires)}
        for line in lines:
            p=line.split();w=[int(t[1:]) for t in p[1:]]
            if p[0]=='X':q[w[0]]^=1
            elif p[0]=='CX':q[w[1]]^=q[w[0]]
            elif p[0]=='CCX':q[w[2]]^=q[w[0]]&q[w[1]]
            elif p[0]=='SWAP':q[w[0]],q[w[1]]=q[w[1]],q[w[0]]
            else:raise ValueError(line)
        results.append(tuple(q[w] for w in wires))
    return wires,results

def windows():
    _,raw=export(ROOT/'artifacts/20261105_maoxin_v2/release/dqi.kmb')
    hs=json.loads((ROOT/'artifacts/20261106_leo_merge/diffhunks.json').read_text())
    hs=[h for h in hs if h['a0']>50732751];wins=[]
    for i in range(0,len(hs),7):
        for sub in (hs[i:i+3],hs[i+3:i+7]):
            a=sub[0]['a0'];b=max(h['a0']+len(h['a']) for h in sub)
            wins.append({'old_start':a,'old_end':b,'hunks':sub})
    f=io.BytesIO(raw);n=0
    for w in wins:
        while n<w['old_start']:f.readline();n+=1
        old=[]
        while n<w['old_end']:old.append(f.readline().decode().rstrip());n+=1
        new=[];j=0
        for h in w.pop('hunks'):
            k=h['a0']-w['old_start'];new+=old[j:k]
            assert old[k:k+len(h['a'])]==h['a']
            new+=h['b'];j=k+len(h['a'])
        new+=old[j:];w['old']=old;w['new']=new
        a,b=truth(old),truth(new);assert a==b
        w['arbitrary_boundary_truth_cases']=len(a[1]);w['wires']=a[0]
        w['paid_gate_saving']=sum(l.startswith('CCX ') for l in old)-sum(l.startswith('CCX ') for l in new)
    return wins

def main():
    start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    wins=windows();gc.collect()
    c,raw=export(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb')
    stats=c.operation_statistics();svg=c.flame_chart_svg()
    (OUT/'static_flame_chart.svg').write_text(svg)
    el=list(ET.fromstring(svg));stages=[]
    for i,e in enumerate(el):
        if e.tag.endswith('text') and e.attrib.get('y')=='7' and i>=2:
            stages.append({'stage':e.text,'static_T_estimate':stats.num_toffoli_like*float(el[i-1].attrib.get('width',0))/1000,
                           'peak_Q_estimate':c.num_qubits*float(el[i-2].attrib.get('height',0))/100})
    for w in wins:
        for kind in ('old','new'):
            needle=('\n'.join(w[kind])+'\n').encode()
            positions=[];pos=0
            while True:
                pos=raw.find(needle,pos)
                if pos<0:break
                if pos==0 or raw[pos-1]==10:positions.append(pos)
                pos+=1
            w[kind+'_byte_positions']=positions
    # Wire-renaming-insensitive search: failure of literal matches does not
    # mean the arithmetic template disappeared after a register layout change.
    generic=[]
    for template,w in enumerate(wins[:2]):
        for kind in ('old','new'):
            wire_group={};parts=[]
            for line in w[kind]:
                p=line.split();part=[p[0].encode()]
                for wire in p[1:]:
                    if wire not in wire_group:
                        wire_group[wire]=len(wire_group)+1;part.append(rb'q([0-9]+)')
                    else:part.append(('q\\'+str(wire_group[wire])).encode())
                parts.append(b' '.join(part))
            pattern=re.compile(rb'(?m)^'+b'\n'.join(parts)+b'\n')
            matches=[]
            for match in pattern.finditer(raw):
                if len(set(match.groups()))!=len(wire_group):continue
                matches.append({'byte_start':match.start(),'byte_end':match.end(),
                                'wire_map':{k:int(match.group(g)) for k,g in wire_group.items()}})
            generic.append({'template':template,'kind':kind,'count':len(matches),'matches':matches})
    result={'scope':'Actual circuit static comparison; independent local truth tables, no full official run or hash matching',
            'native':{'Q':c.num_qubits,'ops':len(c),'bits':c.num_bits,'static_T':stats.num_toffoli_like,'statistics':dict(stats)},
            'stages':stages,'stage_scope':'Rounded SVG coordinates, approximate static stage costs and live-Q proxies',
            'old_window_count':sum(bool(w['old_byte_positions']) for w in wins),'new_window_count':sum(bool(w['new_byte_positions']) for w in wins),
            'generic_templates':generic,'windows':wins,'seconds':time.monotonic()-start}
    (OUT/'migration_census.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='windows'},indent=2))

if __name__=='__main__':main()
