"""Run single-mask replacement search with the exact cutting-plane evaluator."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import model as M
from fast_eval import Evaluator

OUT = M.ART
WIRES = OUT / "wires"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rots", default="15")
    ap.add_argument("--families", default="lin,pair")
    ap.add_argument("--out", default="search_run.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sparse-max", type=int, default=400000,
                    help="wires with popcount below this join the sparse set")
    args = ap.parse_args()
    rots = [int(r) for r in args.rots.split(",")]
    fams = args.families.split(",")

    m = M.load_model()
    masks = m["masks"]
    ev = Evaluator(m)
    base_m = int(ev.base_margin.min())
    print(f"baseline margin {base_m}", flush=True)
    recs = []
    t0 = time.time()
    n_eval = 0
    for i in rots:
        z = np.load(WIRES / f"cp_{i:02d}.npz")
        W = [np.unpackbits(z[f"w{j}"], bitorder="little")[: M.MAXX].astype(bool)
             for j in range(62)]
        pops = [int(w.sum()) for w in W]
        tgt = m["targets"][i]
        f = masks[i]
        cands = []
        if "lin" in fams:
            for j in range(62):
                if j != tgt:
                    cands.append((f"lin {j}", f ^ W[j], 0.0))
        if "trunc" in fams:
            for j in range(62):
                if j != tgt:
                    cands.append((f"trunc {j}", f & W[j], 1.0))
        if "pair" in fams:
            for a in range(62):
                if a == tgt:
                    continue
                for b in range(a + 1, 62):
                    if b == tgt:
                        continue
                    cands.append((f"pair {a},{b}", f ^ (W[a] & W[b]), 1.0))
        if "gsparse" in fams:
            sparse = [j for j in range(62) if j != tgt and pops[j] < args.sparse_max]
            for a in range(62):
                if a == tgt:
                    continue
                for x in range(len(sparse)):
                    for y in range(x + 1, len(sparse)):
                        b, c = sparse[x], sparse[y]
                        if a in (b, c):
                            continue
                        cands.append((f"gsparse {a}|{b}^{c}", f ^ (W[a] & (W[b] ^ W[c])), 1.0))
        if "lin2" in fams:
            for a in range(62):
                if a == tgt:
                    continue
                for b in range(a + 1, 62):
                    if b == tgt:
                        continue
                    cands.append((f"lin2 {a}^{b}", f ^ W[a] ^ W[b], 0.0))
        if "guard54" in fams:
            a = 54
            for b in range(62):
                if b == tgt or b == a:
                    continue
                for c in range(b + 1, 62):
                    if c == tgt or c == a:
                        continue
                    cands.append((f"guard54 {b}^{c}", f ^ (W[a] & (W[b] ^ W[c])), 1.0))
        if args.limit:
            cands = cands[: args.limit]
        print(f"rot {i} tgt q{tgt} candidates {len(cands)}", flush=True)
        for k, (name, g, cost) in enumerate(cands):
            t = time.time()
            out = ev.eval(i, g)
            n_eval += 1
            rec = {"rot": i, "name": name, "cost": cost,
                   "margin": out["margin"], "rejected": out["rejected"],
                   "lp_margin": out["lp_margin"],
                   "iters": len(out["history"]),
                   "history": out["history"] if not out["rejected"] else None,
                   "theta_units": out["theta"].tolist() if out["theta"] is not None else None,
                   "seconds": round(time.time() - t, 3)}
            recs.append(rec)
            if (k + 1) % 50 == 0:
                good = [r for r in recs if not r["rejected"]]
                print(f"  {k+1}/{len(cands)} elapsed {time.time()-t0:.0f}s "
                      f"kept {len(good)} best "
                      f"{max([r['margin'] for r in good], default=0)/1e6:.2f}M "
                      f"rate {(k+1)/(time.time()-t0):.2f}/s", flush=True)
                if (k + 1) % 200 == 0:
                    (OUT / args.out).write_text(json.dumps(recs) + "\n")
        (OUT / args.out).write_text(json.dumps(recs) + "\n")
    good = [r for r in recs if not r["rejected"]]
    good.sort(key=lambda r: -(r["margin"] or -1))
    print(f"done {n_eval} evals in {time.time()-t0:.0f}s; kept {len(good)}")
    for r in good[:15]:
        print(f"  rot {r['rot']} {r['name']} cost {r['cost']} margin "
              f"{r['margin']/1e6:.2f}M iters {r['iters']}")
    (OUT / args.out).write_text(json.dumps(recs) + "\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
