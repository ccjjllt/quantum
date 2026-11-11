"""DQI spillcolor: strict interference graph over 6 cuts + brute-force MIS.

Strict edge rule (conservative, cf. spillglobal's lifecycle-reclassified gate):
nodes = {S(first fragment), D, E, F, G, H}.
Edge A-B iff ANY of:
  (w) A-window touches B-victim or B-borrow (either direction), where the
      S window = files [S_B..S_K] and S rewrite's new lines are also checked
      for introduced cross-touches of other cuts' victim/borrow qubits;
  (g) another cut's window falls inside A-borrow gap [birth..F_B) AND touches
      the borrow line there (positional gap intrusion);
  (k) kill-bit collision (same kill bit retargeted by two cuts).
Windows are pairwise disjoint (asserted). S retargets no kill-HMR (its HMR
q24 line is untouched), so S has no (k) edge by construction.

Borrow births: found by backward scan for each cut (assert HMR line),
except D/E/F/G/H which cross-check the recorded births from
spillmulti/spillglobal (assert equality).

Writes artifacts/20261110_spillcolor/colorgraph.json
(adjacency, edge reasons, all maximum independent sets).
No simulation here; no kmb built; no official verifier touched.
"""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

TMP = os.environ.get("TMPDIR", "/tmp/")
KMX = os.path.join(TMP, "dqi_e9diff", "e9.kmx")
ART = Path("artifacts/20261110_spillcolor")

# file coords (orig). S window covers rewritten orig lines + untouched tail.
BLOCKS = {
    # tag: victim, borrow, F_B, F_K, kill_bit (None = no kill retarget)
    "S": {"victim": "q22", "borrow": "q20",
          "F_B": 16446733, "F_K": 16446738, "kill_bit": None},
    "F": {"victim": "q848", "borrow": "q15",
          "F_B": 13831839, "F_K": 13832124, "kill_bit": "b100685"},
    "G": {"victim": "q852", "borrow": "q879",
          "F_B": 16051849, "F_K": 16053224, "kill_bit": "b101253"},
    "E": {"victim": "q878", "borrow": "q875",
          "F_B": 41258103, "F_K": 41258109, "kill_bit": "b99126"},
    "H": {"victim": "q861", "borrow": "q849",
          "F_B": 52088951, "F_K": 52089238, "kill_bit": "b99619"},
    "D": {"victim": "q863", "borrow": "q845",
          "F_B": 52299461, "F_K": 52299746, "kill_bit": "b99524"},
}
# recorded borrow births (file lines) from prior rounds; re-asserted by scan
RECORDED_BIRTH = {"F": 13831428, "G": 16051755, "E": 41247877,
                  "H": 52087388, "D": 52101869}
# S rewrite: orig 4 lines -> new 5 lines (spillfrag.diff, asserted verbatim)
S_ORIG = ["R q22", "CCX q18 q143 q22", "CX q22 q95", "CX q22 q143"]
S_NEW = ["R q20", "CCX q18 q143 q20", "CX q20 q95", "CX q20 q143", "R q20"]


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


def main():
    ART.mkdir(parents=True, exist_ok=True)
    with open(KMX, errors="replace") as f:
        lines = f.readlines()
    print(f"loaded {len(lines)} lines", flush=True)
    tags = ["S", "F", "G", "E", "H", "D"]

    # --- block text asserts (windows incl. S partial window) ---
    for t in tags:
        c = BLOCKS[t]
        if t == "S":
            got = [lines[i].strip() for i in range(c["F_B"], c["F_B"] + 4)]
            assert got == S_ORIG, got
            assert lines[c["F_B"] + 4].strip() == "CX q17 q84"
            assert lines[c["F_B"] + 5].strip() == "HMR q24 b101243"
        else:
            assert lines[c["F_B"]].strip() == f"R {c['victim']}", (t, lines[c["F_B"]][:60])
            assert lines[c["F_K"]].strip() == f"HMR {c['victim']} {c['kill_bit']}", \
                (t, lines[c["F_K"]][:60])

    # --- windows pairwise disjoint ---
    ranges = sorted((BLOCKS[t]["F_B"], BLOCKS[t]["F_K"], t) for t in tags)
    overlap = [(ranges[i], ranges[i + 1]) for i in range(len(ranges) - 1)
               if ranges[i][1] >= ranges[i + 1][0]]
    assert not overlap, overlap

    # --- borrow births (backward scan; cross-check recorded) ---
    births = {}
    for t in tags:
        c = BLOCKS[t]
        fb = None
        for i in range(c["F_B"] - 1, -1, -1):
            if has_qtok(lines[i], c["borrow"]):
                fb = i
                break
        assert fb is not None, t
        assert lines[fb].strip().startswith(f"HMR {c['borrow']} b"), (t, lines[fb][:60])
        for i in range(fb + 1, c["F_B"]):
            assert not has_qtok(lines[i], c["borrow"]), (t, "gap touch", i)
        births[t] = fb
        if t in RECORDED_BIRTH:
            assert fb == RECORDED_BIRTH[t], (t, fb, RECORDED_BIRTH[t])
        print(f"[{t}] borrow {c['borrow']} birth file={fb} gap={c['F_B'] - fb}", flush=True)

    # --- (w) window touches, ordered pairs ---
    touches = {}  # (A, q-of-B) -> count
    for a in tags:
        for b in tags:
            if a == b:
                continue
            A, B = BLOCKS[a], BLOCKS[b]
            for role in ("victim", "borrow"):
                q = B[role]
                n = sum(1 for i in range(A["F_B"], A["F_K"] + 1)
                        if has_qtok(lines[i], q))
                touches[(a, b, role)] = n

    # --- (w2) introduced cross-touches by each cut's rewrite ---
    intros = {}
    for t in tags:
        c = BLOCKS[t]
        other = [BLOCKS[o][r] for o in tags if o != t for r in ("victim", "borrow")]
        if t == "S":
            new = [l + "\n" for l in S_NEW]
            old = [lines[i] for i in range(c["F_B"], c["F_B"] + 4)]
        else:
            new = [rename(lines[i], c["victim"], c["borrow"])
                   for i in range(c["F_B"], c["F_K"] + 1)]
            old = [lines[i] for i in range(c["F_B"], c["F_K"] + 1)]
        hit = [(q) for l, o in zip(new, old) for q in other
               if has_qtok(l, q) and not has_qtok(o, q)]
        intros[t] = sorted(set(hit))

    # --- (g) positional gap intrusion: other window inside borrow gap + touches ---
    gap_hits = {}
    for t in tags:
        c = BLOCKS[t]
        for o in tags:
            if o == t:
                continue
            O = BLOCKS[o]
            if births[t] < O["F_B"] and O["F_K"] < c["F_B"]:
                n = sum(1 for i in range(O["F_B"], O["F_K"] + 1)
                        if has_qtok(lines[i], c["borrow"]))
                if n:
                    gap_hits[(o, t)] = n

    # --- (k) kill-bit collision ---
    kills = {t: BLOCKS[t]["kill_bit"] for t in tags if BLOCKS[t]["kill_bit"]}
    assert len(set(kills.values())) == len(kills), kills

    # --- strict adjacency ---
    adj = {t: set() for t in tags}
    reasons = {}
    for a in tags:
        for b in tags:
            if a >= b:
                continue
            rs = []
            for (x, y, role) in ((a, b, "victim"), (a, b, "borrow"),
                                 (b, a, "victim"), (b, a, "borrow")):
                # touches[(x,y,role)] = x-window touches y's <role> line
                n = touches[(x, y, role)]
                if n:
                    q = BLOCKS[y][role]
                    rs.append(f"{x}win~{q}({y}{role[0]})x{n}")
            if intros[a] or intros[b]:
                rs.append(f"intro({a}:{intros[a]},{b}:{intros[b]})")
            if (a, b) in gap_hits or (b, a) in gap_hits:
                rs.append("gap-intrusion")
            if reasons is not None and BLOCKS[a]["kill_bit"] and \
                    BLOCKS[a]["kill_bit"] == BLOCKS[b]["kill_bit"]:
                rs.append("kill-collision")
            if rs:
                adj[a].add(b)
                adj[b].add(a)
                reasons[f"{a}-{b}"] = rs

    # --- brute-force MIS (2^6) ---
    def independent(s):
        s = list(s)
        return all(b not in adj[a] for i, a in enumerate(s) for b in s[i + 1:])
    best, mis_sets = 0, []
    for r in range(6, 0, -1):
        cur = [set(c) for c in itertools.combinations(tags, r) if independent(c)]
        if cur:
            best, mis_sets = r, cur
            break
    print("adjacency:", {t: sorted(v) for t, v in adj.items()}, flush=True)
    print("reasons:", reasons, flush=True)
    print(f"MIS size={best} count={len(mis_sets)}",
          sorted([sorted(s) for s in mis_sets]), flush=True)

    out = {
        "nodes": {t: {**{k: v for k, v in BLOCKS[t].items()},
                       "borrow_birth_file": births[t]} for t in tags},
        "windows_disjoint": True,
        "kill_bits_distinct": True,
        "window_touches_nonzero": {f"{a}win~{BLOCKS[b][r]}({b}{r[0]})": n
                                   for (a, b, r), n in touches.items() if n},
        "introduced_cross": intros,
        "gap_intrusion": {f"{o}win-in-{t}gap": n for (o, t), n in gap_hits.items()},
        "adjacency": {t: sorted(v) for t, v in adj.items()},
        "edge_reasons": reasons,
        "mis_size": best,
        "mis_sets": sorted([sorted(s) for s in mis_sets]),
    }
    (ART / "colorgraph.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote colorgraph.json", flush=True)


if __name__ == "__main__":
    main()
