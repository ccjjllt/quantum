import io, json, subprocess, sys, time
from pathlib import Path
import kickmix as km
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')
c = km.Circuit.from_file(ROOT / 'artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb')
buf = io.StringIO(); c.to_file(buf, format='kmx')
lines = buf.getvalue().splitlines()
hdr = [l for l in lines if l.startswith(('APPEND', 'REGISTER'))]
ops = [l for l in lines if not l.startswith(('APPEND', 'REGISTER'))]
cands = [int(x) for x in Path('/tmp/tail_fresh.txt').read_text().split()]
print('tail fresh candidates:', len(cands), flush=True)
res = []
for i in cands:
    new = [l for j, l in enumerate(ops) if j != i]
    cand = km.Circuit.from_file(io.StringIO('\n'.join(hdr + new) + '\n'), format='kmx')
    out = ROOT / 'artifacts/20261105_rotlp/proto_tail.kmb'
    cand.to_file(out, format='kmb')
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / 'scripts/manual_verify.py'), 'invsqrt', str(out),
                        '--salt', 'tail-%d' % i], capture_output=True, text=True, cwd=str(ROOT))
    try:
        js = json.loads(r.stdout)
        st, sc, er = js.get('status'), js.get('score'), js.get('error', '')
    except Exception:
        st, sc, er = 'PARSE', None, r.stdout[-80:]
    res.append({'op': i, 'line': ops[i], 'status': st, 'score': sc, 'err': er})
    print('%5d %-30s %s score=%s %.1fs %s' % (i, ops[i][:30], st, sc, time.time()-t0, er[:50]), flush=True)
    Path('/tmp/tail_results.json').write_text(json.dumps(res, indent=1))
ok = [x for x in res if x['status'] == 'PASS']
print('PASS:', len(ok))
for r in ok: print('  ', r['op'], r['line'], r['score'])
