"""Final summary numbers for the streaming investigation."""
from __future__ import annotations

import collections
import json

import common

Q61 = common.ROOT / "artifacts/20261106_q61/value_liveness.json"


def main() -> None:
    lv = json.loads(Q61.read_text())["value_liveness"]
    rf = json.loads((common.OUT / "rotation_read_free.json").read_text())
    dep = json.loads((common.OUT / "dependency_table.json").read_text())
    gen = json.loads((common.OUT / "value_genealogy.json").read_text())
    hist = json.loads((common.OUT / "value_history.json").read_text())["changes"]
    changes = {int(k[1:]): v for k, v in hist.items()}
    sym = json.loads((common.OUT / "symbolic_masks.json").read_text())
    spans = rf["machinery_spans"]

    diff = collections.defaultdict(int)
    for w, ivs in lv.items():
        for a, b in ivs:
            diff[a] += 1
            diff[b + 1] -= 1
    cur = 0
    prof = []
    for i in range(0, 49052):
        cur += diff.get(i, 0)
        prof.append(cur)
    peak = max(prof)
    peaks = [i for i, v in enumerate(prof) if v >= peak]
    segs = []
    for i in peaks:
        if segs and i == segs[-1][1] + 1:
            segs[-1][1] = i
        else:
            segs.append([i, i])

    def in_spans(op):
        return any(a <= op <= b for a, b in spans)

    inside = sum(1 for i in peaks if in_spans(i))
    gadget = sum(b - a + 1 for a, b in segs
                 if (15283 <= a and b <= 15612) or (25462 <= a and b <= 25612))
    corr = sum(b - a + 1 for a, b in segs if 15691 <= a and b <= 16152)
    mid = sum(b - a + 1 for a, b in segs if 23826 <= a and b <= 24364)
    arith = len(peaks) - gadget - corr - mid
    print(f"baseline peak {peak}, {len(peaks)} ops in {len(segs)} segments")
    print(f"  rotation gadget ancilla {gadget} ops, rotation correction {corr} ops, "
          f"arithmetic {arith} ops, mid spikes {mid} ops")
    print(f"  (coarse: {inside} ops lie inside the merged machinery spans, "
          f"{len(peaks) - inside} outside)")
    print(f"  rotation-read-free peak {rf['rotation_read_free_peak']} "
          f"({rf['peak_ops']} ops) first at op {rf['rotation_read_free_peak_op']}")
    print(f"  peak ops that survive: {rf['peak_ops_list'][:8]} ...")

    # production spread per block
    for block in (15247, 25392):
        rows = [r for r in dep["rotations"] if r["block_start"] == block]
        allbits = sorted({w for r in rows for w in r["support"]})
        av = {}
        for w in allbits:
            last = -1
            for c in changes[w]:
                if c < block:
                    last = c
                else:
                    break
            av[w] = last + 1
        early = sum(1 for w in allbits if av[w] < block - 400)
        print(f"\nblock {block}: {len(allbits)} distinct support bits; "
              f"{len(allbits) - early} produced in the last 400 ops before the block; "
              f"earliest production {min(av.values())}, latest {max(av.values())}")
        rows2 = [r for r in dep["rotations"] if r["block_start"] == block]
        print(f"  support sizes {sorted(r['support_size'] for r in rows2)}")
        print(f"  earliest coexistence of each rotation's support:",
              sorted({g['earliest_coexistence'] for g in gen['rotations']
                      if g['block_start'] == block}))
        print(f"  max interleaving gain (op - earliest_coexistence):",
              max(g['gain_vs_actual'] for g in gen['rotations']
                  if g['block_start'] == block))

    out = {
        "baseline_peak": peak,
        "baseline_peak_segments": len(segs),
        "baseline_peak_ops": len(peaks),
        "peak_ops_rotation_gadget_ancilla": gadget,
        "peak_ops_rotation_correction": corr,
        "peak_ops_arithmetic": arith,
        "peak_ops_mid_spikes": mid,
        "peak_ops_inside_merged_machinery_spans": inside,
        "rotation_read_free_peak": rf["rotation_read_free_peak"],
        "rotation_read_free_peak_ops": rf["peak_ops"],
        "rotation_read_free_peak_ops": rf["peak_ops_list"],
        "blocks": {
            "block1": {"start": 15247, "bits": 45, "rotations": 15},
            "block2": {"start": 25392, "bits": 27, "rotations": 26},
        },
        "symbolic_exact_full_domain": all(r["exact_full_domain"]
                                         for r in sym["per_rotation"]),
        "masks_equal_to_another_single_wire_at_z_pow": 0,
        "added_C_estimate": 0,
        "candidate_generated": False,
        "reason": "peak stays 62 even with every rotation-machine read removed",
    }
    (common.OUT / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print("\nwrote", common.OUT / "summary.json")


if __name__ == "__main__":
    main()
