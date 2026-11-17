"""Turn a plan_basis_<k>.json (cuts in the rank-74 low basis) into a literal plan
state, emit the .kmx and report the exact Toffoli count.  This is
compile_basis.compile_one's emit path, minus the (unshipped) all-branch proof.
"""
import sys, json, hashlib, argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'compiler'))
sys.path.insert(0, str(HERE))
from planner import complete_words, cross_tensor, padded_words, NDIM  # noqa: E402
from lowbasis import inverse15, to_physical, transform_target  # noqa: E402
from extract_matching import matching  # noqa: E402
from emit_plan import emit  # noqa: E402

BUILD = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds')
SHIPPED = [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]


def build(k, state_path, outdir):
    st = json.loads(Path(state_path).read_text())
    assert int(st['k']) == k
    z = np.load(BUILD / 'submission.npz', allow_pickle=False)
    W = np.asarray(z['angle_words'], np.uint8)
    Wc = complete_words(W)
    target = cross_tensor(Wc, k)
    parts = st['parts']
    cuts = st['cuts']
    rows = st['rows']
    B = inverse15(rows)
    # sanity: every cut really annihilates the 75 determined slices, in the low basis it was found in
    from planner import basis, reduce, BlockPlan
    tt = transform_target(target, B)
    bp = BlockPlan(tt, parts, [], per_coord=True, hmax=76)
    for pi in range(len(parts)):
        bb = basis(bp.full[pi])
        for c in cuts[pi]:
            assert reduce(int(c), bb) == 0, f'cut {pi} is not an annihilator of block {pi}'
    s_new = {'parts': parts, 'cuts': cuts}
    pairs, cert = matching(s_new)
    prods = [{'l1': int(to_physical(p[2], B)), 'l2': int(to_physical(p[3], B)), 'out': int(p[4])}
             for p in pairs]
    Wpad = padded_words(W, k, int(st['F']))
    prefix = hashlib.sha256(np.ascontiguousarray(W, dtype=np.uint8).tobytes()).hexdigest()
    s = {'k': k, 'explicit_products': prods,
         'explicit_certificate': dict(cert, method='shipped rank-74 low basis + planner descent on the '
                                      'marculera table (this experiment)', sum_cuts=int(st['sum_cuts']),
                                      low_basis_dual_rows=[int(x) for x in rows]),
         'padding_completion': {'version': 1, 'first_unused_address': 1220, 'word_width': 75,
                                'words': Wpad[1220:].astype(int).tolist(),
                                'real_word_prefix_sha256': prefix}}
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rep = emit(s, Wc, outdir / f'angle_k_{k}.kmx')
    (outdir / f'angle_k_{k}.plan_state.json').write_text(json.dumps(s, indent=1))
    return rep, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--state', default=None)
    ap.add_argument('--outdir', default='build_new')
    ap.add_argument('--write-state', action='store_true')
    a = ap.parse_args()
    state = a.state or str(HERE / f'basis_plan_k{a.k}.json')
    rep, s = build(a.k, state, HERE / a.outdir)
    print(json.dumps({'k': a.k, 'products': rep['product_count'], 'toffoli': rep['toffoli_count'],
                      'qubits': rep['num_qubits'], 'shipped': SHIPPED[a.k],
                      'delta': rep['toffoli_count'] - SHIPPED[a.k],
                      'sum_cuts': s['explicit_certificate']['sum_cuts']}), flush=True)


if __name__ == '__main__':
    main()
