"""dqi_fastshift: (1) price the reference `_initial_shift_loop`, (2) measure the
12x12 multiply-block interface of tape 575b043f.

Kaggle CPU only (enable_gpu=false / enable_tpu=false).  Read-only over the tape and
over the competition verifier sources; the official verifier is NOT run.

Part 1 — reference shift pricing
    build ProosAndZalkaDecoder._initial_shift_loop(n=70, m=73, degree=12), forward and
    adjoint, with the competition's own kickmix, and report static toffoli_like, the
    opcode census, and the CX count if the CSWAPs are expanded into CCX+2CX (the tape
    has CSWAP = 0, so that is the only comparable idiom).

Part 2 — multiply-block interface
    for each sampled 42-CCX block: word triple (A,B,C), the CCX target qubits (the
    product scratch bits), the word-closure window, ANF closure (are A and B restored,
    is C = itself + degree 2), and the bilinear tensor T (12x12x12) extracted by
    bit-sliced simulation of all 144 basis inputs, cross-checked against an independent
    ANF term extraction; flattening ranks; identification against GF(2^12).

Writes /kaggle/working/dqi_fastshift.json and prints a compact report.
"""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

T0 = time.time()
WORK = pathlib.Path('/kaggle/working')
OUT = {}
DEG = 12


def say(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


# ------------------------------------------------------------------ environment
def find(pattern, root='/kaggle/input'):
    for p in pathlib.Path(root).rglob(pattern):
        return p
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


COMP = None
for cand in pathlib.Path('/kaggle/input').rglob('dqi_reference_circuit.py'):
    COMP = cand.parent.parent.parent
    break
say('competition root', COMP)
sys.path.insert(0, str(COMP / 'kickmix'))
sys.path.insert(0, str(COMP))
import kickmix as km                       # noqa: E402

IR_PY = find('vqcc_ir.py')
say('vqcc_ir', IR_PY, 'kickmix', km.__file__)
spec = importlib.util.spec_from_file_location('vqcc_ir', IR_PY)
ir = importlib.util.module_from_spec(spec)
sys.modules['vqcc_ir'] = ir
spec.loader.exec_module(ir)

RAWF = WORK / 'tape.kmb'
XZ = find('dqi_575b043f.kmb.xz')
if not RAWF.exists() and XZ is not None:
    say('decompress', XZ)
    with lzma.open(XZ, 'rb') as fi, open(RAWF, 'wb') as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
TAPE = str(RAWF) if RAWF.exists() else str(find('dqi_575b043f.kmb'))
say('tape', TAPE, 'bytes', pathlib.Path(TAPE).stat().st_size)

# ===================================================================== part 1
from verifiers.dqi.dqi_reference_circuit import ProosAndZalkaDecoder   # noqa: E402


def price_reference(n=70, degree=12, logm_override=None):
    m = n + 3
    res = {}
    for adj in (False, True):
        b = km.CircuitBuilder()
        reg_a = [b.alloc_qubits(degree) for _ in range(3)] + \
                [b.alloc_qubits(degree) for _ in range(n)]
        logm = logm_override or (m.bit_length() + 1)
        n_A = b.alloc_qubits(logm)
        dec = ProosAndZalkaDecoder(n, km.GF2Field(degree))
        # reproduce the preamble the tape's shift sees: n_A = n
        b.gf2_iadd(n, target=n_A)
        dec._initial_shift_loop(b, reg_a, n_A, is_adjoint=adj)
        c = b.finish_circuit()
        st = c.operation_statistics()
        d = dict(st)
        res['adjoint' if adj else 'forward'] = {
            'toffoli_like': st.num_toffoli_like,
            'num_instructions': st.num_instructions,
            'num_qubits': c.num_qubits,
            'CSWAP': d.get('CSWAP', 0),
            'CCX': d.get('CCX', 0),
            'CX': d.get('CX', 0),
            'ops': d,
            'CX_if_cswap_expanded': d.get('CX', 0) + 2 * d.get('CSWAP', 0),
            'T_if_cswap_expanded': st.num_toffoli_like,
            'n_shift_steps': n - 1,
        }
    return res


OUT['reference_shift'] = price_reference()
OUT['reference_shift_m7'] = price_reference(logm_override=7)
OUT['reference_source'] = {
    'path': str(COMP / 'verifiers/dqi/dqi_reference_circuit.py'),
    'sha256': sha256(COMP / 'verifiers/dqi/dqi_reference_circuit.py'),
}
for k in ('reference_shift', 'reference_shift_m7'):
    f = OUT[k]['forward']
    a = OUT[k]['adjoint']
    say(k, 'fwd T', f['toffoli_like'], 'CSWAP', f['CSWAP'], 'CCX', f['CCX'],
        'CX', f['CX'], 'CXexp', f['CX_if_cswap_expanded'],
        '| adj T', a['toffoli_like'], 'CXexp', a['CX_if_cswap_expanded'])

# ===================================================================== part 2
FM = km.GF2Field(DEG)


def field_tensor():
    T = np.zeros((DEG, DEG, DEG), np.uint8)
    for i in range(DEG):
        for j in range(DEG):
            p = int(FM.mul(1 << i, 1 << j))
            for k in range(DEG):
                T[i, j, k] = (p >> k) & 1
    return T


TF = field_tensor()


def gf2_rank(M):
    M = np.array(M, np.uint8).copy()
    rows, cols = M.shape
    r = 0
    for c in range(cols):
        p = None
        for i in range(r, rows):
            if M[i, c]:
                p = i
                break
        if p is None:
            continue
        M[[r, p]] = M[[p, r]]
        for i in range(rows):
            if i != r and M[i, c]:
                M[i] ^= M[r]
        r += 1
        if r == rows:
            break
    return r


# ---- bit-sliced simulator (X/CX/CCX/SWAP/R/HMR; Z/CZ/NEG are basis-state no-ops)
NOOP = {'Z', 'CZ', 'NEG', 'INFO_TAG', 'POP_CONDITION', 'PUSH_CONDITION'}


def simulate(ops, init, nq):
    nruns = len(next(iter(init.values())))
    S = {q: np.zeros(nruns, np.uint8) for q in range(nq)}
    for q, v in init.items():
        S[q] = v.copy()
    touched = set()
    for (i, name, qs, tb, cb) in ops:
        base = name[:-3] if name.endswith('_IF') else name
        if cb is not None and base not in ('Z', 'CZ'):
            raise ValueError(f'classically-conditioned bit-flip {name} at {i}')
        if base == 'X':
            S[qs[0]] ^= 1
        elif base == 'CX':
            S[qs[1]] ^= S[qs[0]]
        elif base == 'CCX':
            S[qs[2]] ^= S[qs[0]] & S[qs[1]]
        elif base == 'SWAP':
            S[qs[0]], S[qs[1]] = S[qs[1]], S[qs[0]]
        elif base in ('R', 'HMR'):
            S[qs[0]] = np.zeros(nruns, np.uint8)
        elif base in NOOP:
            continue
        else:
            raise ValueError(f'unsupported op {name} at {i}')
        touched.update(qs)
    return S, touched


def extract_tensor(ops, nq, wa, wb, wc):
    runs = [('bil', i, j) for i in range(DEG) for j in range(DEG)]
    runs += [('a', i, 0) for i in range(DEG)]
    runs += [('b', 0, j) for j in range(DEG)]
    runs += [('zero', 0, 0)]
    nr = len(runs)
    init = {q: np.zeros(nr, np.uint8) for q in range(nq)}
    for r, (kind, ai, bj) in enumerate(runs):
        a = ai if kind in ('bil', 'a') else None
        b = bj if kind in ('bil', 'b') else None
        for t in range(DEG):
            if a is not None and t == a:
                init[wa * DEG + t][r] = 1
            if b is not None and t == b:
                init[wb * DEG + t][r] = 1
    S, touched = simulate(ops, init, nq)
    T = np.zeros((DEG, DEG, DEG), np.uint8)
    LA = np.zeros((DEG, DEG), np.uint8)
    LB = np.zeros((DEG, DEG), np.uint8)
    z = DEG * DEG + 2 * DEG
    ib = lambda i, j: i * DEG + j            # noqa: E731
    ia = lambda i: DEG * DEG + i             # noqa: E731
    jb = lambda j: DEG * DEG + DEG + j       # noqa: E731
    for k in range(DEG):
        q = wc * DEG + k
        for i in range(DEG):
            for j in range(DEG):
                T[i, j, k] = (S[q][ib(i, j)] ^ S[q][ia(i)] ^ S[q][jb(j)] ^ S[q][z]) & 1
        for i in range(DEG):
            LA[i, k] = (S[q][ia(i)] ^ S[q][z]) & 1
        for j in range(DEG):
            LB[j, k] = (S[q][jb(j)] ^ S[q][z]) & 1
    restored = [q for q in sorted(touched) if np.array_equal(S[q], init[q])]
    dirty = [q for q in sorted(touched) if not np.array_equal(S[q], init[q])]
    return dict(T=T, LA=LA, LB=LB, restored=restored, dirty=dirty, touched=sorted(touched))


def bilinear_check(ops, nq, wa, wb, wc, T, nrand=64, seed=3):
    rng = np.random.default_rng(seed)
    runs = [(int(rng.integers(1, 1 << DEG)), int(rng.integers(1, 1 << DEG)))
            for _ in range(nrand)]
    nr = len(runs)
    init = {q: np.zeros(nr, np.uint8) for q in range(nq)}
    for r, (a, b) in enumerate(runs):
        for t in range(DEG):
            if (a >> t) & 1:
                init[wa * DEG + t][r] = 1
            if (b >> t) & 1:
                init[wb * DEG + t][r] = 1
    S, _ = simulate(ops, init, nq)
    bad = 0
    for r, (a, b) in enumerate(runs):
        pred = np.zeros(DEG, np.uint8)
        for i in range(DEG):
            if (a >> i) & 1:
                for j in range(DEG):
                    if (b >> j) & 1:
                        pred ^= T[i, j]
        obs = np.array([S[wc * DEG + k][r] for k in range(DEG)], np.uint8)
        bad += not np.array_equal(pred, obs)
    return {'n_random': nrand, 'mismatches': int(bad)}


# ---- ANF term extraction (independent method) ---------------------------------
def _xor(dst, src):
    out = dict(dst)
    for m in src:
        if m in out:
            del out[m]
        else:
            out[m] = 1
    return out


def anf_terms(ops, wa, wb, wc):
    qword = {(w * DEG + b): (w, b) for w in (wa, wb, wc) for b in range(DEG)}
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    nv = len(qubits)
    val = {q: {1 << lv[q]: 1} for q in qubits}
    pex = {q: {} for q in qubits}
    ands = []

    def bits(m):
        return [b for b in range(nv) if (m >> b) & 1]
    for (i, name, qs, tb, cb) in ops:
        base = name[:-3] if name.endswith('_IF') else name
        if base == 'CX':
            a, b = qs
            val[b] = _xor(val[b], val[a])
            pex[b] = _xor(pex[b], pex[a])
        elif base == 'CCX':
            c1, c2, d = qs
            if pex[c1] or pex[c2]:
                raise ValueError(f'product used as control at {i}')
            if any(any(m.bit_count() > 1 for m in val[vv]) for vv in (c1, c2)):
                raise ValueError(f'non-linear control at {i}')
            ands.append((i, [b for m in val[c1] for b in bits(m)],
                         [b for m in val[c2] for b in bits(m)]))
            out = dict(val[d])
            for m1 in val[c1]:
                for m2 in val[c2]:
                    m = m1 | m2
                    if m.bit_count() > 2:
                        raise ValueError(f'degree>2 at {i}')
                    if m in out:
                        del out[m]
                    else:
                        out[m] = 1
            val[d] = out
            pex[d] = _xor(pex[d], {len(ands) - 1: 1})
        elif base == 'SWAP':
            a, b = qs
            val[a], val[b] = val[b], val[a]
            pex[a], pex[b] = pex[b], pex[a]
        elif base == 'X':
            val[qs[0]] = _xor(val[qs[0]], {0: 1})
        else:
            raise ValueError(f'unsupported {name} at {i}')
    qid = {i: q for q, i in lv.items()}
    terms = []
    for tid, (i, u, v) in enumerate(ands):
        um = 0
        for x in u:
            q = qid[x]
            if qword.get(q, (None,))[0] == wa:
                um |= 1 << qword[q][1]
        vm = 0
        for x in v:
            q = qid[x]
            if qword.get(q, (None,))[0] == wb:
                vm |= 1 << qword[q][1]
        wm = 0
        for q in qubits:
            if qword.get(q, (None,))[0] == wc and tid in pex[q]:
                wm |= 1 << qword[q][1]
        terms.append({'op': int(i), 'u': um, 'v': vm, 'w': wm,
                      'u_bits': sorted(qword[qid[x]] for x in u),
                      'v_bits': sorted(qword[qid[x]] for x in v),
                      'u_len': len(u), 'v_len': len(v)})
    T = np.zeros((DEG, DEG, DEG), np.uint8)
    for t in terms:
        for i in range(DEG):
            if (t['u'] >> i) & 1:
                for j in range(DEG):
                    if (t['v'] >> j) & 1:
                        for k in range(DEG):
                            if (t['w'] >> k) & 1:
                                T[i, j, k] ^= 1
    return terms, T


def anf_closure(ops, wa, wb, wc):
    qubits = sorted({q for (_, _, qs, _, _) in ops for q in qs})
    lv = {q: i for i, q in enumerate(qubits)}
    val = {q: {1 << lv[q]: 1} for q in qubits}
    for (i, name, qs, tb, cb) in ops:
        if name not in ('X', 'CX', 'CCX', 'SWAP'):
            return None
        if name == 'CX':
            a, b = qs
            val[b] = _xor(val[b], val[a])
        elif name == 'CCX':
            c1, c2, d = qs
            if any(any(m.bit_count() > 1 for m in val[vv]) for vv in (c1, c2)):
                return None
            out = dict(val[d])
            for m1 in val[c1]:
                for m2 in val[c2]:
                    m = m1 | m2
                    if m.bit_count() > 2:
                        return None
                    if m in out:
                        del out[m]
                    else:
                        out[m] = 1
            val[d] = out
        elif name == 'SWAP':
            a, b = qs
            val[a], val[b] = val[b], val[a]
        else:
            val[qs[0]] = _xor(val[qs[0]], {0: 1})
    ident, acc, bad = set(), set(), set()
    for q, anf in val.items():
        lin = [m for m in anf if m.bit_count() == 1]
        pairs = [m for m in anf if m.bit_count() == 2]
        const = 0 in anf
        if lin == [1 << lv[q]] and not pairs and not const:
            ident.add(q)
        elif lin == [1 << lv[q]] and pairs and not const:
            acc.add(q)
        else:
            bad.add(q)
    return ident, acc, bad


def word_closure_window(c, a, b, words, span=3000):
    ops = c.decode(max(0, a - span), min(c.num_ops, b + span))
    idx = {o[0]: k for k, o in enumerate(ops)}
    ia, ib = idx[a], idx[b - 1]

    def ok(o):
        qs = o[2]
        return (not qs) or {q // DEG for q in qs} <= words
    lo = ia
    while lo > 0 and ok(ops[lo - 1]):
        lo -= 1
    hi = ib + 1
    while hi < len(ops) and ok(ops[hi]):
        hi += 1
    return ops[lo][0], ops[hi - 1][0] + 1


def field_report(T):
    rep = {'one_bits': int(T.sum()),
           'equals_km_field_mul': bool(np.array_equal(T, TF)),
           'commutative': bool(np.array_equal(T, np.transpose(T, (1, 0, 2)))),
           'flatten_ranks': {
               'A|BC': int(gf2_rank(T.reshape(DEG, DEG * DEG).T)),
               'B|AC': int(gf2_rank(np.transpose(T, (1, 0, 2)).reshape(DEG, DEG * DEG).T)),
               'C|AB': int(gf2_rank(T.reshape(DEG * DEG, DEG)))}}
    mats = {}
    for a in range(1, 1 << DEG):
        v = np.array([(a >> b) & 1 for b in range(DEG)], np.uint8)
        mats[a] = np.tensordot(v, T, axes=(0, 0)) % 2
    rep['min_nonzero_rank'] = int(min(gf2_rank(M) for M in mats.values()))
    rep['identity_elements'] = [a for a, M in mats.items()
                                if np.array_equal(M, np.eye(DEG, dtype=np.uint8))]
    basis = [np.array([(a >> b) & 1 for b in range(DEG)], np.uint8) for a in range(DEG)]

    def mv(x, y):
        return np.einsum('i,j,ijk->k', x, y, T) % 2
    rep['associative'] = all(
        np.array_equal(mv(mv(basis[i], basis[j]), basis[k]), mv(basis[i], mv(basis[j], basis[k])))
        for i in range(DEG) for j in range(DEG) for k in range(DEG))
    # polynomial basis: does some basis element act as the companion shift?
    poly = None
    for b in range(1, DEG):
        M = mats[b]
        if all(M[i, i + 1] == 1 and int(M[i].sum()) == 1 for i in range(DEG - 1)):
            p = (1 << DEG)
            for k in range(DEG):
                p |= int(M[DEG - 1, k]) << k
            poly = {'basis_element': b, 'modulus': p, 'modulus_hex': hex(p)}
            break
    rep['polynomial_basis'] = poly
    return rep


BLOCKS = [(17576206, 'fwd0'), (17585915, 'fwd1'), (21385877, 'c132_0'),
          (21435178, 'c132_1'), (36295669, 'rev0'), (40670415, 'rev_mid')]


def analyse_block(c, start, name):
    ops = c.decode(start, start + 9000)
    ccx = [o for o in ops if o[1] == 'CCX'][:42]
    tri = {tuple(q // DEG for q in o[2]) for o in ccx}
    rec = {'name': name, 'first_ccx': start, 'last_ccx': ccx[-1][0],
           'n_ccx_taken': len(ccx), 'word_triples': ['/'.join(map(str, t)) for t in sorted(tri)]}
    if len(tri) != 1:
        rec['status'] = 'mixed-word-triple'
        return rec
    (wa, wb, wc), = tri
    rec['words'] = {'A': wa, 'B': wb, 'C': wc,
                    'A_qubits': [wa * DEG, wa * DEG + DEG - 1],
                    'B_qubits': [wb * DEG, wb * DEG + DEG - 1],
                    'C_qubits': [wc * DEG, wc * DEG + DEG - 1]}
    rec['ccx_target_qubits'] = sorted({o[2][2] for o in ccx})
    rec['ccx_cond_depth'] = sorted({str(o[4]) for o in ccx})
    lo, hi = word_closure_window(c, ccx[0][0], ccx[-1][0] + 1, {wa, wb, wc})
    wops = c.decode(lo, hi)
    # scratch-bit liveness: the 42 CCX targets are the product scratch bits
    tgt = sorted({o[2][2] for o in ccx})
    wide = c.decode(max(0, lo - 2000), min(c.num_ops, hi + 2000))
    touch = [i for (i, nm, qs, tb, cb) in wide if any(q in tgt for q in qs)]
    rec['scratch_liveness'] = {'bits': tgt, 'first_op': touch[0], 'last_op': touch[-1],
                              'width': touch[-1] - touch[0] + 1,
                              'window_width': hi - lo,
                              'window_inside_liveness': bool(lo >= touch[0] and hi - 1 <= touch[-1])}
    rec['window'] = {'lo': lo, 'hi': hi, 'n_ops': len(wops),
                     'census': {k: sum(1 for o in wops if o[1] == k) for k in {o[1] for o in wops}}}
    cl = anf_closure(wops, wa, wb, wc)
    if cl is None:
        rec['status'] = 'anf-invalid'
        return rec
    ident, acc, bad = cl
    wA = {wa * DEG + b for b in range(DEG)}
    wB = {wb * DEG + b for b in range(DEG)}
    wC = {wc * DEG + b for b in range(DEG)}
    rec['closure'] = {
        'n_ident': len(ident), 'n_acc': len(acc), 'n_bad': len(bad),
        'A_restored': bool(wA <= ident), 'B_restored': bool(wB <= ident),
        'bad_words': sorted({q // DEG for q in bad}),
        'acc_words': sorted({q // DEG for q in acc}),
        'touched_outside_ABC': sorted({q // DEG for q in (set(ident) | set(acc) | set(bad))
                                       if q // DEG not in (wa, wb, wc)}),
    }
    r = extract_tensor(wops, c.num_qubits, wa, wb, wc)
    T = r['T']
    rec['linear_part_bits'] = {'A_to_C': int(r['LA'].sum()), 'B_to_C': int(r['LB'].sum())}
    rec['n_touched_qubits'] = len(r['touched'])
    rec['field'] = field_report(T)
    rec['bilinear_random_check'] = bilinear_check(wops, c.num_qubits, wa, wb, wc, T)
    try:
        terms, Ta = anf_terms(wops, wa, wb, wc)
        rec['anf'] = {'n_ands': len(terms),
                      'agrees_with_bitslice': bool(np.array_equal(Ta, T)),
                      'u_popcounts': sorted({t['u'].bit_count() for t in terms}),
                      'v_popcounts': sorted({t['v'].bit_count() for t in terms}),
                      'w_popcounts': sorted({t['w'].bit_count() for t in terms}),
                      'distinct_u': len({t['u'] for t in terms}),
                      'distinct_v': len({t['v'] for t in terms}),
                      'distinct_uv': len({(t['u'], t['v']) for t in terms}),
                      'distinct_w': len({t['w'] for t in terms}),
                      'u_span_rank': int(gf2_rank(np.array(
                          [[(t['u'] >> b) & 1 for b in range(DEG)] for t in terms], np.uint8))),
                      'v_span_rank': int(gf2_rank(np.array(
                          [[(t['v'] >> b) & 1 for b in range(DEG)] for t in terms], np.uint8))),
                      'rank1_terms_expanded': int(sum(t['u'].bit_count() * t['v'].bit_count()
                                                      for t in terms))}
        rec['terms'] = terms
    except Exception as ex:
        rec['anf'] = {'error': str(ex), 'type': type(ex).__name__}
    rec['T'] = ''.join(str(x) for x in T.reshape(-1))
    rec['status'] = 'ok'
    return rec


c = ir.Circuit.read(TAPE)
say('tape', c.num_ops, c.num_qubits, c.num_bits, c.sha256()[:16])
OUT['tape'] = {'num_ops': c.num_ops, 'num_qubits': c.num_qubits, 'num_bits': c.num_bits,
               'sha256': c.sha256()}

# ---- register table: does S_i = qubits 12i..12i+11 hold in the tape itself? -----
bad_reg, named = [], []
for nm, ids in c.registers:
    q = ids[ids >> 31 == 1] & 0x7FFFFFFF
    if not len(q):
        continue
    if nm and nm.startswith('S') and nm[1:].isdigit():
        i = int(nm[1:])
        if sorted(q.tolist()) != list(range(DEG * i, DEG * i + DEG)):
            bad_reg.append(nm)
        named.append(i)
    if int(q.min()) >= 840:
        bad_reg.append('pool:' + str(nm))
OUT['tape']['registers'] = {
    'n_registers': len(c.registers),
    'n_named_S': len(named), 'S_index_range': [min(named), max(named)] if named else None,
    'S_not_12i_12i11': bad_reg[:10], 'n_bad': len(bad_reg)}
say('registers', OUT['tape']['registers'])
OUT['km_modulus'] = int(FM.modulus)
OUT['blocks'] = []
for (s, nm) in BLOCKS:
    r = analyse_block(c, s, nm)
    OUT['blocks'].append(r)
    if r['status'] == 'ok':
        f = r['field']
        say(nm, 'scratch liveness', r.get('scratch_liveness', {}).get('width'),
            'window', r['window']['lo'], r['window']['hi'])
        say(nm, r['words']['A'], r['words']['B'], r['words']['C'],
            'window', r['window']['lo'], r['window']['hi'],
            'A_rest', r['closure']['A_restored'], 'B_rest', r['closure']['B_restored'],
            'bad', r['closure']['n_bad'], 'ones', f['one_bits'],
            'eq_field', f['equals_km_field_mul'], 'assoc', f['associative'],
            'linA', r['linear_part_bits']['A_to_C'], 'linB', r['linear_part_bits']['B_to_C'],
            'bilin_mismatch', r['bilinear_random_check']['mismatches'],
            'anf', r.get('anf', {}).get('agrees_with_bitslice'))
    else:
        say(nm, r['status'], r['words'])

# ---- cluster census (op counts only, no simulation) ---------------------------
SPANS = {'fwd_cluster': (19508954, 21385877), 'rev_cluster': (46230185, 52842219)}
OUT['clusters'] = {}
for nm, (a, b) in SPANS.items():
    cnt = collections.Counter()
    ccx = 0
    step = 200000
    for s in range(a, b, step):
        for (i, name, qs, tb, cb) in c.decode(s, min(b, s + step)):
            cnt[name] += 1
            if name == 'CCX':
                ccx += 1
    OUT['clusters'][nm] = {'lo': a, 'hi': b, 'n_ops': b - a, 'CCX': ccx,
                           'CX': cnt['CX'], 'SWAP': cnt['SWAP'],
                           'CX_per_CCX': round(cnt['CX'] / max(ccx, 1), 2), 'census': dict(cnt)}
    say(nm, 'ops', b - a, 'CCX', ccx, 'CX', cnt['CX'], 'CX/CCX', OUT['clusters'][nm]['CX_per_CCX'])

p = WORK / 'dqi_fastshift.json'
p.write_text(json.dumps(OUT, indent=1))
say('wrote', p, p.stat().st_size)
if RAWF.exists():
    RAWF.unlink()
    say('deleted', RAWF)
