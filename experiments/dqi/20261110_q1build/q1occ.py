"""DQI Q-1 first build: elimination-line full-circuit occ census (gap analysis).

Fixed inputs (read-only):
  kmb: artifacts/20261108_public_frontier/release/dqi.kmb (sha256 4432ec5f...)
  kmx: $TMPDIR/dqi_e9diff/e9.kmx (58,341,262 file lines)

Verified windows (file coords, inclusive; cf. spillcolor colorgraph.json):
  S [16446733..16446738] q22->q20 (no kill-bit change; +1-line shape)
  F [13831839..13832124] q848->q15  kill b100685
  G [16051849..16053224] q852->q879  kill b101253
  E [41258103..41258109] q878->q875  kill b99126
  H [52088951..52089238] q861->q849  kill b99619
  D [52299461..52299746] q863->q845  kill b99524

Elimination candidates (max 2 per brief):
  1st: q845 (D borrow; HMR-born, D-window borrow verified MERGE_EQUAL in {D,H})
  2nd: q849 (H borrow; HMR-born, H-window borrow verified MERGE_EQUAL in {D,H})

For each candidate: full-kmx single-pass occ census (token-exact), per-op roles,
inside-vs-outside split against the 6 verified windows, R/HMR provision/kill
counts, file-span, bucket histogram, and full outside gap lists.
No candidate kmb is built (gaps unclosed -> no hard construction, no verifier run).

Writes artifacts/20261110_q1build/occ_summary.json + gaps_q845.txt + gaps_q849.txt.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

TMP = os.environ.get("TMPDIR", "/tmp/")
KMX = os.path.join(TMP, "dqi_e9diff", "e9.kmx")
ART = Path("artifacts/20261110_q1build")

WINDOWS = {
    "S": (16446733, 16446738),
    "F": (13831839, 13832124),
    "G": (16051849, 16053224),
    "E": (41258103, 41258109),
    "H": (52088951, 52089238),
    "D": (52299461, 52299746),
}
CANDS = ["q845", "q849"]


def classify(op, args, q):
    """Read/write role of q in this op (role-aware, cf. exactlive transfer)."""
    try:
        pos = args.index(q)
    except ValueError:
        return "none"
    if op == "R":
        return "provision-write(R)"
    if op == "HMR":
        return "measure-read+reset(HMR)"
    if op == "X":
        return "write(X-target)"
    if op == "CX":
        return "write(CX-target)" if pos == 1 else "read(CX-control)"
    if op == "CCX":
        return "write(CCX-target)" if pos == 2 else "read(CCX-control)"
    if op in ("CZ", "CCZ", "Z"):
        return "read(phase)"
    if op == "SWAP":
        return "write(SWAP)"
    if op == "CSWAP":
        return "write(CSWAP)"
    if op in ("APPEND_TO_REGISTER", "REGISTER", "INFO_TAG", "BIT_STORE0",
              "BIT_STORE1", "BIT_INVERT", "NEG", "PUSH_CONDITION",
              "POP_CONDITION", "SEMANTIC", "ANNOTATION"):
        return "n/a"
    return "read(other)"


def main():
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    n = len(lines)
    print(f"loaded {n} file lines", flush=True)
    # sanity: window boundary texts (same asserts as spillmulti/DH scripts)
    assert lines[52299461].strip() == "R q863", lines[52299461][:60]
    assert lines[52299746].strip() == "HMR q863 b99524", lines[52299746][:60]
    assert lines[52088951].strip() == "R q861", lines[52088951][:60]
    assert lines[52089238].strip() == "HMR q861 b99619", lines[52089238][:60]
    assert lines[41258103].strip() == "R q878", lines[41258103][:60]
    assert lines[41258109].strip() == "HMR q878 b99126", lines[41258109][:60]

    win_list = list(WINDOWS.items())

    summary = {"kmx_lines": n, "windows_files": {k: list(v) for k, v in WINDOWS.items()},
               "candidates": {}}
    gap_files = {c: open(ART / f"gaps_{c}.txt", "w") for c in CANDS}
    for c in CANDS:
        gap_files[c].write(f"# outside-window touches of {c} (file:op:role:text); "
                           f"windows={WINDOWS}\n")

    tot = {c: 0 for c in CANDS}
    per_op = {c: Counter() for c in CANDS}
    per_role = {c: Counter() for c in CANDS}
    per_win = {c: Counter() for c in CANDS}
    nR = {c: 0 for c in CANDS}
    nHMR = {c: 0 for c in CANDS}
    min_touch = {c: None for c in CANDS}
    max_touch = {c: None for c in CANDS}
    buckets = {c: Counter() for c in CANDS}  # 10M-file-line buckets for outside touches
    sample = {c: [] for c in CANDS}
    n_out = {c: 0 for c in CANDS}

    for idx, line in enumerate(lines):
        # fast prefilter
        if "q845" not in line and "q849" not in line:
            continue
        toks = line.split()
        if not toks:
            continue
        op = toks[0]
        args = []
        for t in toks[1:]:
            if t == "if":
                break
            args.append(t)
        # which window (if any)
        wfound = None
        for k, (a, b) in win_list:
            if a <= idx <= b:
                wfound = k
                break
        for c in CANDS:
            if c in args:
                tot[c] += 1
                per_op[c][op] += 1
                role = classify(op, args, c)
                per_role[c][role] += 1
                if op == "R":
                    nR[c] += 1
                if op == "HMR":
                    nHMR[c] += 1
                if min_touch[c] is None:
                    min_touch[c] = idx
                max_touch[c] = idx
                if wfound is not None:
                    per_win[c][wfound] += 1
                else:
                    n_out[c] += 1
                    buckets[c][idx // 10_000_000] += 1
                    gap_files[c].write(f"{idx}:{op}:{role}:{line.strip()[:90]}\n")
                    if len(sample[c]) < 60:
                        sample[c].append({"file": idx, "op": op, "role": role,
                                         "text": line.strip()[:90]})
        if idx % 10_000_000 == 0:
            print(idx, tot, flush=True)

    for c in CANDS:
        gap_files[c].close()

    for c in CANDS:
        summary["candidates"][c] = {
            "total_touches": tot[c],
            "per_op": dict(per_op[c]),
            "per_role": dict(per_role[c]),
            "inside_per_window": {k: per_win[c].get(k, 0) for k in WINDOWS},
            "inside_total": sum(per_win[c].values()),
            "outside_total": n_out[c],
            "outside_fraction": n_out[c] / tot[c] if tot[c] else 0.0,
            "n_provision_R": nR[c],
            "n_kill_HMR": nHMR[c],
            "file_span": [min_touch[c], max_touch[c]],
            "outside_buckets_10M": {str(k): buckets[c][k]
                                    for k in sorted(buckets[c])},
            "outside_sample_first60": sample[c],
        }
        print(f"[{c}] total={tot[c]} inside={sum(per_win[c].values())} "
              f"outside={n_out[c]} R={nR[c]} HMR={nHMR[c]} "
              f"span=[{min_touch[c]}..{max_touch[c]}]", flush=True)

    (ART / "occ_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print("wrote occ_summary.json + gaps_*.txt", flush=True)


if __name__ == "__main__":
    main()
