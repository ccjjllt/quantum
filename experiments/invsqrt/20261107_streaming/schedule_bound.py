"""Dependency table, production order and the best-order coefficient liveness.

Inputs (all produced by the scripts in this directory):
  symbolic_masks.json    exact per-rotation support over the block-start state
  value_history.json     ops at which every wire's value changed (ops < 25392)
  rotation_read_free.json q61 liveness with all rotation reads removed
  (q61 baseline) artifacts/20261106_q61/value_liveness.json

Output: artifacts/20261107_streaming/dependency_table.json
        artifacts/20261107_streaming/dependency_table.md
"""
from __future__ import annotations

import collections
import json

import common

Q61 = common.ROOT / "artifacts/20261106_q61/value_liveness.json"


def available_since(changes: dict[int, list[int]], wire: int, at: int) -> int:
    """Start of the constant run of wire's value that contains op `at`.

    Value can only be used from `last_change + 1`; if the wire never changed
    before `at`, the initial value (an input bit) is available from op 0.
    """
    last = -1
    for c in changes[wire]:
        if c < at:
            last = c
        else:
            break
    return last + 1


def main() -> None:
    sym = json.loads((common.OUT / "symbolic_masks.json").read_text())
    hist = json.loads((common.OUT / "value_history.json").read_text())["changes"]
    changes = {int(k[1:]): v for k, v in hist.items()}
    rf = json.loads((common.OUT / "rotation_read_free.json").read_text())
    lv = json.loads(Q61.read_text())["value_liveness"]

    rot_rows = []
    for r in sym["per_rotation"]:
        bstart = r["block_start"]
        sup = r["support"]
        av = {w: available_since(changes, w, bstart) for w in sup}
        order = sorted(sup, key=lambda w: (av[w], w))
        idx = {w: k for k, w in enumerate(order)}
        prod = max(av.values())
        row = {
            "rot": r["rot"], "op": r["op"], "block_start": bstart,
            "support": sup, "support_size": len(sup),
            "available_since": av,
            "production_order": order,
            "bit_index": {w: idx[w] for w in sup},
            "bit_index_min": min(idx.values()),
            "bit_index_max": max(idx.values()),
            "bit_index_count": len(set(idx.values())),
            "earliest_placement": prod,
            "earliest_placement_minus_block_start": prod - bstart,
            "is_prefix_of_local_order": set(idx.values()) == set(range(len(sup))),
            "support_oldest": min(av.values()),
            "support_newest": prod,
        }
        rot_rows.append(row)

    print("rot  op     block  |S|  earliest  span_start  bit_idx(range)")
    for r in rot_rows:
        print(f"{r['rot']:3d} {r['op']:6d} {r['block_start']:6d} {r['support_size']:3d}"
              f" {r['earliest_placement']:9d} {r['support_oldest']:11d}"
              f"   {r['bit_index_min']}..{r['bit_index_max']}")

    # Is every support wire needed again after the rotation machinery?
    spans = rf["machinery_spans"]

    def in_machinery(op):
        return any(a <= op <= b for a, b in spans)

    freed_class = []
    for r in rot_rows:
        later = {}
        for w in r["support"]:
            ivs = lv[f"q{w}"]
            # interval(s) that cover the rotation op
            ends = [b for a, b in ivs if a <= r["op"] <= b]
            end = max(ends) if ends else None
            later[w] = {"interval_end": end,
                        "ends_inside_machinery": None if end is None else in_machinery(end)}
        n_outside = sum(1 for v in later.values()
                        if v["ends_inside_machinery"] is False)
        freed_class.append({"rot": r["rot"], "wire_status": later,
                            "support_needed_after_machinery": n_outside})
        r["support_needed_after_machinery"] = n_outside

    print("\nrot  |S|  support wires whose value is still read after the rotation machinery")
    for r in rot_rows:
        print(f"{r['rot']:3d} {r['support_size']:3d}  {r['support_needed_after_machinery']:3d}")

    # Global production order over the whole support union of a block, then the
    # prefix/suffix test that actually matters: is each rotation's support a
    # prefix (or suffix) of that global order?
    for label, block in (("block1", 15247), ("block2", 25392)):
        rows = [r for r in rot_rows if r["block_start"] == block]
        allbits = sorted({w for r in rows for w in r["support"]})
        av = {w: available_since(changes, w, block) for w in allbits}
        gorder = sorted(allbits, key=lambda w: (av[w], w))
        gidx = {w: k for k, w in enumerate(gorder)}
        print(f"\n{label} global production order ({len(gorder)} bits):")
        print("  " + ", ".join(f"q{w}@{av[w]}" for w in gorder))
        for r in rows:
            ids = sorted(gidx[w] for w in r["support"])
            r["global_bit_index"] = ids
        pre = sum(1 for r in rows if r["global_bit_index"] == list(range(len(r["support"]))))
        print(f"  rotations whose support is a prefix of the global order: {pre}/{len(rows)}")

    # Best-order coefficient liveness.  ``t_i`` is the earliest op at which all
    # of rotation i's support values are simultaneously available somewhere
    # (value genealogy, not just per-wire last write).
    gen_by_rot = {g["rot"]: g for g in
                  json.loads((common.OUT / "value_genealogy.json").read_text())["rotations"]}
    for label, block in (("block1", 15247), ("block2", 25392)):
        rows = [r for r in rot_rows if r["block_start"] == block]
        allbits = sorted({w for r in rows for w in r["support"]})
        av = {w: available_since(changes, w, block) for w in allbits}
        t_i = {r["rot"]: gen_by_rot[r["rot"]]["earliest_coexistence"] for r in rows}
        for r in rows:
            r["earliest_coexistence"] = t_i[r["rot"]]
        consume = {w: [] for w in allbits}
        for r in rows:
            for w in r["support"]:
                consume[w].append(t_i[r["rot"]])
        freed_at = {w: max(v) for w, v in consume.items()}
        # profile over ops between first production and last placement
        ev = collections.Counter()
        for w in allbits:
            ev[av[w]] += 1
            ev[freed_at[w] + 1] -= 1
        live = peak = 0
        at = None
        for i in sorted(ev)[:-1]:
            live += ev[i]
            if live > peak:
                peak, at = live, i
        print(f"\n{label}: {len(allbits)} distinct support wires, best-order peak "
              f"simultaneously-live = {peak} at op {at}")
        print("   production ops:", {w: av[w] for w in allbits})
        r = {"block_start": block, "n_bits": len(allbits),
             "production_ops": {str(w): av[w] for w in allbits},
             "freed_at": {str(w): freed_at[w] for w in allbits},
             "best_order_peak_live_bits": peak, "peak_op": at,
             "placements": {str(rr["rot"]): rr["earliest_placement"] for rr in rows}}
        (common.OUT / f"coeff_liveness_{label}.json").write_text(
            json.dumps(r, indent=1) + "\n")

    # Markdown dependency table.
    lines = ["# 41-rotation mask dependency table (exact, all 3,133,452 x)", "",
             "`support` is the set of wire values at the block-start op that the mask",
             "depends on.  `avail` is the op from which that value exists",
             "(last value change + 1, full-domain trace).", ""]
    for label, block in (("block 1 (ops 15247..15616)", 15247),
                        ("block 2 (ops 25392..25661)", 25392)):
        lines += [f"## {label}", "",
                  "| rot | Z_POW | |support| | support wires | earliest placement |",
                  "|---:|---:|---:|---|---:|"]
        for r in rot_rows:
            if r["block_start"] != block:
                continue
            sup = ", ".join(f"q{w}@{r['available_since'][w]}"
                            for w in r["production_order"])
            lines.append(f"| {r['rot']} | {r['op']} | {r['support_size']} | "
                         f"{sup} | {r['earliest_coexistence']} |")
        lines.append("")
    (common.OUT / "dependency_table.md").write_text("\n".join(lines) + "\n")

    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "dependency_table.json").write_text(json.dumps({
        "scope": "exact mask support over block-start wire values",
        "rotations": rot_rows,
        "rotation_read_free_peak": rf["rotation_read_free_peak"],
        "baseline_peak": rf["baseline_peak"],
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
