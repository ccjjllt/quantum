"""Task3d: spill-validity via cone-input invariance.

For each wire w, track at idx 2006: inps[w] = wires read (not produced) by w's
production chain (= cone input set), prod[w] = last write < 2006.
Spill w across [2006,14215] is valid only if every c in inps[w] is untouched on
[prod[w],14215] (else uncompute/recompute with stale/changed inputs is wrong).
Report for all segment-untouched wires: inps, prod, invariance verdict.
Also: min segment touches among non-input wires; first-write op of q0..q23.
"""
import io
import json
from pathlib import Path

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
SLO, SHI = 2006, 14215


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def main():
    ops = parse_ops()
    inps = [set() for _ in range(62)]
    prod = [-1] * 62
    depth = 0
    for idx, l in enumerate(ops):
        if idx == SLO:
            break
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        if cond:
            continue  # prefix [0:2006] is unconditional (verified separately)
        if op in ("HMR", "R"):
            w = int(p[1][1:])
            inps[w] = set()
            prod[w] = idx
        elif op == "X":
            w = int(p[1][1:])
            prod[w] = idx
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            inps[b] = inps[b] | inps[a] | {a}
            prod[b] = idx
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            inps[t] = inps[t] | inps[a] | inps[b] | {a, b}
            prod[t] = idx
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            inps[a], inps[b] = inps[b], inps[a]
            prod[a] = prod[b] = idx

    # global touch lists (static, any operand incl. conditional)
    touch = {w: [] for w in range(62)}
    for i, l in enumerate(ops):
        if l.startswith(("PUSH", "POP")):
            continue
        for t in l.split()[1:]:
            if t.startswith("q") and t[1:].isdigit():
                touch[int(t[1:])].append(i)

    import bisect
    seg_untouched = [w for w in range(62)
                     if not any(SLO <= t < SHI for t in touch[w])]
    print(f"wires untouched in [{SLO},{SHI}): {seg_untouched}")
    res = []
    for w in seg_untouched:
        bad = {}
        for c in sorted(inps[w]):
            tl = touch[c]
            k = bisect.bisect_left(tl, prod[w])
            later = [t for t in tl[k:] if t <= SHI]
            if later:
                bad[c] = later[:4]
        ok = not bad
        res.append({"w": w, "prod": prod[w], "prod_op": ops[prod[w]],
                    "n_inps": len(inps[w]), "inps": sorted(inps[w]),
                    "invariant": ok, "violations": bad})
        print(f"q{w}: prod={prod[w]} [{ops[prod[w]]}] inps={sorted(inps[w])} "
              f"invariant_on_[prod,14215]={ok}")
        if bad:
            for c, ts in list(bad.items())[:4]:
                print(f"    input q{c} touched at {ts} ...")

    # min segment touches among wires written before segment (non-fresh)
    seg_n = {w: sum(1 for t in touch[w] if SLO <= t < SHI) for w in range(62)}
    others = sorted(((w, seg_n[w]) for w in range(62)
                     if w not in seg_untouched), key=lambda x: x[1])
    print("min seg touches among touched wires:", others[:6])
    print("first-write ops q0..q23:")
    for w in range(24):
        print(f"  q{w}: [{prod[w]}] {ops[prod[w]]}" if prod[w] >= 0 else f"  q{w}: never")
    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task3d_invariance.json").write_text(
        json.dumps({"segment_untouched": res,
                    "min_touched": others[:6]}, indent=2) + "\n")
    print("wrote task3d_invariance.json")


if __name__ == "__main__":
    main()
