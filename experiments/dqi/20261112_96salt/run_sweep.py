# Re-run the paired sweep used in this record. Writes JSONL under artifacts/.
# Usage: uv run python experiments/dqi/20261112_96salt/run_sweep.py START END
import json, subprocess, sys, time
from pathlib import Path
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
FILES = {
    'cd71': ROOT/'artifacts/20261112_public_25367/candidate/dqi.kmb',
    'eae': ROOT/'artifacts/20261112_dqi96/dqi.kmb',
}
out = ROOT/'artifacts/20261112_dqi96/results.jsonl'
for seed in range(int(sys.argv[1]), int(sys.argv[2])):
    for name, path in FILES.items():
        t0 = time.time()
        p = subprocess.run([sys.executable, 'scripts/manual_verify.py', 'dqi', str(path), '--seed', str(seed)],
                           cwd=ROOT, capture_output=True, text=True)
        txt = p.stdout + '\n' + p.stderr
        obj = None
        for i in range(len(txt)-1, -1, -1):
            if txt[i] == '{':
                try:
                    obj = json.loads(txt[i:]); break
                except Exception:
                    pass
        rec = {'seed': seed, 'name': name, 'returncode': p.returncode, 'seconds': round(time.time()-t0, 1)}
        if obj:
            for k in ('score','verified_shots','value_errors','phase_errors','repetition_factor','toffoli_count','max_toffoli_count','num_qubits','circuit_sha256'):
                rec[k] = obj.get(k)
        with out.open('a') as f:
            f.write(json.dumps(rec)+'\n')
        print(json.dumps(rec), flush=True)
