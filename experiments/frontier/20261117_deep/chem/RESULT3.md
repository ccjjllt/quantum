# RESULT3 — Λ(W) lever at (8,143,44,brot=8): what is real, what is deliverable

Date: 2026-11-17. Chemistry only. Local work = closed-form arithmetic on the
shipped npz + official formulas. All eigen / e1 numbers come from the Kaggle CPU
kernel in §5. No simulation locally, no verifier locally, nothing submitted.

Baseline `a73b25d2` (T 14,706, Q 427, λ_eff 46.921716818, cost 294,643,137.73,
GM 28.15083, `error_1 = 0.0199999985`, `error_2 = 0.0199999997`, `E_gap` at floor).
Gold = 28.71339. Target here: **Λ ≤ 250 ⇒ λ_eff 44.0695 (−6.08 %) ⇒ chem 276.7 M
⇒ GM 28.745**; Λ ≤ 194 ⇒ GM ≈ 29.9.

## 0. The three separate questions (do not mix them)

| # | question | status |
|---|---|---|
| **B** | keep the shipped 76 one-body rows, move only `W` → Λ down, `error_1 ≤ 20 mHa` | **analytically dead** (§1) |
| **A** | Λ_min(W) with `error_1` free (i.e. allow re-encoding the 76 rows) | measured in the kernel (§5) — value unknown yet |
| **C** | if A is good: is it *deliverable*? (a) 8-bit re-encode of 76 rows reaches `error_1 ≤ 20 mHa`; (b) the 15 loaders can be rebuilt | (a) measured in the kernel; (b) **blocked**: the shipped emitter covers batches 0–8 only, k9–k14 have no equivalent implementation in the tree (`pipeline/CODE2_STATUS.md`, quoted in §3) |

**`Λ_min` and "deliverable" are reported separately everywhere below.** A low
`Λ_min` alone is not a candidate.

## 1. Why case B is dead (kept for the record)

`error_1` is built as: shipped rows `v_j` (fixed) + the eigenvalues of the *new*
`H1p` matched by `|overlap|`, then
`error_1 = ‖Σ_j λ_j v_j v_jᵀ − H1p(new)‖_F`. The diagonal is absorbed into the
matched `λ_j`; what is left is the **off-diagonal residual of `H1p(new)` in the
fixed `v` basis** — 76·75/2 = 2,850 constraints against 352 free `W` entries. It is
overdetermined, and the current point sits at 19.9999985 of a 20.000000 gate
(1.5e-6 slack). So any `ΔW ≠ 0` fails. Case B requires `ΔW ≈ 0`, i.e. it is not a
lever. (This also explains `LAMBDA.md`'s "no admissible projected step": it is the
same statement seen locally.)

## 2. Where the Λ mass is (exact, from the shipped npz)

```
a_rc = sum_b |w_rcb| :  min 0.717  mean 1.180  max 3.074   sum a^2 = 522.380
                        (sum a)^2/352 = 522.2  ->  a is uniform: no L1 slack in w
W_rc (= H2_I)        :  sum |W| = 179.503   sum W^2 = 105.441   mean |W| = 0.510
lam_h2 = 0.25[sum a^2 + 2 sum a|W| + sum W^2] = 270.115   (sum a|W| = 226.320)
lam_h2(W=0) = 130.595     -> the |W| cross term is 52 % of lam_h2
```

Two structural facts used below:

1. `lam_h2` and the `E_SOS` term `−0.5ΣW²` see **`|W|` only**; the 352 **signs**
   are free for both, and only move `H1p` (hence `lam_h1`, `tr h1`).
2. `E_gap = Cg + 2·Nneg + 0.5ΣW²` with `Nneg = Σ_{eig<0}|eig|` and
   `Λ = lam_h2 + tr h1 + 2·Nneg`. So per unit of `E_gap`, `ΣW²` costs 0.25 Λ and
   `Nneg` costs 1.0 Λ — `ΣW²` is the cheaper knob, the signs are the second knob.

The closed-form "`|W|` on the k smallest-`a` cells at fixed `ΣW²`" table (Λ =
lam_h2 + 13.03, `lam_h1` assumed constant) is an **approximation only** — it ignores
that moving `|W|` changes `Nneg`/`lam_h1`. It is kept as the *shape* prior, not as
a result:

| k | cross | lam_h2 | Λ (approx) | λ_eff | GM |
|---:|---:|---:|---:|---:|---:|
| 1 | 7.37 | 160.64 | 173.67 | 36.667 | 30.56 |
| 4 | 14.73 | 164.52 | 177.55 | 37.02 | 30.45 |
| 16 | 29.46 | 171.68 | 184.71 | 37.83 | 30.15 |
| 44 | 48.82 | 181.72 | 194.75 | 38.84 | 29.87 |
| 352 (actual) | 226.32 | 270.12 | 283.14 | 46.92 | 28.15 |

**Decision rule: only the kernel's numerically solved `Λ` (explicit `E_gap = floor`,
real `eigvalsh`) counts.** If it disagrees with this table, the kernel wins; the
disagreement is `lam_h1(W)` moving.

## 3. Deliverability gates  (independent of Λ)

| gate | state |
|---|---|
| `error_2` | **free**: `W` does not enter `e2`; `w`/`U` untouched → `e2` bit-identical (19.9999997 mHa) |
| `E_gap` | must be solved back to the floor (kernel does it explicitly) |
| `error_1` after 8-bit re-encode of the 76 one-body rows | **the real gate**; measured in the kernel (step 4). ~0 slack (gate 20.000000, now 19.999999) |
| rows 76..1219 (two-body words) | unchanged → 1,144 of the 1,220 rows of every loader table are unchanged |
| 15 loader rebuild | **blocked**: "the k14 1-gate win is not emittable with the shipped emitter: batches 9, 10 and 14 have a different bit7 XOR bit6 helper convention, and batches 11-13 fail the six-AND low-cache independence assertion. The last six loaders need a different emitter that is not in the tree" (`pipeline/CODE2_STATUS.md`). So batches 9–14 (6 of 15 loaders) cannot be regenerated at all, even at the unchanged geometry. scout is checking maoxin's loader-generation kernel for a full emitter. |

Consequence: even a perfect (A) result needs **both** (i) `error_1 ≤ 20 mHa` after
re-encoding and (ii) a working emitter for the last six loaders. Neither is
assumed anywhere in this note.

## 4. What the kernel measures (exact scope)

```
step 0  reproduce: lam_h2, lam_h1, tr h1, Nneg, E_gap, error_1(shipped rows), g_now
step 1  k in {1,2,4,8,16,32,44,88,176} smallest-a cells; |W| = sqrt(S/k)
step 2  S in {1.00,1.05,1.15,1.30,1.60} * S0; for each (k,S) a greedy sign search
        over the k signs, objective lam_eff(W) with a hard penalty on E_gap < floor
step 3  Powell polish over all 352 entries of W from the best feasible profile
step 4  error_1 (a) with the shipped rows ("case B"), (b) after re-fitting every
        one of the 76 rows' 75 tree angles to eig(H1p(W)) and rounding to 8 bits
```
Reported per candidate: `Λ`, `lam_h1`, `lam_h2`, `tr h1`, `Nneg`, `ΣW²`, `Σ|W|`,
cross, `E_gap`, `λ_eff`, `error_1` (both variants).

## 5. Kernel and status

`qingyu1232/qcc-chem-lambda-offset-min`, CPU only (`enable_gpu=false`,
`enable_tpu=false`), pushed 2026-11-17 v3, RUNNING at the time of writing.

Measured output goes in §6. Nothing in §6 is assumed.

## 6. Measured output

_(pending — kernel v3)_
