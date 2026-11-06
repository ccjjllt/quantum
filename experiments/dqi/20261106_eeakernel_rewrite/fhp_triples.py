"""full_head_product 3-gate exact ANF deletion, fhp126 first (C(126,3)=325500). Multiprocess + slice accumulation."""
import itertools
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T")
OUT = Path("artifacts/20261106_eeakernel_rewrite/fhp_triples.json")
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


def check_triple(trip):
    a, b, c = trip
    drop = {a, b, c}
    sub = [p for i, p in enumerate(_OPS) if i not in drop]
    m = anf_for(sub, _WIRES)
    if m is None:
        return (trip, "blowup")
    if all(m[w] == _BASE[w] for w in _WIRES):
        return (trip, "FOUND")
    return (trip, None)


def run_slice(name, ops, wires, triples, workers=8, chunk=64):
    t0 = time.monotonic()
    base = anf_for(ops, wires)
    assert base is not None, f"{name} base ANF blowup"
    found, blow, tested = [], 0, 0
    with mp.get_context("fork").Pool(workers, initializer=init_worker,
                                      initargs=(ops, wires, base)) as pool:
        for i, (trip, res) in enumerate(pool.imap_unordered(check_triple, triples, chunksize=chunk)):
            tested += 1
            if res == "FOUND":
                found.append(trip)
            elif res == "blowup":
                blow += 1
            if (i + 1) % 20000 == 0:
                print(json.dumps({"template": name, "progress": i + 1, "total": len(triples),
                                  "found": len(found), "elapsed": round(time.monotonic() - t0, 1)}), flush=True)
    rec = {"tested": tested, "blowups": blow, "redundant_triples": found,
           "wall_seconds": round(time.monotonic() - t0, 1)}
    print(json.dumps({"template": name, **rec}), flush=True)
    return rec


def main():
    spans = {"fhp126": (13924713, 13929128), "fhp168": (13948965, 13955942),
             "fhp210": (13978497, 13988431)}
    # argv: specs like fhp126:0:81375 fhp126:81375:162750 ...
    specs = sys.argv[1:] or ["fhp126:0:all"]
    # group by template
    by_tpl = {}
    for spec in specs:
        parts = spec.split(":")
        name = parts[0]
        lo = int(parts[1]) if len(parts) > 1 and parts[1] not in ("", "all") else 0
        hi = int(parts[2]) if len(parts) > 2 and parts[2] not in ("", "all") else None
        by_tpl.setdefault(name, []).append((lo, hi))
    out = {}
    if OUT.exists():
        try:
            out = json.loads(OUT.read_text())
        except Exception:
            out = {}
    path = TMP / "dqi891.kmx"
    for name, slices in by_tpl.items():
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
        ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
        all_trips = list(itertools.combinations(ccx, 3))
        total = len(all_trips)
        rec = out.get(name, {"n_ccx": len(ccx), "triples_total": total, "triples_tested": 0,
                             "blowups": 0, "redundant_triples": [], "wall_seconds": 0.0,
                             "slices_done": []})
        for lo, hi in slices:
            hi = total if hi is None else hi
            if [lo, hi] in rec.get("slices_done", []):
                print(json.dumps({"template": name, "slice": [lo, hi], "skipped_cached": True}), flush=True)
                continue
            r = run_slice(name, ops, wires, all_trips[lo:hi])
            rec["triples_tested"] += r["tested"]
            rec["blowups"] += r["blowups"]
            rec["redundant_triples"] += r["redundant_triples"]
            rec["wall_seconds"] = round(rec["wall_seconds"] + r["wall_seconds"], 1)
            rec["slices_done"].append([lo, hi])
            rec["complete"] = (rec["blowups"] == 0 and rec["triples_tested"] == total)
            out[name] = rec
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("DONE")


if __name__ == "__main__":
    main()
