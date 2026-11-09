from __future__ import annotations

import difflib
import io
import json
from pathlib import Path
import kickmix as km


def load_stage_lines(kmb_path: Path) -> tuple[list[str], dict[str, tuple[int, int]], dict]:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    stack: list[str] = []
    stage_ranges: dict[str, list[int]] = {}
    for idx, l in enumerate(lines):
        if l.startswith("INFO_TAG "):
            tag = l.strip().split('"', 2)[1]
            if tag.startswith("@enter:"):
                name = tag[7:]
                if not stack:
                    stage_ranges[name] = [idx, idx]
                stack.append(name)
            elif tag.startswith("@exit:") and stack:
                name = stack.pop()
                if not stack and name in stage_ranges:
                    stage_ranges[name][1] = idx
    meta = {
        "num_qubits": int(c.num_qubits),
        "num_bits": int(c.num_bits),
        "num_registers": int(c.num_registers),
        "num_lines": len(lines),
        "stats": {k: int(v) for k, v in c.operation_statistics().items()},
    }
    return lines, {k: (v[0], v[1]) for k, v in stage_ranges.items()}, meta


def diff_stage(lines_a: list[str], start_a: int, end_a: int,
               lines_b: list[str], start_b: int, end_b: int,
               stage_name: str) -> list[dict]:
    sub_a = lines_a[start_a:end_a + 1]
    sub_b = lines_b[start_b:end_b + 1]
    if sub_a == sub_b:
        return []
    # Find matching blocks by anchoring on identical lines or using SequenceMatcher on paid/tag lines
    # Since sub_a and sub_b are ~5.7M lines and only differ in ~40 local windows,
    # we can find differing regions rapidly by chunking (e.g. 1000-line blocks) or two-pointer scan!
    hunks = []
    i, j = 0, 0
    na, nb = len(sub_a), len(sub_b)
    while i < na and j < nb:
        if sub_a[i] == sub_b[j]:
            i += 1
            j += 1
            continue
        # Found a mismatch at (i, j). Find where they resynchronize with at least 20 identical consecutive lines.
        sync_a, sync_b = None, None
        window = 400
        # Build a lookup of 5-line tuples in sub_b[j:j+window]
        b_fingerprints = {}
        for bj in range(j, min(nb - 5, j + window)):
            fp = tuple(sub_b[bj:bj + 5])
            if fp not in b_fingerprints:
                b_fingerprints[fp] = bj
        for ai in range(i, min(na - 5, i + window)):
            fp = tuple(sub_a[ai:ai + 5])
            if fp in b_fingerprints:
                bj = b_fingerprints[fp]
                # Check if 20 lines match
                if sub_a[ai:min(na, ai + 20)] == sub_b[bj:min(nb, bj + 20)]:
                    sync_a, sync_b = ai, bj
                    break
        if sync_a is None:
            raise RuntimeError(f"Could not resync at {stage_name} offset {i}, {j}")
        # Refine hunk inside sub_a[i:sync_a] vs sub_b[j:sync_b] using SequenceMatcher
        sm = difflib.SequenceMatcher(None, sub_a[i:sync_a], sub_b[j:sync_b], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            old_chunk = sub_a[i + i1:i + i2]
            new_chunk = sub_b[j + j1:j + j2]
            # Find surrounding context and active INFO_TAGs
            ctx_before = sub_a[max(0, i + i1 - 15):i + i1]
            ctx_after = sub_a[i + i2:min(na, i + i2 + 15)]
            old_paid = sum(1 for l in old_chunk if l.split()[0] in ("CCX", "CCZ", "CSWAP"))
            new_paid = sum(1 for l in new_chunk if l.split()[0] in ("CCX", "CCZ", "CSWAP"))
            hunks.append({
                "stage": stage_name,
                "v9_line_start": start_a + i + i1,
                "v9_line_end": start_a + i + i2,
                "frontier_line_start": start_b + j + j1,
                "frontier_line_end": start_b + j + j2,
                "tag": tag,
                "old_paid": old_paid,
                "new_paid": new_paid,
                "delta_paid": new_paid - old_paid,
                "old": old_chunk,
                "new": new_chunk,
                "ctx_before": ctx_before,
                "ctx_after": ctx_after,
            })
        i, j = sync_a, sync_b
    return hunks


def main() -> None:
    v9_path = Path("artifacts/20261106_syed_v9/release/dqi.kmb")
    fr_path = Path("artifacts/20261108_public_frontier/release/dqi.kmb")
    out_dir = Path("artifacts/20261109_subagent_research")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading Syed V9...")
    lines_v9, ranges_v9, meta_v9 = load_stage_lines(v9_path)
    print("Loading Frontier 4432ec5f...")
    lines_fr, ranges_fr, meta_fr = load_stage_lines(fr_path)

    all_hunks = []
    stage_identical = {}
    for st in ranges_v9:
        sa, ea = ranges_v9[st]
        sb, eb = ranges_fr[st]
        hunks = diff_stage(lines_v9, sa, ea, lines_fr, sb, eb, st)
        stage_identical[st] = (len(hunks) == 0)
        print(f"Stage {st}: {len(hunks)} diff hunks, delta_paid={sum(h['delta_paid'] for h in hunks)}")
        all_hunks.extend(hunks)

    report = {
        "meta_v9": meta_v9,
        "meta_frontier": meta_fr,
        "stage_ranges_v9": ranges_v9,
        "stage_ranges_frontier": ranges_fr,
        "stage_identical": stage_identical,
        "total_hunks": len(all_hunks),
        "total_delta_paid": sum(h["delta_paid"] for h in all_hunks),
        "hunks": all_hunks,
    }
    out_path = out_dir / "diff_v9_to_4432ec5f.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(all_hunks)} hunks to {out_path}")


if __name__ == "__main__":
    main()
