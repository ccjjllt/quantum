# DQI width / mean-T / decoder-generation — three decisive measurements

Date 2026-11-17. Line: `zhuating`, DQI. Target: beat the shipped leg
`61c8348d` = **Q 890 / mean T 367,120.004 / R 1.1912605 / official clean cost
346,413,579,540.50** (public 28.15083 combo). Gold 28.71339 needs one leg
**−5.763 %** (DQI ≤ 326.45e9).

Everything below is read from the shipped tape itself, on Kaggle CPU kernels
(`enable_gpu=false`, `enable_tpu=false`, private, competition data not needed for
these runs). **No simulation, no verifier run, no candidate, no submission.**
Raw reports: `evidence/k20_wiretable_v3.txt`, `evidence/k21_audit.txt`,
`evidence/k22_pooltable.txt`.

## 0. Verdicts

| attack surface | verdict | decisive number |
|---|---|---|
| **(A)① width, all 50 pool wires** | **NO-GO** | cheapest honest rebuild **1,831 T/qubit** (q889) vs a **826 T** break-even; average **3,822 T/qubit**; whole 840Q move **191,122 T** against a **45,005 T** tie budget / **21,254 T** gold budget |
| **(A)② half-serial one working word** | **NO-GO** | all 12 bits of *all four* 12-bit groups are live at **100 % of the 2,760,326 peak-width ops** → no free window; the cheapest group's Toffoli-only floor is 6,684 T/12Q but it absorbs **1,177,299 CX accumulations** of non-live products, so replay is not finite |
| **(B) mean-T conditioning** | **NO-GO** | the *entire* mean-T discount on this tape is **873.0 T = 0.237 % of T = 0.079 % of cost = +0.008 GM**; 45,356 T sits in 1-bit regions and already fires ~98 % of the time; no Z-basis measurement exists to build a new predicate |
| **(C) new decoder generation** | **NO-GO** | the published space optimum for this instance is **2nb = 1,680 Q** (ref circuit 1,893 Q); our tape is **890 Q = 0.53 ×** that, and the LLM-discovered DQI decoder is 442,397 T at **1,837 Q** = **5.1 × worse** in Q²T |

Best single wire in the whole table: `q889`, **1,831 T** for 1 qubit →
GM **28.12526** (**−0.0256**, a loss). Best 50-wire combination: GM **25.44**.
Even the absolute floor of the whole move (62,664 T = one AND per Toffoli-window)
gives GM **27.76**, i.e. still below 28.15083.

## 1. The tape, decoded (new facts; the earlier width note was on `ccc2ab84`)

`61c8348d…`, 479,128,630 B, header `Q=890, registers=4165, ops=57,520,809,
staticT=367,993`.

* **Registers decoded from the payloads** (`u32 kind, u32 count, name,
  u32 ids` with bit 31 tagging qubits): exactly 70 × `S0..S69` = **qubits 0..839**
  and 4095 × `E0..E4094` = **bits 0..49131**. `S67 = 804..815`, `S68 = 816..827`,
  `S69 = 828..839`. `Q = 840 + 50`, pool `= 840..889`.
* Opcode census: `X 41,308 · Z 108,396 · R 48,043 · CZ 526,319 · CX 30,098,766 ·
  SWAP 373,859 · CCZ 5,977 · CCX 362,016 · CSWAP 0 · BIT_INVERT 2,814,615 ·
  BIT_STORE0 55,496 · BIT_STORE1 17,896,996 · HMR 71,990 · PUSH/POP 2,558,513
  each`. Static T = 362,016 + 5,977 = **367,993**; there is **no CSWAP**.
* **The gate set has no `H`** (kernel `strings`: `CCX CCZ CSWAP CX CZ HMR RY RZ Rx
  Rz SWAP Z_POW cx cz cswap hmr init_and del_and reset rx ry rz`). The input is a
  computational-basis state (the verifier writes the syndromes classically), so
  every wire holds a definite bit, `Z`/`CZ`/`CCZ` are pure global phase, and
  **`HMR` = X-basis measure + reset = a fresh uniform random bit plus |0>**.
  There is no way to read a computational-basis value into a classical bit.
* **This tape already borrows three syndrome registers as scratch**: `S67`, `S68`,
  `S69` are HMR'd **4 / 2 / 4** times and restored (the file verifies 0/0, so the
  restore is exact). Effective scratch = **86 wires for a Q charge of 50**. Every
  other suspect wire (804..889) is either one of those three registers or the
  50-wire pool; there is no dead block.
* Static vs mean: **367,993 → 367,120.004**, discount **873.0 T (0.237 %)**.
  Gating structure (PUSH/POP_CONDITION depth of each Toffoli): depth 0
  **317,590 T**, depth 1 **45,356 T**, depth 2 **5,047 T**; a random-bit model
  would discount 26,463 T, the tape only discounts 873 T, so **the existing
  1-bit conditions are near-constant-true and already harvested**.

## 2. (A)① The full 50-wire shed table

Roles: `CCX/CSWAP` write C and read A,B; `CX` writes C, reads A; `SWAP` writes
A and C; `CCZ` is diagonal (read only); `X/R/HMR` write A.

* `windows` = R/HMR-delimited value lifetimes (each needs its value rebuilt).
* `winT` = windows that contain ≥1 Toffoli write (floor of the rebuild count).
* `writeT` = Toffoli writes into the wire = **honest rebuild floor**.
* `T_win` = static Toffoli inside the wire's live windows.
* `net1`/`netC` = `windows × 1 T` (physically impossible bound) / `writeT`.
* Deleted compute/uncompute term = **0**: every one of the 50 wires is read at
  44,717–104,773 points and no write is dead (`RESULT.md` §5: 0 dead writes,
  0 cancel pairs, all 54k bits referenced on this tape family), so shedding a wire
  deletes its writes **and** forces the same work elsewhere.

| wire | touches | reads | writeT | writeCX | writeX | resets | windows | winT | T_win | net1 | netC |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 840 | 1,506,017 | 755,108 | 28,804 | 697,007 | 37 | 16 | 17 | 16 | 367,849 | 17 | 28,804 |
| 841 | 787,889 | 392,083 | 14,824 | 366,856 | 37 | 16 | 16 | 16 | 367,836 | 16 | 14,824 |
| 842 | 546,938 | 232,464 | 8,252 | 297,527 | 38 | 16 | 16 | 16 | 367,847 | 16 | 8,252 |
| 843 | 376,315 | 126,906 | 3,368 | 244,286 | 39 | 16 | 16 | 14 | 367,773 | 16 | 3,368 |
| 844 | 370,868 | 97,793 | 2,012 | 267,708 | 43 | 16 | 16 | 16 | 367,841 | 16 | 2,012 |
| 845 | 340,613 | 72,627 | 460 | 265,260 | 42 | 16 | 16 | 16 | 367,847 | 16 | 460 |
| 846 | 309,522 | 76,444 | 460 | 232,450 | 95 | 16 | 16 | 14 | 367,851 | 16 | 460 |
| 847 | 293,833 | 59,451 | 130 | 233,891 | 95 | 16 | 16 | 14 | 367,842 | 16 | 130 |
| 848 | 293,703 | 57,864 | 270 | 235,434 | 96 | 16 | 16 | 14 | 367,851 | 16 | 270 |
| 849 | 285,175 | 62,058 | 50 | 222,926 | 110 | 16 | 16 | 14 | 367,849 | 16 | 50 |
| 850 | 278,714 | 51,057 | 10 | 227,489 | 127 | 16 | 16 | 14 | 367,812 | 16 | 10 |
| 851 | 269,228 | 44,686 | 10 | 224,376 | 125 | 16 | 16 | 14 | 367,817 | 16 | 10 |
| 852 | 220,432 | 73,195 | 3,290 | 136,472 | 62 | 14 | 14 | 14 | 367,378 | 14 | 3,290 |
| 853 | 170,250 | 52,851 | 1,378 | 112,380 | 158 | 14 | 14 | 14 | 367,387 | 14 | 1,378 |
| 854 | 152,618 | 48,651 | 722 | 101,086 | 171 | 14 | 14 | 14 | 367,356 | 14 | 722 |
| 855 | 138,544 | 47,756 | 624 | 89,805 | 172 | 14 | 14 | 14 | 367,385 | 14 | 624 |
| 856 | 141,124 | 44,410 | 198 | 94,711 | 196 | 14 | 14 | 14 | 367,306 | 14 | 198 |
| 857 | 141,139 | 47,050 | 52 | 93,026 | 227 | 14 | 14 | 3 | 367,391 | 14 | 52 |
| 858 | 141,403 | 47,812 | 124 | 93,082 | 191 | 14 | 14 | 14 | 366,607 | 14 | 124 |
| 859 | 139,393 | 44,205 | 88 | 94,734 | 191 | 14 | 14 | 14 | 366,599 | 14 | 88 |
| 860 | 143,004 | 46,564 | 52 | 96,049 | 198 | 14 | 14 | 14 | 366,592 | 14 | 52 |
| 861 | 138,987 | 49,464 | 52 | 89,107 | 227 | 14 | 14 | 14 | 366,621 | 14 | 52 |
| 862 | 142,911 | 49,050 | 52 | 93,413 | 259 | 14 | 14 | 14 | 366,607 | 14 | 52 |
| 863 | 127,080 | 45,724 | 52 | 81,080 | 219 | 14 | 14 | 14 | 366,607 | 14 | 52 |
| 864 | 202,445 | 96,192 | 7,214 | 83,212 | 584 | 9,400 | 5,112 | 4,796 | 172,381 | 5,112 | 7,214 |
| 865 | 162,848 | 74,714 | 2,775 | 79,614 | 635 | 1,608 | 1,328 | 921 | 179,104 | 1,328 | 2,775 |
| 866 | 167,664 | 84,402 | 3,359 | 74,680 | 646 | 1,587 | 1,320 | 888 | 179,652 | 1,320 | 3,359 |
| 867 | 175,069 | 86,123 | 3,466 | 79,904 | 664 | 1,602 | 1,328 | 919 | 170,124 | 1,328 | 3,466 |
| 868 | 184,995 | 88,817 | 3,352 | 86,358 | 611 | 1,645 | 1,347 | 904 | 177,741 | 1,347 | 3,352 |
| 869 | 185,748 | 93,780 | 7,520 | 70,615 | 652 | 9,499 | 5,223 | 4,901 | 199,997 | 5,223 | 7,520 |
| 870 | 195,749 | 88,825 | 7,376 | 86,142 | 539 | 9,682 | 5,372 | 4,889 | 195,237 | 5,372 | 7,376 |
| 871 | 192,507 | 90,070 | 7,624 | 81,556 | 456 | 9,760 | 5,459 | 4,976 | 216,747 | 5,459 | 7,624 |
| 872 | 177,775 | 85,859 | 3,450 | 82,142 | 637 | 1,619 | 1,357 | 895 | 178,579 | 1,357 | 3,450 |
| 873 | 173,500 | 87,189 | 4,088 | 76,561 | 473 | 1,455 | 1,181 | 836 | 151,549 | 1,181 | 4,088 |
| 874 | 191,859 | 89,366 | 3,988 | 91,345 | 572 | 1,718 | 1,430 | 954 | 181,590 | 1,430 | 3,988 |
| 875 | 174,438 | 90,194 | 3,490 | 75,662 | 636 | 1,555 | 1,308 | 891 | 180,619 | 1,308 | 3,490 |
| 876 | 206,281 | 95,364 | 7,564 | 88,058 | 551 | 9,681 | 5,372 | 4,960 | 208,465 | 5,372 | 7,564 |
| 877 | 196,400 | 101,012 | 7,966 | 74,895 | 595 | 9,714 | 5,409 | 4,951 | 194,245 | 5,409 | 7,966 |
| 878 | 209,472 | 97,898 | 7,466 | 88,103 | 608 | 9,674 | 5,387 | 4,967 | 205,363 | 5,387 | 7,466 |
| 879 | 207,105 | 95,707 | 7,389 | 88,852 | 677 | 9,602 | 5,324 | 4,925 | 206,119 | 5,324 | 7,389 |
| 880 | 150,341 | 73,215 | 2,833 | 69,345 | 531 | 1,422 | 1,153 | 802 | 161,122 | 1,153 | 2,833 |
| 881 | 209,058 | 104,773 | 8,056 | 82,079 | 640 | 9,661 | 5,357 | 4,938 | 215,593 | 5,357 | 8,056 |
| 882 | 85,514 | 44,717 | 1,970 | 36,358 | 246 | 387 | 354 | 210 | 276,391 | 354 | 1,970 |
| 883 | 199,516 | 93,268 | 3,492 | 94,655 | 712 | 1,480 | 1,205 | 861 | 170,651 | 1,205 | 3,492 |
| 884 | 169,439 | 80,713 | 3,263 | 79,514 | 535 | 1,630 | 1,350 | 885 | 187,765 | 1,350 | 3,263 |
| 885 | 165,281 | 80,820 | 3,034 | 74,546 | 632 | 1,368 | 1,157 | 814 | 187,766 | 1,157 | 3,034 |
| 886 | 166,920 | 76,324 | 2,937 | 81,220 | 589 | 1,492 | 1,223 | 829 | 170,958 | 1,223 | 2,937 |
| 887 | 184,966 | 87,359 | 3,228 | 88,070 | 707 | 1,582 | 1,303 | 882 | 179,298 | 1,303 | 3,228 |
| 888 | 181,063 | 85,203 | 7,057 | 80,111 | 605 | 9,589 | 5,274 | 4,877 | 175,030 | 5,274 | 7,057 |
| 889 | 94,653 | 45,753 | 1,831 | 42,830 | 348 | 1,141 | 909 | 658 | 166,123 | 909 | 1,831 |
| **pool** | | | **191,122** | 6,726,582 | | 119,914 | **72,903** | **62,664** | | | **avg 3,822** |

Group totals (T/qubit in parentheses):

| group | wires | resets | windows | winT | writeT | per qubit |
|---|---:|---:|---:|---:|---:|
| word `840-851` | 12 | 192 | 193 | 178 | 58,650 | 4,888 |
| word `852-863` | 12 | 168 | 168 | 157 | 6,684 | **557** |
| pool `864-875` | 12 | 46,628 | 31,765 | 26,770 | 57,702 | 4,808 |
| pool `876-887` | 12 | 55,260 | 34,594 | 30,024 | 59,198 | 4,933 |
| flags `888-889` | 2 | 10,730 | 6,183 | 5,535 | 8,888 | 4,444 |
| **total** | **50** | **119,914** | **72,903** | **62,664** | **191,122** | **3,822** |

**Width profile** (R/HMR-delimited, the sound model for this tape: a wire can only
be reused after a reset): **pool-live peak = 50 → Q 890**, exactly
`2,760,326` ops at the peak in **961 episodes** spanning ops 21,603,819–52,638,295.
Because the peak is 50 = |pool| at every one of those ops, *all 50* wires are
live at *every* peak op. So — unlike the older `ccc2ab84` tape —
**any single wire shed really does drop Q to 889**. That makes each wire's marginal
value exactly `(889/890)² − 1 = 0.2245 % = 826 T`.

**The exchange, wire by wire** (best to worst by honest rebuild):

| rank | wire | rebuild floor T | allowance (tie 28.15083) | verdict |
|---:|---:|---:|---:|---|
| 1 | q889 | **1,831** | 826 | **2.2 × over** → GM 28.12526 (−0.026) |
| 2 | q882 | 1,970 | 826 | 2.4 × over |
| 3 | q865 | 2,775 | 826 | 3.4 × over |
| 4 | q880 | 2,833 | 826 | 3.4 × over |
| 5 | q886 | 2,937 | 826 | 3.6 × over |
| … | … | … | 826 | … |
| 50 | q840 | 28,804 (and `T_win = 367,849`, i.e. live across the whole tape → replay **not finite**) | 826 | — |

Whole-move arithmetic (Q 890→840):

| model | ΔT | Q | GM |
|---|---:|---:|---:|
| honest rebuild floor `Σ writeT` | 191,122 | 840 | **25.44** |
| absolute floor `Σ winT` (one AND per Toffoli-window) | 62,664 | 840 | **27.76** |
| budget to tie 28.15083 | 45,005 | 840 | 28.15083 |
| budget for gold 28.71339 | 21,254 | 840 | 28.71339 |

So even the *physically impossible* one-AND-per-window bound is 1.39× over the
tie budget and 2.95× over the gold budget. **The width axis is closed on all 50
wires, not just on q864.**

## 3. (A)② Half-serial rewrite of a working word

Because the peak is 50 = |pool| at every peak op, every bit of all four 12-bit
groups is live at **every one of the 2,760,326 peak-width ops** (k20 reached the
same conclusion independently over its superset plateau: `3,491,848/3,491,848`).
There is therefore **no op inside the plateau at which the high half of any group
is dead while the low half is live** — a "compute the high half, reuse its wires
for the low half" rewrite has no window to exploit; it can only be done by
re-ordering the schedule.

What that costs, bounded from the tape:

* the cheapest group (`852-863`) has only **6,684 T** of Toffoli writes into it
  (557 T/qubit — apparently under the 826 bar), **but** it also absorbs
  **1,174,945 CX writes** (XOR accumulations of product values that live in other
  wires at the time), and `T_win = 366,607–367,391` for its bits, i.e. they are
  live across essentially the whole tape. Replaying them needs the *products*,
  which are not live. **Replay is not finite, and 557 T/qubit is not a mechanism.**
* the two groups with genuinely short-lived content are the AND pools
  `864-887`: ≈2.2 Toffoli writes per Toffoli-bearing window, 4,808–4,933 T/qubit, i.e. **5.7×**
  the 826 bar. They are already the "serial-friendly" object (a value per window),
  so half-serialising them is the case the table already covers.

**NO-GO.** No tape-level half-serial mechanism lands under 826 T/qubit; the only
sub-826 number in the table (557) is an artefact of counting Toffoli writes while
ignoring the CX-accumulated products.

## 4. (B) mean-T: measured discount, and why it cannot grow

* Static **367,993**, official mean **367,120.004** → **the whole mean-T
  discount is 873.0 T = 0.237 % of T**. In cost terms: 0.079 % ⇒ **+0.008 GM if
  it were doubled**. This is the entire size of the prize on this axis.
* Toffoli by PUSH/POP depth: **depth 0 = 317,590 T, depth 1 = 45,356 T, depth 2 =
  5,047 T**. A model in which each pushed condition is an independent fresh HMR
  bit predicts a 26,463 T discount; the tape realises **873 T**, so the existing
  1-bit conditions are **~98 % true** — the builder already gated only blocks
  whose phase is almost always needed.
* Mechanically closed: the gate set is `X Z R CZ CX SWAP CCZ CCX HMR + classical
  bits` — **no `H`**, and `HMR` is an X-basis measurement of a computational-basis
  state, i.e. a *fresh uniform random bit* followed by a Z reset. A classical bit
  can therefore never hold a data value, so no "skip this arithmetic unless the
  data says so" predicate can be built. The only gates that may legally be gated
  are phase blocks whose action vanishes with the measured mask, and every
  remaining such block is tagged by ≥ 12 bits (`264 T / 4096 = 0.064 T` per block,
  `< 1 T` over the whole tape — reproduces `RESULT5.md` §3 on this tape).
* The E registers do not help either: `E0..E4094` hold the **random masks M_j**
  which are the *phase* conditions (already folded to 0-T `CZ if b`), not data.

**NO-GO**, with the quantitative ceiling: any future mechanism on this axis must
beat `873 T / 0.237 %`, and the only remaining 1-bit-gated pool is 45,356 T that
currently fires 98 % of the time, so the realistic extra is `45,356 × 0.02 ≈ 900 T`
= 0.24 % of T = 0.08 % of cost = **+0.008 GM**, at the cost of re-deriving the
phase repayment of those blocks.

## 5. (C) New decoder generation (papers)

Read: **arXiv:2408.08292** (Jordan et al., *Optimization by Decoded Quantum
Interferometry*, Nature 646:831, 2025 — the algorithm behind this benchmark);
**arXiv:2510.10967** (Khattar, Shutty, Gidney, Zalcman, Yosri, Maslov, Babbush,
Jordan, *Verifiable Quantum Advantage via Optimized DQI Circuits*, 2025-10-13);
**arXiv:2610.22367** (Gu, Kemeny, Yelin, Lukin, *Discovering state-of-the-art
quantum circuits with LLMs*, 2026-10-15).

| source | claim | number for our instance (m=4095, n=70, b=12) | vs our 890 Q / 367,993 T |
|---|---|---|---|
| 2510.10967 | "leading-order space complexity to the theoretical minimum of **2nb** qubits", 5.72 M Toffoli for classically intractable instances | **2·70·12 = 1,680 Q** | our tape is **0.53 ×** the published space minimum |
| shipped reference circuit (`dqi_reference_circuit.py`, implements 2510.10967) | `reg_b = 70×12` fresh + 67 syndromes + ~42 ancillas | **1,893 Q** (verified reference) | 2.13 × our Q ⇒ 4.5 × our cost at equal T |
| 2610.22367 | LLM-discovered DQI decoder | **442,397 T at 1,837 Q** | Q²T = 1.49e12 vs 2.91e11 ⇒ **5.1 × worse** |

Neither paper offers (i) a classical-register substitution for a quantum working
word — impossible here, since the only measurement is X-basis + reset (§4) and
`E0..E4094` are the fixed random masks — nor (ii) an in-place 840Q formulation:
the published optimum is *out-of-place* (two `nb` register arrays), which is
exactly why it needs 1,680 Q. Our 890 Q is already an in-place formulation that
beats the published bound by 1.9×, and it already monetises the only free-space
trick available: **it borrows S67/S68/S69 (36 of the 840 contract qubits) as
working scratch** (§1), i.e. the effective scratch is 86 wires for a Q charge of
50.

**NO-GO.** A further borrow cannot beget a borrow: parking 12 syndrome bits for
the duration of a borrow costs 12 wires (no Z-measurement ⇒ no classical stash),
so borrowing is self-limiting at zero net qubits.

## 5b. Draw risk (does not change anything here)

`61c8348d` draws **dirty at the default salt** (1 value error →
348,004,440,260.46) and the public ref `58454232` is its **clean** draw
346,413,579,540.50 (`intel/RESULT_public_salt_model.md`). Any candidate is a new
SHA ⇒ a new seed ⇒ an unknowable draw worth `+0.459 %` when lost, so a candidate
needs a *clean* cut of ≳ 0.09 % just to break even. The best shed measured here
(q889) is a **loss even on the clean draw** (GM 28.12526 vs 28.15083), so the
draw question never arises.

## 6. What would have to be true for any of these to pay

1. **Width.** A mechanism that sheds one wire for **< 826 T** (0.22 % of the
   tape's T) while that wire is read at **44,717–104,773** points in **354–9,760**
   separate value lifetimes. The only way that is possible is if the value is a
   *redundant copy or a linear function of live data* (regenerable with CX only).
   There are none: every wire's rebuild needs 1,831–28,804 Toffolis, and 24 of
   them are live across `T_win ≈ 366,600–367,850`, i.e. effectively the whole tape.
   Target for gold: an in-place **≤ 864 Q** formulation at **≤ −0.006 % T**, or
   **840 Q at ≤ +5.79 % T (21,254 T)**, i.e. **≤ 425 T/qubit average**.
2. **mean-T.** A legal way to make a *value* block skippable on most shots. That
   requires a computational-basis measurement; the gate set has none, and no gate
   in the tape can create one (`rx/ry/rz` are phase-only on a basis state).
   Everything else is bounded by 873 T (0.237 %).
3. **New generation.** Either fewer field products per syndrome pass (the count,
   not the rank: rank 42/99 is proven optimal) or an in-place division. Both are
   decoder research programmes, not tape surgery. Anything that raises Q above
   890 is dead on arrival: the width ladder charges 826–900 T/qubit while the gold
   line at Q865 tolerates **−871 T** (i.e. requires a *saving*).

## 7. Verification scope, stated honestly

* **No candidate circuit was built, so no verifier ran and nothing was submitted.**
  The only numbers here are: (a) official constants already on record
  (Q 890, mean T 367,120.004, clean cost 346,413,579,540.50 — reproduced to
  0.00002 % by `R·Q²·T` with R = 1.1912605, the residual being R's rounding), and
  (b) exact static counts read from the 479 MB `.kmb`.
* Kernels (all CPU-only, private, `enable_gpu=false`, `enable_tpu=false`):
  * `zhuating/qcc-dqi-wiretable-61c8` (v3) — sha gate, header, opcode census,
    register/touch index, first 50-row pass, PUSH/POP depth accounting.
  * `zhuating/qcc-dqi-audit-61c8` — register-payload decode (`S0..S69` = 0..839,
    `E0..E4094` = bits 0..49131), full 890-wire census, reset-kind split.
  * `zhuating/qcc-dqi-pooltable-61c8` — definitive 50-wire table with true
    operand roles, pool-live profile, leave-one-out coverage, greedy set.
* Everything else is local arithmetic (allowed: no simulation). Two local
  mistakes were caught and are recorded so they are not repeated:
  (i) the first pass used a per-op boolean as if it were a per-opcode table, which
  made every target look like a read; (ii) `POOL` was initialised to "wires with a
  reset" (86), which wrongly included the three borrowed syndrome registers
  `S67-S69` and inflated the peak to 926. Both are fixed in the table above; the
  86-wire list is itself the finding that the tape borrows three syndrome
  registers.
* Not measured here: value-level (simulated) redundancy between wires, which
  would need a 256-lane value scan (the k7 OOM). It is the only remaining object
  that could in principle produce a sub-826 T/qubit shed, and it can only find
  *duplicate copies* — none is visible structurally (each wire has a distinct
  write set).
