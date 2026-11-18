import kickmix as km
gf = km.GF2Field(12)

def count(fn):
    b = km.CircuitBuilder(); fn(b); c = b.finish_circuit()
    st = c.operation_statistics(); d = {}
    for nm in dir(st):
        if nm.startswith('_'): continue
        v = getattr(st, nm)
        if isinstance(v,(int,float)) and v: d[nm]=int(v)
    return c.num_qubits, d

def one_mul(b, ctrl=False):
    q  = b.alloc_qubits(12); a = b.alloc_qubits(12); t = b.alloc_qubits(12)
    if ctrl:
        cf = b.alloc_qubits(1); b.x(cf[0])
        b.ixor_gf2_mul(q, a, target=t, field=gf, control=cf[0])
    else:
        b.ixor_gf2_mul(q, a, target=t, field=gf)

def one_div(b):
    a = b.alloc_qubits(12); t = b.alloc_qubits(12)
    ratio, scaf = b.init_gf2_div_with_scaffold(t, a, field=gf)
    b.del_gf2_div_with_scaffold(t, a, target=ratio, scaffold=scaf, field=gf)
    b.free(scaf + ratio)

def one_inv(b):
    a = b.alloc_qubits(12); tgt = b.alloc_qubits(12)
    c, chain = b.init_gf2_inverse_with_scaffold(a, target=tgt, field=gf)
    b.del_gf2_inverse_with_scaffold(a, target=tgt, scaffold=chain, field=gf)
    b.free(chain)

for nm, fn in (('ixor_gf2_mul', lambda b: one_mul(b)), ('ixor_gf2_mul_ctrl', lambda b: one_mul(b, True)),
               ('gf2_div+del', one_div), ('gf2_inv+del', one_inv)):
    q, d = count(fn)
    print(nm, 'qubits', q, d)
