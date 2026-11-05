"""Manual Maoxin V2 DQI static/cost study; no hashes or verifier runs.

Public notebook assignments are parsed as literal DATA, never executed.
The native circuit export is held in memory briefly (~0.8 GB); no large text
export is written.  Local kernel algebra assumes the stated boundary contract.
"""
import ast
import bisect
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import kickmix as km
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261105_maoxin_v2/dqi'
SOURCE = OUT / 'sources/kirill_q19_v7_code.py'
CIRCUIT = ROOT / 'artifacts/20261105_maoxin_v2/release/dqi.kmb'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dqi.verify_submission_dqi import clopper_pearson_upper_bound, repetition_overhead


def literal(name):
    for n in ast.parse(SOURCE.read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise ValueError(name)


class Export:
    def write(self, chunk):
        self.data = chunk if isinstance(chunk, bytes) else chunk.encode()
        return len(chunk)
    def flush(self):
        pass


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    c = km.Circuit.from_file(CIRCUIT, format='kmb')
    stats = c.operation_statistics()
    svg = c.flame_chart_svg()
    (OUT / 'static_flame_chart.svg').write_text(svg)
    elements = list(ET.fromstring(svg))
    stages = []
    for i, e in enumerate(elements):
        if e.tag.endswith('text') and e.attrib.get('y') == '7' and i >= 2:
            rect, blue = elements[i-1], elements[i-2]
            w = float(rect.attrib.get('width', 0))
            stages.append({'stage':e.text, 'static_toffoli_estimate':stats.num_toffoli_like*w/1000,
                           'static_share_percent':w/10,
                           'peak_live_Q_estimate':c.num_qubits*float(blue.attrib.get('height',0))/100})

    upstream = literal('FULL_REPORTS')['dqi']
    q, t, n = c.num_qubits, upstream['toffoli_count'], 102400
    r0 = repetition_overhead(clopper_pearson_upper_bound(0, n))
    failure = []
    for k in (0,1,2,3,5,10):
        eps = clopper_pearson_upper_bound(k,n)
        r = repetition_overhead(eps)
        failure.append({'errors':k,'eps_plus':eps,'R':r,'cost_at_upstream_mean_T':r*q*q*t,
                        'DQI_cost_change_percent_vs_zero':100*(r/r0-1),
                        'GM_change_percent_vs_zero':100*((r0/r)**(1/3)-1),
                        'T_saving_to_offset_penalty':t*(1-r0/r)})
    widths = [{'Q':w,'extra_T_break_even_at_fixed_R':t*((q/w)**2-1),
               'GM_change_percent_at_fixed_T_R':100*((q/w)**(2/3)-1)}
              for w in (892,890,889,888,883,877,864,840)]
    gains = [{'saved_T':dt,'DQI_gain_percent':100*dt/t,
              'GM_gain_percent':100*((t/(t-dt))**(1/3)-1)}
             for dt in (1,14,100,500,1000,2000,10000)]

    # Exact native export positions bind the public split-kernel DATA to this
    # local circuit without computing or comparing a hash.
    data = literal('DQI_SDK_DELTA')
    sink = Export(); c.to_file(sink, format='kmx'); raw = sink.data
    ends = np.flatnonzero(np.frombuffer(raw,dtype=np.uint8)==10)
    def line(i):
        a = 0 if i == 0 else int(ends[i-1])+1
        return raw[a:int(ends[i])].decode()
    def span(a,b):
        left=0 if a==0 else int(ends[a-1])+1
        right=0 if b==0 else int(ends[b-1])+1
        return raw[left:right]
    shifts = [shift for shift in (0,-1) if all(
        [line(d['new_line']+shift+j) for j in range(len(d['new']))] == d['new']
        for d in data['deltas'])]
    if len(shifts)!=1:
        raise ValueError(f'Cannot uniquely bind all 42 public fragments: {shifts}')
    shift=shifts[0]
    conditional = []
    for m in re.finditer(rb'(?m)^(?:PUSH_CONDITION|POP_CONDITION)[^\n]*', raw):
        conditional.append((int(np.searchsorted(ends,m.start())),m.group().decode()))
    def stack_at(pos):
        stack=[]
        for i,s in conditional:
            if i>=pos: break
            if s.startswith('PUSH_CONDITION'):stack.append(s)
            else:stack.pop()
        return stack
    def last_writer(wire,pos,lookback=1000000):
        left=max(0,pos-lookback)
        preceding=span(left,pos).splitlines()
        for offset in range(len(preceding)-1,-1,-1):
            words=preceding[offset].decode().split()
            if not words:continue
            op=words[0]
            targets={'R':(1,),'HMR':(1,),'X':(1,),'CX':(2,),
                     'CCX':(3,),'SWAP':(1,2),'CSWAP':(2,3)}.get(op,())
            if any(len(words)>k and words[k]==wire for k in targets):
                idx=left+offset
                guarded='if' in words or bool(stack_at(idx))
                return {'line':idx,'instruction':' '.join(words),'guarded':guarded,
                        'unconditional_reset_proves_clean':op in ('R','HMR') and not guarded}
        return {'unconditional_reset_proves_clean':False,'not_found_in_last_lines':lookback}
    def clean_via_reset_swap(wire,pos,depth=8):
        w=last_writer(wire,pos)
        result={'wire':wire,'at_line':pos,'last_writer':w,'proved_clean':False}
        if w.get('unconditional_reset_proves_clean'):
            result['proved_clean']=True
        elif depth and not w.get('guarded',True) and w.get('instruction','').startswith('SWAP '):
            parts=w['instruction'].split()
            other=parts[1] if parts[2]==wire else parts[2]
            child=clean_via_reset_swap(other,w['line'],depth-1)
            result.update(proved_clean=child['proved_clean'],source=child)
        return result
    kernels=[]
    for j in range(14):
        first,swap,last=data['deltas'][3*j:3*j+3]
        a,b,z=[d['new_line']+shift for d in (first,swap,last)]
        carrier=first['new'][0].split()[-1]
        destination=swap['new'][0].split()[-1]
        middle=[]
        for name,left,right in ((carrier,a+len(first['new']),b),(destination,b+1,z)):
            part=span(left,right)
            pat=re.compile(rb'(?m)^[^\n]*\b'+name.encode()+rb'\b[^\n]*$')
            touches=[m.group().decode() for m in pat.finditer(part)]
            middle.append({'wire':name,'line_interval':[left,right],
                           'touch_count':len(touches),'first_touches':touches[:12]})
        same_end_names=set(first['old'][0].split()[1:3])==set(last['old'][0].split()[1:3])
        controls=first['old'][0].split()[1:3]
        control_last_writers=[last_writer(w,z) for w in controls]
        kernels.append({'kernel':j,'first_line':a,'swap_line':b,'end_line':z,
                        'endpoint_op':last['old'][0].split()[0],
                        'same_physical_control_names':same_end_names,
                        'same_names_are_not_temporal_product_proof':True,
                        'start_controls_last_writers_before_endpoint':control_last_writers,
                        'product_proved_by_same_unchanged_controls':same_end_names and all(w.get('line',a)>=0 and w.get('line',a)<a for w in control_last_writers),
                        'start_condition_stack':stack_at(a),'swap_condition_stack':stack_at(b),'end_condition_stack':stack_at(z),
                        'initial_carrier_last_writer':last_writer(carrier,a),
                        'swap_destination_last_writer':last_writer(destination,b),
                        'swap_destination_clean_trace':clean_via_reset_swap(destination,b),
                        'cache_line_span':z-a,'middle_carrier_touches':middle})

    # Independent Boolean/phase calculation of the conditional algebra, using
    # seven temporal boundary bits a,b,c,d,first_target,end_target,measurement.
    cases=positive_value=positive_phase=negative_phase=0
    for bits in range(128):
        a,b,c0,d,t0,u,m=[(bits>>i)&1 for i in range(7)]
        if a*b!=c0*d:continue
        cases+=1
        for op in ('CCX','CCZ'):
            p=a*b
            old_value=(t0^p,u^(c0*d) if op=='CCX' else u,0,0)
            new_value=(t0^p,u^p if op=='CCX' else u,0,0)
            old_phase=c0*d*u if op=='CCZ' else 0
            new_phase=(p*u if op=='CCZ' else 0)^(p*m)^(c0*d*m)
            positive_value+=old_value!=new_value
            positive_phase+=old_phase!=new_phase
        negative_phase+=(p*m)!=0

    out={'scope':'Static native circuit measurements, official cost helper sensitivity, and conditional kernel algebra only; no full official verification or new optimized candidate.',
         'hash_computed_or_matched':False,
         'native':{'num_qubits':q,'private_qubits':q-840,'num_bits':c.num_bits,'num_registers':c.num_registers,
                   'num_ops':len(c),'static_toffoli_like':stats.num_toffoli_like,'operations':dict(stats)},
         'upstream_runtime_reference':{'source':'Kirill Q19 V7 FULL_REPORTS literal, author run not repeated here',
                 'mean_T':t,'reaction_depth':upstream['reaction_depth'],'shots':n,
                 'value_errors':upstream['value_errors'],'phase_errors':upstream['phase_errors']},
         'static_minus_author_mean_T':stats.num_toffoli_like-t,
         'static_runtime_gap_percent':100*(stats.num_toffoli_like-t)/stats.num_toffoli_like,
         'stages':stages,'stage_scope':'Native SVG rounded coordinates; approximate static Toffoli shares and live-Q proxies, not runtime profiling.',
         'failure_sensitivity':failure,'width_sensitivity':widths,'paid_gate_sensitivity':gains,
         'T_reduction_for_0_1_percent_GM_gain':t*(1-1/(1.001**3)),
         'upstream_R41_saving':{'mean_T_saved':13.816,'DQI_percent':100*13.816/(t+13.816),
                              'GM_percent':100*(((t+13.816)/t)**(1/3)-1),'source':'Busy V18, 3 paired seeds; author claim'},
         'binding':{'canonical_lines':len(ends),'public_fragment_count':len(data['deltas']),
                    'all_42_actual_fragments_match_literal_instructions':True,'line_index_shift':shift,
                    'not_checked':'Unchanged global stream versus parent993c; no parent binary was loaded.'},
         'cache_kernels':kernels,
         'conditional_algebra':{'cases_per_type':cases,'types':['CCX','CCZ'],
            'value_differences':positive_value,'phase_differences':positive_phase,
            'negative_removed_CZ_phase_differences_per_type':negative_phase,
            'assumptions':'Clean initial carriers; unchanged common action; endpoint product equals saved product; every HMR outcome. These conditions are NOT established globally by the 80-case algebra.'},
         'elapsed_seconds':time.monotonic()-start}
    (OUT/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('cache_kernels','native')},indent=2))


if __name__=='__main__':
    main()
