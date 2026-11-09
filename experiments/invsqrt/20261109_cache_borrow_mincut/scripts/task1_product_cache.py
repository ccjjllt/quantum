"""Task1: [8860:15800] 58 CCX product-cache census.

- Literal + control-symmetric triple grouping (k>=2 in window), global occurrences.
- Full-domain bit-parallel sim (48961 uint64 words, unconditional X/CX/CCX/SWAP/CSWAP/HMR/R
  only, skip PUSH/POP depth and `if` lines -- same convention as audit_frontier_7c10edba.py):
  control/target word equality at every occurrence (before gate application),
  all-zero / all-one flags at each group span start.
- Static untouched-wire scan per group span + net benefit under clean/dirty borrow models.
"""
import io
import json
from collections import defaultdict
from pathlib import Path

import kickmix as km
import numpy as np

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
WLO, WHI = 8860, 15800
N_INPUTS = 3133452
N_WORDS = (N_INPUTS + 63) // 64


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def sym_key(line):
    p = line.split()
    return (tuple(sorted(p[1:3])), p[3])


def main():
    ops = parse_ops()
    win_ccx_all = [(i, l) for i, l in enumerate(ops[WLO:WHI], start=WLO)
                   if l.startswith("CCX")]
    win_ccx = win_ccx_all
    n_cond_ccx = sum(1 for _, l in win_ccx if " if " in l)
    print(f"window CCX count: {len(win_ccx)}, conditional CCX: {n_cond_ccx}")
    assert n_cond_ccx == 0
    by_sym = defaultdict(list)
    for i, l in win_ccx:
        by_sym[sym_key(l)].append(i)
    groups = {k: v for k, v in by_sym.items() if len(v) >= 2}
    print(f"in-window sym groups k>=2: {len(groups)}")

    # --- global occurrences per window triple ---
    glob = defaultdict(list)
    for i, l in enumerate(ops):
        if l.startswith("CCX"):
            glob[sym_key(l)].append(i)

    # --- full-domain sim with targeted snapshots ---
    targets = set()
    for v in groups.values():
        targets.update(v)
    for v in glob.values():
        pass
    # also snapshot global partners of in-window triples occurring once in window
    once_extra = set()
    for k, v in by_sym.items():
        if len(v) == 1 and len(glob[k]) >= 2:
            once_extra.update(glob[k])
    targets.update(once_extra)

    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = (np.uint64(1) << np.uint64(N_INPUTS % 64)) - np.uint64(1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF))
    ones[-1] = last_mask

    snap = {}   # idx -> {w: words copy} for controls/targets only
    zero_at = {}  # idx -> {w: 0/1/2} 0=zero,1=one,2=other
    need_wires = defaultdict(set)
    for i in targets:
        p = ops[i].split()
        a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
        need_wires[i] = {a, b, t}
    group_starts = {v[0] for v in groups.values()}
    depth = 0
    for idx, l in enumerate(ops):
        if idx in targets:
            if idx in group_starts:
                zf = {}
                for w in range(62):
                    a = q[w].copy()
                    a[-1] &= last_mask
                    if not np.any(a):
                        zf[w] = 0
                    else:
                        o = a ^ ones
                        o[-1] &= last_mask
                        zf[w] = 1 if not np.any(o) else 2
                zero_at[idx] = zf
            snap[idx] = {w: q[w].copy() for w in need_wires[idx]}
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        p = l.split()
        op = p[0]
        if op in ("HMR", "R"):
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[b] ^= q[a]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b].copy(), q[a].copy()
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            q[t] ^= (q[a] & q[b])
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            d = q[a] ^ q[b]
            pr = q[cc] & d
            q[a] ^= pr
            q[b] ^= pr

    def words_equal(x, y):
        xx = x.copy()
        xx[-1] &= last_mask
        yy = y.copy()
        yy[-1] &= last_mask
        return bool(np.array_equal(xx, yy))

    def popcount_xor(x, y):
        d = (x ^ y).copy()
        d[-1] &= last_mask
        return int(np.sum(np.bitwise_count(d)))

    out_groups = []
    for k in sorted(groups, key=lambda k: groups[k][0]):
        v = groups[k]
        (ca, cb), t = k
        lit = sorted({ops[i] for i in v})
        eq = []
        p0 = ops[v[0]].split()
        a0, b0, t0 = int(p0[1][1:]), int(p0[2][1:]), int(p0[3][1:])
        for i in v[1:]:
            p = ops[i].split()
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            # map to canonical control order by matching words to o1
            e_ab = words_equal(snap[i][a], snap[v[0]][a0]) and \
                words_equal(snap[i][b], snap[v[0]][b0])
            e_ba = words_equal(snap[i][a], snap[v[0]][b0]) and \
                words_equal(snap[i][b], snap[v[0]][a0])
            ce = e_ab or e_ba
            te = words_equal(snap[i][t], snap[v[0]][t0])
            dp = popcount_xor(snap[i][a] & snap[i][b],
                              snap[v[0]][a0] & snap[v[0]][b0])
            eq.append({"idx": i, "controls_equal": ce,
                       "target_equal": te, "product_xor_pop": dp})
        a, bspan = v[0], v[-1]
        untouched, clean, cone1, dirty = [], [], [], []
        zf = zero_at[a]
        for w in range(62):
            wq = f"q{w}"
            hit = False
            for j in range(a + 1, bspan):
                lj = ops[j]
                if lj.startswith(("PUSH", "POP")):
                    continue
                if wq in lj.split()[1:]:
                    hit = True
                    break
            if not hit:
                untouched.append(w)
                if zf[w] in (0, 1):
                    clean.append(w)
                else:
                    dirty.append(w)
        out_groups.append({
            "sym": f"CCX {{{ca},{cb}}} q{t}",
            "literals": lit,
            "same_target": len({ops[i].split()[3] for i in v}) == 1,
            "k_window": len(v), "window_idx": v,
            "global_idx": glob[k],
            "endpoint_equivalence": eq,
            "span": [a, bspan], "span_len": bspan - a,
            "untouched": untouched, "clean_or_const1": clean,
            "dirty_untouched": dirty,
        })
        net = -(len(v) - 1) if clean else (len(v) - 1)
        print(f"{k} k={len(v)} span=[{a},{bspan}] "
              f"same_tgt={len({ops[i].split()[3] for i in v}) == 1} "
              f"ctrl_eq={[e['controls_equal'] for e in eq]} "
              f"prod_pop={[e['product_xor_pop'] for e in eq]} "
              f"untouched={untouched} clean={clean} net_CCX={net:+d}")

    once = []
    for k, v in sorted(by_sym.items(), key=lambda kv: kv[1]):
        if len(v) == 1 and len(glob[k]) >= 2:
            w0 = v[0]
            p0 = ops[w0].split()
            a0, b0, t0 = int(p0[1][1:]), int(p0[2][1:]), int(p0[3][1:])
            eq = []
            for g in glob[k]:
                if g == w0:
                    continue
                p = ops[g].split()
                a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
                e_ab = words_equal(snap[g][a], snap[w0][a0]) and \
                    words_equal(snap[g][b], snap[w0][b0])
                e_ba = words_equal(snap[g][a], snap[w0][b0]) and \
                    words_equal(snap[g][b], snap[w0][a0])
                dp = popcount_xor(snap[g][a] & snap[g][b],
                                  snap[w0][a0] & snap[w0][b0])
                eq.append({"idx": g, "controls_equal": e_ab or e_ba,
                           "product_xor_pop": dp})
            once.append({"sym": f"CCX {{{k[0][0]},{k[0][1]}}} {k[1]}",
                         "window_idx": w0, "global_idx": glob[k],
                         "endpoint_equivalence": eq})
    print(f"once-in-window with global partners: {len(once)}")
    for e in once:
        print("  ", e["sym"], "win=", e["window_idx"],
              "partners=", [(x["idx"], x["controls_equal"],
                             x["product_xor_pop"])
                            for x in e["endpoint_equivalence"]])

    out = {"window": [WLO, WHI], "n_ccx": len(win_ccx),
           "groups_k_ge_2": out_groups,
           "once_in_window_global_dupes": once}
    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task1_groups.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print("wrote task1_groups.json")


if __name__ == "__main__":
    main()
