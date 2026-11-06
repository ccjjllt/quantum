"""full_head_product pair-wise exact ANF deletion, multiprocess + checkpointed."""
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T")
OUT = Path("artifacts/20261106_eeakernel_rewrite/fhp_pairs.json")
CAP = 800000

_WIRES = None
_OPS = None
_BASE = None


def anf_for(op_list, wires):
    idx = {w: i for i, w in enumerate(wires)}
    poly = {w: set([frozenset([idx[w]])]) for w in wires}
    for p in op_list:
        if p[0] == "CX":
            a, b = p[1], p[2]
            s = set(poly[b]) ^ set(poly[a])
            if len(s) > CAP:
                return None
            poly[b] = s
        elif p[0] == "CCX":
            a, b, t = p[1], p[2], p[3]
            prod = set()
            for x in poly[a]:
                for y in poly[b]:
                    prod.add(x | y)
                    if len(prod) > CAP:
                        return None
            s = set(poly[t]) ^ prod
            if len(s) > CAP:
                return None
            poly[t] = s
        elif p[0] == "SWAP":
            a, b = p[1], p[2]
            poly[a], poly[b] = poly[b], poly[a]
    return poly


def init_worker(ops, wires, base):
    global _OPS, _WIRES, _BASE
    _OPS = ops
    _WIRES = wires
    _BASE = base


def check_pair(pair):
    a, b = pair
    drop = {a, b}
    sub = [p for i, p in enumerate(_OPS) if i not in drop]
    m = anf_for(sub, _WIRES)
    if m is None:
        return (pair, "blowup")
    if all(m[w] == _BASE[w] for w in _WIRES):
        return (pair, "FOUND")
    return (pair, None)


def run_template(name, ops, wires, workers=8, chunk=64, limit=None, lo=0, hi=None):
    t0 = time.monotonic()
    base = anf_for(ops, wires)
    assert base is not None, f"{name} base ANF blowup"
    ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
    full = list(itertools.combinations(ccx, 2))
    pairs = full[lo:hi] if (lo or hi is not None) else full
    if limit:
        pairs = pairs[:limit]
    found = []
    tested = 0
    blow = 0
    with mp.get_context("fork").Pool(workers, initializer=init_worker,
                                     initargs=(ops, wires, base)) as pool:
        for i, (pair, res) in enumerate(pool.imap_unordered(check_pair, pairs, chunksize=chunk)):
            tested += 1
            if res == "FOUND":
                found.append(pair)
            elif res == "blowup":
                blow += 1
            if (i + 1) % 2000 == 0:
                print(json.dumps({"template": name, "progress": i + 1, "total": len(pairs),
                                  "found": len(found), "elapsed": round(time.monotonic() - t0, 1)}), flush=True)
    rec = {"n_ccx": len(ccx), "pairs_total": len(full), "pairs_tested": tested,
           "blowups": blow, "redundant_pairs": found,
           "wall_seconds": round(time.monotonic() - t0, 1),
           "slice": [lo, lo + len(pairs)]}
    print(json.dumps({"template": name, **rec}), flush=True)
    return rec


def main():
    import re
    path = TMP / "dqi891.kmx"
    spans = {"fhp126": (13924713, 13929128), "fhp168": (13948965, 13955942),
             "fhp210": (13978497, 13988431)}
    out = {}
    if OUT.exists():
        try:
            out = json.loads(OUT.read_text())
        except Exception:
            out = {}
    which = sys.argv[1:] or list(spans)
    for spec in which:
        parts = spec.split(":")
        name = parts[0]
        lo, hi = 0, None
        if len(parts) >= 2 and parts[1] not in ("", "all"):
            lo = int(parts[1])
        if len(parts) >= 3 and parts[2] not in ("", "all"):
            hi = int(parts[2])
        if name in out and out[name].get("complete"):
            print(json.dumps({"template": name, "skipped_cached": True}), flush=True)
            continue
        s, e = spans[name]
        ops, wires, seen = [], [], set()
        with open(path) as f:
            for ln, line in enumerate(f, 1):
                if s <= ln <= e and not line.startswith(("APPEND", "REGISTER", "INFO_TAG")):
                    p = tuple(line.split())
                    if p[0] not in ("CX", "CCX", "SWAP"):
                        raise ValueError(f"unexpected op {p}")
                    ops.append(p)
                    for t in p[1:]:
                        if t.startswith("q") and t not in seen:
                            seen.add(t)
                            wires.append(t)
        prev = out.get(name) if isinstance(out.get(name), dict) else None
        rec = run_template(name, ops, wires, lo=lo, hi=hi)
        if prev and prev.get("pairs_total") == rec["pairs_total"] and not prev.get("complete"):
            rec["pairs_tested"] += prev.get("pairs_tested", 0)
            rec["blowups"] += prev.get("blowups", 0)
            rec["redundant_pairs"] = prev.get("redundant_pairs", []) + rec["redundant_pairs"]
            rec["wall_seconds"] = round(rec["wall_seconds"] + prev.get("wall_seconds", 0), 1)
        out[name] = rec
        out[name]["complete"] = (out[name]["blowups"] == 0
                                 and out[name]["pairs_tested"] == out[name]["pairs_total"])
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("DONE")


if __name__ == "__main__":
    main()
