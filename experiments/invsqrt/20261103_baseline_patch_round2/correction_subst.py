"""Correction-substitution search v2: random pre-screen then full proof.
Manual run only."""
import sys, json, random
sys.path.insert(0, 'experiments/invsqrt/20261103_baseline_patch_round2')
import patch62r2 as R2
import patch62 as P61

_, ops = P61.load_baseline()
OUT = R2.ART / "correction_subst.json"
WINDOWS = {
    "W1": {"lo": 35485, "p2": 35538, "c": 28, "a": 15},
    "W2": {"lo": 35557, "p2": 35605, "c": 28, "a": 15},
}
out = {}
for tag, cfg in WINDOWS.items():
    base = R2.run_prefix2(ops, cfg["lo"])
    s = base.fork().run(ops[cfg["lo"]:cfg["p2"]], start=cfg["lo"])
    v = s.values
    entry = set(base.wire)
    wa = s.wire[cfg["a"]]
    survivors = []
    for w in range(62):
        cand = v.and_(v.xor(s.wire[w], wa), s.wire[cfg["c"]])
        try:
            syms = P61.sliced_symbols(v, entry, cand)
        except P61._Unalignable:
            continue
        keys = sorted(syms, key=str)
        rng = random.Random(1000 + w)
        ok = True
        for _ in range(200):
            env = {k: rng.getrandbits(1) for k in keys}
            if P61.eval_sliced(v, cand, entry, env) != 0:
                ok = False
                break
        if ok:
            survivors.append((w, len(keys)))
    print(tag, "random-screen survivors:", survivors, flush=True)
    # full proof for survivors only
    hits, unk = [], []
    for (w, _) in survivors:
        cand = v.and_(v.xor(s.wire[w], wa), s.wire[cfg["c"]])
        r = P61.sliced_equiv(v, entry, cand, v, entry, v.zero)
        (hits if r["verdict"] == "equivalent" else unk).append(w)
        print(tag, "wire", w, r["verdict"], flush=True)
    out[tag] = {"hits": hits, "unknown": unk}
R2.ART.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1) + "\n")
print("wrote correction_subst.json")
