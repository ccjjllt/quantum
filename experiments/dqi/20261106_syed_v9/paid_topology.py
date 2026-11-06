"""Broader Leo census ignoring intervening free gates; no candidate mutation."""
import json,re,time
from inspect_migration import ROOT,OUT,export
from match_commuted import bind
def main():
    t0=time.monotonic();wins=json.loads((OUT/'leo_windows.json').read_text())
    _,raw=export(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb')
    lo=raw.index(b'INFO_TAG "@enter:unextract"');hi=raw.index(b'INFO_TAG "@exit:unextract"')
    paid=[(m.start()+lo,m.end()+lo,m.group().decode()) for m in re.finditer(rb'(?m)^(?:CCX|CCZ|CSWAP) [^\n]+',raw[lo:hi])]
    results=[]
    for template,w in enumerate(wins[:2]):
        seq=[l for l in w['old'] if l.startswith('CCX ')];n=len(seq);hits=[]
        for i in range(len(paid)-n+1):
            lines=[p[2] for p in paid[i:i+n]]
            if any(l.split()[0]!='CCX' for l in lines):continue
            mapping=bind(seq,lines)
            if mapping:
                segment=raw[paid[i][0]:paid[i+n-1][1]].decode()
                hits.append({'byte_start':paid[i][0],'byte_end':paid[i+n-1][1],'wire_map':mapping,
                             'line_count':segment.count('\n')+1,'support':sorted(set(re.findall(r'q\d+',segment))),
                             'preview':segment[:3000]})
        results.append({'template':template,'paid_length':n,'hits':hits})
    out={'scope':'Unextract paid-gate topology with all intervening nonpaid gates ignored; arbitrary injective wire mapping and control commutation. A match alone is not an equivalent rewrite.',
         'unextract_paid_gates':len(paid),'results':results,'seconds':time.monotonic()-t0}
    (OUT/'paid_topology.json').write_text(json.dumps(out,indent=2)+'\n');print([(r['template'],len(r['hits'])) for r in results])
if __name__=='__main__':main()
