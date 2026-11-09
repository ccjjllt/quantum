import io, sys
import numpy as np
import kickmix as km
from pathlib import Path
sys.path.insert(0, 'data/competition/verifiers/invsqrt')
from verify_submission_invsqrt import to_bits
KMB = Path('artifacts/20261108_public_frontier/release/invsqrt.kmb')
c = km.Circuit.from_file(str(KMB))
buf = io.StringIO(); c.to_file(buf, format='kmx')
lines = buf.getvalue().splitlines()
hdr = [l for l in lines if l.startswith(('APPEND','REGISTER'))]
ops = [l for l in lines if l and not l.startswith(('APPEND','REGISTER'))]
A, B = 15987, 16262
frag = ['CCX q21 q25 q4','CX q4 q28','CCX q21 q25 q4','CX q4 q28']
new_ops = ops[:A] + frag + ops[A+1:B] + frag + ops[B+1:16263]
base_ops = ops[:16263]
cb = km.Circuit.from_file(io.StringIO('\n'.join(hdr+base_ops)+'\n'), format='kmx')
cn = km.Circuit.from_file(io.StringIO('\n'.join(hdr+new_ops)+'\n'), format='kmx')
sb, sn = cb.operation_statistics(), cn.operation_statistics()
print('BASE toffoli_like:', sb.num_toffoli_like, 'NEW:', sn.num_toffoli_like, 'DELTA:', sn.num_toffoli_like - sb.num_toffoli_like, flush=True)
x_reg = km.array([km.q(i) for i in range(22)])
qall = km.array([km.q(i) for i in range(62)])
xs = [1,2,3,1000,100000,1000000,3103559,3133452]
mism = 0; cells = 0
worst = None
for seed in (11,22):
    for x in xs:
        outs = {}
        for name, circ in (('base',cb),('new',cn)):
            sim = km.Simulator(batch_size=1, debug_print=False, seed=seed*7919+x)
            sim.clear_for_shot()
            sim.write_across_shots(x_reg, to_bits(np.array([x], dtype=np.uint64), 22))
            sim.do(circ)
            outs[name] = np.array(sim.read_across_shots(qall)[0]).astype(bool)
        cells += 1
        if not np.array_equal(outs['base'], outs['new']):
            mism += 1
            diff = np.where(outs['base']!=outs['new'])[0].tolist()
            worst = (seed,x,diff)
            print('MISMATCH seed',seed,'x',x,'diff qubits',diff, flush=True)
print('cells:',cells,'mismatches:',mism, flush=True)
print('QHASH base==new' if mism==0 else 'DIFFER', flush=True)
