"""Locate old Leo windows by native semantic tag path in the new decoder."""
import bisect,gc,json,re
import numpy as np
from inspect_migration import ROOT,OUT,export

def contexts(raw):
    stack=[];counts={};rows=[]
    for m in re.finditer(rb'(?m)^INFO_TAG "@(enter|exit):([^"\n]+)"\n',raw):
        kind,name=m[1].decode(),m[2].decode()
        if kind=='enter':
            parent=stack[-1]['path'] if stack else ''
            key=(parent,name);number=counts.get(key,0);counts[key]=number+1
            item={'path':parent+'/'+name+':'+str(number),'name':name,'start':m.end(),'end':None}
            rows.append(item);stack.append(item)
        else:
            assert stack[-1]['name']==name
            stack.pop()['end']=m.start()
    assert not stack
    return rows

def main():
    wins=json.loads((OUT/'leo_windows.json').read_text())
    _,raw=export(ROOT/'artifacts/20261105_maoxin_v2/release/dqi.kmb')
    tags=contexts(raw);ends=np.flatnonzero(np.frombuffer(raw,dtype=np.uint8)==10)
    selected=[]
    for i,w in enumerate(wins):
        pos=int(ends[w['old_start']-1])+1
        parents=[t for t in tags if t['start']<=pos<t['end']]
        t=parents[-1];block=raw[t['start']:t['end']]
        selected.append({'window':i,'old_path':t['path'],'old_CCX':len(re.findall(rb'(?m)^CCX ',block)),
                         'old_ops':block.count(b'\n'),
                         'old_local_offset':raw[t['start']:pos].count(b'\n')})
    del raw,ends,tags;gc.collect()
    _,raw=export(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb');tags=contexts(raw);by_path={t['path']:t for t in tags}
    for row in selected:
        t=by_path.get(row['old_path'])
        row['new_path_exists']=t is not None
        if t:
            block=raw[t['start']:t['end']]
            row['new_CCX']=len(re.findall(rb'(?m)^CCX ',block));row['new_ops']=block.count(b'\n')
    (OUT/'semantic_contexts.json').write_text(json.dumps(selected,indent=2)+'\n')
    print([{k:v for k,v in row.items() if k not in ('old_scope','new_scope')} for row in selected])

if __name__=='__main__':main()
