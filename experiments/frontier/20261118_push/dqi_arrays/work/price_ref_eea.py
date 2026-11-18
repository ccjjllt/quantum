import importlib.util, sys
spec=importlib.util.spec_from_file_location("ref","data/competition/verifiers/dqi/dqi_reference_circuit.py")
ref=importlib.util.module_from_spec(spec); sys.modules["ref"]=ref; spec.loader.exec_module(ref)
import kickmix as km

def eea_only(n, degree=12, n_iters=None, both=False):
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
    eea = (reg_a, reg_b, nA,nB,na,nb,nq, flag, counter, hc)
    dec = ref.ProosAndZalkaDecoder(n, gf)
    init_ones = km.array([reg_a[0][0], reg_b[m-1][0], na[0], flag])
    b.x(init_ones); b.gf2_iadd(n, target=nA); b.gf2_iadd(n+1, target=nB)
    with b.mark('fwd'):
        dec._synchronized_eea(b, *eea, n_iters=n_iters, is_adjoint=False)
    if both:
        with b.mark('rev'):
            dec._synchronized_eea(b, *eea, n_iters=n_iters, is_adjoint=True)
    return b.finish_circuit()

print(f"{'n':>3} {'m':>3} {'iters':>6} {'tof(1 pass)':>12} {'T/iter':>9} {'rows*m':>7}")
for n in (2,3,4,5,8):
    for it_extra in (0,1):
        ni = ref.default_n_iters(n) + it_extra
        c = eea_only(n, n_iters=ni)
        st = c.operation_statistics()
        print(f"{n:>3} {n+3:>3} {ni:>6} {st.num_toffoli_like:>12} {st.num_toffoli_like/ni:>9.1f}")
