#!/usr/bin/env python3
"""Public-salt model arithmetic for the quantum-compilation ledger.

ZERO compute: local arithmetic over costs already recorded in the submission
ledger (kaggle competitions submissions -c ... --csv, account qingyu1232) and
in intel/RESULT_*.md.  No simulation, no verifier runs, no downloads.

Model
-----
  GM = (R1/ci * R2/cd * R3/cc)^(1/3)
  score = const * mean_toffoli_count * repetition_factor       (commutation)
  R(0 value errors) = 1.1912604648115832
  R(1 value error)  = 1.1967314991687559      rho = 1.0045926433

  ci and cc are salt-invariant (verified, 3/3).  cd(<file>) is a FIXED
  per-file hidden-public-salt constant: either clean or clean*rho, each to
  within the per-salt mean-T wobble (~1e-6 relative).

Precision budget
----------------
  public GM is published to 5 dp -> cd relative +-3*0.5e-5/GM ~= +-5.4e-7
  per-salt mean-T wobble (observed)      -> cd relative +-1.0e-6
  clean|lost separation = 4.6e-3         -> ~3000x the ambiguity
"""
R1 = 2076774.233715
R2 = 24439463583672.93
R3 = 3355599588.3155375

RHO = 1.1967314991687559 / 1.1912604648115832


def gm(ci, cd, cc):
    return (R1 / ci * R2 / cd * R3 / cc) ** (1.0 / 3.0)


def _rest(g, a, b):
    return R1 * R2 * R3 / (g ** 3 * a * b)


def solve_cd(g, ci, cc):
    return _rest(g, ci, cc)


def solve_ci(g, cd, cc):
    return _rest(g, cd, cc)


def solve_cc(g, ci, cd):
    return _rest(g, ci, cd)


INV = {"0af21cb8": 74797.36535717871, "f2cdab0b": 75006.37653863191,
       "8b410e77": 75038.1340, "2c125b39": 75082.09, "47b31838": 75170.62,
       "9c708f7b": 93555.32, "a15b0d73": 93925.35, "26ebf39d": 94537.59}

DQI_CLEAN = {"61c8348d": 346413579540.4963, "957d6733": 346654523463.49384,
             "f425ea20": 346992317312.81555, "b0983d55": 347045216047.3212,
             "66b4f18b": 347128304010.81165, "00ac37d4": 347357914646.9683,
             "ccc2ab84": 347375470571.73334}

CHEM = {"a73b25d2": 294643137.73357135, "93326853": 294762512.64351326,
        "bdae290f": 294762632.0817748, "sub1": 294762697.43843937,
        "f6e12f02": 294762732.9775791, "a970f175": 294762689.353492,
        "703843d3": 294762512.8596263, "881d9dae": 294763525.68,
        "marculera6": 294800582.44, "maoxin303": 298720881.30,
        "p0_79f790fa": 299497670.48, "f21b8a87": 297557548.71}

# public GM -> implied cd, per ledger row (kaggle CSV, 2026-11-17)
ROWS = [
    # ref, invsqrt, dqi, chem, publicGM, stated cd (or None)
    (58453168, "0af21cb8", "b0983d55", "93326853", 28.08701, 347045216047.3212),
    (58452435, "0af21cb8", "61c8348d", "93326853", 28.14703, 346413579540.4963),
    (58451475, "0af21cb8", "f425ea20", "93326853", 28.08843, 346992317312.81555),
    (58442668, "0af21cb8", "66b4f18b", "bdae290f", 28.12769, 347128304010.81165),
    (58436763, "f2cdab0b", "66b4f18b", "bdae290f", 28.10154, 347128304010.81165),
    (58424363, "f2cdab0b", "ccc2ab84", "sub1", 28.09486, 347375470571.73334),
    (58420406, "8b410e77", "ccc2ab84", "f6e12f02", 28.09090, 347375470571.73334),
    (58410043, "2c125b39", "4b350932", "881d9dae", 28.07502, 347760709936.55),
    (58392219, "47b31838", "46446af1", "marculera6", 28.05896, 347904227556.0),
    (58228252, "a15b0d73", "9fcda0c1", "maoxin303", 25.30340, 374685006336.0),
    (58190972, "26ebf39d", "e9", "p0_79f790fa", 25.22676, 376407450170.0),
]


def cls(r):
    if abs(r - 1.0) < 1.5e-6:
        return "CLEAN"
    if abs(r - RHO) < 1.5e-6:
        return "LOST"
    if abs(r - 1.0 / RHO) < 1.5e-6:
        return "LOST->CLEAN"
    return "*** OTHER ***"


print(f"rho = 1 value error / 0 errors = {RHO:.10f}")
print(f"clean|lost separation {RHO-1:.3e}, ambiguity ~1.5e-06 "
      f"-> {(RHO-1)/1.5e-6:.0f}x\n")

# ------------------------------------------------------------------ proofs
print("=" * 86)
print("A. SAME-FILE PAIRS ACROSS SUBMISSIONS  (determinism, re-derived)")
print("=" * 86)
c1 = solve_cd(28.09090, INV["8b410e77"], CHEM["f6e12f02"])
c2 = solve_cd(28.09486, INV["f2cdab0b"], CHEM["sub1"])
print(f"ccc2ab84  58420406 (8b410e77 + f6e12f02) {c1:>18,.1f}")
print(f"ccc2ab84  58424363 (f2cdab0b + sub1)     {c2:>18,.1f}"
      f"   delta {abs(c1-c2)/c1:.2e}   [both other legs differ]")
c3 = solve_cd(28.12769, INV["0af21cb8"], CHEM["bdae290f"])
c4 = solve_cd(28.10154, INV["f2cdab0b"], CHEM["bdae290f"])
print(f"66b4f18b  58442668 (0af21cb8)            {c3:>18,.1f}")
print(f"66b4f18b  58436763 (f2cdab0b)            {c4:>18,.1f}"
      f"   delta {abs(c3-c4)/c3:.2e}   [invsqrt differs]")
imp_chem = (27.31193 / 27.31541) ** 3
rec_chem = 294878860.58 / 294991455.82
print(f"821bf8d1  58382097 / 58350759 chem ratio implied {imp_chem:.8f}"
      f" vs recorded {rec_chem:.8f}  delta {imp_chem-rec_chem:+.1e}")
print(f"e9        58190972 (self-built) and 58181743 (upstream zip), same three"
      f" circuit bytes: 25.22676 == 25.22676")

# ------------------------------------------------------- ledger inversion
print()
print("=" * 86)
print("B. LEDGER INVERSION  public GM -> implied public cost of the DQI leg")
print("=" * 86)
print(f"{'ref':>9} {'dqi':>9} {'pub GM':>9} {'GM if lab cost':>9} "
      f"{'dGM':>8} {'implied cd':>21} {'vs stated':>11} {'class':>12}")
implied = {}
for ref, ci, cd, cc, g, stated in ROWS:
    v = solve_cd(g, INV[ci], CHEM[cc])
    implied.setdefault(cd, []).append(v)
    r = v / stated
    fwd = gm(INV[ci], stated, CHEM[cc])
    print(f"{ref:>9} {cd:>9} {g:>9.5f} {fwd:>13.5f} {g-fwd:>+8.5f} "
          f"{v:>21,.1f} {r:>11.8f} {cls(r):>12}")

print("\nB2. rows with identifiable hashes that CANNOT be inverted "
      "(two of three costs unknown)")
NOINV = [
    (58382097, "1ba197b0", "821bf8d1", "v119 294878860.58", 27.31541,
     "ci(1ba197b0) never recorded numerically"),
    (58350759, "1ba197b0", "821bf8d1", "4033 294991455.82*", 27.31193,
     "ci never recorded; chem inferred from the A/B pair"),
    (58349843, "Atakan", "821bf8d1", "4033", 27.30661, "two costs unknown"),
    (58299045, "321aff83", "7cbe8ecf", "6418ec8e", 27.00209,
     "46Q family; no costs recorded"),
    (58290992, "9c708f7b", "392k-swap", "5d5007a75784", 25.44039,
     "chem never recorded numerically"),
    (58271862, "9c708f7b", "eae396ba", "5d5007a75784", 25.40482,
     "chem never recorded numerically"),
    (58265561, "9c708f7b", "eae396ba", "f21b8a87 297557548.71", 25.39570,
     "ci never recorded numerically"),
    (58256166, "9c708f7b 93555.32", "cd71c482", "f21b8a87 297557548.71", 25.38868,
     "cd never recorded numerically"),
    (58239559, "6c6a734d", "cd71c482", "297558526.59", 25.36085,
     "ci never recorded numerically"),
    (58235797, "6c6a734d", "cd71c482", "8afd4c67 (loaders only)", 25.33133,
     "ci and cc never recorded; see note"),
    (58222873, "Ozertuu portfolio", "-", "-", 25.29661, "no per-file costs"),
    (58181743, "gengsr portfolio", "e9", "79f790fa", 25.22676,
     "upstream zip; same bytes as 58190972 -> same score"),
    (58123354, "7c10edba", "4432ec5f", "c1321df2", 25.14222, "no costs"),
    (58041132, "-", "-", "-", 24.94081, "no hashes"),
    (58014726, "-", "-", "-", 24.78590, "no hashes"),
    (57980157, "-", "-", "-", 24.54651, "no hashes"),
    (57876561, "-", "-", "-", 23.83790, "no hashes"),
    (57808271, "-", "-", "-", 23.00037, "no hashes"),
]
for ref, ci, cd, cc, g, why in NOINV:
    print(f"{ref:>9} {cd:>14} {g:>9.5f}  {why}")
print("  note 58235797 vs 58239559: same invsqrt + same DQI + same loader table")
print("  but GM 25.33133 vs 25.36085 -> the chem npz is NOT the same file")
print("  ('8afd4c67' is the loader-table name, not the npz hash). No model")
print("  violation; the pair yields cc(58235797) = 297,558,526.59*(25.36085/"
      "25.33133)^3 = 298,600,000-class.")

# -------------------------------------------------- definitive per-file table
print()
print("=" * 86)
print("C. DEFINITIVE PER-FILE TABLE")
print("=" * 86)
PUB = {}
for cd, vals in implied.items():
    vals = sorted(vals)
    PUB[cd] = vals[len(vals) // 2]
print(f"{'dqi file':>9} {'clean cost (lab)':>21} {'public cost':>21} "
      f"{'ratio':>11} {'status':>6}")
CLEAN_REF = dict(DQI_CLEAN)
CLEAN_REF["4b350932"] = 347760709936.55        # ledger PASS, 0/0
CLEAN_REF["46446af1"] = 347904227556.0         # publisher default 0/0
CLEAN_REF["9fcda0c1"] = 374685006336.0         # ledger PASS
CLEAN_REF["e9"] = 376407450170.0 / RHO         # ledger value was the LOST draw
for cd in ["61c8348d", "957d6733", "f425ea20", "b0983d55", "66b4f18b",
           "00ac37d4", "ccc2ab84", "4b350932", "46446af1", "9fcda0c1", "e9"]:
    ref = CLEAN_REF[cd]
    if cd in PUB:
        print(f"{cd:>9} {ref:>21,.1f} {PUB[cd]:>21,.1f} "
              f"{PUB[cd]/ref:>11.8f} {cls(PUB[cd]/ref):>6}")
    else:
        print(f"{cd:>9} {ref:>21,.1f} {'unrevealed':>21} {'-':>11} {'?':>6}")
print(f"{'821bf8d1':>9} {'(not recorded)':>21} {'fixed, class unknown':>21} "
      f"{'-':>11} {'?':>6}")
print("\nno ratio outside {1+-1.5e-6, rho+-1.5e-6, 1/rho+-1.5e-6}: "
      "no 2-lost-shot file, no new penalty observed.")
print(f"revealed tally: 7 CLEAN (61c, 66b4, ccc, 4b35, 46446, 9fcd, e9) / "
      f"2 LOST (f425, b098)")

print("\nC2. e9 detail: stated 376,407,450,170 is the LOST draw")
print(f"  implied public      {PUB['e9']:>21,.1f}")
print(f"  stated / rho        {376407450170.0/RHO:>21,.1f}"
      f"   delta {PUB['e9']/(376407450170.0/RHO)-1:+.2e}")

print("\nC3. 58392219 publisher cross-check")
print(f"  implied cd(46446af1) {PUB['46446af1']:,.1f}  vs stated "
      f"347,904,227,556 (x{PUB['46446af1']/347904227556.0:.7f})")
print(f"  GM at cd*rho {gm(INV['47b31838'], PUB['46446af1']*RHO, CHEM['marculera6']):.5f}"
      f"  (publisher's two failed-shot salts: 28.016)")

# ------------------------------------------------------------------ combos
print()
print("=" * 86)
print("D. COMBO TABLE   invsqrt 0af21cb8 (min known) + chem a73b25d2 (min known)")
print("=" * 86)
STATUS = {"61c8348d": "CLEAN", "66b4f18b": "CLEAN", "ccc2ab84": "CLEAN",
          "4b350932": "CLEAN", "46446af1": "CLEAN", "9fcda0c1": "CLEAN",
          "f425ea20": "LOST", "b0983d55": "LOST",
          "957d6733": "unknown", "00ac37d4": "unknown"}
SET = ["61c8348d", "66b4f18b", "ccc2ab84", "f425ea20", "b0983d55",
       "957d6733", "00ac37d4"]
print(f"{'dqi':>9} {'status':>8} {'cd(a) worst':>21} {'GM (a)':>9} "
      f"{'cd(b) 40%':>21} {'GM (b)':>9} {'E[GM] (b)':>9} {'if CLEAN':>9}")
res = {"a": [], "b": [], "bE": []}
for cd in SET:
    clean = DQI_CLEAN[cd]
    lost = clean * RHO
    st = STATUS[cd]
    if st == "unknown":
        cda = lost
        cdb = 0.6 * clean + 0.4 * lost
        eg = 0.6 * gm(INV["0af21cb8"], clean, CHEM["a73b25d2"]) + \
             0.4 * gm(INV["0af21cb8"], lost, CHEM["a73b25d2"])
    else:
        cda = cdb = PUB[cd]
        eg = gm(INV["0af21cb8"], cdb, CHEM["a73b25d2"])
    ga = gm(INV["0af21cb8"], cda, CHEM["a73b25d2"])
    gb = gm(INV["0af21cb8"], cdb, CHEM["a73b25d2"])
    print(f"{cd:>9} {st:>8} {cda:>21,.0f} {ga:>9.5f} {cdb:>21,.0f} "
          f"{gb:>9.5f} {eg:>9.5f} {gm(INV['0af21cb8'], clean, CHEM['a73b25d2']):>9.5f}")
    res["a"].append((ga, cd)); res["b"].append((gb, cd)); res["bE"].append((eg, cd))
print(f"\nmodel (a) worst-case  argmax: {max(res['a'])[1]}  GM {max(res['a'])[0]:.5f}")
print(f"model (b) 40%-lost    argmax: {max(res['b'])[1]}  GM {max(res['b'])[0]:.5f}"
      f"   (E[GM] {max(res['bE'])[0]:.5f})")

print("\nD2. chem alternatives on 0af + 61c8348d-public-clean (exact)")
for cc in ["a73b25d2", "93326853", "bdae290f", "sub1", "f6e12f02"]:
    print(f"  {cc:>9} {CHEM[cc]:>19,.4f}   GM "
          f"{gm(INV['0af21cb8'], PUB['61c8348d'], CHEM[cc]):.8f}")

print("\nD3. DQI alternatives on 0af + a73b25d2, ranking by clean cost")
for cd in sorted(SET, key=lambda k: DQI_CLEAN[k]):
    print(f"  {cd:>9} clean {DQI_CLEAN[cd]:>18,.1f}   clean-GM "
          f"{gm(INV['0af21cb8'], DQI_CLEAN[cd], CHEM['a73b25d2']):.5f}")

# --------------------------------------------------------- gold requirement
print()
print("=" * 86)
print("E. CEILING AND GOLD 28.68633")
print("=" * 86)
ci, cd, cc = INV["0af21cb8"], PUB["61c8348d"], CHEM["a73b25d2"]
cur = gm(ci, cd, cc)
GOLD = 28.68633
print(f"best known-byte combo (0af + 61c-public + a73b) = {cur:.8f}")
print(f"  pending 58454232 prediction                     = {cur:.5f}")
print(f"previous public best (58452435)                   = 28.14703")
k = (GOLD / cur) ** 3
print(f"gold gap {GOLD-cur:+.5f};  product must shrink {(k-1)*100:.3f}%")
print(f"  single leg alone          /{k:.6f}  (each leg -{(1-1/k)*100:.3f}%)")
print(f"  all three equally         /{k**(1/3):.6f}  (each leg "
      f"-{(1-1/k**(1/3))*100:.3f}%)")
print(f"  invsqrt needed {solve_ci(GOLD, cd, cc):>14,.3f}  (now {ci:,.3f})")
print(f"  DQI     needed {solve_cd(GOLD, ci, cc):>14,.1f}  (now {cd:,.1f})")
print(f"  chem    needed {solve_cc(GOLD, ci, cd):>14,.1f}  (now {cc:,.1f})")
print(f"  DQI mean-T equivalent: {367789.4945800781*(1-solve_cd(GOLD,ci,cc)/cd):,.0f}"
      f" Toffoli off 367,789")

# ------------------------------------------------------- 58453168 hindsight
print()
print("=" * 86)
print("F. 58453168 POST-MORTEM")
print("=" * 86)
b = DQI_CLEAN["b0983d55"]
print(f"  b0983d55 clean + 93326853 : GM "
      f"{gm(INV['0af21cb8'], b, CHEM['93326853']):.5f}   (28.12994 predicted)")
print(f"  b0983d55 lost  + 93326853 : GM "
      f"{gm(INV['0af21cb8'], b*RHO, CHEM['93326853']):.5f}   <-- observed 28.08701")
print(f"  61c8348d public-clean     : GM "
      f"{gm(INV['0af21cb8'], PUB['61c8348d'], CHEM['93326853']):.5f}   (ref 58452435)")
print(f"  b0983d55 clean + a73b25d2 : GM "
      f"{gm(INV['0af21cb8'], b, CHEM['a73b25d2']):.5f}   <-- even a CLEAN b098 "
      f"cannot beat 61c")
print(f"  61c8348d public-clean+a73b: GM "
      f"{gm(INV['0af21cb8'], PUB['61c8348d'], CHEM['a73b25d2']):.5f}   <-- optimal")
print(f"  cost gap 61c-clean vs b098-clean: "
      f"{b-PUB['61c8348d']:,.1f} ({(b/PUB['61c8348d']-1)*100:.4f}%)")
print(f"  even a CLEAN b098 is {gm(INV['0af21cb8'], PUB['61c8348d'], CHEM['a73b25d2'])-gm(INV['0af21cb8'], b, CHEM['a73b25d2']):.5f}"
      f" BEHIND 61c -- the leg was strictly dominated before the slot was spent")

print()
print("  lab-record prior, Beta(7,2) from the 7/9 revealed public rate:")
for cd, k, n in [("b0983d55", 3, 3), ("61c8348d", 1, 3)]:
    p = (k + 7) / (n + 9)
    ev = p * gm(INV["0af21cb8"], DQI_CLEAN[cd], CHEM["a73b25d2"]) + \
        (1 - p) * gm(INV["0af21cb8"], DQI_CLEAN[cd] * RHO, CHEM["a73b25d2"])
    print(f"    {cd}: lab {k}/{n} -> P(public clean) {p:.3f};  "
          f"E[GM] {ev:.5f}")
print("    with 61c's status already REVEALED clean the comparison is")
print(f"    61c {gm(INV['0af21cb8'], PUB['61c8348d'], CHEM['a73b25d2']):.5f} vs "
      f"b098 E[GM] "
      f"{0.833*gm(INV['0af21cb8'], b, CHEM['a73b25d2'])+0.167*gm(INV['0af21cb8'], b*RHO, CHEM['a73b25d2']):.5f}")
