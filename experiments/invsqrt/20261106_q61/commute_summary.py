"""Combine the verified-cheap parking cover with the sound commutation cover."""
from __future__ import annotations

import json

import common


def main():
    peak = set(json.loads((common.OUT / "park_missing.json").read_text())["peak_ops"])
    v4 = json.loads((common.OUT / "commute_v4.json").read_text())
    comm = set()
    chunks = []
    for c in v4["chosen"]:
        a, b = c["block"]
        comm |= set(range(a, b))
        chunks.append({"block": [a, b], "wire": c["wire"], "moved": c["moved"]})
    pm = json.loads((common.OUT / "park_missing.json").read_text())
    scr = json.loads((common.OUT / "park_rebuild_screen.json").read_text())
    pack = set(pm["free_covered"])
    rem = set(pm["missing"])
    cheap = [o for o in scr if o["screen_cost"] <= 1]
    park_parts = []
    while rem:
        best = max(cheap, key=lambda o: len(set(o["covered"]) & rem), default=None)
        g = len(set(best["covered"]) & rem) if best else 0
        if g == 0:
            break
        park_parts.append({"wire": best["wire"], "gap": best["gap"],
                           "gain": g, "cost": 1 if best["screen_cost"] >= 1 else 0})
        pack |= set(best["covered"]) & rem
        rem -= set(best["covered"])
    park_cost = sum(p["cost"] for p in park_parts)
    union = (pack | comm) & peak
    left = sorted(peak - union)
    runs = []
    for i in left:
        if runs and runs[-1][1] == i:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    print(f"peak ops                         {len(peak)}")
    print(f"verified-cheap parking cover     {len(pack & peak):>5} ops  cost {park_cost} C")
    print(f"sound commutation cover          {len(comm & peak):>5} ops  cost 0 C")
    print(f"union                            {len(union):>5} ops  cost {park_cost} C")
    print(f"uncovered                        {len(left):>5} ops in {len(runs)} runs")
    print(f"\ncommutation chunks ({len(chunks)}):")
    for c in chunks:
        print(f"  block {c['block']} wire q{c['wire']}: {c['moved']} moved reads, 0 C")
    print(f"\nuncovered runs (>=10 ops):")
    for a, b in runs:
        if b - a >= 10:
            print(f"  [{a},{b}) len {b-a}")
    out = {
        "peak_ops": len(peak), "parking_ops": len(pack & peak), "parking_cost_C": park_cost,
        "commutation_ops": len(comm & peak), "commutation_cost_C": 0,
        "union_ops": len(union), "uncovered_ops": len(left),
        "uncovered_runs": runs, "commutation_chunks": chunks, "parking_parts": park_parts,
        "budget_C": 25.833098,
        "verdict": "no 61Q schedule: uncovered peak ops remain",
    }
    (common.OUT / "commute_summary.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
