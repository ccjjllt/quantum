"""Census of the fixed Syed V9 DQI extract/unextract asymmetry.

Reads the flattened .kmx stream once and reports, for the two top-level
stages `extract` and `unextract`:

  * paid-gate totals and nested-tag counts;
  * blocks split at paid-gate line gaps > 5000 (the 17/23 node blocks);
  * CCX segments split at CCX line gaps > 100;
  * the count of 99-CCX multiplier-shaped segments per block;
  * a canonical (wire-renaming-invariant) CCX-shape diff between the two
    stages, which is the exact accounting of the +35,347 CCX;
  * exact duplicate segment signatures and the 42 duplicate 99-kernels;
  * canonical-shape provenance of every unextract segment against the
    forward stages (extract, synthesis, convert, scan, unconvert,
    unsynthesis);
  * phase-mixed classification of the segments.

No simulator and no official verifier are called.  Everything here is a
static op-stream measurement.
"""
import argparse
import collections
import json
from pathlib import Path

KMX_DEFAULT = ('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/'
               'T/opencode/dqi_phase/syed_v9.kmx')
ROOT = Path(__file__).resolve().parents[4]
OUT_DEFAULT = ROOT / 'artifacts/20261106_phase_recovery/subagents/unextract_census.json'

PHASE_OPS = {'HMR', 'CZ', 'CCZ', 'CSWAP', 'R', 'Z', 'X', 'BIT_INVERT',
             'BIT_STORE0', 'BIT_STORE1', 'NEG', 'PUSH_CONDITION',
             'POP_CONDITION'}
PAID = ('CCX ', 'CCZ ', 'CSWAP ')
PAID_BYTES = tuple(x.encode() for x in PAID)


def parse_stage(stream, stage):
    """Return paid records (line, op, args) inside the outermost `stage`."""
    recs = []
    stack = []
    inside = False
    for line_no, line in enumerate(stream):
        if line.startswith(b'INFO_TAG '):
            tag = line.strip().split(b'"', 2)[1].decode()
            if tag.startswith('@enter:'):
                name = tag[7:]
                if name == stage:
                    inside = True
                stack.append(name)
            else:
                if stack:
                    stack.pop()
                if tag[6:] == stage:
                    inside = False
            continue
        if not inside or not line.startswith(PAID_BYTES):
            continue
        p = line.split()
        recs.append((line_no, p[0].decode(), tuple(x.decode() for x in p[1:])))
    return recs


def paid_blocks(recs, gap=5000):
    """Split a stage at paid-gate line gaps > gap."""
    starts = [0]
    for i in range(1, len(recs)):
        if recs[i][0] - recs[i - 1][0] > gap:
            starts.append(i)
    starts.append(len(recs))
    return [(recs[a][0], recs[b - 1][0], b - a) for a, b in zip(starts, starts[1:])]


def ccx_segments(recs, gap=100):
    """Split a stage's CCX subsequence at line gaps > gap."""
    ccx = [r for r in recs if r[1] == 'CCX']
    if not ccx:
        return []
    starts = [0]
    for j in range(1, len(ccx)):
        if ccx[j][0] - ccx[j - 1][0] > gap:
            starts.append(j)
    starts.append(len(ccx))
    return [ccx[a:b] for a, b in zip(starts, starts[1:])]


def canon(triples):
    """Canonicalise a CCX triple sequence up to injective wire renaming."""
    mp = {}
    out = []
    for row in triples:
        r = []
        for x in row:
            if x not in mp:
                mp[x] = len(mp)
            r.append(mp[x])
        out.append(tuple(r))
    return tuple(out)


def triples(seg):
    return [(min(a, b), max(a, b), t) for _, a, b, t in
            [(r[0], r[2][0], r[2][1], r[2][2]) for r in seg]]


def shape(seg):
    return (len(seg), canon(triples(seg)))


def opcounts_for_segments(stream, segs):
    """Count every operation in each segment's [first CCX, last CCX] span."""
    ranges = [(s[0][0], s[-1][0]) for s in segs]
    counts = [collections.Counter() for _ in segs]
    ri = 0
    for line_no, line in enumerate(stream):
        if line_no < ranges[0][0]:
            continue
        if line_no > ranges[-1][1]:
            break
        while ri + 1 < len(ranges) and line_no > ranges[ri][1]:
            ri += 1
        while ri + 1 < len(ranges) and line_no > ranges[ri + 1][0]:
            ri += 1
        if line.startswith(b'INFO_TAG '):
            continue
        counts[ri][line.split(b' ', 1)[0].decode().strip()] += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kmx', default=KMX_DEFAULT)
    ap.add_argument('--out', default=str(OUT_DEFAULT))
    args = ap.parse_args()
    path = Path(args.kmx)

    stages = ['extract', 'synthesis', 'convert', 'scan', 'unconvert',
              'unsynthesis', 'unextract']
    recs = {}
    with path.open('rb') as f:
        # The five forward/recovery stages before unextract are cheap to
        # collect in the same pass; unextract is the last one.
        current = {}
        stack = []
        for line_no, line in enumerate(f):
            if line.startswith(b'INFO_TAG '):
                tag = line.strip().split(b'"', 2)[1].decode()
                if tag.startswith('@enter:'):
                    stack.append(tag[7:])
                else:
                    if stack:
                        stack.pop()
                continue
            if not line.startswith(PAID_BYTES) or not stack:
                continue
            top = stack[0]
            if top in stages:
                p = line.split()
                current.setdefault(top, []).append(
                    (line_no, p[0].decode(), tuple(x.decode() for x in p[1:])))
    recs = current
    for s in stages:
        recs.setdefault(s, [])

    # For the block/segment analysis we need to reread the two long stages
    # separately because the single pass above loses the stage boundary.
    # The records themselves are already exact; blocks are split on line
    # gaps, so no reread is needed.
    out = {'scope': 'Static op-stream census; no simulation or official verification.'}
    out['paid_totals'] = {s: dict(collections.Counter(r[1] for r in recs[s]))
                          for s in stages}
    out['paid_totals']['extract_ccx'] = len([r for r in recs['extract'] if r[1] == 'CCX'])
    out['paid_totals']['unextract_ccx'] = len([r for r in recs['unextract'] if r[1] == 'CCX'])
    out['paid_totals']['extra_ccx'] = (out['paid_totals']['unextract_ccx'] -
                                       out['paid_totals']['extract_ccx'])

    # Blocks and per-block 99-kernel counts.
    blocks = {}
    for s in ('extract', 'unextract'):
        bs = paid_blocks(recs[s])
        segs = ccx_segments(recs[s])
        # Assign segments to blocks by their first CCX line.
        per_block = []
        for (lo, hi, n) in bs:
            inside = [x for x in segs if lo <= x[0][0] <= hi]
            c = collections.Counter(len(x) for x in inside)
            per_block.append({'line_lo': lo, 'line_hi': hi,
                              'paid': n, 'ccx': sum(len(x) for x in inside),
                              'segments': len(inside), 'n99': c[99],
                              'ccx99': 99 * c[99]})
        blocks[s] = per_block
    out['blocks'] = blocks

    # Exact canonical-shape diff (wire renaming tolerated).
    def shape_counter(s):
        return collections.Counter(shape(x) for x in ccx_segments(recs[s]))

    se, su = shape_counter('extract'), shape_counter('unextract')
    known_extra = collections.Counter()
    novel_extra = collections.Counter()
    missing = collections.Counter()
    for k, v in su.items():
        e = se.get(k, 0)
        if v > e:
            (known_extra if e else novel_extra)[k[0]] += v - e
    for k, v in se.items():
        if su.get(k, 0) < v:
            missing[k[0]] += v - su.get(k, 0)
    wall = {
        'known_extra_ccx': sum(k * v for k, v in known_extra.items()),
        'novel_extra_ccx': sum(k * v for k, v in novel_extra.items()),
        'missing_ccx': -sum(k * v for k, v in missing.items()),
        'known_extra_by_size': dict(known_extra),
        'novel_extra_by_size': dict(novel_extra),
        'missing_by_size': dict(missing),
    }
    wall['net'] = (wall['known_extra_ccx'] + wall['novel_extra_ccx'] +
                   wall['missing_ccx'])
    out['shape_wall'] = wall

    # 99-kernel census.
    e99 = [x for x in ccx_segments(recs['extract']) if len(x) == 99]
    u99 = [x for x in ccx_segments(recs['unextract']) if len(x) == 99]
    out['kernels99'] = {
        'extract': len(e99),
        'unextract': len(u99),
        'extra': len(u99) - len(e99),
        'extra_ccx': 99 * (len(u99) - len(e99)),
        'extract_canonical_shapes': len({canon(triples(x)) for x in e99}),
        'unextract_canonical_shapes': len({canon(triples(x)) for x in u99}),
        'extract_shapes_subset_of_unextract':
            {canon(triples(x)) for x in e99} <=
            {canon(triples(x)) for x in u99},
    }

    # Exact duplicate segments (same wires) and duplicate 99-kernels.
    def duplicate_census(s):
        segs = ccx_segments(recs[s])
        sig = collections.defaultdict(list)
        for x in segs:
            sig[tuple(triples(x))].append(x)
        extra_by_size = collections.Counter()
        groups = 0
        extra_copies = 0
        for v in sig.values():
            if len(v) > 1:
                groups += 1
                extra_copies += len(v) - 1
                extra_by_size[len(v[0])] += len(v) - 1
        return {'duplicate_groups': groups,
                'extra_copies': extra_copies,
                'extra_ccx': sum(k * v for k, v in extra_by_size.items()),
                'extra_by_size': dict(extra_by_size)}

    out['exact_duplicates'] = {s: duplicate_census(s)
                               for s in ('extract', 'unextract')}

    # Canonical-shape provenance of every unextract segment.
    shapes_by_stage = {s: shape_counter(s) for s in stages}
    u_segs = ccx_segments(recs['unextract'])
    prov = collections.Counter()
    prov_detail = collections.Counter()
    order = ['extract', 'synthesis', 'convert', 'scan', 'unconvert',
             'unsynthesis']
    for x in u_segs:
        k = shape(x)
        hit = next((s for s in order if shapes_by_stage[s].get(k, 0)), 'novel')
        prov[hit] += len(x)
        prov_detail[(hit, len(x))] += 1
    out['unextract_shape_provenance'] = {
        'first_forward_shape_hit_ccx': dict(prov),
        'by_hit_and_size': {f'{k[0]}:{k[1]}': v for k, v in prov_detail.items()},
    }

    # Phase-mixed classification.
    e_counts = opcounts_for_segments(path.open('rb'), ccx_segments(recs['extract']))
    u_counts = opcounts_for_segments(path.open('rb'), ccx_segments(recs['unextract']))
    cls = {}
    for s, segs, counts in (('extract', ccx_segments(recs['extract']), e_counts),
                            ('unextract', u_segs, u_counts)):
        pure = mixed = 0
        for x, c in zip(segs, counts):
            if any(op in PHASE_OPS for op in c):
                mixed += len(x)
            else:
                pure += len(x)
        cls[s] = {'pure_ccx': pure, 'phase_mixed_ccx': mixed}
    cls['extra'] = {
        'pure_ccx': cls['unextract']['pure_ccx'] - cls['extract']['pure_ccx'],
        'phase_mixed_ccx': (cls['unextract']['phase_mixed_ccx'] -
                            cls['extract']['phase_mixed_ccx']),
    }
    out['phase_class'] = cls

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in
                      ('paid_totals', 'kernels99', 'shape_wall',
                       'exact_duplicates', 'phase_class')}, indent=1))


if __name__ == '__main__':
    main()
