import importlib.util, sys
spec=importlib.util.spec_from_file_location("ref","data/competition/verifiers/dqi/dqi_reference_circuit.py")
ref=importlib.util.module_from_spec(spec); sys.modules["ref"]=ref; spec.loader.exec_module(ref)
import kickmix as km
from collections import Counter

C = Counter()
_orig_div = km.CircuitBuilder.init_gf2_div_with_scaffold
_orig_mul = km.CircuitBuilder.ixor_gf2_mul
_orig_flip = km.CircuitBuilder.flip_if_equal
_orig_cswap = km.CircuitBuilder.cswap
_orig_ccx = km.CircuitBuilder.ccx
def div(self,*a,**k): C['div']+=1; return _orig_div(self,*a,**k)
def mul(self,*a,**k): C['mul']+=1; return _orig_mul(self,*a,**k)
def fl(self,*a,**k): C['flip_if_equal']+=1; return _orig_flip(self,*a,**k)
def cs(self,*a,**k): C['cswap']+=1; return _orig_cswap(self,*a,**k)
def cc(self,*a,**k): C['ccx']+=1; return _orig_ccx(self,*a,**k)
km.CircuitBuilder.init_gf2_div_with_scaffold=div
km.CircuitBuilder.ixor_gf2_mul=mul
km.CircuitBuilder.flip_if_equal=fl
km.CircuitBuilder.cswap=cs
km.CircuitBuilder.ccx=cc

def eea_only(n, degree=12, n_iters=None):
    gf = km.GF2Field(degree); m = n + 3
    n_iters = ref.default_n_iters(n) if n_iters is None else n_iters
    b = km.CircuitBuilder()
    syn = [b.create_quantum_register(degree, name=f'S{i}') for i in range(n)]
    reg_a = [b.alloc_qubits(degree) if i < 3 else syn[i-3] for i in range(m)]
    reg_b = [b.alloc_qubits(degree) for _ in range(m)]
    logm = m.bit_length() + 1
    nA,nB,na,nb,nq = (b.alloc_qubits(logm) for _ in range(5))
    flag = b.alloc_qubits(1)[0]; counter = b.alloc_qubits(2)
    hc = b.alloc_qubits(n_iters.bit_length())
    dec = ref.ProosAndZalkaDecoder(n, gf)
    b.x(km.array([reg_a[0][0], reg_b[m-1][0], na[0], flag]))
    b.gf2_iadd(n, target=nA); b.gf2_iadd(n+1, target=nB)
    dec._synchronized_eea(b, reg_a, reg_b, nA,nB,na,nb,nq, flag, counter, hc,
                          n_iters=n_iters, is_adjoint=False)
    return b.finish_circuit()

print(f"{'n':>3} {'m':>3} {'iters':>6} {'div':>5} {'div/it':>7} {'mul':>6} {'mul/it':>7} {'mul/(it*m)':>10} {'ccx':>7} {'tof':>8}")
for n in (2,3,4,5,8):
    C.clear()
    ni = ref.default_n_iters(n); m=n+3
    c = eea_only(n)
    st = c.operation_statistics()
    print(f"{n:>3} {m:>3} {ni:>6} {C['div']:>5} {C['div']/ni:>7.2f} {C['mul']:>6} {C['mul']/ni:>7.2f} "
          f"{C['mul']/(ni*m):>10.3f} {C['ccx']:>7} {st.num_toffoli_like:>8}")
