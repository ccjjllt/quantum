# DQI multiply rank — is 42 slack? **CLOSED: no.** The 33 in WCC 2022 Table 2 is an **F₄** number, not F₂

Line: `dqi_multrank`. Question: can a 12×12 GF(2) bilinear multiplier (the tape's 42-CCX block)
be built with fewer than 42 ANDs, i.e. is there a real DQI lever?

**Verdict: `关闭` (closed). The best known bilinear complexity of multiplication in GF(2¹²)
over GF(2) remains 42. Nothing below 42 is published, and nothing below 42 is implementable.**

The candidate that motivated this round — WCC 2022 Table 2, row `U^{P_deg4}`, n = 12 → **33** —
is a **base-field-F₄** result (multiplication in GF(4¹²) = GF(2²⁴) over GF(4)), not an F₂ result.
Four independent checks below, three of them internal to the paper itself. The F₂ row of the same
table gives **51** at n = 12, i.e. *worse* than the 42 the tape already has.

**The three answers asked for:**

1. **Best known upper bound for `μ₂(12)` (base field F₂, all coefficients in F₂): 42.**
   Ballet–Pieltant–Rambaud–Randriambololona–Rolland–Chaumine, *Russian Math. Surveys* 76(1)
   (2021) 29–89, Table 2: `μ_sym_2(12) ≤ 42` (DOI 10.1070/RM9928). The same 42 is reached
   unconditionally and explicitly by Toom-4 over F₈ (7 evaluation points × `μ_2(3) = 6`), which
   is what the tape implements. Lower bound 23 (Winograd / de Groote); exact value open.
2. **Is there an explicit, implementable-in-hours F₂ algorithm with r ≤ 40? No.** The only
   published r < 42 at n = 12 (WCC 2022's 33) is an F₄ result; transplanted to F₂ it would cost
   33 × 3 = 99 ANDs. No F₂ decomposition below 42 appears in any table I could find.
3. **Therefore: `关闭` — no lever.** The +0.93 GM belonged to GF(4¹²)/GF(4).

---

## 1. What WCC 2022 Table 2 actually says

Source: S. Ballet, A. Bonnecaze, B. Pacifico, *Multiplication in finite fields with
Chudnovsky-type algorithms over the projective line*, WCC 2022 (Rostock), paper 65.
<https://www.wcc2022.uni-rostock.de/storages/uni-rostock/Tagungen/WCC2022/Papers/WCC_2022_paper_65.pdf>
(preprint: HAL hal-02911546). 11 pages; Table 2 is on p. 9.

Transcribed verbatim (layout-preserving text extraction, `ref/wcc2022_paper65.txt`):

```
  n            2    3    4    5   6    7    8   9   10   11   12  13   14   15    16   17    18
  µ(U^{P_deg2}_{2,n}) 3  6   11   15  18   26   29  37  40   48   51  60   65   70    78   81    90
  µ(U^{P_deg3}_{3,n}) 3  6    9   12  16   19   24  28  31   36   40  43   48   52    55   60    64
  µ(U^{P_deg4}_{4,n}) 3  5    8   11  14   17   20  23  27   30   33  37   40   43+   47   50+   53
  Table 2: Bilinear complexity of U^{P}_{q,n} in small extensions of F2, F3 and F4.
```

Caption + body text:

* caption: *"Bilinear complexity of U^{P}_{q,n} in small extensions of **F₂, F₃ and F₄**"*;
* body (§4, immediately above the table): *"Table 2 shows this bilinear complexity for the
  extensions of degree lower than 18 of F_q, **with q = 2, 3, 4**. We underline the bilinear
  complexity when it equals the one given by Table 2 of [2] (= the Ballet–Pieltant survey,
  `μ_sym_q` for q = 2,3,4), and we denote by **+** when we beat this complexity."*

So the three rows are the three **base fields**, and each row's superscript names the maximum
place degree used for that base field (`deg d` with q = d ∈ {2,3,4}). Row 1 = F₂, row 2 = F₃,
row 3 = F₄.

*Caveat on the row labels, stated for the record:* the PDF's small type extracts as
`µ(U P deg 2,n )`, i.e. superscript and subscript run together, so the label alone does not
distinguish "q = 2, maxdeg 2" from "q = 2 with degree bound 2". The caption and the sentence
above (`q = 2, 3, 4`) plus the underline/`+` comparison against the three-row Table 2 of [2]
fix the reading: one row per base field. Checks (a) and (d) below are independent of that
reading — they exclude **any** F₂ interpretation of the 33.

### 1.1 Four checks that row 3 (`33`) is not F₂

**(a) de Groote's equality condition, applied to the paper's own n = 3 entry.**
The paper's introduction states Winograd–de Groote: `μ_q(n) ≥ 2n−1`, with equality **iff**
`n ≤ q/2 + 1`. Row 3 at n = 3 gives **5 = 2·3−1**, i.e. equality. That needs
`3 ≤ q/2 + 1 ⟺ q ≥ 4`. For q = 2 it is impossible: `μ_2(3) = 6` exactly (§2 below).
Rows 1 and 2 give 6 at n = 3, consistent with q ∈ {2,3}; only row 3 gives 5. Therefore
**row 3 cannot be F₂** — by the theorem the authors themselves cite.

**(b) The `+` marks are silent at n = 12.** The paper marks a value `+` when it beats the
survey's Table 2. The survey gives `μ_sym_2(12) ≤ 42` and `μ_sym_4(12) ≤ 33`
(see §3). Row 3's n = 12 entry is `33` **with no `+`**: 33 = 33 (equal → underlined), not
33 < 42 (which would be a headline improvement and would have to be marked `+`). The only
`+` marks in the whole table sit at row 3, n = 15 (43 < 45) and n = 17 (50 < 53), exactly the
two places where row 3 beats the survey's **μ_sym_4** row — and row 3's n = 14, 16, 18 values
(40, 47, 53) are *worse* than μ_sym_4's (39, 45, 51), which is why they carry no mark.
That irregular pattern is inexplicable unless row 3 is compared against the F₄ row.

**(c) Row 3 reproduces the published F₄ row exactly.** Row 3 for n = 2..13 is
`3 5 8 11 14 17 20 23 27 30 33 37`; the survey's `μ_sym_4(n)` for n = 2..13 is
`3 6 8 11 14 17 20 23 27 30 33 37`. Identical at n = 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
(11 of 12 consecutive entries), differing only at n = 3 where WCC gives 5 and the survey 6.
Reproducing an F₄ table for 11 consecutive n is not something an F₂ construction does.

**(d) The construction is infeasible over F₂ at n = 12.** The paper's RPGC setup (§4) requires
a set of *distinct* places with `Σ deg P_i = 2n − 1` and `dim L(2D − G) = 0` (Theorem 2c).
For n = 12 that is `Σ deg P_i = 23`. Over F₂(x) the places of degree ≤ 4 are
2 monic irreducibles of degree 1 (`x`, `x+1`), 1 of degree 2 (`x²+x+1`), 2 of degree 3
(`x³+x+1`, `x³+x²+1`), 3 of degree 4 → total degree available
`2·1 + 1·2 + 2·3 + 3·4 = 22 < 23`. A `q = 2, maxdeg = 4` instantiation at n = 12 **does not
exist**; over F₄ there are 5 + 10 + 40 + 85 places, so there is no shortage. (Note also that
the same count with `P_∞` added as an extra evaluation place yields 22 evaluation degrees and
a cost of 3·1 + 1·3 + 2·6 + 3·9 = 45 using the best F₂ leaf values, never 33.)

**Either way the 33 is not an F₂ number**: if the rows are base fields (checks a, b, c) it is the
F₄ value; if the rows were degree bounds at fixed q = 2, then (a) rules out its n = 3 entry and
(d) rules out its n = 12 entry.

### 1.2 What the F₂ row does say
`μ_2(12) ≤ 51` from the `deg2` row — *worse* than the tape's 42, because that row uses only
places of degree ≤ 2 over F₂ and cannot use the F₈ subfield trick. The `deg3` row (`40` at
n = 12) is likewise the F₃ row: 40 > μ_sym_3(12) = 36, and it carries no `+`.

**Nothing in this paper improves on 42 for F₂ at n = 12.**

---

## 2. `μ₂(3)`: exactly 6, not 5 — and what that implies for 42

* Upper: 6, explicit (3-term Karatsuba / Montgomery's 3-term formula; also Toom over F₂ with
  the `n = q/2 + 1` variant of the WCC paper's Proposition 2, and the tape's own leaf).
* Lower: `≥ 2n − 1 = 5`, and 5 is excluded because equality needs `n ≤ q/2 + 1`, i.e.
  `3 ≤ 2`, false. Hence `μ_2(3) ≥ 6`.

So **`μ_2(3) = 6`** — this is the F₂ value; the `5` that appears in WCC Table 2 (row 3, n = 3)
and in the F₄ column is `μ_4(3) = 5`, a different base field.

Consequence for the tape: 42 = 7 × 6 = (2·4−1 evaluation points for a degree-3×3 Toom split)
× (`μ_2(3) = 6`) is the **optimum of the whole Toom-over-subfield family over F₂**, and the
leaf cannot be improved. This confirms, and is confirmed by, `μ_sym_2(12) ≤ 42` in the survey
(the two constructions coincide numerically at 42). It does *not* prove `μ_2(12) = 42` — the
true value is open in [23, 42] — but it removes the "42 is a slack heuristic" hypothesis.

---

## 3. Best known upper bound for `μ₂(12)` (F₂ base field only)

| bound | value at n = 12 | source |
|---|---:|---|
| **best known upper bound** | **42** | Ballet–Pieltant–Rambaud–Randriambololona–Rolland–Chaumine, *Russian Math. Surveys* 76(1) (2021) 29–89, **Table 2**, `μ_sym_2(12) ≤ 42`; DOI 10.1070/RM9928, arXiv:1906.07456. Also quoted as `μ_sym_2(12) ≤ 42` in arXiv:1601.00126 |
| explicit unconditional construction at 42 | 42 | Toom-4 over F₈: 12 = 4×3 bits, 7 evaluation points in F₈, leaf `μ_2(3) = 6` → 7·6. All linear maps over F₂. (The survey's 42 relies on a Chudnovsky bound that arXiv:1601.00126 flags as resting on an unproven moduli-field assumption; **the Toom-4 42 does not** — it is elementary and is what the tape implements.) |
| uniform asymmetric bound (non-symmetric algorithms) | 121 = (189/22)·12 + 18 | Pieltant–Randriambololona, *Math. Comp.* 84 (2015) 2023–2045, Thm 4.1; DOI 10.1090/S0025-5718-2015-02921-4, arXiv:1305.5166 |
| Chudnovsky-type over P¹, q = 2, deg ≤ 2 places | 51 | WCC 2022 Table 2, row `deg2` |
| lower bound | 23 | Winograd 1979; de Groote, *SIAM J. Computing* 12(1) (1983) 101–117: `μ_q(n) ≥ 2n−1`, equality iff `n ≤ q/2+1` |
| exact values known | n = 2: 3, n = 3: 6, n = 4: 9, n = 6: 15 | survey Table 1 + §2 above |

No table anywhere lists an F₂ value below 42 at n = 12. The 2026 automated-lower-bound framework
of Wang (arXiv:2603.07280, §8) lists *extension-field* multiplication as an explicitly open
problem for that method, i.e. even the lower-bound technology has nothing at n = 12.

**Answer to "is there an explicit, implementable-in-hours F₂ algorithm with r ≤ 40?" — No.**
The only published r < 42 at n = 12 is the F₄ number 33, which is (i) a different base field and
(ii) even if transplanted would cost 33 F₄-multiplications × 3 ANDs = 99 ANDs over F₂, i.e.
2.4× worse than the tape.

---

## 4. Cost arithmetic (for the record, `scripts/gm.py`)

Baseline = the shipped triple (invsqrt 74,560.90687, dqi 346,409,762,292.72, chem 294,643,137.73),
GM 28.180659. DQI cost `= 1.1912605·890²·T`, T = 367,116.0572. Savings counted only on the
3,068 rank-42 blocks (`dqi_algo` census), which is the honest model; the brief's "3,793 blocks"
model is shown for comparison because it is what the +0.93 figure used.

| r_best | T saved (3,068 blocks) | GM | Δ | T saved (3,793-block model) | Δ |
|---:|---:|---:|---:|---:|---:|
| 42 (actual) | 0 | 28.1807 | — | 0 | — |
| 41 (hypothetical) | 3,068 | 28.2596 | +0.079 | 3,793 | +0.098 |
| 40 (hypothetical) | 6,136 | 28.3394 | +0.159 | 7,586 | +0.197 |
| 33 (the F₄ number, *not* F₂) | 27,612 | 28.9248 | +0.744 | 34,137 | **+0.932** |
| 23 (bilinear floor) | 58,292 | 29.8526 | +1.672 | 72,067 | +1.987 |

The +0.93 GM that motivated this round is exactly the r = 33 row of this table — and it does not
exist for F₂. The realistic hypothetical (r = 40) would have been +0.16 GM; the r = 41 case,
+0.08 GM. Neither is available.

---

## 5. Side measurement (already paid for): the tape block *is* the GF(2¹²) field tensor

Kernel `zhuating/qcc-dqi-mult-tensor` v1 (CPU, `enable_gpu=false`, COMPLETE, 8.1 s of compute)
ran while this literature check was happening. It is not needed for the verdict — another line owns block
structure — but it closes the only remaining loophole, namely "maybe the block computes a
cheaper tensor than a full field product".

Method: exact GF(2) ANF to degree 2 over the block window (every op is X/CX/CCX/SWAP, each CCX
creates one product variable), so the recovered `T` is exact, not sampled. Result for the first
forward block `[17576206, 17577498]`, window pad 12, words (A, B, C) = (0, 1, 70):

* 42 ANDs, all `u` forms supported on word 0, all `v` forms on word 1, 12 product-carrying
  qubits, all in word 70; the 42 terms reproduce `T` exactly (`terms_reproduce_T: true`);
* `T` is 12×12→12, 363 non-zero entries, **commutative, associative, identity = basis bit 0,
  every non-zero element invertible** → it is a **field** multiplication, i.e. GF(2¹²);
* minimal polynomial of the basis element `e₁` (and of its Frobenius conjugates `e₂, e₄, e₈`):
  **`x¹² + x⁶ + x⁴ + x + 1`** (0x1053) → the block computes multiplication in
  `GF(2)[x]/(x¹²+x⁶+x⁴+x+1)`;
* flattening ranks of `T`: (12, 12, 12) — the generic bound, useless as a lower bound here;
  the applicable lower bound is de Groote's 2n−1 = 23.

Window identification, stated exactly (this is where the earlier line gave up). A pad sweep over
`[first−pad, last+1+pad)` shows: pad ≤ 10 cuts the carrier preparation and the recovered `T` is
**not associative**; pad = 12 is the unique window in which every `u` form is inside word 0,
every `v` form inside word 1 and `T` is a field; pad ≥ 14 pulls in the next gadget on the same
accumulator (`bad_u` = 21 at pad 14, rising to 36 at pad 28) and the tensor stops being a field.
The pad-12 window still leaves **2 qubits** not restored (`n_bad_qubits: 2`), i.e. the block's
true closure boundary is one or two instructions wider than the tensor needs — irrelevant here,
because the tensor depends only on the 42 AND controls and the accumulator set, both of which are
fully inside the window.

So "the rank of the block" **is** `μ_2(12)`, with no cheaper-tensor escape. Engine validated
locally against a synthetic truncated product and a synthetic `GF(2¹²)` product before the run
(`work/test_engine.py`, both recovered exactly, modulus recovered as 0x100021).

---

## 6. Deployment feasibility (moot, but recorded)

Since no r < 42 bilinear algorithm exists for this tensor, there is nothing to deploy, and the
null-splice toolchain (`zhuating/qcc-dqi-null-splice`, byte-exact round trip, depth-0 cuts) is not
exercised. Had a 40-AND F₂ decomposition existed, deployment would have been *feasible*: the
operand map is now known exactly (words 0/1 → word 70, identity = bit 0, modulus
`x¹²+x⁶+x⁴+x+1`) and a replacement is only CX (free) + r CCX.

---

## 7. Exact commands and files

```
curl -sL -o ref/wcc2022_paper65.pdf <WCC 2022 paper 65 URL>          # then pypdf text extraction
.venv/bin/python experiments/.../dqi_multrank/work/test_engine.py     # engine validation, local
python scripts/kgpu.py push  --dir .../dqi_multrank/k_tensor --account zhuating
python scripts/kgpu.py fetch --kernel zhuating/qcc-dqi-mult-tensor --account zhuating \
       --out artifacts/20261118_push_dqi_multrank
```

| path | note |
|---|---|
| `ref/wcc2022_paper65.pdf`, `ref/wcc2022_paper65.txt` | WCC 2022 source of the 33 (p. 9, Table 2) |
| `k_tensor/main.py`, `k_tensor/kernel-metadata.json` | tensor kernel (`zhuating/qcc-dqi-mult-tensor` v1, COMPLETE) |
| `work/test_engine.py` | local validation of the ANF/tensor engine (`ENGINE OK`) |
| `artifacts/20261118_push_dqi_multrank/tensor.json` | measured T, 42 terms, minpolys, sweep |
| `artifacts/20261118_push_dqi_multrank/qcc-dqi-mult-tensor.log` | kernel log |

No verifier was run, nothing was submitted, no package was modified.

## 8. Bottom line

* `r_best_known` (F₂, published) = **42**; lower bound 23; exact value open.
* `r_best_deployable` (tonight) = **42** — i.e. nothing.
* **DQI multiply-rank lever: closed.** The +0.93 GM belonged to GF(4¹²)/GF(4), not GF(2¹²)/GF(2).
* `μ_2(3) = 6` means the tape's 7 × 6 = 42 is already the optimum of its own family, so 42 is
  not a slack heuristic; it is the best known construction, and the F₂ row of the very table that
  suggested otherwise gives 51.
