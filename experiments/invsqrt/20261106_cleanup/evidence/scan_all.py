import io
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')
C = km.Circuit.from_file(ROOT / 'artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb')
BUF = io.StringIO(); C.to_file(BUF, format='kmx')
LINES = BUF.getvalue().splitlines()
HDR = [l for l in LINES if l.startswith(('APPEND', 'REGISTER'))]
OPS = [l for l in LINES if not l.startswith(('APPEND', 'REGISTER'))]


def work(op):
    wid = os.getpid()
    out = ROOT / ('artifacts/20261105_rotlp/scan_%d_%d.kmb' % (wid, op))
    try:
        new = [l for j, l in enumerate(OPS) if j != op]
        cand = km.Circuit.from_file(io.StringIO('\n'.join(HDR + new) + '\n'), format='kmx')
        cand.to_file(out, format='kmb')
        t0 = time.time()
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/manual_verify.py'), 'invsqrt',
                            str(out), '--salt', 'scan-%d' % op],
                           capture_output=True, text=True, cwd=str(ROOT))
        try:
            js = json.loads(r.stdout)
            st, sc, er = js.get('status'), js.get('score'), js.get('error', '')
            tof = js.get('toffoli_count')
        except Exception:
            st, sc, er, tof = 'PARSE', None, r.stdout[-100:], None
        return {'op': op, 'line': OPS[op], 'status': st, 'score': sc,
                'toffoli': tof, 'err': er, 'sec': round(time.time() - t0, 1)}
    finally:
        try:
            out.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    ops_list = [int(x) for x in Path('/tmp/rest_paid.txt').read_text().split()]
    print('candidates:', len(ops_list), flush=True)
    t0 = time.time()
    res = []
    passes = []
    with Pool(10) as pool:
        for k, r in enumerate(pool.imap_unordered(work, ops_list, chunksize=1)):
            res.append(r)
            if r['status'] == 'PASS':
                passes.append(r)
                print('PASS op %d %s score=%s tof=%s' % (r['op'], r['line'], r['score'], r['toffoli']), flush=True)
            if (k + 1) % 50 == 0:
                print('  %d/%d  %.0fs  passes=%d' % (k + 1, len(ops_list), time.time() - t0, len(passes)), flush=True)
    Path('/tmp/scan_results.json').write_text(json.dumps(res, indent=1))
    print('done %.0fs' % (time.time() - t0))
    from collections import Counter
    print('status counts:', Counter(r['status'] for r in res))
    print('PASS list:', [(r['op'], r['line'], r['score']) for r in passes])
