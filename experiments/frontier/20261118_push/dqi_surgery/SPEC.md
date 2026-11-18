# SPEC — surgical replacement of both EEA passes of tape `575b043f`

Status: **specification only.** Nothing here is implemented, no verifier has been run, no file in
`submissions/` is touched. Every measured input comes from `INTERFACE.md`.

Scope: replace the Toffoli-bearing arithmetic of the two EEA passes
(`[17,576,206, 30,151,421)` and its reverse counterpart) with a **normalized divstep EEA** that
does one scalar multiplication row per degree, and leave the Chien/Forney stage
(4,025 positions, 44,275 static T) exactly as the tape has it.

---

## 1. Target and the arithmetic that fixes the budget

```
score      = 1.1912605 · Q² · meanT            (Q = 890 fixed: wires are already compact)
GM         = (REF_inv·REF_dqi·REF_chem / (C_inv·C_dqi·C_chem))^(1/3)
GM(T)      = 28.180659 · (367,116.06 / T)^(1/3)
```

| item | T |
|---|---:|
| tape today (mean) | 367,116.06 |
| Chien: 4,025 positions × 11 (10 CCX + 1 CCZ) | 44,275 |
| remaining `CCZ` outside the 4,025 positions | 1,952 |
| **Chien/Forney total (kept verbatim)** | **46,227** |
| EEA both passes today (CCX only) | **321,762 = 7,661 × 42 exactly** |

Exact closure: `321,762 + 44,275 + 1,952 = 367,989`, the tape's static Toffoli.
The brief's `321,772 / 46,217` is the same sum with the 10 `CCX` of the straddling Chien position
(30,335,009…30,335,027) counted on the EEA side; both splits close exactly. This spec uses the
`321,762` split because it makes the multiplication count integral: **7,661 blocks = 42 T each.**

### 1.1 Why 69 steps is the right step count (derived, not assumed)

The tape's EEA does 35 outer iterations. Per iteration it applies `δ+1` quotient rows, and
Σ(δ+1) = 104 over 35 iterations (measured: 3,783 multiplications per pass ≈ 104 × 36.4 effective
words). Therefore Σδ = 104 − 35 = **69**, i.e. the total degree removed per pass is exactly 69 —
which is also `deg` of a left-aligned 70-word polynomial. A normalized schedule removes exactly one
degree per step, so **exactly 69 steps per pass**, data-independently.

### 1.2 Cost of one step under the normalized schedule

One step = one scalar row `b ← b + c·a` (or `a`), `c ∈ GF(2¹²)` a single field element, applied over
the *live window* of the other polynomial. If the window shrinks by one word per step
(69 → 1 words), the average window is 35 words:

```
row cost        = 35 words × 42 CCX = 1,470 T
per pass        = 69 × 1,470          = 101,430 T
both passes     =                     = 202,860 T
```

### 1.3 T budget table

| line | T/pass | T both | share |
|---|---:|---:|---:|
| scalar multiply rows (`69 × 35 × 42`) | 101,430 | 202,860 | 100 % |
| word-level `SWAP` of `a ↔ b` per step (70 words × 12 bits) | 0 | 0 | `SWAP` = 3 `CX` |
| conditional / fixed window shift (lane rotate, `CX`/`SWAP`) | 0 | 0 | 0 Toffoli |
| `δ` register (2–3 bits, `iadd` + `flip_if_less`) | 0 | 0 | classical/`CX` |
| the conditional selection of *which* row (if any) | 0 | 0 | `CX_IF` / `PUSH` |
| **normalization of the leading coefficient (open, §3)** | `n·69` | `n·138` | must be ≤ 113 T/step |
| **EEA total** | | **202,860 + 138·n** | |
| Chien/Forney (kept) | | 46,217 | |
| **mean T** | | **249,087 + 138·n** | |

| normalization cost `n` (T/step) | mean T | GM | verdict |
|---:|---:|---:|---|
| 0 (projective, §3 case A) | 249,087 | **32.07** | target |
| 113 (the gap) | 264,681 | 31.43 | the gate |
| 315 (one 12-bit quantum inverse, measured idiom) | 292,557 | 30.40 | **fails the gate** |
| 1,470 (a second full row, fraction-free) | 451,947 | 26.29 | abort |

**Decision rule for step 2: the normalization mechanism must cost ≤ 113 T per step, i.e. ≤ 15,613 T
over both passes. Anything that inverts a 12-bit field element once per step (315 T, measured on
the `dqi_algo` line) does not fit; it must be amortised or avoided.**

Savings, for the record: `321,762 − 202,860 = 118,902 T` (brief's split: 118,912 T).
New mean `T = 202,860 + 46,227 = 249,087` ⇒ GM **32.07**; at `n = 113` per step the gate closes at
`264,700` ⇒ GM **31.43**.

## 2. State and representation

The replacement must reproduce the tape's representation, because the Chien stage is kept:

```
two interleaved 35-word polynomials over the same physical 70-word array   (INTERFACE.md §5, §7)
  a_k = word 2k,  b_k = word 2k+1        (stride-2 ladder, measured)
pool words 70..73 (Q840..Q887) + Q888/Q889: multiply scratch, δ, flags
```

Divstep state:

| object | width | lives in | note |
|---|---|---|---|
| `a`, `b` | 70 words | `S0..S69` (interleaved) | the tape's own array, in place |
| `δ` | 2–3 bits | pool | `δ ← 1 − δ`, `δ ← −δ`; integers in `[−68, 68]` ⇒ 8 bits if stored unarily, 3 if biased |
| `u`, `v` (Bezout) | 70 words | **the second half of the pair** — see §2.1 | the tape's `b` half *is* the Bezout accumulator |
| predicate bits | 1 qubit each | pool | zero-test of a 12-bit word, sign of δ |

### 2.1 Where the Bezout coefficients come from — the one design decision

The tape carries **only 70 words**, and the first multiplication is `S0 × S1` — i.e. the tape's EEA
is *in place*: the second polynomial of the classic 3-array EEA (a, b, and the Bezout array) is
folded into the interleaved layout, and the Bezout update is carried by the same rows. Concretely
the divstep form must be applied to **both pairs at once**:

```
per step:   (a, b) ← (b, b + c·a)          with c = lead(b)/lead(a)     [degree step]
            (u, v) ← (v, v + c·u)          same c, same row width       [Bezout step]
```

The second row is *not* extra Toffoli: it is the same 42-CCX multiply block applied to the other
half of the array, which is exactly the 2-array structure the measured stride-2 ladder implies
(`0,2,4,…,44` = one polynomial's ladder, `46,50,54,58,62` = the other's, `48,52,56,60,64` = the
product accumulators). **The T budget in §1.3 already counts this**, because the 3,783
multiplications/pass measured on the tape is the same row count for both halves.

**TODO-2:** confirm with one dump that each 42-CCX block multiplies *two* words of one half against
each other (as `dqi_block` showed for `(66,1,67)`) rather than one word of each half. If the ladder
pairs are cross-half, then the Bezout row is a *separate* row and the budget doubles (§5 risk R2).

## 3. Normalization: the three cases, priced

`c = lead(a)/lead(b)` must be a single field element so that one row suffices. `lead(·)` is a
12-qubit word at a compile-time-fixed position (the window head) — reading it is free. The division
is the problem. Three constructions, in order of preference:

**Case A — projective normalization (0 T/step).** Never divide. Keep the recursion
`a ← lead(b)·a + lead(a)·b`, which is *degree-correct* but scales the pair by `lead(b)`; or keep
`a ← a + c·b` with `c` left as the *pair* `(lead a, lead b)` and defer the division to the consumer.
This is legal **iff every consumer of `(σ, ω)` is homogeneous of degree 0**, which is true here:

* Chien root test: `σ(α^{-j}) == 0` — homogeneous (scale-invariant).
* Forney value: `e_j = ω(α^{-j}) / σ'(α^{-j})` — homogeneous, because `σ'` (formal derivative)
  scales by the same factor as `σ`.
* The phase actually applied: `(-1)^{Σ_j popcount(e_j & M_j)}` — homogeneous.

So a *common* scalar factor on the `(σ, ω)` pair is invisible to the rest of the tape. This is the
only case that fits the gate, and it is the one the 202,860 figure assumes. **It requires an
end-to-end proof that `σ` and `ω` come from the same Bezout row** (they do in the key-equation
setup: `σ = v`, `ω = v·S mod x^{2t}`), and it is exactly what the first verifier salt will confirm.

**Case B — one 12-bit inverse per step (315 T/step).** Use the tape's own
`init_gf2_inverse_with_scaffold(12)` idiom on `lead(b)`. Cost 315 T × 138 = 43,470 T ⇒ 292,557 total
⇒ GM 30.40. **Does not fit the 264,700 gate.** Only acceptable if case A is refuted *and* the gate
is relaxed.

**Case C — fraction-free / Bareiss (2 rows/step).** `a ← lead(b)·a + lead(a)·b` with both scalar
multiplies materialised. 405,720 T for both passes ⇒ 451,947 total ⇒ GM 26.29. **Abort** — worse
than the tape. Only useful as a correctness oracle for case A on small parameters.

### 3.1 Shifts: which kind, and why they are 0 T

The divstep's move is "drop the leading coefficient and shift the window by one word" and
"conditionally halve" (`/x`). Both are **word permutations**, implemented as a chain of `SWAP`
(= 3 `CX`, 0 Toffoli) or of `CX` with a *classical* condition (`CX_IF`, 0 Toffoli — the tape already
uses 18,180 of them). The tape itself does exactly this between the EEA and the Chien: 183,037 `CX`
of lane rotation at **0 Toffoli** (`INTERFACE.md` §4). So the shift budget is genuinely 0, not
"cheap".

Do **not** implement the shift as a `CSWAP` ladder with a *quantum* control: a conditional 70-word
shift under a qubit control is 70 × 12 = 840 `CCX` = 840 T/step, which is 57 % of the whole budget.
The predicate must be a *classical* bit (measured, then coherently uncomputed, exactly the idiom the
Chien uses at 0 T: 10 `HMR` + 10 `CZ_IF`).

## 4. Output contract — what the new forward pass must leave at the cut

Cut **P2 = 30,151,421** (the tape's last EEA `CCX` is at 30,151,420; depth 0 on both sides).
The 183,995-op realignment sweep `[30,151,421, ~30,334,700)` is kept verbatim, so the new EEA must
reproduce **the pre-sweep layout**, which by measurement is:

1. the 70-word array `S0..S69` holds the interleaved `(a, b)` result as the tape's last block leaves
   it — final write targets are pool word 72/73/74 and `S7` (`win2_eea_last_mult.txt`);
2. all pool scratch qubits `Q840..Q889` back to their pre-EEA values — 8 pool qubits
   (`Q840,842,844,845,846,848,849,851`) are *live* at the EEA start (they carry state in) and must be
   restored bit-for-bit at the end;
3. the 13 classical flags `B49782, B53665..B53676` in the same state the tape leaves them
   (they belong to the Chien, so a fresh forward pass must leave them at 0 — measured: they are
   `BIT_STORE0`-cleared at every position boundary);
4. every `E` register untouched by the EEA (the EEA region writes only 18 `BIT_STORE1_IF` in the
   whole forward pass, all inside the straddling Chien position).

**The cheapest way to satisfy (1)–(4) is not to re-derive them: keep the tape's tail block and the
sweep.** §6 gives the cut points that do this.

## 5. Cut points and depth

| # | op | role | depth | inside/outside |
|---|---|---:|---:|---|
| P1 | 17,576,206 | first EEA op (`CCX S0[0],S1[0]→Q840`) | 0 | new forward pass starts here |
| P2 | **30,151,421** | first op after the last EEA `CCX` | 0 | new forward pass ends here; sweep kept |
| P3 | 57,520,821 | tape end | 0 | new reverse pass ends here |

All three re-verified depth 0 on the tape (`survey.json:depth`). `P2' = 30,335,416` (the nominal,
anchor-based cut) is **also depth 0 but is not usable**: it falls inside the first Chien position
(10-CCX chain spans 30,335,009…30,335,027, the `E2730` permutation ends at 30,335,415).

Reverse side: the tape's reverse EEA begins after the last Chien position closes. Its first
multiplication is **TODO-3** (one dump: the last `CCX` with an EEA operand ladder on the way back);
by symmetry it is the mirror of P2. The reverse replacement is `new_forward†`, spliced from that
mirror point to P3.

## 6. New reverse pass = the exact adjoint

```
new_tape = tape[0, P1)  ·  new_fwd  ·  tape[P2, Pm)  ·  new_fwd†  ·  tape[Pn, end)
```

where `tape[P2, Pm)` is the kept realignment sweep + the 4,025 Chien positions + the mirror sweep,
and `Pm`/`Pn` are its two ends (depth 0, `INTERFACE.md` §1). Because `new_fwd · new_fwd† = I`, the
composite is the identity on every qubit the new passes touch, and the phase applied by the kept
Chien is unchanged. Three consequences worth writing down:

* The reverse pass will have a *completely different op census* from the tape's reverse pass
  (measured asymmetry: 6,441,970 `BIT_INVERT_IF` and 226,522 `SWAP` on the tape's way back vs 3,527
  and 58,470 on the way out). That is expected and not a defect — but it also means **T-count
  symmetry is not a correctness check** for this design.
* The adjoint must undo the *classical* bits as well. `PUSH_CONDITION` depth must balance at every
  splice (`splice.py` enforces it) and every `E` bit the forward pass wrote must be rewritten by the
  adjoint in reverse order.
* Do not try to make the new reverse pass cheaper than the forward one: any asymmetry breaks the
  composite.

## 7. Deliverable shape for step 2 (not this round)

1. a generator `gen_normeea(n=70, field=GF(2^12), poly=0x1053, steps=69)` emitting
   `(name, qubits, bits)` triples in tape order, with `len(b)` per step a compile-time constant;
2. `splice.py` on the three ranges, `Circuit._check()`, then `k_patch` (see `VERIFY.md`);
3. if `P2`'s layout is not reproduced exactly, fall back to splicing **P1..P2 plus the sweep** and
   emit directly into the Chien layout (the sweep is 0 T, so this only buys risk reduction).

Explicitly out of scope this round: `k_patch` runs, verifier runs, submissions, any edit to
`data/competition/` or `submissions/`.
