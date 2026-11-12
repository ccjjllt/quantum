"""End-to-end test of the output-basis idea on a real circuit (k=4, lowbits=4, per-output ESOP).

  1. identity: decompose the 40 delta bits of circuit k=4, build the circuit, replay it
     symbolically over all 2048 addresses, count CCX.
  2. basis:    pick a random invertible B (40x40 over GF(2)), build the same decomposition for
     g = B f, build the circuit, then apply the CX recovery network f = B^-1 g on the word
     register (CX only, 0 T) and check the words are restored exactly.

The point is not that this construction is competitive (per-output is worse than Maoxin's
shared products), but that the transform + free-CX recovery is *semantically* valid and that
the CCX count does not go down: it goes up, because every nonzero element of the 40-dim space
has interior rank 15 and only the 5 zero-padded LSBs are cheaper.

Usage: python basis_roundtrip.py [--write /tmp/dir]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'))
import tensorqrom8 as tq  # noqa: E402

W_PATH = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
J, BROT, LOWBITS, N = 5, 8, 4, 1220
NQUBIT_BITS = 2048


def delta_of(W, k):
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def bits40(delta):
    out = np.zeros((N, 40), np.uint8)
    for j in range(J):
        for b in range(BROT):
            out[:, j * BROT + b] = (delta[:, j] >> b) & 1
    return out


def pack_words(bits):
    """(N, 40) bits -> (N, 5) words, little endian per word."""
    arr = np.asarray(bits)
    d = np.zeros((arr.shape[0], J), np.int64)
    for j in range(J):
        for b in range(BROT):
            d[:, j] |= arr[:, j * BROT + b].astype(np.int64) << b
    return d


def invertible(rng):
    while True:
        B = rng.integers(0, 2, (40, 40)).astype(np.uint8)
        piv, rk = {}, 0
        for o in range(40):
            v = int(sum(int(B[o, c]) << c for c in range(40)))
            while v:
                p = v.bit_length() - 1
                if p in piv:
                    v ^= piv[p]
                else:
                    piv[p] = v
                    rk += 1
                    break
        if rk == 40:
            return B


def inverse(B):
    """Gauss-Jordan over GF(2) on 40x40."""
    n = 40
    A = [[int(B[i][j]) for j in range(n)] + [1 if i == j else 0 for j in range(n)] for i in range(n)]
    row = 0
    for col in range(n):
        piv = next((r for r in range(row, n) if A[r][col]), None)
        if piv is None:
            continue
        A[row], A[piv] = A[piv], A[row]
        for r in range(n):
            if r != row and A[r][col]:
                A[r] = [a ^ b for a, b in zip(A[r], A[row])]
        row += 1
    return np.array([[A[i][n + j] for j in range(n)] for i in range(n)], np.uint8)


def replay_kmx(path: Path, nq: int):
    """Final truth table of every qubit, plus the gate histogram (R/HMR reset to 0)."""
    lines = path.read_text().splitlines()
    names, regs = {}, {}
    for ln in lines:
        m = re.fullmatch(r'APPEND_TO_REGISTER q(\d+) r(\d+)', ln)
        if m:
            regs.setdefault(int(m.group(2)), []).append(int(m.group(1)))
        m = re.fullmatch(r'REGISTER r(\d+) "(\w+)"', ln)
        if m:
            names[int(m.group(1))] = m.group(2)
    qname = {}
    for rid, qs in regs.items():
        nm = names[rid]
        for i, q in enumerate(qs):
            qname[q] = (f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}')
    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            i = int(nm[3:])
            period = 1 << i
            block = ((1 << period) - 1) << period
            v = 0
            for s in range(0, NQUBIT_BITS, 2 * period):
                v |= block << s
            f[q] = v
    hist = {}
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g, qs = parts[0], [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        hist[g] = hist.get(g, 0) + 1
        if g == 'CX':
            f[qs[1]] ^= f[qs[0]]
        elif g == 'CCX':
            f[qs[2]] ^= f[qs[0]] & f[qs[1]]
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ((1 << NQUBIT_BITS) - 1)
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown {g}')
    return f, qname, hist


def word_qubits(qname, nq):
    return [q for q in range(nq) if qname.get(q, '').startswith('w')]


def main() -> None:
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/tmp/esop_roundtrip')
    outdir.mkdir(parents=True, exist_ok=True)
    W = np.load(W_PATH)['angle_words']
    delta = delta_of(W, 4)
    b_id = bits40(delta)
    rng = np.random.default_rng(11)

    results = {}
    for tag, bits in (('identity', b_id), ('randomB', None)):
        if tag == 'randomB':
            B = invertible(rng)
            bits = ((b_id.astype(np.int64) @ B.T.astype(np.int64)) & 1).astype(np.uint8)
        d = pack_words(bits)
        C = tq.anf_tensor(d, BROT, LOWBITS, full=True)
        terms = tq.per_output(C)
        c = tq.build_circuit(d, terms, 11, BROT, LOWBITS, full=True)
        path = outdir / f'{tag}.kmx'
        c.to_file(path, format='kmx')
        f, qname, hist = replay_kmx(path, c.num_qubits)
        wq = word_qubits(qname, c.num_qubits)
        got = [f[q] for q in wq]
        # expected: the truth table of g over the 2048 padded addresses
        # only the 1220 real addresses matter: the ANF truncates q at H = ceil(1220/16) = 77,
        # so monomials of q >= 77 are dropped and rows 1220..2047 are don't-care garbage.
        exp = [0] * 40
        for o in range(40):
            v = 0
            for a in range(N):
                if bits[a, o]:
                    v |= 1 << a
            exp[o] = v
        mask = (1 << N) - 1
        exp_id = [0] * 40
        for o in range(40):
            v = 0
            for a in range(N):
                if b_id[a, o]:
                    v |= 1 << a
            exp_id[o] = v
        ok_native = all((g & mask) == e for g, e in zip(got, exp))
        n_ccx = hist.get('CCX', 0)
        if tag == 'randomB':
            # CX recovery: f = B^-1 g on the word bits.  CX gates must read the *old* g, so
            # keep the source list fixed and build the new one (equivalent to a CX network
            # applied in place with the standard copy discipline).
            Binv = inverse(B)
            src = list(got)
            new = []
            for o in range(40):
                v = 0
                for cc in range(40):
                    if Binv[o, cc]:
                        v ^= src[cc]
                new.append(v)
            ok_recovered = all((g & mask) == e for g, e in zip(new, exp_id))
        else:
            ok_recovered = None
        results[tag] = dict(ccx=n_ccx, qubits=c.num_qubits, native=ok_native,
                            recovered=ok_recovered, cx=hist.get('CX', 0), r=hist.get('R', 0))
        print(f'{tag}: qubits={c.num_qubits} CCX={n_ccx} CX={hist.get("CX",0)} R={hist.get("R",0)}'
              f' | circuit computes its own g exactly = {ok_native}'
              + (f' | XOR-recovered f (0 T) = {ok_recovered}' if ok_recovered is not None else ''))

    did = results['identity']['ccx']
    db = results['randomB']['ccx']
    print(f'\nidentity per-output T = {did}  (products {did - results["identity"]["r"]}'
          f' + cache {results["identity"]["r"]})')
    print(f'random-B  per-output T = {db}  (products {db - results["randomB"]["r"]}'
          f' + cache {results["randomB"]["r"]})')
    print(f'delta = {db - did:+d} CCX; Maoxin k=4 shared-product reference = 268')
    print('kmx files written to', outdir)


if __name__ == '__main__':
    main()
