# Section 4 verdict (bounded): no positive-gain candidate this round

Scope kept exactly as ordered: free Z/CZ elimination with explicit gate sequences (4.1);
g = q23 XOR q21 shared-AND with domain/boundary/out-of-domain checks (4.2);
multi-condition branches up to 8 with GF(2) + inclusion-exclusion coverage (4.3);
256 expressions, seed 8121, then stop.

## 4.1 Free phase elimination: NEGATIVE (screen + exact refutations)

- Screen `free_elim_screen.py` on `shortcache_zero.kmb` (`97e639…`), window [26111,30599),
  38 CCZs (G1 19x `CCZ q18 q23 w` + G2 19x `CCZ q27 q23 w`, word set identical),
  25809 inputs (1..16383 + bit boundaries + random + address/delta + out-of-domain),
  seeds 101/202. Template family per CCZ: {delete, Z u, CZ u v}, u,v over all 62 wires
  (incl. cache q41=ab, q50=abc). Saved per-CCZ option tables in `free_elim_screen.json`.
- All 11 firing CCZs (prod 11..787 on samples): **zero** two-seed survivors — every template,
  cache-wire ones included, refuted on concrete samples (sample mismatch with fixed
  measurement outcomes is a valid full counterexample: data trajectory is
  measurement-independent, only classical guards vary).
- 21 survivors are all vacuous (prod <= 1 on 25809 samples): gates that (almost) never fire
  on samples; deleting them would save ~0 execution-weighted cost regardless of proof.
- Exact Z3 legal-prefix miters (`free_elim_spotproof.py`, 60s timeout, shortcache coords,
  entry x in [1,3133452], symbolic HMR outcomes) for the top firing CCZs x cache templates:
  26655 x {CZ q41 q23, CZ q50 q14, Z q41} and 27227 x {CZ q41 q23, CZ q50 q14, Z q50} —
  all 6 returned **sat (refuted)** with saved counterexample x
  (1651, 1536, 3022, 317, 764, 388; 23k SSA nodes, 3-33s each).
  `free_elim_spotproofs.json` PASS-as-refutations (all verdicts sat, none unknown).
- Verdict 4.1: no free Z/CZ elimination for any firing CCZ, with or without cache wires.

## 4.2 g*u shared AND: domain facts + why no template built

- From the saved 25809-sample matrix (recomputed inputs() reproduces 25809 xs):
  q21 == (x<=63) exactly (matches the proven 65-claim prefix proof in audit_stage1);
  q23&(x<=63)==0; q21&q23==0; G1 fires 3264 / G2 fires 960 / overlap (q18&q27&q23) 192 —
  G1 vs G2 are NOT mutually exclusive; G3/G4 (q21 groups) are exclusive vs q23 groups.
- Correction to the earlier "g恒1" note: it held only on the 1..4096 slice; on the wider
  set q23 fires 4066/25809, g has zeros. g is not constant, but that does not help (below).
- Out-of-domain phase: every CCZ phase monomial syntactically contains its data controls
  (qa&qb&word), so out-of-domain phase is 0 by construction. No `ab·word` term was ever
  treated as a free phase: the only cache-template equalities ever tested are the 6
  Z3-refuted miters above (all sat). No g*u construction was built because 4.1+4.3 close it.

## 4.3 Multi-condition branches (up to 8) with inclusion-exclusion: NEGATIVE by residual count

- `search256_gshared.py` (seed 8121, first 256 u, columns [1]+truth(62)+[u&t(62)]=125,
  8229-sample matrix with Q snapshot + per-candidate rank saved in `search256_gshared.json`;
  script+seed reproduce the matrix; Q snapshot is the saved matrix).
- Result: per-group distinct-nonzero-residual histogram is **{19: 256}** for G1, G2 and the
  joint proxy alike — every trial leaves all 19 targets with pairwise-distinct nonzero
  residuals (best trial 0 still n_res=19, rank 116/125). Observed-distinct on samples
  implies truly distinct (samples can only merge, never split, equal functions).
- A branch with k classical conditions can absorb at most k distinct residuals
  (error = R1·f1 + ... + Rk·fk vanishes iff all k parities are 0; stage-1 recipe is k=1).
  Minimum over 256 trials is 19 > any feasible budget (8 branches x <=3 conditions).
  Inclusion-exclusion coverage computation is moot: no branch with <=7 conditions exists
  in the searched set, so no tree was built, no KMB generated.
- The 256-expression budget for this round is consumed;扩搜停止.

## Cost accounting used (no ~4C)

Comparison window [26111,30599): 2 original ANDs + G1 + G2 + stage1-joint = 5-2^-18 both sides;
four selector groups proper = 3-2^-18 (G1+G2 = 2-2^-18, joint = 1.0). No positive candidate,
so no new cost to audit; diagnostic shortcache stays exactly 0C (proven).

## Status

Sections 2-3 delivered and proven. Section 4: bounded negative (4.1 screen + 6 exact
refutations; 4.2 domain facts, no template built; 4.3 0/256, min residual count 19).
No positive-gain KMB => no sample sim / official verification triggered (per plan, only
the final positive candidate would run them). No Kaggle submission, no push.
