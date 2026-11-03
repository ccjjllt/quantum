"""Correction-term analysis for the two windows. Manual run only.

For each window: correction w = a*c at P2 point; (a) prove w==0?
(b) w on a single wire? (c) w == wi xor wj for some pair?
Writes artifacts/20261103_baseline_patch_round2/invsqrt/correction.json
"""
import sys, json
sys.path.insert(0, 'experiments/invsqrt/20261103_baseline_patch_round2')
import patch62r2 as R2
import patch62 as P61

_, ops = P61.load_baseline()
OUT = R2.ART / "correction.json"

WINDOWS = {
    "W1": {"lo": 35485, "hi": 35544, "u": 20, "c": 28, "a": 15,
           "p1": 35509, "p2": 35538},
    "W2": {"lo": 35557, "hi": 35610, "u": 16, "c": 28, "a": 15,
           "p1": 35578, "p2": 35605},
}


def analyze(tag, cfg):
    lo = cfg["lo"]
    base = R2.run_prefix2(ops, lo)
    # run to just before P2 (P2 index cfg['p2'] is the CCX itself)
    s = base.fork().run(ops[lo:cfg["p2"]], start=lo)
    v = s.values
    wa = s.wire[cfg["a"]]
    wc = s.wire[cfg["c"]]
    wcorr = v.and_(wa, wc)
    entry = set(base.wire)
    rec = {"window": tag, "p2": cfg["p2"]}
    # (a) zero?
    r = P61.sliced_equiv(v, entry, wcorr, v, entry, v.zero)
    rec["correction_zero"] = r
    # (b) single wire holding wcorr?
    rec["single_wires"] = [w for w in range(62) if s.wire[w] == wcorr]
    # (c) pair xor?
    pairs = []
    for i in range(62):
        for j in range(i + 1, 62):
            if v.xor(s.wire[i], s.wire[j]) == wcorr:
                pairs.append([i, j])
    rec["xor_pairs"] = pairs
    # also: full-window proof budget estimate (sliced symbols at P2)
    try:
        syms = P61.sliced_symbols(v, entry, wcorr)
        rec["n_symbols_correction"] = len(syms)
    except Exception as e:
        rec["n_symbols_correction"] = "unalignable: %s" % e
    print(tag, "zero:", r["verdict"], "singles:", rec["single_wires"],
          "pairs:", pairs, "nsym:", rec.get("n_symbols_correction"))
    return rec


out = {}
for tag, cfg in WINDOWS.items():
    out[tag] = analyze(tag, cfg)
R2.ART.mkdir(parents=True, exist_ok=True)
(OUT).write_text(json.dumps(out, indent=1) + "\n")
print("wrote correction.json")
