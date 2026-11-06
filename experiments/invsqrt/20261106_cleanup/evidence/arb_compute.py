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
           (16045,16061,16045,16050,16060)]
cands = []
for line in Path('/tmp/skel3_survivors.txt').read_text().splitlines():
    if not line.strip(): continue
    wid, kind = line.split()
    a,b,p0,p1,p2 = triples[int(wid)]
    m = re.match(r'del-?(\d+)(?:-mod(\d+)p(\d+)->(q\d+))?', kind)
    dpos = int(m.group(1))
    touched = {dpos}
    newl = None; mpos = pos = tgt = None
    if m.group(2):
        mpos, pos, tgt = int(m.group(2)), int(m.group(3)), m.group(4)
        touched.add(mpos)
        pp = ops[mpos].split()
        parts = list(pp[1:4])
        if parts[pos-1] == tgt: continue
        parts[pos-1] = tgt
        if len(set(parts)) < 3: continue
        newl = ' '.join([pp[0]] + parts)
    kinds = {ops[i].split()[0] for i in touched}
    if kinds <= {'CCZ'}: continue
    cands.append((wid, kind, dpos, mpos, pos, tgt, newl))
print('compute-touching valid candidates:', len(cands), flush=True)
res = []
for (wid, kind, dpos, mpos, pos, tgt, newl) in cands:
    new = []
    for i, l in enumerate(ops):
        if i == dpos: continue
        if mpos is not None and i == mpos: l = newl
        new.append(l)
    try:
        cand = km.Circuit.from_file(io.StringIO('\n'.join(hdr + new) + '\n'), format='kmx')
    except ValueError as e:
        print('%-34s INVALID %s' % (kind, str(e)[:50]), flush=True)
        continue
    out = ROOT / 'artifacts/20261105_rotlp/proto_mixc.kmb'
    cand.to_file(out, format='kmb')
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / 'scripts/manual_verify.py'), 'invsqrt', str(out),
                        '--salt', 'mixc-%s' % kind.replace('->', '_')], capture_output=True, text=True, cwd=str(ROOT))
    try:
        js = json.loads(r.stdout); st, sc, er = js.get('status'), js.get('score'), js.get('error', '')
    except Exception: st, sc, er = 'PARSE', None, r.stdout[-80:]
    res.append((kind, st, sc, er))
    print('%-34s %s score=%s %.1fs %s' % (kind, st, sc, time.time()-t0, er[:55]), flush=True)
ok = [r for r in res if r[1] == 'PASS']
print('PASS:', len(ok), ok)
