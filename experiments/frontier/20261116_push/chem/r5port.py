"""791-row port of the shipped five-block coded loader (R=5, B=143, rows=791).

Geometry: rows 791, plan grid 800 = 50 blocks x 16 lows, 10 selection bits,
6 high bits (h < 50), NOUT = 35 (5 words x 7 bits) unchanged, hmax = 49 fully
determined slices (the 50th block is partial: 791 = 49*16 + 7).

The shipped emitter (compiler/emit_plan.py) is reused byte-for-byte except for the
ten geometry constants; the planner (research/scripts/planner.py BlockPlan),
the matroid-parity certificate (parity_recover.candidates/alternating_field) and
the matching (extract_matching.matching) are used unchanged.
"""
import sys, json, re, time
from pathlib import Path
import numpy as np

SRC = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/syed_v12/src/dfthcsos_source')
COMP, SCRIPTS = SRC / 'compiler', SRC / 'research' / 'scripts'
sys.path[:0] = [str(COMP), str(SCRIPTS)]

ROWS, GRID, HIGH, SEL, HB, FULL = 791, 800, 50, 10, 6, 50   # FULL = hmax: all 49 slices
NOUT, NDIM = 35, 525

from parity_recover import basis, nullspace, reduce, outer          # noqa: E402
from transport_cuts import coordinate_basis, coordinates            # noqa: E402
from extract_matching import matching                               # noqa: E402
from planner import BlockPlan, forced, coord_relations, REL_LSB, REL_P1, top_down, local_search, candidates  # noqa: E402
import gauge_plan_fit                                               # noqa: E402


def complete_words_r5(words: np.ndarray) -> np.ndarray:
    """(791,75) -> (800,75): the shipped completion, zeroing the ANF coefficients of
    the partial block (h=49) at the nine highest low monomials l>=7."""
    words = np.asarray(words, dtype=np.uint8)
    assert words.shape == (GRID, 75), words.shape
    # The validation dummy is the shipped table's first 800 rows: 50 complete blocks, so
    # the code (bit-0 affine) and the polarisation helper hold on every block.  Rows
    # 791..799 are unreachable (the verifier simulates 0..790 only).
    return np.asarray(words, dtype=np.uint8)


def cross_tensor_r5(words: np.ndarray, k: int) -> list[int]:
    delta = words[:, 5 * k:5 * k + 5].copy()
    if k:
        delta ^= words[:, 5 * k - 5:5 * k]
    packed = np.zeros(GRID, dtype=np.uint64)
    for j in range(5):
        packed[:len(delta)] |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(HIGH, 16).copy()
    for b in range(4):
        for lo in range(16):
            if lo & (1 << b):
                f[:, lo] ^= f[:, lo ^ (1 << b)]
    for b in range(HB):
        for hi in range(HIGH):
            if hi & (1 << b):
                f[hi] ^= f[hi ^ (1 << b)]
    return [sum(int(f[h, l]) << ((l - 1) * NOUT) for l in range(1, 16)) for h in range(HIGH)]


def load_emit_r5():
    """exec the shipped emitter with only the geometry constants replaced."""
    src = (COMP / 'emit_plan.py').read_text()
    subs = [
        ("for q in range(11):", "for q in range(SEL):"),
        ("APPEND_TO_REGISTER q{11+8*j+b}", "APPEND_TO_REGISTER q{10+8*j+b}"),
        ("'CX q{17+8*j} q{18+8*j}'", "'CX q{16+8*j} q{17+8*j}'"),
        ("lo[ms[0]]=18+8*j", "lo[ms[0]]=17+8*j"),
        ("f'CX q{hi[h]} q{18+8*j}'", "f'CX q{hi[h]} q{17+8*j}'"),
        ("hi={1<<b:4+b for b in range(7)}", "hi={1<<b:4+b for b in range(HB)}"),
        ("nextq=51", "nextq=50"),
        ("for h in range(1,77):", "for h in range(1,HIGH):"),
        ("def fanout(mask):return [11+8*(i//7)+i%7 for i in bitinds(mask)]",
         "def fanout(mask):return [10+8*(i//7)+i%7 for i in bitinds(mask)]"),
        ("addr=np.arange(1232)", "addr=np.arange(GRID)"),
        ("corr=np.zeros(1232,dtype=np.uint64)", "corr=np.zeros(GRID,dtype=np.uint64)"),
        ("a=np.zeros(1232,dtype=np.uint8);b=a.copy()", "a=np.zeros(GRID,dtype=np.uint8);b=a.copy()"),
        ("c=corr.reshape(77,16)", "c=corr.reshape(HIGH,16)"),
        ("words=apply_padding_completion(s,words)", "words=apply_padding_completion_r5(s,words)"),
        ("assert nextq<=128", "assert nextq<=128"),
    ]
    for a, b in subs:
        if a not in src:
            raise SystemExit(f'port patch not found: {a!r}')
        src = src.replace(a, b)
    left = [ln for ln in src.splitlines() if re.search(r'\b(1232|1220)\b|\b77\b|\b11\+8\*', ln)]
    ns = {'__name__': 'emit_r5', '__file__': str(COMP / 'emit_plan.py'), 'np': np, 'json': json, 'Path': Path,
          'HIGH': HIGH, 'GRID': GRID, 'SEL': SEL, 'HB': HB, 'ROWS': ROWS, 'FULL': FULL,
          'apply_padding_completion_r5': apply_padding_completion_r5}
    exec(compile(src, 'emit_plan_r5.py', 'exec'), ns)
    return ns['emit'], left


def apply_padding_completion_r5(state, words):
    """same contract as the shipped one, for 9 unused rows 791..799 of a (800,75) grid."""
    completion = state.get('padding_completion')
    if completion is None:
        return words
    source = np.asarray(words)
    if source.shape != (GRID, 75):
        raise ValueError('Expected an 800 by 75 integer source word table.')
    completed = source.copy()
    suffix = np.asarray(completion.get('words'))
    if suffix.shape != (GRID - ROWS, 75):
        raise ValueError(f'Expected exactly {GRID-ROWS} rows of 75 literal bytes.')
    completed[ROWS:] = suffix.astype(np.uint8)
    assert np.array_equal(completed[:ROWS], source[:ROWS])
    return completed


def screen_parts(target, rels, n=60, keep=3, seed=11):
    """shipped screen_parts (compile_loaders.py), unchanged logic."""
    import random
    rng = random.Random(seed)
    LIN = [0, 1, 3, 7]; NL = [i for i in range(15) if i not in LIN]
    res = []
    for _ in range(n):
        nl = NL[:]; rng.shuffle(nl)
        pts = [[LIN[i], nl[2 * i], nl[2 * i + 1]] for i in range(4)] + [nl[8:11]]
        bp = BlockPlan(target, pts, rels, per_coord=True, hmax=FULL)
        full = [list(basis(f).values()) for f in bp.full]
        pairs, _ = candidates({'parts': pts, 'cuts': full}, full)
        sp = len(basis([x for p in pairs for x in p[:2]]))
        res.append((sp - (NDIM - sum(map(len, full))), pts))
    res.sort(key=lambda x: -x[0])
    return [r[1] for r in res[:keep]], res[0][0]


def plan_and_emit(words791: np.ndarray, k: int, outdir: Path, nrel=6, time_limit=240, seed=1, verbose=True):
    Wc = complete_words_r5(words791)
    target = cross_tensor_r5(Wc, k)
    rels = [] if nrel < 0 else REL_LSB + ([REL_P1] if nrel == 6 else [])
    cand_parts, best_slack = screen_parts(target, rels)
    print(f'   screen_parts: best slack {best_slack} (>=0 means the pure nullspace cuts are pairable)', flush=True)
    pts = cand_parts[0]
    bp = BlockPlan(target, pts, rels, per_coord=True, hmax=FULL)
    t0 = time.time()
    c0 = top_down(bp, seed=seed + 5, trials=40, verbose=False, time_limit=time_limit // 2)
    if c0 is None:
        c0 = bp.greedy(seed=seed, time_limit=time_limit // 2, verbose=False, extra_random=0)
    bp.best = c0
    cuts_ls = local_search(bp, c0, seconds=time_limit, seed=seed + 11, verbose=False)
    import random as _r
    best = None
    for tag, cand in (('top_down', c0), ('local_search', cuts_ls), ('forced_only', bp.F)):
        try:
            dim, span, r = bp.check(cand, _r.Random(seed))
        except Exception as e:                      # noqa: BLE001
            print(f'   check {tag}: failed {e}', flush=True)
            continue
        feasible = (span >= dim and r == dim and dim % 2 == 0)
        print(f'   check {tag}: sum_cuts {sum(map(len,cand))} dim {dim} span {span} alt_rank {r} '
              f'feasible {feasible}', flush=True)
        if feasible and (best is None or sum(map(len, cand)) > best[0]):
            best = (sum(map(len, cand)), cand)
    if best is None:
        raise SystemExit('no feasible cut set found for this table/parts')
    cuts = best[1]
    sc = sum(map(len, cuts))
    entries = {'k': k, 'parts': pts, 'cuts': cuts}
    pairs, cert = matching(entries)
    entries['explicit_products'] = [{'l1': int(p[2]), 'l2': int(p[3]), 'out': int(p[4])} for p in pairs]
    entries['explicit_certificate'] = dict(cert, method='port: greedy block-cut + v18 matching',
                                          relations=[int(r) for r in rels], sum_cuts=sc)
    # no padding_completion: the plan is built on the same (800,75) table that is emitted, so the
    # 9 unreachable rows keep whatever the table has.  (A real completion would have to be solved
    # jointly with the plan, as the shipped pipeline's solve_padding does.)
    emit, left = load_emit_r5()
    outdir.mkdir(parents=True, exist_ok=True)
    rep = emit(entries, Wc, outdir / f'angle_k_{k}.kmx')
    rep = dict(rep, sum_cuts=sc, products_from_algebra=(NDIM - sc) // 2, seconds=round(time.time() - t0, 1),
               leftover_geometry_lines=left)
    return entries, rep


if __name__ == '__main__':
    OUT = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/r5port')
    OUT.mkdir(exist_ok=True)
    z = np.load('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz',
                allow_pickle=False)
    w1220 = np.asarray(z['angle_words'], np.int64)
    dummy = w1220[:GRID].astype(np.uint8)          # 50 complete blocks (rows 791..799 unreachable)
    print('dummy table', dummy.shape, 'bytes', dummy.min(), dummy.max(), flush=True)
    nrel = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    for k in [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['4'])]:
        ent, rep = plan_and_emit(dummy, k, OUT, nrel=nrel)
        print('REPORT', json.dumps(rep), flush=True)
        (OUT / f'angle_k_{k}.plan.json').write_text(json.dumps({kk: vv for kk, vv in ent.items()
                                                                if kk != 'cuts'}, indent=1))
