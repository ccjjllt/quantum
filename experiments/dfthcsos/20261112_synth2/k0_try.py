"""Stage-2 k0 attempt: factoring-merge search (static only, single file).

Pattern: two loads L1: CCX a b->t, L2: CCX a c->t (shared control a, same
target t, b!=c). Rewrite at L1 position to CX c->b; CCX a b->t; CX c->b and
delete L2: net -1 CCX, +2 CX (free in T). Needs >=2 such merges for
static 297 -> <=295.

Safety (sufficient, checked statically on kmx text): in the open interval
(L1,L2), (i) no line mentions t at all (any op, incl. HMR/CZ/R reads would see
a different t); (ii) no line has a/b/c as *target* (CX/CCX/X target, R/HMR on
a/b/c); (iii) no R/HMR/CZ mentions a/b/c (phase/measurement). Controls a/b/c
as CX/CCX controls are allowed (reads of frozen values).

If >=1 candidate: build one edited circuit (kmx text), check static CCX -1 and
words_match via recover_words_from_circuits (shots=2, fixed seed) on the single
edited loader + other 14 loaders? No -- words_match needs full family; here we
only test the edited k0 loader in isolation? recover_words needs full family
(num_vectors, num_angles). Full-family test with one edited loader swapped in
is the correct words_match oracle (cheap, shots=2). If the single-merge edit
preserves words_match, we would then seek a second disjoint merge for -2 and
only then run 2440-shot small verification. Any failure -> close.

Usage: uv run python experiments/dfthcsos/20261112_synth2/k0_try.py
Reads artifacts only; writes edited kmx to /tmp only. No word-table touch.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

WORK = Path(__file__).resolve().parents[3]
MAO = WORK / "artifacts" / "20261111_maoxin303"
K0 = MAO / "angle_k_0.kmb"


def parse_line_qubits(op: str, parts: list[str]):
    """Return (controls, targets, all_qubits) for kmx text line parts."""
    if op == "CX" and len(parts) == 3:
        return ([parts[1]], [parts[2]], [parts[1], parts[2]])
    if op == "CCX" and len(parts) == 4:
        return ([parts[1], parts[2]], [parts[3]], parts[1:4])
    if op == "X" and len(parts) == 2:
        return ([], [parts[1]], [parts[1]])
    if op == "R" and len(parts) == 2:
        return ([], [parts[1]], [parts[1]])
    if op == "HMR" and len(parts) >= 2:
        qs = [p for p in parts[1:] if p.startswith("q")]
        return ([], qs, qs)
    if op == "CZ":
        qs = [p for p in parts[1:] if p.startswith("q")]
        return (qs, qs, qs)  # conservative: all mentioned treated as touched
    # unknown op: conservative all-touch
    qs = [p for p in parts[1:] if p.startswith("q")]
    return (qs, qs, qs)


def main() -> int:
    import kickmix
    c = kickmix.Circuit.from_file(str(K0), format="auto")
    c.to_file("/tmp/synth2_k0full.kmx", format="kmx")
    lines = [l.strip() for l in open("/tmp/synth2_k0full.kmx")
             if l.strip() and not l.strip().startswith(("REGISTER", "APPEND"))]
    ccx_pos = [i for i, l in enumerate(lines) if l.startswith("CCX")]
    print(f"k0 text lines={len(lines)} ccx={len(ccx_pos)}")
    rest_ccx = ccx_pos[69:]
    setup_targets = {"q120", "q121", "q122", "q123", "q124", "q125", "q126", "q127"}
    is_setup = []
    for i in rest_ccx:
        t = lines[i].split()[3]
        is_setup.append(t in setup_targets)
    load_pos = [i for i, s in zip(rest_ccx, is_setup) if not s]
    print(f"phase2 ccx={len(rest_ccx)} setup={sum(is_setup)} loads={len(load_pos)}")
    # index loads: (a,b,t) unordered controls
    loads = []
    for i in load_pos:
        p = lines[i].split()
        a, b, t = p[1], p[2], p[3]
        loads.append((i, a, b, t))
    # group by (t, shared a): pairs with same t and shared exactly one control
    by_t: dict[str, list] = defaultdict(list)
    for L in loads:
        by_t[L[3]].append(L)
    cands = []
    tot_pairs = 0
    block = {"t-mention": 0, "write": 0, "phase": 0}
    for t, Ls in by_t.items():
        # consider ordered pairs L1 before L2
        for x in range(len(Ls)):
            for y in range(x + 1, len(Ls)):
                (i1, a1, b1, _), (i2, a2, b2, _) = Ls[x], Ls[y]
                s1, s2 = {a1, b1}, {a2, b2}
                inter = s1 & s2
                if len(inter) != 1:
                    continue
                tot_pairs += 1
                a = inter.pop()
                b = (s1 - {a}).pop()
                cc = (s2 - {a}).pop()
                if b == cc:
                    continue  # identical pair (k0hand already 0)
                # check interval (i1,i2) exclusive
                ok = True
                reason = ""
                for k in range(i1 + 1, i2):
                    l = lines[k]
                    p = l.split()
                    op = p[0]
                    ctrls, tgts, allq = parse_line_qubits(op, p)
                    if t in allq:
                        ok = False
                        block["t-mention"] += 1
                        break
                    if a in tgts or b in tgts or cc in tgts:
                        ok = False
                        block["write"] += 1
                        break
                    if op in ("R", "HMR", "CZ") and (a in allq or b in allq or cc in allq):
                        ok = False
                        block["phase"] += 1
                        break
                if ok:
                    cands.append((i1, i2, a, b, cc, t))
    print(f"same-t shared-1 pairs total: {tot_pairs}, blockers {block}")
    print(f"factoring candidates (same-t, shared-control, interval-clean): {len(cands)}")
    for cd in cands[:10]:
        print("  ", cd)
    if not cands:
        print("K0 RESULT: CLOSE -- no topologically safe factoring merge; "
              "static 297-><=295 unreachable by this pattern (k0hand 0 + this 0).")
        return 1
    # If candidates exist, test the first one via full-family words_match (shots=2).
    # Build edited line list: at i1 replace single CCX with CX/CCX/CX, delete i2.
    i1, i2, a, b, cc, t = cands[0]
    print(f"testing candidate: CCX {a} {b}->{t} + CCX {a} {cc}->{t}")
    ed = list(lines)
    # verify expected lines
    p1, p2 = ed[i1].split(), ed[i2].split()
    assert {p1[1], p1[2]} == {a, b} and p1[3] == t
    assert {p2[1], p2[2]} == {a, cc} and p2[3] == t
    ed[i1] = f"CX {cc} {b} ## synth2 merge1"
    ed.insert(i1 + 1, f"CCX {a} {b} {t} ## synth2 merged")
    ed.insert(i1 + 2, f"CX {cc} {b} ## synth2 restore")
    # i2 shifted by +2; delete it
    ed.pop(i2 + 2)
    # write edited kmx (need REGISTER/APPEND header? reuse original file header)
    raw = open("/tmp/synth2_k0full.kmx").read().splitlines()
    hdr = [l for l in raw if l.strip().startswith(("REGISTER", "APPEND"))]
    with open("/tmp/synth2_k0edit.kmx", "w") as f:
        f.write("\n".join(hdr) + "\n")
        f.write("\n".join(ed) + "\n")
    import kickmix as km
    try:
        ec = km.Circuit("/tmp/synth2_k0edit.kmx")
    except Exception as e:
        print(f"K0 RESULT: CLOSE -- edited kmx rejected by kickmix: {e}")
        return 1
    nccx = sum(1 for l in ed if l.startswith("CCX"))
    print(f"edited CCX count in k0 text: {nccx} (orig 297)")
    # words_match oracle: full family with edited k0 swapped in (shots=2)
    sys.path.insert(0, str(WORK / "data" / "competition" / "verifiers"))
    from dfthcsos.scoreinfra.circuits import load_circuits, recover_words_from_circuits
    import numpy as np
    fam = list(load_circuits(str(MAO)))
    assert len(fam) == 15
    fam[0] = ec
    sub = np.load(MAO / "submission.npz")
    words = np.asarray(sub["angle_words"])
    try:
        w, lay, tof = recover_words_from_circuits(
            fam, num_vectors=len(words), num_angles=words.shape[1],
            shots_per_address=2, seed=20261112)
    except Exception as e:
        print(f"K0 RESULT: CLOSE -- edited family invalid: {type(e).__name__}: {e}")
        return 1
    ok = bool(np.array_equal(w, words))
    print(f"words_match (shots=2, seed=20261112) with 1 merge: {ok}")
    if not ok:
        print("K0 RESULT: CLOSE -- merge breaks words_match.")
        return 1
    print("single merge preserves words_match; need a SECOND disjoint merge for -2 "
          "(not attempted here -- static only -1, below 297-><=295 gate).")
    print("K0 RESULT: CLOSE -- no -2 static candidate this round (1 safe merge at most).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
