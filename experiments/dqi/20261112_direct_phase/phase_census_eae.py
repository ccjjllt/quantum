"""Count phase gates per INFO_TAG stage in eae396ba and locate the phase block.

Family bet: if the phase is applied before the uncompute, a direct-phase/MBU
rewrite may remove part of the 51.3% uncompute. This census is read-only.
"""
import json, sys, tempfile
from collections import Counter
from pathlib import Path
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'.worktree/dqi/experiments/dqi/20261110_e9diff'))
from stage_census import dump_kmx, SKIP_PREFIX  # noqa: E402

KMB = ROOT/'artifacts/20261112_eae_candidate/dqi.kmb'
OUT = ROOT/'.worktree/dqi/artifacts/20261112_direct_phase'
OUT.mkdir(parents=True, exist_ok=True)
PHASE = ('Z_POW','CZ','CCZ','Z','NEG')

def main():
    with tempfile.TemporaryDirectory() as td:
        kmx = dump_kmx(KMB, Path(td))
        print('kmx', kmx, kmx.stat().st_size, flush=True)
        stack=[]; stage_counts={}; first={}; last={}; op_index=0
        with kmx.open('r', encoding='utf-8', errors='replace') as f:
            for l in f:
                l=l.rstrip('\n')
                if l.startswith('INFO_TAG '):
                    try: tag=l.strip().split('"',2)[1]
                    except IndexError: continue
                    if tag.startswith('@enter:'): stack.append(tag[7:])
                    elif tag.startswith('@exit:') and stack: stack.pop()
                    continue
                if not l or l.startswith(SKIP_PREFIX): continue
                stage=stack[0] if stack else 'header'
                op=l.split()[0]
                if op in PHASE:
                    d=stage_counts.setdefault(stage, Counter())
                    d[op]+=1
                    first.setdefault(stage, (op_index, op, l[:120]))
                    last[stage]=(op_index, op, l[:120])
                op_index+=1
        res={'stages':{s:dict(c) for s,c in stage_counts.items()},
             'first':{s:first[s] for s in first},'last':{s:last[s] for s in last},
             'total_ops':op_index}
    (OUT/'phase_census_eae.json').write_text(json.dumps(res,indent=2)+'\n')
    print(json.dumps(res,indent=2), flush=True)

if __name__=='__main__': main()
