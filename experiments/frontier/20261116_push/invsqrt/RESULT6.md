# invsqrt RESULT6: 4-head dual-branch follow-up — located, not built (generator blocker)

Work in `experiments/frontier/20261116_push/invsqrt/`. Account `jiyujia` Kaggle CPU only
for inspection; local work below is hash/GM arithmetic only (INV decode + sha256 +
score/GM arithmetic, no simulation, no local verifier runs, no local kmb parsing).
No candidate was built, no verifier was run, nothing submitted.

## 0. Verdict

**The 4 unconverted staircase heads are confirmed present at the exact NEW indices,
and the v27 generator flow needed to convert them is confirmed absent from every
public artifact. So nothing was built and no verifier was run.** This is the located
headroom of `RESULT5.md` §5 carried to its endpoint: same-class convertible in
principle, generator-only in practice (`RESULT5.md` §6 blocker stands, now with a
Kaggle-executed proof of absence).

## 1. What was executed (and what was not)

- **Kaggle CPU kernel `jiyujia/qcc-invsqrt-r6-heads-static` — COMPLETE** (static only:
  input walk for generator sources + `kickmix.Circuit.from_file` → `.kmx` text parse,
  no `Simulator`, no verifier). Log + restaged `circ.kmx`/`invsqrt_0af21cb8.kmb` in
  kernel output. Proves §2–§3 below.
- **Local**: decoded the v27 notebook `INV` payload (base64+zlib+sha256 only):
  34,968-char string → 180,382 B, sha256
  `0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b` (match),
  header `d750c7d5…6151…` (differs from the 179,768 B class). GM arithmetic for §4.
- **Not executed**: no candidate emission, no
  `verify_submission_invsqrt.py` run at any salt/shot count (no bytes exist to verify),
  no local simulation, no local verifier, no hand edit (per mandate, `RESULT5.md` §6
  is not repeated). The `zhuating/qcc-verify-new-4-files` v1 numbers are cited, not re-run.

## 2. Generator-absence proof (the blocker)

- Author flow: `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`
  (14:51 run that emitted `0af21cb8`). Full notebook fetched and read: 10 cells, code
  cells 1/3/5/7/9. Cell 5 is `INV = "eNrtvQMg…"` (zlib-compressed base64 of the
  finished `0af21cb8` bytes) + `zlib.decompress` + sha256 assert + write to
  `SUB/invsqrt.kmb`. Cells 1/3 pin and stage the public DQI/chem bytes by sha256;
  cells 7/9 run the unchanged official verifiers and pack `submission.zip`. **There
  is no emitter, no patch list, no `CircuitBuilder`/carry/divider/loader source in
  the notebook.**
- Kaggle input walk inside the R6 kernel (competition mount only):
  34 files under `/kaggle/input`, 14 py/json/zip/sh, **0 generator-like path hits**
  (`generat|emit|builder|carry|divider|patch|source_zip`), 12 `.kmb` all under
  `sample_submission/` (competition sample bytes). So the kernel that produced the
  14:51 bytes does not attach its generator as code or dataset.
- Notebook credits say the circuit "starts from Syed Asad Ali's 46-qubit generator
  line" with private rescheduling (table-load absorption, two coefficient-wire
  retire/rebuilds, phase-exit, mixed-segment division clean-up) plus measured-CZ /
  dead-write ideas — i.e. a private fork of the `syed3000` v12 line, not the pinned
  `jiyujia/qcc-invsqrt-v12-generator-source` tree. That fork is unpublished. The
  v12 tree cannot emit the §3 construction (different architecture, different census).
- Consequence: there is no public re-emission site for the 4 heads — no patch arg,
  no certificate override, no builder hook. Forking "the author's generator flow" is
  impossible from available artifacts. Requesting it needs the author's private tree.

## 3. Head-site construction doc (Kaggle static evidence, text ops 20856)

Opcode census (R6 kernel, matches `RESULT5.md` §3): `CCX 1526, CCZ 34, CX 12316,
CZ 2136, HMR 1276, X 964, Z 1045, Z_POW 43, SWAP 12, PUSH/POP 697/697,
BIT_INVERT 54, BIT_STORE0 3, NEG 30`, directives 23.

Heads (unconditional `CCX+CX+CX` staircase triples, retained before the HMRs):

| head | NEW ops (verified text) |
|---|---|
| H1a @12139 | `CCX q31 q15 q16` + `CX q16 q15` + `CX q15 q31` |
| H1b @12142 | `CCX q29 q41 q15` + `CX q15 q41` + `CX q41 q29` → `HMR q41 b191` @12145 |
| H2 @12596 | `CCX q31 q21 q15` + `CX q15 q21` + `CX q21 q31` → `HMR q21 b180` @12599 |
| H3 @13037 | `CCX q8 q41 q15` + `CX q15 q41` + `CX q41 q8` → `HMR q41 b180` @13040 |

Converted tails (already in file, `RESULT5.md` §4 shape, R6 block census confirms):
each tail span holds **CCX 4 / CCZ 2** (two complementary branches × 2 CCX + 1 CCZ),
HMR 5, `BIT_INVERT` 1 — exactly one branch's Toffolis fire per shot:
`HMR qX[bit]` + 34-op conditional compute
(CX 17, X 8, CCX 2, PUSH, Z 2, CZ 2, CCZ 1, POP) + 28-op conditional phase
(4×PUSH/POP, Z 6, CZ 11, HMR 2) + `BIT_INVERT` + inverted-bit re-application.
Windows: NEW `12145..12262`, `12599..12707`, `13040..13147`
(R6 census: `{CX 48/40/40, CZ 20, X 12, Z 10, PUSH 8, POP 8/7/6, HMR 5, CCX 4, CCZ 2, BIT_INVERT 1}`).

Why redesign, not copy: each head's target feeds its tail's measured wire
(H1 `q41/q15` → `HMR q41`; H2 `q21` → `HMR q21`; H3 `q41/q15` → `HMR q41`), so the
measured-carry choice, the complementary branch conditions, and the global wire
relabel (`RESULT5.md` §4: `q41/q42/q36/q34/q20/q21/q9/q32` role swaps) must be
re-derived inside the generator. Splicing a copied tail would double-drive those
wires and void the exact full-domain proof. This is the `RESULT5.md` §6 point, now
grounded in the R6 static dumps.

## 4. T / score / GM before → expected-after (local arithmetic only)

Before (unchanged-verifier PASS, full 200,540,928 shots, default salt; `RESULT5.md`
§2 = verify_new §3): score **74797.36535717871**, mean Toffoli **1459.3748802688297**,
max 1560, T **2.499900279707492**, C **1699.9401217540617**, rotations 33 /
1.64e-13, depth 1233, num_ops 20833, Q44, worst 0.9995605646154175 / worst_x 231.
GM with `66b4f18b` (347128304010.81165) + `bdae290f` (294762632.0817748), refs
2076774.233715 / 24439463583672.93 / 3355599588.3155375: **28.12769291**.

Expected-after *if* the generator converts the 4 heads with the tails' firing rates
(`RESULT5.md` §5: ≈ −2 to −4 mean Toffolis; T untouched so ΔC = Δmean; Δscore = 44·ΔC):

| Δmean | Δscore | score | GM |
|---:|---:|---:|---:|
| −2.0 | −88.0 | 74709.36536 | 28.13873243 (+0.01104) |
| −3.0 | −132.0 | 74665.36536 | 28.14425869 (+0.01657) |
| −4.0 | −176.0 | 74621.36536 | 28.14978929 (+0.02210) |

i.e. ≈ **−90..−180 score, +0.01..+0.02 GM**. No T/rotation/Q/depth lever is claimed
(closed per `RESULT5.md` §5; not re-argued here). These are projections, not
measurements — no bytes exist to verify.

## 5. Kernel refs

- `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` (14:51 2026-11-16,
  the run that emitted `0af21cb8`; notebook read in full this session — bytes-only,
  no generator).
- `zhuating/qcc-verify-new-4-files` v1 (unchanged verifiers, full shots default +
  2 salts; `0af21cb8` 12/12 PASS 74797.36535717871 / …7955 / …8739 — cited from
  verify_new §0–§3, not re-run).
- `jiyujia/qcc-invsqrt-r6-heads-static` (this session, COMPLETE; static generator
  search + head/tail dumps, no simulation, no verifier).
- Local scripts: `gen_r6heads.py` (kernel generator), notebook cells quoted in §2;
  `analyze_live.py` `load_ops` model reused by reference only (no local run).

## 6. Blocker and handoff

**Blocker: the v27 emitter is private and unattached — the 4 sites are not exposed
to any fork.** No concrete candidate can be emitted from public artifacts, so per
the no-blind-edit mandate no verifier time was spent (≈3 × 600 s full-shot runs at
near-zero hand-edit PASS probability) and nothing was submitted. Handoff to the
generator owner: apply the §3 dual-branch construction recursively at NEW
12139/12142, 12596, 13037 (heads feed HMRs at 12145/12599/13040 — branches must be
redesigned, not copied) and re-emit; expected §4 payoffs if firing rates match the
converted tails. If the owner publishes the fork (or a patch/certificate hook for
these sites), the follow-up is: emit → full-shot default + 2-salt unchanged
verification → new RESULT.
