import io
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')
MAXX = 3133452
NROT = 41

C = km.Circuit.from_file(ROOT / 'artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb')
BUF = io.StringIO(); C.to_file(BUF, format='kmx')
LINES = BUF.getvalue().splitlines()
HDR = [l for l in LINES if l.startswith(('APPEND', 'REGISTER'))]
OPS = [l for l in LINES if not l.startswith(('APPEND', 'REGISTER'))]
NQ = C.num_qubits

D = np.load(ROOT / 'artifacts/20261105_rotlp/full_masks.npz')
ROT_IDX = [int(x) for x in D['rot_idx']]
ROT_POS = {op: k for k, op in enumerate(ROT_IDX)}
BASE_INT = []
for k in range(NROT):
    BASE_INT.append(int.from_bytes(D['mask_%d' % k].tobytes(), 'little'))

ALL = (1 << MAXX) - 1


def fresh_wires():
    wires = [0] * NQ
    xs = np.arange(1, MAXX + 1, dtype=np.uint64)
    for b in range(22):
        bv = ((xs >> np.uint64(b)) & np.uint64(1)).astype(np.uint8)
        wires[b] = int.from_bytes(np.packbits(bv, bitorder='little').tobytes(), 'little')
    return wires


def step(wires, l, rot_masks):
    p = l.split()
    tag = p[0]
    if tag == 'CX':
        a, t = int(p[1][1:]), int(p[2][1:])
        wires[t] ^= wires[a]
    elif tag == 'CCX':
        a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
        wires[t] ^= wires[a] & wires[b]
    elif tag == 'X':
        wires[int(p[1][1:])] ^= ALL
    elif tag == 'HMR':
        wires[int(p[1][1:])] = 0
    elif tag == 'SWAP':
        a, b = int(p[1][1:]), int(p[2][1:])
        wires[a], wires[b] = wires[b], wires[a]
    elif tag == 'CSWAP':
        cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
        d = wires[cc] & (wires[a] ^ wires[b])
        wires[a] ^= d
        wires[b] ^= d
    elif tag == 'Z_POW':
        pass
    elif tag in ('Z', 'CZ', 'CCZ', 'R', 'NEG', 'BIT_STORE0', 'BIT_STORE1',
                 'BIT_INVERT', 'PUSH_CONDITION', 'POP_CONDITION'):
        pass
    else:
        raise ValueError(l)


def run_window(job):
    wid, a, b, variants = job
    wires = fresh_wires()
    rot_masks = {}
    for i in range(0, a):
        l = OPS[i]
        step(wires, l, None)
        if l.split()[0] == 'Z_POW' and i in ROT_POS:
            rot_masks[ROT_POS[i]] = wires[int(l.split()[1][1:])]
    base_prefix = list(wires)
    out = []
    for kind, spec in variants:
        wires = list(base_prefix)
        masks = dict(rot_masks)
        for i in range(a, len(OPS)):
            if spec[0] == 'del' and i == spec[1]:
                continue
            if spec[0] == 'delmod' and i == spec[1]:
                continue
            l = OPS[i]
            if spec[0] == 'delmod' and i == spec[2]:
                l = spec[3]
            step(wires, l, None)
            if l.split()[0] == 'Z_POW' and i in ROT_POS:
                masks[ROT_POS[i]] = wires[int(l.split()[1][1:])]
        ok = all(masks.get(k, 0) == BASE_INT[k] for k in range(NROT))
        out.append((wid, kind, 'SURVIVOR' if ok else 'rotmask'))
    return out


def window_support(a, b):
    s = set()
    for i in range(a, b):
        p = OPS[i].split()
        for t in p[1:]:
            if re.fullmatch(r'q\d+', t):
                s.add(t)
    return sorted(s)


if __name__ == '__main__':
    import glob as _glob
    wins = set()
    for f in _glob.glob('experiments/invsqrt/20261105_shared_target/*.md') + \
             _glob.glob('experiments/invsqrt/20261105_w15395/*.md'):
        for m in re.finditer(r'\[(\d+),(\d+)\)', open(f, errors='ignore').read()):
            wins.add((int(m.group(1)), int(m.group(2))))

    def tested_overlap(a, b):
        return any(not (e <= a or s >= b) for s, e in wins)

    ccx = [i for i, l in enumerate(OPS) if l.split()[0] == 'CCX' and 16000 <= i < 25800]
    triples = []
    for k in range(len(ccx) - 2):
        a, b = ccx[k], ccx[k + 2] + 1
        if b - a <= 120 and not tested_overlap(a, b):
            triples.append((a, b, ccx[k], ccx[k + 1], ccx[k + 2]))
    print('fresh triples:', len(triples), flush=True)
    jobs = []
    total = 0
    for wid, (a, b, p0, p1, p2) in enumerate(triples):
        support = window_support(a, b)
        paid = [p0, p1, p2]
        variants = []
        for d in range(3):
            variants.append(('del-%d' % paid[d], ('del', paid[d])))
        for d in range(3):
            for m in range(3):
                if m == d:
                    continue
                pm = paid[m]
                pp = OPS[pm].split()
                cur = pp[3]
                for tgt in support:
                    if tgt == cur:
                        continue
                    nl = '%s %s %s %s' % (pp[0], pp[1], pp[2], tgt)
                    variants.append(('del%d-mod%d->%s' % (paid[d], paid[m], tgt),
                                     ('delmod', paid[d], pm, nl)))
        total += len(variants)
        jobs.append((wid, a, b, variants))
    print('total candidates:', total, flush=True)
    t0 = time.time()
    counts = {}
    survivors = []
    with Pool(10) as pool:
        for out in pool.imap_unordered(run_window, jobs, chunksize=2):
            for wid, kind, res in out:
                counts[res] = counts.get(res, 0) + 1
                if res == 'SURVIVOR':
                    survivors.append((wid, kind))
                    print('SURVIVOR window=%s kind=%s' % (triples[wid][:2], kind), flush=True)
    print('done in %.0fs' % (time.time() - t0))
    print('verdict counts:', counts)
    print('survivors:', survivors)
    Path('/tmp/skel2_survivors.txt').write_text('\n'.join('%d %s' % (w, k) for w, k in survivors))
