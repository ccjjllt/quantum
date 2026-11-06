"""Summarize all single-mask replacement search runs."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

import model as M

OUT = M.ART
BASE_M = M.OFFICIAL["baseline_margin"]


def main() -> None:
    rows = []
    for path in sorted(glob.glob(str(OUT / "search_*.json"))):
        if "test_" in path:
            continue
        try:
            recs = json.loads(Path(path).read_text())
        except Exception:
            continue
        if not isinstance(recs, list) or not recs:
            continue
        for r in recs:
            r["file"] = Path(path).name
            rows.append(r)
    print("total evaluations", len(rows))
    by_file = {}
    for r in rows:
        f = by_file.setdefault(r["file"], {"n": 0, "rej": 0, "kept": 0,
                                           "best": -10**18, "rots": set()})
        f["n"] += 1
        f["rots"].add(r["rot"])
        if r["rejected"]:
            f["rej"] += 1
        else:
            f["kept"] += 1
            f["best"] = max(f["best"], r["margin"] or -10**18)
    for f, v in by_file.items():
        print(f"{f:28s} n={v['n']:5d} rejected={v['rej']:5d} kept={v['kept']:5d} "
              f"best={v['best']/1e6:8.3f}M rots={sorted(v['rots'])}")
    good = [r for r in rows if not r["rejected"]]
    good.sort(key=lambda r: -(r["margin"] or -1))
    print("\nbest kept candidates:")
    for r in good[:20]:
        gain = (r["margin"] or 0) - BASE_M
        print(f"  rot {r['rot']:2d} {r['name']:18s} cost {r['cost']} margin "
              f"{(r['margin'] or 0)/1e6:10.4f}M gain {gain:12d} "
              f"saveC {M.margin_saving_C(BASE_M, max(r['margin'],1)):6.3f}")
    # any positive?
    pos = [r for r in good if (r["margin"] or 0) > BASE_M]
    print("\nstrictly positive candidates:", len(pos))
    for r in pos:
        save = M.margin_saving_C(BASE_M, r["margin"])
        net = save - r["cost"]
        print(f"  rot {r['rot']} {r['name']} margin {r['margin']} cost {r['cost']} "
              f"save {save:.3f}C net {net:.3f}C")
    summary = {
        "total_evaluations": len(rows),
        "by_file": {k: {kk: (sorted(vv) if isinstance(vv, set) else vv)
                        for kk, vv in v.items()} for k, v in by_file.items()},
        "n_strictly_positive": len(pos),
        "baseline_margin": BASE_M,
        "best_kept": [{"rot": r["rot"], "name": r["name"], "cost": r["cost"],
                       "margin": r["margin"]} for r in good[:30]],
    }
    (OUT / "search_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\nwrote search_summary.json")


if __name__ == "__main__":
    main()
