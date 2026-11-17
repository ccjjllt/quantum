"""invsqrt 0af21cb8: wire-liveness / compaction census, with the OFFICIAL kickmix.so.

Question: can the shipped 44-qubit inverse-square-root circuit be COMPACTED (wire
renaming that reuses one physical wire for two previously distinct wires with
disjoint live ranges) to 42 or 40 declared qubits, keeping the identical gate
multiset?

Static only: this kernel parses the tape and counts live wires.  It does NOT run
the verifier and does NOT simulate the circuit.

Models:
  A  naive interval = [first op touching the wire, last op touching it]
  B  constancy: a wire is occupied while it holds a value that is not a known
     computational-basis constant.  All writes on this tape are XOR-accumulating,
     so a wire can only be released by an (unconditional) HMR measure+reset.
  C  reset segments: split every wire at its unconditional HMRs, then colour the
     resulting intervals (interval-graph clique = peak, greedy = min #wires).
Also exhaustively tests every wire pair for disjoint live ranges.

CPU only: enable_gpu=false, enable_tpu=false, no internet.
"""
from __future__ import annotations

import base64
import collections
import hashlib
import itertools
import json
import pathlib
import re
import sys
import zlib

WORK = pathlib.Path('/kaggle/working')
INPUT = pathlib.Path('/kaggle/input')
WANT_SHA = '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b'
B64_TEXT = '''__B64__'''

ONE_Q = {'X', 'Z', 'H', 'R', 'Z_POW', 'NEG'}
CLASSICAL = {'BIT_INVERT', 'BIT_STORE0', 'BIT_STORE1'}

REPORT = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


for comp in sorted(INPUT.glob('*')):
    if (comp / 'kickmix').is_dir():
        COMP = comp
        break
else:
    hits = list(INPUT.rglob('verify_submission_invsqrt.py'))
    COMP = hits[0].parent.parent.parent
sys.path.insert(0, str(COMP / 'kickmix'))
import kickmix  # noqa: E402

K_SHA = hashlib.sha256((COMP / 'kickmix/kickmix.so').read_bytes()).hexdigest()
log(f'mount {COMP}')
log(f'kickmix sha {K_SHA}')

raw = zlib.decompress(base64.b64decode(B64_TEXT))
sha = hashlib.sha256(raw).hexdigest()
log(f'pinned circuit {len(raw)} B sha {sha}')
assert sha == WANT_SHA, sha
p = WORK / 'invsqrt_0af21cb8.kmb'
p.write_bytes(raw)

circuit = kickmix.Circuit.from_file(str(p), format='kmb')
stats = circuit.operation_statistics()
log(f'num_qubits {circuit.num_qubits} num_bits {circuit.num_bits} '
    f'num_registers {circuit.num_registers} ops {len(circuit)}')
log(f'registers {[(k, len(v)) for k, v in circuit.register_data.items()]}')
log(f'stats {dict(stats)}')

kmx = WORK / 'invsqrt_0af21cb8.kmx'
with kmx.open('w') as f:
    circuit.to_file(f, format='kmx')
lines = kmx.read_text().splitlines()
header = [l for l in lines if l.startswith('APPEND_TO_REGISTER') or l.startswith('REGISTER')]
body = [l for l in lines if l not in header]
assert len(body) == len(circuit), (len(body), len(circuit))
log(f'kmx body {len(body)} header {len(header)}')

# ---------------------------------------------------------------- parse the tape
ops = []
depth = 0
max_depth = 0
for i, line in enumerate(body):
    tok = line.split()
    name = tok[0]
    if name == 'PUSH_CONDITION':
        depth += 1
        max_depth = max(max_depth, depth)
        continue
    if name == 'POP_CONDITION':
        depth -= 1
        continue
    qs = [int(t[1:]) for t in tok[1:] if re.fullmatch(r'q\d+', t)]
    ops.append({'i': i, 'op': name, 'q': qs, 'cond': 'if' in tok, 'depth': depth})
NW = circuit.num_qubits
hmr = [o for o in ops if o['op'] == 'HMR']
log(f'parsed ops {len(ops)} cond nesting max {max_depth} '
    f'HMR {len(hmr)} conditional HMR {sum(1 for o in hmr if o["cond"])}')

first = [None] * NW
last = [None] * NW
for o in ops:
    for w in o['q']:
        if first[w] is None:
            first[w] = o['i']
        last[w] = o['i']
assert all(f is not None for f in first), 'unused wire'


def sweep(segs):
    ev = []
    for s, e, w in segs:
        ev.append((s, 1, w))
        ev.append((e, 0, w))
    ev.sort(key=lambda x: (x[0], x[1]))
    live = set()
    peak = 0
    at = None
    who = []
    for idx, kind, w in ev:
        if kind:
            live.add(w)
        else:
            live.discard(w)
        if len(live) > peak:
            peak, at, who = len(live), idx, sorted(live)
    return peak, at, who


# ------------------------------------------------------------------- model A
segA = [(first[w], last[w], w) for w in range(NW)]
peakA, atA, setA = sweep(segA)
log(f'A interval peak {peakA} at op {atA} wires {setA}')


# ------------------------------------------------------------------- model B
def occupancy(exclude=frozenset()):
    const = [True] * NW
    val = [0] * NW
    for w in range(22):          # x register q0..q21 holds arbitrary input |x>
        const[w] = False
    curve = []
    peak = 0
    peak_at = None
    peak_set = []
    for o in ops:
        name, qs = o['op'], o['q']
        if name == 'HMR' and qs and not o['cond']:
            const[qs[0]] = True
            val[qs[0]] = 0
        elif name == 'X' and qs:
            if const[qs[0]]:
                val[qs[0]] ^= 1
        elif name == 'CX' and len(qs) == 2:
            a, b = qs
            if not const[a]:
                const[b] = False
            elif val[a] == 1 and const[b]:
                val[b] ^= 1
        elif name in ('CCX', 'CCZ') and len(qs) == 3:
            a, b, c = qs
            if not const[a] and not const[b]:
                if name == 'CCX':
                    const[c] = False
            elif not const[a] and const[b] and val[b] and name == 'CCX':
                const[c] = False
            elif not const[b] and const[a] and val[a] and name == 'CCX':
                const[c] = False
            elif name == 'CCX' and const[a] and const[b] and val[a] and val[b] and const[c]:
                val[c] ^= 1
        elif name == 'SWAP' and len(qs) == 2:
            a, b = qs
            const[a], const[b] = const[b], const[a]
            val[a], val[b] = val[b], val[a]
        elif name == 'CSWAP' and len(qs) == 3:
            a, b, c = qs
            if (not const[a]) or val[a] == 1:
                const[b], const[c] = const[c], const[b]
                val[b], val[c] = val[c], val[b]
        elif name in ONE_Q or name in CLASSICAL:
            pass
        k = sum(1 for w in range(NW) if not const[w] and w not in exclude)
        curve.append((o['i'], k))
        if k > peak:
            peak, peak_at = k, o['i']
            peak_set = [w for w in range(NW) if not const[w] and w not in exclude]
    return curve, peak, peak_at, peak_set


base, peakB, atB, setB = occupancy()
log(f'B constancy peak {peakB} at op {atB}  ({body[atB]})')
log(f'B wires at peak: {setB}')
hist = collections.Counter(k for _, k in base)
log(f'B occupancy histogram {dict(sorted(hist.items(), reverse=True))}')
for thr in (44, 43, 42, 41, 40):
    idx = [i for i, k in base if k >= thr]
    if idx:
        log(f'B ops with occupancy >= {thr}: {len(idx)} window {idx[0]}..{idx[-1]}')
log('B single-wire removal -> peak: ' +
    str({w: occupancy(frozenset([w]))[1] for w in range(NW)}))
for pair in [(24, 25), (22, 25), (22, 23)]:
    log(f'B removing {pair} -> peak {occupancy(frozenset(pair))[1]}')

# ------------------------------------------------------------------- model C
cur = [None] * NW
segs = []
for o in ops:
    for w in o['q']:
        is_hmr = o['op'] == 'HMR' and o['q'][0] == w and not o['cond']
        if cur[w] is None:
            cur[w] = o['i']
        if is_hmr:
            segs.append((cur[w], o['i'], w))
            cur[w] = None
for w in range(NW):
    if cur[w] is not None:
        segs.append((cur[w], last[w], w))
peakC, atC, setC = sweep(segs)
log(f'C reset-segment peak {peakC} at op {atC}; segments {len(segs)}; '
    f'segments/wire {[sum(1 for s in segs if s[2] == w) for w in range(NW)]}')

# interval colouring == minimum number of physical wires for this segment set
order = sorted(segs, key=lambda s: (s[0], s[1]))
free = {}
ncol = 0
for s, e, w in order:
    pick = None
    for c, l in free.items():
        if l < s:
            pick = c
            break
    if pick is None:
        pick = ncol
        ncol += 1
    free[pick] = e
log(f'C greedy interval colouring uses {ncol} physical wires (min for this tape)')

# exhaustive disjoint-pair test
def disjoint(a, b):
    for s1, e1 in [(s, e) for s, e, w in segs if w == a]:
        for s2, e2 in [(s, e) for s, e, w in segs if w == b]:
            if not (e1 < s2 or e2 < s1):
                return False
    return True


pairs = [(a, b) for a, b in itertools.combinations(range(NW), 2) if disjoint(a, b)]
log(f'C wire pairs with disjoint live ranges: {len(pairs)} {pairs[:20]}')

# --------------------------------------------------------------- cost summary
C_UNIT = 74797.36535717871 / 44
GOLD = 70486.58
summary = {
    'circuit_sha256': sha,
    'kickmix_sha256': K_SHA,
    'num_qubits': int(circuit.num_qubits),
    'num_ops': len(circuit),
    'static_toffoli_like': int(stats.num_toffoli_like),
    'peak_A_interval': peakA,
    'peak_A_op': atA,
    'peak_B_constancy': peakB,
    'peak_B_op': atB,
    'peak_B_op_text': body[atB],
    'peak_B_wires': setB,
    'peak_C_segment': peakC,
    'peak_C_op': atC,
    'min_wires_interval_colouring': ncol,
    'disjoint_wire_pairs': len(pairs),
    'occupancy_hist': dict(sorted(hist.items(), reverse=True)),
    'C_per_qubit_current': C_UNIT,
    'gold_cost_target': GOLD,
    'note': 'static tape analysis only; no simulation, no verifier run',
}
log('SUMMARY ' + json.dumps(summary))
(WORK / 'liveness.json').write_text(json.dumps(summary, indent=2))
(WORK / 'report.txt').write_text('\n'.join(REPORT) + '\n')
log('done')
