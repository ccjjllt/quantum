# RESULT2 — the group-merge experiment: can R be reduced at fixed B?

Date: 2026-11-17/18 (this session). Chemistry. Follows `LAMBDA_MEASURE/RESULT.md`.
Local, exact full-space `||YY^T - H||_F` (2926-dim, no eigenspace truncation), the
verifier's own metric code and FCIDUMP, `SpinFreeData_V1` for T_h/Q. No kickmix, no
circuit, no verifier run, no submission.

Question: my earlier finding "`B` governs accuracy, not `B/C`" was measured only at
`R=8` (where `B` and `R*B` are the same dial). This session separates them by
reducing the group axis, exactly as scoped: `(8,136,96) -> (7,136,96) -> ...` and
`(8,143,88) -> ...`, plus a proper Gauss-Newton w-step and an optimised
projector-span (dictionary) subproblem.

## 0. Verdict

**NO-GO on `error_2 <= 20 mHa` for both 5-group shapes.** And this time it is not an
optimizer artifact — the merge is *irreducibly* lossy, and the loss is measured with
an **optimised** span:

| test (one merge, best possible 136/143-projector span) | capture | column residual |
|---|---:|---:|
| a shipped group, its own 143 projectors (control) | **100.0000 %** | 0.02 mHa |
| `(8,136,96)` pair (4,7): 192 cols -> 136 projectors | 99.568 % | **239 mHa** |
| `(8,136,96)` pair (0,1): 192 cols -> 136 projectors | 98.800 % | **392 mHa** |
| `(8,143,88)` pair: 176 cols -> 143 projectors | 99.582 % | **231 mHa** |
| `(8,143,44)` pair: 88 cols -> 143 projectors | 99.663 % | **207 mHa** |

Merging **one pair of groups** costs 0.21–0.39 Ha of representational capacity — 10–20×
the 20 mHa gate — and three merges are needed. Note the last row: even 88 columns in
143 projectors loses 207 mHa, because two groups' 143-dim spans are different
subspaces and one span cannot be close to both. **The resource is the total projector
count `R*B = rows - 76`, i.e. rows itself; `B` alone is not the dial.**

## 1. The merge chain, per stage (what was asked)

| shape | rows | K | floor | continuous `error_2` |
|---|---:|---:|---:|---:|
| (8,136,96) source | 1164 | 768 | 0.310 | **17.46** |
| (7,136,96) after merge | 1028 | 672 | 0.371 | pair (4,7) truncation loss **184.5 mHa**; merged init 1519; GN x3 on the merged group **378.0** |
| (8,143,88) source | 1220 | 704 | 0.338 | **13.77** |
| (7,143,88) after merge | 1077 | 616 | 0.488 | pair (5,7) truncation loss **156.3 mHa**; init 1712; GN x3 **491.1** |

Stages R=6 and R=5 were not run: the first merge already lands 20-25× above the gate
and the GN improvement is ~1.3×/sweep, so the chain cannot cross 20 mHa. The
truncation loss is structural (`B*C` columns must be represented by `B` projectors),
not a starting-point accident.

**Why the pairwise truncation is the wrong operation, and what it would take:** a
*global* rank-480 truncation of the same 768-column solution costs only 0.03 mHa
(17.46 -> 17.49), because it drops the smallest singular directions of the whole
factor. The loss appears only when 96 columns are squeezed into the span of one
group. Making that work would need the 480 columns re-partitioned *and* each group's
span re-optimised jointly (a 480x480 orthogonal gauge plus 5 span problems), and the
span optimiser above says the target spans capture only 88-96 % of the *ideal*
eigenbasis columns — so there is no evidence such a partition exists.

## 2. Measured accuracy frontier (rows = 76 + R*B), exact objective

| shape | rows | R*B | B | K | `error_2` |
|---|---:|---:|---:|---:|---:|
| (8,143,44) shipped shape | 1220 | 1144 | 143 | 352 | 16.55 |
| (8,143,88) | 1220 | 1144 | 143 | 704 | **13.77** |
| (8,143,128) | 1220 | 1144 | 143 | 1024 | 15.43 |
| (8,136,96) | 1164 | 1088 | 136 | 768 | **17.46** |
| (8,136,44) | 1164 | 1088 | 136 | 352 | **21.61** (8 rounds) |
| (8,129,44) | 1108 | 1032 | 129 | 352 | 27.2 |
| (8,96,44) | 844 | 768 | 96 | 352 | 89.2 |
| **(5,136,96)** | 756 | 680 | 136 | 480 | **168** (direct fit) |
| (8,62,44) | 572 | 496 | 62 | 352 | 280 |
| official baseline | 3976 | 3900 | 60 | 3900 | 16.13 |

Two things are now clear: (i) at fixed rows, K is nearly free (13.8-17.5); (ii) the
error explodes as rows fall (1220 -> 16.5, 1164 -> 17.5-21.6, 1108 -> 27, 756 -> 168,
572 -> 280). The gate needs **rows >= ~1160**, i.e. the shipped 1220 is ~5 % from the
frontier, not 38 % as the `B/C` law suggested.

## 3. Cost for the record (exact `SpinFreeData_V1`, shipped loader density)

| shape | rows | Q | T_h | T | cost | GM | `error_2` |
|---|---:|---:|---:|---:|---:|---:|---:|
| (5,143,88) | 791 | 429 | 7539 | 12754 | **256.74 M** | 29.473 | not legal |
| (5,136,96) | 756 | 430 | 7916 | 12901 | **260.29 M** | 29.339 | not legal |
| (6,143,88) | 934 | 430 | 8399 | 14557 | 293.71 M | 28.181 | — |
| (6,136,96) | 892 | 430 | 8854 | 14735 | 297.31 M | 28.067 | — |
| (8,136,44) | 1164 | 427 | 6648 | 14323 | 286.96 M | 28.400 | 21.61 (borderline) |
| (8,140,44) | 1196 | 427 | 6656 | 14584 | 291.35 M | 28.256 | not measured (~19-20 expected) |
| (8,143,44) shipped | 1220 | 427 | 6662 | 14706 | 294.64 M | 28.151 | 20.00 as submitted |

Also note the cost model is *fragile in the loader*: the Q_AXIS "lin" density
(`4022*rows/1220`) gives 260.29 M for (5,136,96), but the model that reproduces the
shipped 269-Toffoli loader exactly (`15*(6 + high + 193)`, `high = nh-1 - #powers of
2`) gives `L = 15*(6+41+193) = 3600` at rows 756, i.e. `T = 15116`, cost **305.0 M,
GM 28.06 — a loss**. With no loader built at 756 rows, the sign of the cost win is
itself unproven.

So the best *measured* row-reduction option is **(8,136,44)** at 286.96 M
(+0.24 GM) — and it is 21.6 mHa, just outside the gate.

## 4. Emitter: can it be pointed at 791/756 rows?

Partly — the address layer yes, the plan no.

* `work/ds/code2/planner.py::_addr_shape(rows)` is already generalised:
  `nh = ceil(rows/16)`, `rem = rows - 16*(nh-1)`, `hbits = (nh-1).bit_length()`, and its
  docstring names the exact targets: **791 -> nh 50, rem 7; 756 -> nh 48, rem 4**
  (1220 -> nh 77, rem 4, hbits 7). `complete_words(words, rows)` handles the padding
  slice for any row count, and the code asserts byte-identity at 1220.
* What changes: selection width 11 -> **10** bits (`ceil(log2 791) = ceil(log2 756) = 10`),
  high-value count 77 -> 50/48, `hbits` 7 -> 6, and the whole word table is
  791x75 / 756x75 instead of 1220x75.
* What is missing: the **loader plan** (which cuts/pairings produce the ~269-Toffolis-
  per-loader structure) is table-specific and must be re-found with
  `compile_basis.plan_one`; RESULT6 showed that planner could not find a plan even on
  the 1220-row table in a 900 s budget. And `emit_from_basis`/`emit_DC_from_basis`
  carry the `first_unused_address: 1220` padding convention.
* Verdict on the emitter: no hard architectural blocker (the author left the
  `_addr_shape` hook and even named 791/756), but it is **not a drop-in**: new plan,
  new loader Toffoli counts (so the cost model must be re-measured, not extrapolated),
  new padding address, 10-bit selection. That work is only worth doing after a shape
  clears 20 mHa, which none of the 5-group shapes does.

## 5. What this closes and what is left

* Closes: the group-axis reduction as a route to the ~236-260 M chemistry leg. The
  merge is irreducibly 10-20x the gate per step at both `B=136` and `B=143`.
* Corrects: "`B` governs, `R` doesn't". At `R=8` the two are confounded; the merge
  test is the separation, and it says the *total* projector count (= rows) governs.
* Left: (a) `(8,136,44)` at 21.6 mHa / 286.96 M (+0.24 GM) and `(8,140,44)` at
  ~19-20 mHa / 291.35 M (+0.11 GM) are the only shapes near the gate — both are
  ~1-2 Toffolis-of-chemistry-scale gains, not gold; (b) the loader plan at reduced
  rows, which is only meaningful after (a) clears.
