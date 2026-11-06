"""Bounded no-recomputation recycling probe for the added q891 scratch line.

No reference to an idle line is a deliberately strong sufficient requirement,
not a general liveness or qubit-complexity lower bound.
"""
import bisect,collections,json,re,time
from inspect_migration import ROOT,OUT,export

def main():
    start=time.monotonic();c,raw=export(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb')
    events=[(m.start(),m.end(),m.group().decode()) for m in re.finditer(rb'(?m)^[^\n]*\bq891\b[^\n]*$',raw)]
    stage_names={'mask_projection','initial','extract','synthesis','convert','scan','unconvert','unsynthesis','unextract','uninitial','restore_masks'}
    stage_markers=[(m.start(),m[1].decode()) for m in re.finditer(rb'(?m)^INFO_TAG "@enter:([^"\n]+)"',raw) if m[1].decode() in stage_names]
    starts=[p for p,n in stage_markers]
    def stage(p):return stage_markers[bisect.bisect_right(starts,p)-1][1] if p>=starts[0] else 'initial'
    rows=[];lo=0;count=0
    for pos,end,line in events:
        if not line.startswith(('R q891','HMR q891')):
            if count==0:lo=pos
            count+=1;continue
        if count:
            block=raw[lo:end]
            referenced={int(m[1]) for m in re.finditer(rb'\bq(8[4-8][0-9]|890)\b',block)}
            # Include quantum inputs too for the stricter all-wire exhaustion
            # observation; they are not automatically clean when unused.
            all_used={int(m[1]) for m in re.finditer(rb'\bq([0-9]+)\b',block)}
            rows.append({'epoch':len(rows),'byte_start':lo,'byte_end':end,
                         'stage_start':stage(lo),'stage_end':stage(end),
                         'q891_nonreset_references':count,'closing_reset':line,
                         'unused_private_candidates':sorted(set(range(840,891))-referenced),
                         'unused_any_wire_candidates':sorted(set(range(891))-all_used),
                         'scope':'No-reference candidate set only. Clean-at-entry and condition-stack contracts not proved.'})
        lo=end;count=0
    out={'scope':'Sufficient idle-carrier substitution screen over whole q891 reset-delimited epochs. No new circuit, no impossibility claim for shortened lifetimes/recomputation/dirty-wire algebra.',
         'Q':c.num_qubits,'q891_total_references':len(events),'epochs':rows,
         'q891_operation_counts':dict(collections.Counter(l.split()[0] for p,e,l in events)),
         'epochs_with_no_private_idle_wire':sum(not r['unused_private_candidates'] for r in rows),
         'epochs_with_no_idle_wire_at_all':sum(not r['unused_any_wire_candidates'] for r in rows),
         'unclosed_nonreset_references':count,'seconds':time.monotonic()-start}
    (OUT/'extra_wire_probe.json').write_text(json.dumps(out,indent=2)+'\n')
    print({k:v for k,v in out.items() if k!='epochs'});print('epochs',len(rows))

if __name__=='__main__':main()
