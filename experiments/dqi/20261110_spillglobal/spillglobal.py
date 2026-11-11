"""DQI spillglobal: 3 new borrow-reroute cuts + 5-cut merged evidence.

Extends spillmulti (per-block full-window replay) and spillunified (merge +
combined slice) to D+E+F+G+H = 5 cuts. New blocks come from the 238 long
blocks (scan.py: victim R at L-1, kill = first HMR; stale.py: victim
stale-|0> proof). Each new block verified independently (strict q20 borrow,
roles, paid, TAIL=0 4-shot slice seed 99 / init 0xD91 + determinism rerun),
then 5-cut interference census, then merged diff + combined slice
(header + [ENTRY..maxK], all 5 renames, same protocol).

Stage 1 (per-block): pass -> writes spill{F,G,H}.{diff,json} + updates
  artifacts/20261110_spillglobal/cuts.json
Stage 2 (merge, only if all 5 clean): writes spillglobal5.{diff,json}.
Any counterexample -> CONFLICT record, no merge (closed, not merged).

Usage: python spillglobal.py [--stage1 | --stage2]
"""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import numpy as np

import kickmix as km

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx"
ART = Path("artifacts/20261110_spillglobal")
HEADER_END = 54146
ENTRY_CONVERT = 12006935
W = 892
PAID = {"CCX", "CCZ", "CSWAP", "CCX_CARRY"}
CUTS_JSON = ART / "cuts.json"

# D/E carried over from spillmulti/spillunified (file coords, verified).
PRIOR = [
    {"tag": "E", "victim": "q878", "borrow": "q875",
     "F_B": 41258103, "F_K": 41258109, "kill_bit": "b99126"},
    {"tag": "D", "victim": "q863", "borrow": "q845",
     "F_B": 52299461, "F_K": 52299746, "kill_bit": "b99524"},
]

# New cuts F/G/H selected by scan.py + stale.py (filled after selection).
# All: HMR-born borrow, window zero-touch; victim stale-|0> (re-proven in
# verify_block); kill bits distinct from each other and from D/E.
NEW = [
    {"tag": "F", "victim": "q848", "borrow": "q15",
     "F_B": 13831839, "F_K": 13832124, "kill_bit": "b100685"},
    {"tag": "G", "victim": "q852", "borrow": "q879",
     "F_B": 16051849, "F_K": 16053224, "kill_bit": "b101253"},
    {"tag": "H", "victim": "q861", "borrow": "q849",
     "F_B": 52088951, "F_K": 52089238, "kill_bit": "b99619"},
]


def has_qtok(line, q):
    for t in line.split()[1:]:
        if t == "if":
            break
        if t == q:
            return True
    return False


def rename(line, qv, qb):
    p = line.split()
    return " ".join([p[0]] + [qb if t == qv else t for t in p[1:]]) + "\n"


def sim_sized(text, seed, qb, bb):
    c = km.Circuit(text)
    sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
    sim.use_same_registers_as(c)
    sim.write_across_shots(km.array([km.q(i) for i in range(c.num_qubits)]), qb[:c.num_qubits])
    sim.write_across_shots(km.array([km.b(i) for i in range(c.num_bits)]), bb[:c.num_bits])
    sim.do(c)
    return sim, c


def compare(simO, cO, simR, cR):
    qmis = [i for i in range(W)
            if [bool(v) for v in simO.read_across_shots(km.q(i))]
            != [bool(v) for v in simR.read_across_shots(km.q(i))]]
    nbits = min(cO.num_bits, cR.num_bits)
    bmis = []
    for i in range(nbits):
        if ([bool(v) for v in simO.read_across_shots(km.b(i))]
                != [bool(v) for v in simR.read_across_shots(km.b(i))]):
            bmis.append(i)
            if len(bmis) > 20:
                break
    return qmis, nbits, bmis


def value_writers(op, qs):
    """Qubits whose computational-basis value may change (writers)."""
    if op == "X":
        return [qs[0]]
    if op == "CX":
        return [qs[1]]
    if op in ("CCX", "CCX_CARRY"):
        return [qs[2]]
    if op in ("SWAP", "CSWAP"):
        return list(qs)
    if op in ("R", "HMR"):
        return [qs[0]]
    return []


def verify_block(lines, cfg):
    """Strict per-block verification + TAIL=0 slice. Returns result dict."""
    tag, qv, qb = cfg["tag"], cfg["victim"], cfg["borrow"]
    F_B, F_K = cfg["F_B"], cfg["F_K"]
    assert lines[F_B].strip() == f"R {qv}", lines[F_B][:60]
    assert lines[F_K].strip() == f"HMR {qv} {cfg['kill_bit']}", lines[F_K][:60]
    for i in range(F_B, F_K + 1):
        assert " if " not in lines[i], (tag, i, lines[i][:60])
    vlines = [i for i in range(F_B, F_K + 1) if has_qtok(lines[i], qv)]
    assert vlines[0] == F_B and vlines[-1] == F_K
    roles = {}
    for i in vlines:
        roles[lines[i].split()[0]] = roles.get(lines[i].split()[0], 0) + 1
    assert set(roles) <= {"R", "CCX", "CX", "SWAP", "HMR"}, (tag, roles)
    # borrow: zero touches in window (strict q20)
    for i in range(F_B, F_K + 1):
        assert not has_qtok(lines[i], qb), (tag, i, lines[i][:60])
    # borrow birth: backward scan, must be HMR birth with clean gap
    F_birth = None
    for i in range(F_B - 1, -1, -1):
        if has_qtok(lines[i], qb):
            F_birth = i
            break
    assert F_birth is not None
    bt = lines[F_birth].strip()
    assert bt.startswith(f"HMR {qb} b"), (tag, bt[:60])
    for i in range(F_birth + 1, F_B):
        assert not has_qtok(lines[i], qb), (tag, "gap touch", i, lines[i][:60])
    # victim stale-|0>: last VALUE-affecting touch before F_B must be R/HMR
    vnum = int(qv[1:])
    found = None
    for i in range(F_B - 1, -1, -1):
        p = lines[i].split()
        op = p[0]
        if op in ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION",
                  "BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "NEG",
                  "PUSH_CONDITION", "POP_CONDITION"):
            continue
        toks = [t for t in p[1:] if t == qv]
        if not toks:
            continue
        if op in ("CZ", "Z", "CCZ"):
            continue  # phase-only
        if op in ("X", "CX", "CCX", "CCX_CARRY", "SWAP", "CSWAP", "R", "HMR"):
            qs = [t for t in p[1:] if t.startswith("q")]
            if qv in value_writers(op, qs):
                found = (i, lines[i].strip()[:60])
                break
        else:
            found = (i, lines[i].strip()[:60])  # conservative: unknown op counts
            break
    assert found is not None
    assert found[1].split()[0] in ("R", "HMR") and found[1].split()[1] == qv, (tag, found)
    # paid census
    p0 = sum(1 for i in range(F_B, F_K + 1) if lines[i].split()[0] in PAID)
    new_mid = [rename(lines[i], qv, qb) for i in range(F_B, F_K + 1)]
    p1 = sum(1 for l in new_mid if l.split()[0] in PAID)
    assert p0 == p1, (tag, p0, p1)
    # HMR preservation: exactly one HMR touches victim-or-borrow in window
    # (the kill line); other qubits' HMR clusters may share the window tail
    # (e.g. G ends with a 12-HMR cluster) — those wires' values are identical
    # in both versions by the replay induction, and positions are unchanged.
    hO = [i for i in range(F_B, F_K + 1) if lines[i].startswith("HMR")]
    hV = [i for i in hO if has_qtok(lines[i], qv) or has_qtok(lines[i], qb)]
    assert len(hV) == 1 and hV[0] == F_K, (tag, hO)
    assert new_mid[F_K - F_B].strip() == f"HMR {qb} {cfg['kill_bit']}", new_mid[-1][:60]
    # next victim touch after kill (recorded; dead-after or stale-covered)
    nxt = None
    for i in range(F_K + 1, min(F_K + 400000, len(lines))):
        if has_qtok(lines[i], qv):
            nxt = [i, lines[i].strip()[:60]]
            break
    gap = F_B - F_birth
    print(f"[{tag}] roles={roles} paid={p0}->{p1} borrow {qb} birth file={F_birth} "
          f"gap={gap} victim-stale={found[0]}:{found[1][:40]} next_v={nxt}", flush=True)
    header = lines[:HEADER_END]
    a = [f"{i}:{lines[i]}" for i in range(F_B - 3, F_K + 4)]
    b = ([f"{F_B - 3}:{lines[F_B - 3]}", f"{F_B - 2}:{lines[F_B - 2]}",
          f"{F_B - 1}:{lines[F_B - 1]}"]
         + [f"{F_B}+:{l}" for l in new_mid]
         + [f"{F_K + 1}:{lines[F_K + 1]}", f"{F_K + 2}:{lines[F_K + 2]}",
            f"{F_K + 3}:{lines[F_K + 3]}"])
    (ART / f"spill{tag}.diff").write_text("".join(difflib.unified_diff(
        a, b, fromfile="orig_fragment", tofile="rewritten_fragment")))
    tO = "".join(header + lines[ENTRY_CONVERT:F_K + 1])
    tR = "".join(header + lines[ENTRY_CONVERT:F_B] + new_mid)
    cO, cR = km.Circuit(tO), km.Circuit(tR)
    print(f"[{tag}] q/b orig={cO.num_qubits}/{cO.num_bits} "
          f"new={cR.num_qubits}/{cR.num_bits}", flush=True)
    assert cO.num_qubits == cR.num_qubits == W
    assert cO.num_bits == cR.num_bits
    rng = np.random.default_rng(0xD91)
    qb4 = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4 = rng.integers(0, 2, size=(cO.num_bits, 4)).astype(np.bool_)
    print(f"[{tag}] sim orig...", flush=True)
    simO, _ = sim_sized(tO, 99, qb4, bb4)
    print(f"[{tag}] sim rewritten...", flush=True)
    simR, _ = sim_sized(tR, 99, qb4, bb4)
    print(f"[{tag}] sim rewritten again...", flush=True)
    simR2, _ = sim_sized(tR, 99, qb4, bb4)
    qmis, nbits, bmis = compare(simO, cO, simR, cR)
    qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    res = {
        "block": tag, "victim": qv, "borrow": qb,
        "window_files": [F_B, F_K], "kill_bit": cfg["kill_bit"],
        "victim_roles": roles, "n_retargeted": len(vlines),
        "static_paid_orig": p0, "static_paid_new": p1, "static_paid_delta": p1 - p0,
        "borrow_birth": {"file": F_birth, "gap_file_lines": gap},
        "victim_stale_proof": {"last_value_affect": found},
        "next_victim_touch": nxt,
        "hmr_stream": "positions unchanged; only kill-line qubit operand swapped",
        "tail_file_lines": 0,
        "qubits_compared": W, "qubits_equal": len(qmis) == 0,
        "qubit_mismatches": qmis, "qubits_deterministic": qR == qR2,
        "bits_compared": nbits, "bit_mismatches": bmis,
    }
    (ART / f"spill{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"[{tag}] qubits_equal={res['qubits_equal']} det={res['qubits_deterministic']} "
          f"bits={nbits} bmis={bmis[:20]}", flush=True)
    return res


def stage1():
    ART.mkdir(parents=True, exist_ok=True)
    assert NEW, "NEW cuts not selected yet"
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)
    out = {}
    for cfg in NEW:
        r = verify_block(lines, cfg)
        assert r["qubits_equal"] and r["qubits_deterministic"] and not r["bit_mismatches"], \
            (cfg["tag"], "SLICE MISMATCH -> closed")
        out[cfg["tag"]] = r
    CUTS_JSON.write_text(json.dumps(
        {"prior": PRIOR, "new": {k: {"window_files": v["window_files"],
                                     "victim": v["victim"], "borrow": v["borrow"],
                                     "kill_bit": v["kill_bit"],
                                     "paid_delta": v["static_paid_delta"]} for k, v in out.items()}},
        indent=1) + "\n")
    print("stage1 OK: " + json.dumps({k: v["static_paid_delta"] for k, v in out.items()}))


def stage2():
    ART.mkdir(parents=True, exist_ok=True)
    cuts = json.load(open(CUTS_JSON))
    BLOCKS = ([{"tag": c["tag"], **c} for c in PRIOR]
              + [{"tag": t, "victim": v["victim"], "borrow": v["borrow"],
                  "F_B": v["window_files"][0], "F_K": v["window_files"][1],
                  "kill_bit": v["kill_bit"]} for t, v in cuts["new"].items()])
    BLOCKS.sort(key=lambda c: c["F_B"])
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)
    interference = {}
    # pairwise: earlier window vs later block's victim/borrow; windows disjoint
    for i, a in enumerate(BLOCKS):
        for j, b in enumerate(BLOCKS):
            if i == j:
                continue
            hits_v = [k for k in range(a["F_B"], a["F_K"] + 1)
                      if has_qtok(lines[k], b["victim"])]
            hits_b = [k for k in range(a["F_B"], a["F_K"] + 1)
                      if has_qtok(lines[k], b["borrow"])]
            interference[f"{a['tag']}win_touches_{b['victim']}({b['tag']}v)"] = hits_v
            interference[f"{a['tag']}win_touches_{b['borrow']}({b['tag']}b)"] = hits_b
    # ranges disjoint?
    ranges = sorted((c["F_B"], c["F_K"], c["tag"]) for c in BLOCKS)
    overlap = [(ranges[i], ranges[i + 1]) for i in range(len(ranges) - 1)
               if ranges[i][1] >= ranges[i + 1][0]]
    # renames introduce no new cross-touches
    intros = {}
    for cfg in BLOCKS:
        qv, qb = cfg["victim"], cfg["borrow"]
        other = [q for blk in BLOCKS if blk["tag"] != cfg["tag"]
                 for q in (blk["victim"], blk["borrow"])]
        new = [rename(lines[k], qv, qb) for k in range(cfg["F_B"], cfg["F_K"] + 1)]
        cfg["new_mid"] = new
        intro = [(k, q) for k, l in zip(range(cfg["F_B"], cfg["F_K"] + 1), new)
                 for q in other if has_qtok(l, q) and not has_qtok(lines[k], q)]
        intros[f"{cfg['tag']}_introduced_cross"] = intro
        p0 = sum(1 for k in range(cfg["F_B"], cfg["F_K"] + 1)
                 if lines[k].split()[0] in PAID)
        p1 = sum(1 for l in new if l.split()[0] in PAID)
        assert p0 == p1, (cfg["tag"], p0, p1)
        cfg["paid"] = [p0, p1]
    # gap intrusion (positional) + kill distinctness
    births = {}
    for cfg in BLOCKS:
        F_birth = None
        for k in range(cfg["F_B"] - 1, -1, -1):
            if has_qtok(lines[k], cfg["borrow"]):
                F_birth = k
                break
        births[cfg["tag"]] = F_birth
    gap_hits = {}
    for cfg in BLOCKS:
        for o in BLOCKS:
            if o["tag"] == cfg["tag"]:
                continue
            if births[cfg["tag"]] is not None and births[cfg["tag"]] < o["F_B"] < cfg["F_B"]:
                touch = any(has_qtok(lines[k], cfg["borrow"])
                            for k in range(o["F_B"], o["F_K"] + 1))
                gap_hits[f"{o['tag']}win_in_{cfg['tag']}borrow_gap_touch={touch}"] = \
                    [o["F_B"], o["F_K"], births[cfg["tag"]]]
    kills = [c["kill_bit"] for c in BLOCKS]
    # --- analyzed interference gate (strict zero is NOT the soundness boundary;
    # spillunified precedent merged with a proven-harmless reuse documented).
    # An ordered-pair hit (A-window touches B's wire q) is harmless iff:
    #   (a) q is a borrow and all hits are BEFORE borrow birth (birth resets), or
    #   (c) q is a borrow and all hits are AFTER B kill (post-kill |0> both), or
    #   (b) q is a stale-|0> victim (values identical at all times), or
    #   (d) q is the dead-after victim q878 and all hits are AFTER its rebirth.
    # Anything else (mixed timing, pre-rebirth) -> NO-GO (closed, not merged).
    by_q = {}
    for c in BLOCKS:
        by_q[c["victim"]] = (c["tag"], "v", c["F_B"], c["F_K"])
        by_q[c["borrow"]] = (c["tag"], "b", births[c["tag"]], c["F_K"])
    # stale-proven victims: F/G/H (stage1 victim_stale_proof) + D (stale.py blk237)
    stale_victims = {"q848", "q852", "q861", "q863"}
    # E victim q878 is dead-after: compute rebirth (first touch after E kill)
    E_K = next(c["F_K"] for c in BLOCKS if c["tag"] == "E")
    rebirth_E = None
    for k in range(E_K + 1, len(lines)):
        if has_qtok(lines[k], "q878"):
            rebirth_E = k
            assert lines[k].split()[0] in ("R", "HMR"), lines[k][:60]
            break
    assert rebirth_E is not None
    print(f"E victim q878 rebirth file={rebirth_E}: {lines[rebirth_E].strip()[:40]}",
          flush=True)
    classified, bad = {}, {}
    for key, hits in interference.items():
        if not hits:
            continue
        # key format: "{A}win_touches_{q}({B}tag{r})"
        q = key.split("_touches_")[1].split("(")[0]
        owner, role, bfile, kfile = by_q[q]
        if role == "b":
            if all(h < bfile for h in hits):
                cls = "a-pre-birth"
            elif all(h > kfile for h in hits):
                cls = "c-post-kill"
            else:
                cls = "MIXED-TIMING"
        else:
            if q in stale_victims:
                cls = "b-stale-victim"
            elif q == "q878":
                cls = ("d-post-rebirth" if all(h > rebirth_E for h in hits)
                       else "PRE-REBIRTH")
            else:
                cls = "UNKNOWN-VICTIM"
        classified[key] = {"class": cls, "n": len(hits),
                           "first": hits[:3], "last": hits[-1],
                           "boundary": [bfile, kfile]}
        if cls in ("MIXED-TIMING", "PRE-REBIRTH", "UNKNOWN-VICTIM"):
            bad[key] = classified[key]
    no_go = (
        bool(overlap)
        or bool(bad)
        or any(v for v in intros.values() if v)
        or any("touch=True" in k for k in gap_hits)
        or len(set(kills)) != len(kills)
    )
    print(json.dumps({"overlap": overlap, "classified": classified,
                      "bad": bad,
                      "intros": intros, "gap_hits": gap_hits, "kills": kills,
                      "no_go": bool(no_go)}, indent=1)[:3000], flush=True)
    if no_go:
        (ART / "spillglobal5.json").write_text(json.dumps(
            {"verdict": "CONFLICT", "overlap": overlap,
             "classified": classified, "bad": bad,
             "intros": intros, "gap_hits": gap_hits, "kills": kills},
            indent=1) + "\n")
        print("CONFLICT: aborting merge, no combined slice", flush=True)
        sys.exit(2)
    ENTRY = ENTRY_CONVERT
    maxK = max(c["F_K"] for c in BLOCKS)
    diff_parts = []
    for cfg in BLOCKS:
        F_B, F_K = cfg["F_B"], cfg["F_K"]
        a = [f"{i}:{lines[i]}" for i in range(F_B - 3, F_K + 4)]
        b = ([f"{F_B - 3}:{lines[F_B - 3]}", f"{F_B - 2}:{lines[F_B - 2]}",
              f"{F_B - 1}:{lines[F_B - 1]}"]
             + [f"{F_B}+:{l}" for l in cfg["new_mid"]]
             + [f"{F_K + 1}:{lines[F_K + 1]}", f"{F_K + 2}:{lines[F_K + 2]}",
                f"{F_K + 3}:{lines[F_K + 3]}"])
        frag = "".join(difflib.unified_diff(
            a, b, fromfile=f"orig_fragment_{cfg['tag']}",
            tofile=f"rewritten_fragment_{cfg['tag']}"))
        diff_parts.append(f"# block {cfg['tag']}: files [{F_B}..{F_K}] "
                          f"{cfg['victim']}->{cfg['borrow']}\n" + frag)
    (ART / "spillglobal5.diff").write_text("\n".join(diff_parts))
    print("wrote merged diff", flush=True)
    header = lines[:HEADER_END]
    seg = lines[ENTRY:maxK + 1]
    new_seg = list(seg)
    for cfg in BLOCKS:
        for k in range(cfg["F_B"], cfg["F_K"] + 1):
            new_seg[k - ENTRY] = rename(lines[k], cfg["victim"], cfg["borrow"])
    tO = "".join(header + seg)
    tR = "".join(header + new_seg)
    cO, cR = km.Circuit(tO), km.Circuit(tR)
    print(f"q/b orig={cO.num_qubits}/{cO.num_bits} new={cR.num_qubits}/{cR.num_bits}",
          flush=True)
    assert cO.num_qubits == cR.num_qubits == W
    assert cO.num_bits == cR.num_bits
    rng = np.random.default_rng(0xD91)
    qb4 = rng.integers(0, 2, size=(W, 4)).astype(np.bool_)
    bb4 = rng.integers(0, 2, size=(cO.num_bits, 4)).astype(np.bool_)
    print("sim orig...", flush=True)
    simO, _ = sim_sized(tO, 99, qb4, bb4)
    print("sim rewritten...", flush=True)
    simR, _ = sim_sized(tR, 99, qb4, bb4)
    print("sim rewritten again...", flush=True)
    simR2, _ = sim_sized(tR, 99, qb4, bb4)
    qmis, nbits, bmis = compare(simO, cO, simR, cR)
    qR = [[bool(v) for v in simR.read_across_shots(km.q(i))] for i in range(W)]
    qR2 = [[bool(v) for v in simR2.read_across_shots(km.q(i))] for i in range(W)]
    res = {
        "design": "independent-borrow merge (D+E+F+G+H); shared-borrow rejected structurally",
        "windows_files": {c["tag"]: [c["F_B"], c["F_K"]] for c in BLOCKS},
        "kill_bits": {c["tag"]: c["kill_bit"] for c in BLOCKS},
        "paid_per_block": {c["tag"]: {"orig": c["paid"][0], "new": c["paid"][1],
                                      "delta": c["paid"][1] - c["paid"][0]} for c in BLOCKS},
        "paid_total_delta": sum(c["paid"][1] - c["paid"][0] for c in BLOCKS),
        "hmr_stream": "positions unchanged in all windows; only kill-line qubit operands swapped",
        "interference_classified": classified,
        "interference_bad": bad,
        "E_victim_rebirth_file": rebirth_E,
        "slice": {"header_end": HEADER_END, "entry": ENTRY, "tail_file": maxK,
                  "tail_len": 0, "shots": 4, "sim_seed": 99, "init_seed": "0xD91"},
        "qubits_compared": W, "qubits_equal": len(qmis) == 0,
        "qubit_mismatches": qmis, "qubits_deterministic": qR == qR2,
        "bits_compared": nbits, "bit_mismatches": bmis,
        "verdict": ("MERGE_EQUAL" if (len(qmis) == 0 and not bmis) else "MERGE_MISMATCH"),
    }
    (ART / "spillglobal5.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"qubits_equal": res["qubits_equal"],
                      "det": res["qubits_deterministic"], "bmis": bmis,
                      "verdict": res["verdict"]}, indent=1), flush=True)


if __name__ == "__main__":
    if "--stage2" in sys.argv:
        stage2()
    else:
        stage1()
