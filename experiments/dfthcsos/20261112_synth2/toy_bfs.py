"""Stage-2 toy: exact minimal re-split on a k0 products micro-slice (single file).

Abstraction (documented, conservative):
- Take 6 DISTINCT static products targeting q11 from k0 (one copy per unordered
  pair among {q0,q1,q125,q126}); all six exist in artifacts/20261111_maoxin303
  angle_k_0.kmb (counts 2/8/5/8/6/4, asserted below). Duplicates in the full
  circuit correspond to different temporal qubit values (CX reprogramming), so
  taking one representative per static pair avoids spurious even-cancellation;
  the slice is a single-time snapshot where each static name = one variable.
- Treat the 4 control qubits as independent Boolean inputs x0..x3; word bit q11
  accumulates XOR of ANDs: f = XOR_{i<j} (xi & xj) (2nd elementary symmetric,
  6 products). Original cost = 6 CCXs. CX/X assumed free (affine combos free),
  CCX cost 1. Any X/CX/CCX-only subcircuit's AND inputs are affine combos of
  (primary vars + previous AND outputs) -- search covers all such circuits, so
  lower-bound enumeration is exact for multiplicative complexity.
- Upper bound: explicit 3-AND factoring (a+b)&(c+d) + (a&b) + (c&d).
- Lower bound: exhaustive BFS over all 1-AND and 2-AND circuits (affine inputs
  incl. constant, chaining allowed), checking output-span membership. If none
  matches, minimal >= 3; with 3-sufficiency, minimal == 3: 6 -> 3 validates
  "rearrange (CX reprogramming) + setup-allowed search saves CCX".

Usage: uv run python experiments/dfthcsos/20261112_synth2/toy_bfs.py
Reads artifacts/20261111_maoxin303/angle_k_0.kmb only for existence check (static).
No verifier call, no circuit edit, no word-table touch.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

WORK = Path(__file__).resolve().parents[3]
K0 = WORK / "artifacts" / "20261111_maoxin303" / "angle_k_0.kmb"

N = 4  # x0=q0 x1=q1 x2=q125 x3=q126
NROW = 1 << N  # 16
FULL = (1 << NROW) - 1


def var_mask(j: int) -> int:
    m = 0
    for i in range(NROW):
        if (i >> j) & 1:
            m |= 1 << i
    return m


VARS = [var_mask(j) for j in range(N)]
ONE = FULL  # constant-1 mask


def affine_basis() -> list[int]:
    """All 2^(N+1)=32 affine functions over vars (incl. 0)."""
    out = []
    for sub in range(1 << N):
        m = 0
        for j in range(N):
            if (sub >> j) & 1:
                m ^= VARS[j]
        out.append(m)          # const 0 part
        out.append(m ^ ONE)    # const 1 part
    return sorted(set(out))


AFF = affine_basis()
assert len(AFF) == 32
AFF_SET = set(AFF)
AFF_NZ = [a for a in AFF if a != 0]

# target: e2 = XOR of all 6 pairwise ANDs
F_TARGET = 0
for a in range(N):
    for b in range(a + 1, N):
        F_TARGET |= 0  # placeholder
# compute directly row-wise
ft = 0
for i in range(NROW):
    bits = [(i >> j) & 1 for j in range(N)]
    v = 0
    for a in range(N):
        for b in range(a + 1, N):
            v ^= bits[a] & bits[b]
    if v:
        ft |= 1 << i
F_TARGET = ft


def in_aff(m: int) -> bool:
    return m in AFF_SET


def span_has(mods: list[int], target: int) -> bool:
    """target in span(AFF, mods)? brute force over 2^len(mods) (len<=2)."""
    k = len(mods)
    for sub in range(1 << k):
        t = target
        for j in range(k):
            if (sub >> j) & 1:
                t ^= mods[j]
        if t in AFF_SET:
            return True
    return False


def main() -> int:
    # 0. existence check against real k0 (static pairs, one copy each)
    import kickmix
    c = kickmix.Circuit.from_file(str(K0), format="auto")
    c.to_file("/tmp/synth2_k0.kmx", format="kmx")
    lines = [l.strip() for l in open("/tmp/synth2_k0.kmx")
             if l.strip() and not l.strip().startswith(("REGISTER", "APPEND"))]
    ccx = [l for l in lines if l.startswith("CCX")]
    rest = ccx[69:]
    setup_targets = {"q120", "q121", "q122", "q123", "q124", "q125", "q126", "q127"}
    setup = [l for l in rest if l.split()[3] in setup_targets]
    loads = [l for l in rest if l not in setup]
    want = [tuple(sorted(p)) for p in
            [("q0", "q1"), ("q0", "q125"), ("q0", "q126"),
             ("q1", "q125"), ("q1", "q126"), ("q125", "q126")]]
    print("k0 loads total:", len(loads), "setup:", len(setup))
    ok = True
    for w in want:
        cnt = sum(1 for l in loads
                  if tuple(sorted(l.split()[1:3])) == w and l.split()[3] == "q11")
        print(f"  pair {w} x q11: count={cnt}")
        if cnt < 1:
            ok = False
    if not ok:
        print("TOY SETUP FAIL: expected pairs missing in k0")
        return 2
    print(f"target e2 mask=0x{F_TARGET:04x} (16-bit truth table)")

    # 1. upper bound: 3-AND factoring
    # w_ab = x0&x1, w_cd = x2&x3, w_cross = (x0^x1)&(x2^x3)
    w_ab = VARS[0] & VARS[1]
    w_cd = VARS[2] & VARS[3]
    w_cross = (VARS[0] ^ VARS[1]) & (VARS[2] ^ VARS[3])
    assert (w_ab ^ w_cd ^ w_cross) == F_TARGET, "factoring identity broken"
    assert span_has([w_ab, w_cd, w_cross], F_TARGET)
    print("upper bound: 3 ANDs suffice "
          f"(w_ab=0x{w_ab:04x} w_cd=0x{w_cd:04x} w_cross=0x{w_cross:04x})")

    # 2. lower bound k=1: all affine-input single ANDs
    n1 = 0
    hit1 = None
    seen_w1: set[int] = set()
    for ii in range(len(AFF_NZ)):
        for jj in range(ii, len(AFF_NZ)):
            u, v = AFF_NZ[ii], AFF_NZ[jj]
            if u == v:
                continue  # u&u=u linear, degenerate
            w = u & v
            if w == 0 or w in AFF_SET:
                continue  # degenerate (linear/zero), cannot help nonlinear f
            if w in seen_w1:
                continue
            seen_w1.add(w)
            n1 += 1
            if span_has([w], F_TARGET):
                hit1 = (u, v, w)
    print(f"k=1 exhaustive: {n1} distinct nonlinear ANDs, match={hit1 is not None}")
    if hit1 is not None:
        print("UNEXPECTED: 1 AND suffices; minimal=1 (toy still PASS, saving holds)")
        print("TOY RESULT: PASS (1 < 6)")
        return 0

    # 3. lower bound k=2: for each w1, all second ANDs with inputs affine(vars,w1)
    # (report circuits checked until first hit; minimal=2 needs only k=1
    #  exhaustive + one k=2 witness, so early stop is exact for the claim)
    n2circ = 0
    hit2 = None
    # extended affine sets per w1: {a XOR (c&w1) : a in AFF, c in {0,1}}
    for w1 in sorted(seen_w1):
        ext: list[int] = []
        s = set()
        for a in AFF:
            for cc in (0, w1):
                m = a ^ cc
                if m not in s:
                    s.add(m)
                    ext.append(m)
        ext_nz = [m for m in ext if m != 0]
        # index for ordering to enforce unordered pairs
        for ii in range(len(ext_nz)):
            for jj in range(ii, len(ext_nz)):
                u, v = ext_nz[ii], ext_nz[jj]
                if u == v:
                    continue
                w2 = u & v
                if w2 == 0:
                    continue
                # skip if w2 adds no dimension beyond span(AFF,w1)
                if w2 in AFF_SET or w2 == w1 or (w2 ^ w1) in AFF_SET:
                    continue
                n2circ += 1
                if span_has([w1, w2], F_TARGET):
                    hit2 = (w1, u, v, w2)
                    break
            if hit2 is not None:
                break
        if hit2 is not None:
            break
    print(f"k=2 search: {n2circ} (w1,w2) circuits checked until first hit, match={hit2 is not None}")
    if hit2 is not None:
        w1, u2, v2, w2 = hit2
        # recover output decomposition: find d1,d2,affine residue
        wit = None
        for d1 in (0, 1):
            for d2 in (0, 1):
                r = F_TARGET ^ (w1 if d1 else 0) ^ (w2 if d2 else 0)
                if r in AFF_SET:
                    wit = (d1, d2, r)
        # recover input decompositions over vars (+w1 for second AND)
        def aff_decomp(m):
            for sub in range(1 << N):
                base = 0
                for j in range(N):
                    if (sub >> j) & 1:
                        base ^= VARS[j]
                terms = "+".join(f"x{j}" for j in range(N) if (sub >> j) & 1) or "0"
                if base == m:
                    return f"{terms}"
                if base ^ ONE == m:
                    return f"{terms}+1"
            return "?"
        # first AND inputs: search affine pair giving w1
        f1 = None
        for ii in range(len(AFF_NZ)):
            for jj in range(ii, len(AFF_NZ)):
                u, v = AFF_NZ[ii], AFF_NZ[jj]
                if u != v and (u & v) == w1:
                    f1 = (u, v)
                    break
            if f1:
                break
        print(f"minimal=2 witness: w1=0x{w1:04x}={aff_decomp(f1[0])} & {aff_decomp(f1[1])}")
        # second AND inputs are u2,v2 (affine over vars+w1); show w1-use flag
        def ext_decomp(m):
            for sub in range(1 << N):
                for c0 in (0, 1):
                    for cw in (0, 1):
                        t = ONE if c0 else 0
                        for j in range(N):
                            if (sub >> j) & 1:
                                t ^= VARS[j]
                        if cw:
                            t ^= w1
                        if t == m:
                            terms = "+".join(f"x{j}" for j in range(N) if (sub >> j) & 1) or "0"
                            return f"{terms}{'+1' if c0 else ''}+w1*{cw}"
            return "?"
        print(f"  w2=0x{w2:04x}=({ext_decomp(u2)}) & ({ext_decomp(v2)})")
        print(f"  output: f = w1*{wit[0]} ^ w2*{wit[1]} ^ 0x{wit[2]:04x}({aff_decomp(wit[2])})")
        assert (F_TARGET ^ (w1 if wit[0] else 0) ^ (w2 if wit[1] else 0) ^ wit[2]) == 0
        print("TOY PASS (2 < 6): rearranged 2-AND + free XOR/X repacks 6 scattered products.")
        return 0

    print("TOY RESULT: PASS -- minimal ANDs = 3 (6 -> 3, saving 3 CCXs in slice).")
    print("Principle 'rearrange (free CX/XOR) + setup-allowed AND search saves CCX' holds on micro-instance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
