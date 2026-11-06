import io
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')
MAXX = 3133452
c = km.Circuit.from_file(ROOT / 'artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb')
buf = io.StringIO(); c.to_file(buf, format='kmx')
ops = [l for l in buf.getvalue().splitlines() if not l.startswith(('APPEND', 'REGISTER'))]
nq = c.num_qubits

xs = np.arange(1, MAXX + 1, dtype=np.uint64)
ALL = (1 << MAXX) - 1
wires = [0] * nq
for b in range(22):
    bitsv = ((xs >> np.uint64(b)) & np.uint64(1)).astype(np.uint8)
    wires[b] = int.from_bytes(np.packbits(bitsv, bitorder='little').tobytes(), 'little')

parsed = []
for l in ops:
    p = l.split()
    qs = [int(t[1:]) for t in p[1:] if re.fullmatch(r'q\d+', t)]
    bs = [int(t[1:]) for t in p[1:] if re.fullmatch(r'b\d+', t)]
    guard = int(p[p.index('if') + 1][1:]) if 'if' in p else None
    parsed.append((p[0], qs, bs, guard, l))

bl = {}
frames = []

def fmask():
    m = ALL
    for g in frames:
        m &= bl.get(g, 0)
    return m

bit_writes = defaultdict(list)
diag = []
for i, (tag, qs, bs, guard, l) in enumerate(parsed):
    gm = fmask()
    if guard is not None:
        gm &= bl.get(guard, 0)
    if tag == 'PUSH_CONDITION':
        frames.append(guard); continue
    if tag == 'POP_CONDITION':
        frames.pop(); continue
    if tag == 'CCZ':
        a, b, t = qs
        diag.append((i, 'CCZ', wires[a] & wires[b] & wires[t], guard, tuple(frames)))
    elif tag == 'CZ':
        a, b = qs
        diag.append((i, 'CZ', wires[a] & wires[b], guard, tuple(frames)))
    elif tag == 'Z':
        diag.append((i, 'Z', wires[qs[0]], guard, tuple(frames)))
    if tag == 'HMR':
        bl[bs[0]] = wires[qs[0]]; wires[qs[0]] = 0
        bit_writes[bs[0]].append(i)
    elif tag == 'BIT_STORE0':
        bl[bs[0]] = 0; bit_writes[bs[0]].append(i)
    elif tag == 'BIT_STORE1':
        bl[bs[0]] = ALL; bit_writes[bs[0]].append(i)
    elif tag == 'BIT_INVERT':
        bl[bs[0]] = bl.get(bs[0], 0) ^ (bl.get(guard, 0) if guard is not None else ALL)
        bit_writes[bs[0]].append(i)
    elif tag == 'NEG':
        pass
    elif tag == 'X':
        wires[qs[0]] ^= gm
    elif tag == 'CX':
        wires[qs[1]] ^= wires[qs[0]] & gm
    elif tag == 'CCX':
        wires[qs[2]] ^= wires[qs[0]] & wires[qs[1]] & gm
    elif tag == 'CSWAP':
        cc, a, b = qs
        d = wires[cc] & (wires[a] ^ wires[b]) & gm
        wires[a] ^= d; wires[b] ^= d
    elif tag == 'SWAP':
        a, b = qs
        wires[a], wires[b] = wires[b], wires[a]
    elif tag == 'R':
        wires[qs[0]] = 0
    elif tag == 'Z_POW':
        pass
    elif tag in ('CZ', 'Z', 'CCZ'):
        pass
    else:
        raise ValueError(l)

print('diagonal gates:', len(diag))
groups = defaultdict(list)
for (i, kind, prod, guard, fr) in diag:
    groups[(kind, prod, guard, fr)].append(i)

dups = {k: v for k, v in groups.items() if len(v) > 1}
print('distinct (kind,prod,guard,frame):', len(groups), 'duplicated:', len(dups))

safe = []
for (kind, prod, guard, fr), idxs in sorted(dups.items(), key=lambda kv: -len(kv[1])):
    cond_bits = set(fr) | ({guard} if guard is not None else set())
    ok = True
    for a, b in zip(idxs, idxs[1:]):
        for cb in cond_bits:
            if any(a < w < b for w in bit_writes.get(cb, [])):
                ok = False
                break
    pop = bin(prod).count('1')
    print('  %s prod_pop=%d guard=%s frame_len=%d x%d ops %s  %s' %
          (kind, pop, guard, len(fr), len(idxs), idxs[:4], 'SAFE' if ok else 'frame-rewrite'))
    if ok:
        safe.append(((kind, prod, guard, fr), idxs))

print('SAFE groups (provably jointly redundant):', len(safe))
for key, idxs in safe:
    print('  %s ops %s' % (key[0], idxs))
    for i in idxs[:6]:
        print('     op %d %s' % (i, ops[i]))
Path('/tmp/diag_pairs.txt').write_text('\n'.join(
    '%s %s' % (key[0], ' '.join(map(str, idxs))) for key, idxs in safe))
