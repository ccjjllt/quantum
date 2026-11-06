"""Cross-boundary joint redundancy: norm tail + CX gap + scalar head (pre-R/HMR).
Exact ANF single+pair deletion. Read-only; no verifier."""
import itertools
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_eeakernel_fusion/boundary_joint.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

# (name, span_start, span_end): last CCX of norm + gap + scalar head up to first R/HMR
# norm tail CCX at 2701047; gap 2701056-2701079 (24 CX); scalar head CX/SWAP until R@2701093
SPAN = ("norm_scalar_it1", 2701040, 2701092)


def load(lo, hi):
    ops = []
    with open(KMX) as f:
        for ln, line in enumerate(f, 1):
            if lo <= ln <= hi and not line.startswith(("INFO_TAG", "APPEND", "REGISTER")):
                p = line.split()
                if p[0] in ("HMR", "R"):
                    raise ValueError(f"non-classical op in span: {ln} {line.strip()}")
                ops.append(p)
    return ops


def main():
    assert KMX is not None and KMX.exists()
    name, lo, hi = "norm_scalar_it1", 2701040, 2701092
    ops = load(lo, hi)
    kinds = {}
    for p in ops:
        kinds[p[0]] = kinds.get(p[0], 0) + 1
    print(json.dumps({"span": [lo, hi], "n_ops": len(ops), "kinds": kinds}))
    wires = sorted({t for p in ops for t in p[1:] if t.startswith("q")}, key=lambda t: int(t[1:]))
    idx = {w: i for i, w in enumerate(wires)}
    CAP = 600000

    def anf(op_list):
        poly = {w: set([frozenset([idx[w]])]) for w in wires}
        for p in op_list:
            o = p[0]
            if o == "X":
                v = set(poly[p[1]])
                if frozenset() in v:
                    v.remove(frozenset())
                else:
                    v.add(frozenset())
                poly[p[1]] = v
            elif o == "CX":
                a, b = p[1], p[2]
                s = set(poly[b]) ^ set(poly[a])
                if len(s) > CAP:
                    return None
                poly[b] = s
            elif o == "CCX":
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
            elif o == "SWAP":
                a, b = p[1], p[2]
                poly[a], poly[b] = poly[b], poly[a]
            elif o in ("CZ", "Z", "Z_POW"):
                pass
            else:
                raise ValueError(f"unexpected op: {p}")
        return poly

    base = anf(ops)
    assert base is not None
    ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
    print(json.dumps({"n_ccx": len(ccx), "n_wires": len(wires)}))
    red1 = []
    for k in ccx:
        m = anf([p for i, p in enumerate(ops) if i != k])
        if m is not None and all(m[w] == base[w] for w in wires):
            red1.append(k)
            print(json.dumps({"single_redundant": k, "op": ops[k]}))
    red2 = []
    for a, b in itertools.combinations(ccx, 2):
        drop = {a, b}
        m = anf([p for i, p in enumerate(ops) if i not in drop])
        if m is not None and all(m[w] == base[w] for w in wires):
            red2.append([a, b])
            print(json.dumps({"pair_redundant": [a, b]}))
    out = {"span": [lo, hi], "n_ops": len(ops), "n_ccx": len(ccx),
           "redundant_single": red1, "pairs_tested": len(list(itertools.combinations(ccx, 2))),
           "redundant_pairs": red2}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"done": True, "redundant": red1, "pairs": red2}))


if __name__ == "__main__":
    main()
