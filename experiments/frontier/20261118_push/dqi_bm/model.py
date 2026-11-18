#!/usr/bin/env python3
"""Pure-arithmetic cost model for the Berlekamp-Massey DQI decoder feasibility study.

NO simulation, NO verifier, NO kickmix. Every number printed is either
  [paper]  read off arXiv:2610.22367 / arXiv:2510.10967,
  [tape]   measured on 575b043f by the official verifier / by the region split
           (experiments/frontier/20261118_push/dqi_algo/RESULT.md), or
  [arith]  derived here from one of the two above.

Run:  python3 model.py
"""
from __future__ import annotations

import math

# measured cluster dump from the k_rounds kernel (static IR read of 575b043f)
import json
import pathlib
_RJ = pathlib.Path(__file__).with_name("rounds.json")
D = json.loads(_RJ.read_text()) if _RJ.exists() else None
RJ_EXISTS = D is not None

# ---------------------------------------------------------------- constants
REP = 1.1912605                    # verifier repetition factor at 0 errors, 102400 shots
REF = {"invsqrt": 2076774.233715,
       "dqi": 24439463583672.93,
       "chem": 3355599588.3155375}
SHIPPED = {"invsqrt": 74560.90687, "dqi": 346409762292.72, "chem": 294643137.73}

Q0, T0 = 890, 367116.057            # tape 575b043f, official verifier [tape]
COST0 = REP * Q0 * Q0 * T0
N_SYN, B = 70, 12                  # problem shape
L_MAX = 35                         # correctable errors
M_POS = 4095

# tape stage split [tape, dqi_algo/RESULT.md region split, mean executed T]
TAPE = {"eea_fwd": 153180.1, "chien": 44217.0, "eea_rev": 169719.2}
TAPE_STATIC = {"eea_fwd": 153186, "chien": 44264, "eea_rev": 170539}
TAPE_MUL = {"eea_fwd": 1542, "eea_rev": 1526}      # 42-CCX multiply-add blocks
TAPE_MUL_AND = 159300                              # field-multiply ANDs, all regions

# BM decoder as published [paper, 2610.22367 SI I.1]
BM = {"loc_fwd": 140000, "psi_fwd": 44000, "scan": 4024 * 23, "psi_rev": 44000}
BM["loc_rev"] = 440000 - sum(BM.values())          # implied by the 440k total

# n_positions actually scanned by our tape [tape]: 4,025 of 4,095 codeword positions
N_POS_TAPE = 4025


def gm(costs: dict[str, float]) -> float:
    return math.prod(REF[k] / costs[k] for k in REF) ** (1.0 / 3.0)


def dqi_cost(q: int, t: float) -> float:
    return REP * q * q * t


def t_for_gm(target: float, q: int = Q0) -> float:
    """mean T at width q that reaches `target` GM with the other two legs held."""
    # scale the whole dqi cost by (SHIPPED gm / target)^3
    cost = SHIPPED["dqi"] * (gm(SHIPPED) / target) ** 3
    return cost / (REP * q * q)


def header(s: str) -> None:
    print("\n" + s + "\n" + "-" * len(s))


# ---------------------------------------------------------------- 0. metric
header("0. the four decoders in both metrics  [paper]/[tape]/[arith]")
CIRCUITS = [
    ("competition reference dqi.kmb (EEA, 2nb)", 1893, 5725108.4),   # [tape] measured
    ("paper's EEA reimplementation (2nb)", 1938, 5100000),          # [paper]
    ("paper's BM decoder (2nb state)", 1837, 440000),               # [paper]
    ("our tape 575b043f (EEA, 1nb)", 890, 367116.057),              # [tape]
]
for name, q, t in CIRCUITS:
    print(f"  {name:40s} Q {q:>5} T {t:>10,.0f}  Q^2*T {q * q * t:>10.4e}"
          f" ({REP * q * q * t / COST0:6.3f}x cost)   T*Q {q * t:>10.4e}")
print(f"  paper's headline 12x is T*Q: {5100000 * 1938 / (440000 * 1837):.3f};"
      f" under Q^2*T the same pair is {dqi_cost(1938, 5100000) / dqi_cost(1837, 440000):.3f}")
print(f"  BM vs our tape: Q^2*T {dqi_cost(1837, 440000) / COST0:.2f}x worse,"
      f" T*Q {440000 * 1837 / (890 * 367116.057):.2f}x worse  -> the BM loses in its own metric too")

# ---------------------------------------------------------------- 1. target
header("1. what the 29.98-31.43 tier costs on the DQI leg (other two legs shipped)")
print(f"shipped GM {gm(SHIPPED):.6f}   dqi cost {SHIPPED['dqi']:.2f}  Q {Q0}  T {T0:,.1f}")
for g in (31.42723, 31.01379, 30.28512, 29.97900, 28.71339):
    c = SHIPPED["dqi"] * (gm(SHIPPED) / g) ** 3
    print(f"  GM {g:>8.5f} -> dqi cost <= {c:>18,.0f}   T(Q=890) <= {t_for_gm(g):>10,.0f}"
          f"   T(Q=840) <= {t_for_gm(g, 840):>10,.0f}")
print("  (brief's 249.6e9 / 264,600 confirmed to %.0f T)" % t_for_gm(31.42723))

header("1b. break-even T against the shipped tape, as a function of width")
print("  any decoder wider than 890 must also be cheaper in T: T_be(Q) = T0*(890/Q)^2")
for q in (890, 900, 950, 1000, 1100, 1200, 1704, 1837):
    tbe = COST0 / (REP * q * q)
    print(f"  Q={q:>5}: T <= {tbe:>10,.0f}   ({tbe / T0 - 1:+.1%} vs the tape)")

# ---------------------------------------------------------------- 2. BM state
header("2. BM live state at the peak of the forward pass  [arith]")
words = {"syndromes S_1..S_70 (read every round, live to round 70)": N_SYN,
         "locator sigma (deg <= 35, sigma_0=1)": L_MAX + 1,
         "template tau (deg <= 35)": L_MAX + 1}
tot = sum(words.values())
for k, v in words.items():
    print(f"  {v:>3} words = {12 * v:>5} qubits   {k}")
print(f"  {tot:>3} words = {12 * tot:>5} qubits   sum of the three irreversible commitments")
for extra, name in ((12, "temporary discrepancy Delta"), (19, "1-entry history stack [paper]"),
                    (4, "signed counter d"), (12, "sigma(beta)/omega(beta)/Psi(beta) scan temps")):
    print(f"  +{extra:>3} qubits  {name}")
print(f"  => BM floor {12 * tot} Q, published circuit 1,837 Q [paper], paper's no-reuse variant 2,677 Q")
print(f"  our tape 890 Q = {12 * N_SYN} syndrome + 50 pool [tape]")
if RJ_EXISTS:
    print(f"  MEASURED on the tape: the forward EEA's multiply blocks use 12-bit word indices"
          f" 2..73 = {72 * 12} qubits ({D['forward_n_target_words'] - 1} words, word 74 is the 2 flag")
    print("  qubits), and words 0 and 1 are never multiply operands -> one 70-word polynomial")
    print("  array, no second array.  That is the 1nb packing, measured, not inferred.")
print(f"  Q ratio (1704/890)^2 = {(1704 / 890) ** 2:.3f}   (1837/890)^2 = {(1837 / 890) ** 2:.3f}")

# ---------------------------------------------------------------- 3. stage T
header("3. stage table, T  [paper] BM  vs  [tape] 575b043f")
rows = [
    ("locator solve, forward", BM["loc_fwd"], TAPE["eea_fwd"]),
    ("locator solve, reverse", BM["loc_rev"], TAPE["eea_rev"]),
    ("phase scan (Chien/Forney)", BM["scan"], TAPE["chien"]),
    ("Psi = (sigma')^-1 mod sigma, EEA fwd", BM["psi_fwd"], 0),
    ("Psi EEA, reverse", BM["psi_rev"], 0),
]
for name, bm, tape in rows:
    d = "" if not tape else f"   BM/tape {bm / tape:5.2f}x"
    print(f"  {name:<38} BM {bm:>9,.0f}   tape {tape:>9,.0f}{d}")
print(f"  {'TOTAL':<38} BM {sum(BM.values()):>9,.0f}   tape {sum(TAPE.values()):>9,.0f}"
      f"   BM/tape {sum(BM.values()) / sum(TAPE.values()):5.2f}x")
print("  paper also lists the in-place evaluator omega = sigma*S mod z^35 (35*36/2 = 630"
      " multiplies) not separately; if it is not inside loc_fwd it adds ~%d T" % (630 * 42))

header("3b. where the multiplies are  [paper]/[tape]/[arith]")
bm_mul = 2 * sum(min(r // 2, L_MAX) for r in range(1, N_SYN + 1))
print(f"  BM forward multiply count, typical degree L_r ~ r/2: 2*sum(min(r/2,35), r=1..70) = {bm_mul:,}")
print(f"  tape forward multiply blocks (42 CCX)                : {TAPE_MUL['eea_fwd']:,}")
print(f"  => BM does {bm_mul / TAPE_MUL['eea_fwd']:.2f}x the multiplies of the tape's forward EEA")
print(f"  T per multiply, tape fwd : {TAPE_STATIC['eea_fwd'] / TAPE_MUL['eea_fwd']:6.1f}"
      f"   ({TAPE_STATIC['eea_fwd'] / TAPE_MUL['eea_fwd'] - 42:5.1f} T of control)")
print(f"  T per multiply, tape rev : {TAPE_STATIC['eea_rev'] / TAPE_MUL['eea_rev']:6.1f}")
print(f"  T per multiply, BM fwd   : {BM['loc_fwd'] / bm_mul:6.1f}"
      f"   ({BM['loc_fwd'] / bm_mul - 42:5.1f} T of control)   <- the whole BM advantage")
print(f"  tape control share of T  : {(TAPE_STATIC['eea_fwd'] + TAPE_STATIC['eea_rev'] + TAPE_STATIC['chien'] - TAPE_MUL_AND) / 367989:.1%}")
print("  WARNING: the tape's 57.3 T/multiply is a blend.  Measured per-cluster (section 6b):")
print("    forward ladder rounds w=17..30 cost 45.1 T/multiply -- BELOW the published BM's 57.1;")
print("    the excess sits in 93 clusters with w<=3 (69,622 T for 128 multiplies = 544 T each).")
print("  so the BM's 15.1 T of 'control per multiply' is not a saving the tape lacks everywhere.")

# ---------------------------------------------------------------- 4. hybrids
header("4. hybrids that keep the best measured stage of each  [arith]")
hyb_a = BM["loc_fwd"] + BM["loc_rev"] + TAPE["chien"]
hyb_b = hyb_a + 630 * 42
print(f"  A  BM locator (fwd {BM['loc_fwd']:,} + rev {BM['loc_rev']:,}) + tape scan {TAPE['chien']:,.0f}"
      f"  = {hyb_a:,.0f} T")
print(f"  B  A + evaluator omega priced at 630 multiplies x 42 T                = {hyb_b:,.0f} T")
print(f"  C  BM locator + BM scan machinery (published circuit)                = {sum(BM.values()):,.0f} T")
for name, t in (("A", hyb_a), ("B", hyb_b), ("C", sum(BM.values()))):
    print(f"     {name}: vs target {t_for_gm(31.42723):,.0f} T -> {t / t_for_gm(31.42723):.3f}x   "
          f"vs tape {t / T0:.3f}x   at Q=1704 cost {dqi_cost(1704, t):,.0f} "
          f"({dqi_cost(1704, t) / COST0:.2f}x shipped)")
    print(f"        widest Q at which {name} would still beat the tape: "
          f"{math.sqrt(COST0 / (REP * t)):.0f}")

header("4b. the same hybrids if the tape's scan were used AND control were free")
floor_bm = 2 * bm_mul * 42
print(f"  pure rank-42 AND floor of both BM locator passes: 2 x {bm_mul:,} x 42 = {floor_bm:,} T")
print(f"  + tape scan {TAPE_STATIC['chien']:,} = {floor_bm + TAPE_STATIC['chien']:,} T"
      f"  ({((floor_bm + TAPE_STATIC['chien']) / t_for_gm(31.42723) - 1):+.1%} vs target)")
print("  -> the BM+Chien hybrid only fits under the target if EVERY gate except the")
print("     42-AND multipliers and the scan is free; any control logic puts it over.")

# ---------------------------------------------------------------- 5. what would pay
header("5. what would actually have to change at Q=890 (the only width that pays)")
need = T0 - t_for_gm(31.42723)
ctrl = 164425
print(f"  T must fall by {need:,.0f} ({need / T0:.1%}) at Q=890")
print(f"  tape control logic + 12-bit AND chains = {ctrl:,} T ({ctrl / 367989:.1%} of static T)")
print(f"  halving it: T = {T0 - ctrl / 2:,.0f} -> GM {gm({**SHIPPED, 'dqi': dqi_cost(Q0, T0 - ctrl / 2)}):.4f}")
print(f"  removing {need:,.0f}: T = {T0 - need:,.0f} -> GM {gm({**SHIPPED, 'dqi': dqi_cost(Q0, T0 - need)}):.4f}")
print(f"  arithmetic floor of the shipped tape (all control free): "
      f"{TAPE_MUL_AND + TAPE_STATIC['chien']:,} T -> GM "
      f"{gm({**SHIPPED, 'dqi': dqi_cost(Q0, TAPE_MUL_AND + TAPE_STATIC['chien']) }):.4f}")
print(f"  at the bilinear floor 23 ANDs/multiply: {3068 * 23 + TAPE_STATIC['chien']:,} T")

# ------------------------------------------------- 6. the static full-sweep lead
header("6. variant tested and REJECTED by measurement: a static full sweep  [kernel]")
# measured on 575b043f by k_rounds v3 (rounds.json): the forward EEA's clean ladder
# (28 rounds, w = 3..30) fits  T(w) = 41.0*w + 109.3  with r2 = 0.9985, i.e. the
# marginal cost of one multiply position is 41 T -- the 42-AND multiply itself.
LADDER_A, LADDER_B = 41.0, 109.3
print(f"  measured ladder fit: T(w) = {LADDER_A:.1f}*w + {LADDER_B:.1f}  (28 rounds, w=3..30, r2 0.9985)")
print("  -> one window position costs 41 T, i.e. exactly its own 42-CCX multiply and")
print("     no per-position overhead at all, so a wider window can only add ANDs:")
add = (28 * 68 - sum(range(3, 31))) * LADDER_A
print(f"     widening the 28 ladder rounds to 68 positions adds {add:,.0f} T on the forward")
print(f"     ladder alone and removes nothing -> static full sweep REJECTED")

header("6b. where the tape's T actually is  [kernel, rounds.json]")
if RJ_EXISTS:
    for pass_name in ("eea_forward", "eea_reverse"):
        rows = D[pass_name + "_clusters"]
        print(f"  {pass_name}: {len(rows)} clusters, "
              f"T {sum(r['toffoli'] for r in rows):,}, "
              f"mult {sum(r['w'] for r in rows):,}")
        print(f"    {'w bucket':10s} {'n':>4} {'T':>8} {'mult':>6} {'T/mult':>7} {'share':>6}")
        for lo, hi, nm in ((1, 1, "w=1"), (2, 2, "w=2"), (3, 3, "w=3"),
                           (4, 16, "w=4-16"), (17, 30, "w=17-30"), (31, 10 ** 6, "w>=31")):
            s = [r for r in rows if lo <= r["w"] <= hi]
            tt = sum(r["toffoli"] for r in s)
            mm = sum(r["w"] for r in s)
            print(f"    {nm:10s} {len(s):>4} {tt:>8,} {mm:>6,} {tt / mm:>7.1f} {tt / 367989:>6.1%}")
        big = max(rows, key=lambda r: r["toffoli"])
        print(f"    largest single cluster: op {big['op_lo']:,}, w {big['w']}, "
              f"T {big['toffoli']:,} ({big['toffoli'] / 367989:.1%} of the tape), "
              f"{big['blt12']:,} of its Toffolis are in CCX blocks < 12")
else:
    print("  rounds.json missing")
print(f"  the whole target cut is {need:,.0f} T")

header("7. full-leg pricing of the candidates  [arith]")
CAND = [
    ("shipped tape 575b043f", 890, T0),
    ("BM + tape scan (hybrid A) at its Q floor", 1704, hyb_a),
    ("hybrid B (A + evaluator) at its Q floor", 1704, hyb_b),
    ("published BM circuit", 1837, 440000),
    ("hybrid A if it were 890 Q (it cannot be)", 890, hyb_a),
    ("the 890-Q target for GM 31.42723", 890, t_for_gm(31.42723)),
]
print(f"  {'candidate':42s} {'Q':>5} {'T':>9} {'dqi cost':>11} {'x shipped':>9} {'GM':>9}")
for nm, q, t in CAND:
    c = dqi_cost(q, t)
    print(f"  {nm:42s} {q:>5} {t:>9,.0f} {c:>11.4e} {c / COST0:>9.3f} "
          f"{gm({**SHIPPED, 'dqi': c}):>9.4f}")

header("8. scope of the remaining 890-Q lead  [kernel]")
print(f"  target cut {need:,.0f} T; the two biggest clusters hold 95,317 T "
      f"({95317 / need:.1%} of it)")
print("  forward op 19,508,954: 29,543 T, 3 multiply blocks, 20,723 CCX in blocks < 12")
print("  reverse op 46,230,185: 65,774 T, 66 multiply blocks, 46,966 CCX in blocks < 12")

header("9. the multiply floor of the whole shipped tape  [kernel]")
print(f"  3,068 multiply blocks x 42 ANDs = {3068 * 42:,} T = {3068 * 42 / 367989:.1%} of the tape")
print(f"  measured ladder density 41.0 T/multiply => {3068 * 41:,.0f} T floor")
print(f"  the tape spends {367989 - 3068 * 41:,} T ({1 - 3068 * 41 / 367989:.1%}) on everything else")
