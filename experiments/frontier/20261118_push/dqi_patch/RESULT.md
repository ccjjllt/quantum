# Tape surgery (dqi_patch) — toolchain proven, 2026-11-18 03:45 Beijing

Goal: make the DQI tape `575b043f` (mean T 367,116.06, Q 890) cheaper by rewriting an
instruction range in place, without touching the official verifier.

## 1. The file is a struct-of-arrays stream, and a range is a range in every array

`vqcc_ir.Circuit` addresses instructions by index; each opcode's bit flags decide which operand
array it consumes (`L3Q/L2Q/L1Q/L1B/LCOND/LANGLE/LTAG`). So replacing `[a, b)` is one numpy
concatenation per packet plus a `tag_ends` shift — no per-instruction decode of the 57.5M-op
tape. `splice.py` also checks the two invariants that matter: the condition-stack depth must
balance (`depth(a) + depth(new) == depth(b)`) and the replacement must stay inside the tape's
qubit/bit width, then re-runs `Circuit._check()`.

## 2. Measured: the round trip is byte-exact (kernel `zhuating/qcc-dqi-null-splice`, COMPLETE)

| range | ops | identical to source |
|---|---:|---|
| `[19,508,954, 21,385,877)` (fwd cluster) | 1,876,923 | **yes** |
| `[46,230,185, 52,842,219)` (rev cluster) | 6,612,034 | **yes** |
| `[30,335,416, 30,336,416)` (Chien start) | 1,000 | **yes** |
| `[30,000,000, 30,001,000)` (mid) | 1,000 | **yes** |

`from_ops` insertion of `X X` at a depth-0 cut grows the tape by exactly 2 instructions and
re-validates. So a replacement can be written as `[name, qubits, bits]` triples and spliced.

Condition-stack depth at the four cuts: `0/0` for both clusters, `0/1` at the Chien start
(that boundary is inside a PUSH block — avoid it), `0/0` mid. Both clusters are legal stages.

## 3. Measured: the register layout (authoritative, from the .kmb itself)

4,165 registers: `S0..S69` (qubits, 12 each, **contiguous**: `S_i = qubits 12i..12i+11`) and
`E0..E4094` (classical, 12 bits each). 890 qubits = 840 syndrome + 50 pool (words 70..73 + 2).
So `word = qubit // 12` is correct for the syndrome array — the earlier worry that the
aggregates were a grouping artifact is resolved: the word triples are real.

## 4. The two big clusters are multiply streams, not the initial shift

| region | T | CX | CX per CCX | multiply blocks (T/42) |
|---|---:|---:|---:|---:|
| `[19,508,954, 21,385,877)` | 29,543 | 1,826,827 | 61.8 | ≈703 |
| `[46,230,185, 52,842,219)` | 65,774 | 4,326,547 | 65.8 | ≈1,525 |

A controlled swap chain costs exactly 2 CX per CCX, so these can not be `left_rotate(...,
control)` CSWAP ladders. A 12×12 product block is 42 ANDs plus O(10³) free XORs — which is the
measured ratio. **The barrel-shifter/initial-shift hypothesis is dead**; the 95,317 T is EEA
multiplication work, i.e. the same lever as the whole tape's arithmetic (42 ANDs per block,
~3,793 blocks). The only remaining handle on it is the bilinear rank of the 12×12 product.

## 5. Cost arithmetic, corrected

`score = 1.1912605 · Q² · meanT` and GM is the cube root of the three reference/ratio terms, so
T enters **linearly**:

| DQI T change | new T | GM |
|---|---:|---:|
| −95,317 (both clusters fully removed) | 271,799 | **31.151** |
| −85,000 | 282,116 | 30.766 |
| −65,774 (rev cluster only) | 301,342 | 30.098 |
| −102,425 (the 890 Q target cut) | 264,691 | 31.427 |

The earlier note in `RECORD.md` that 85k T is worth +0.9 GM was wrong by 3×; one leg's cost is
linear in T, and 10% of DQI T is +0.94 GM.

## 6. Verifier plumbing

The official DQI verifier must run under `/usr/bin/python3` (the interpreter that carries
`kickmix`); `sys.executable` in a Kaggle script kernel is python3.13 without `km.Circuit`.
`k_patch` now uses `/usr/bin/python3`, reports `qubits_used` / `qubit_gaps` (wire compaction
check), runs one verifier per salt (~160 s each), and only emits `dqi_patched.kmb.xz` when the
sha changed and every salt is 0/0.

## 7. 跑官方 verifier 的正确姿势（本轮踩的坑）

比赛数据自带一份 kickmix：`data/competition/kickmix/kickmix.so`（Kaggle 上是
`/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation/kickmix/`）。
verifier 的 `import kickmix` 必须解析到**这一份**，否则会报
`module 'kickmix' has no attribute 'Circuit'`（系统 python 里的是另一个版本）。

可用写法（见 `experiments/frontier/20261117_deep/integration/main_template.py:174-182`）：

```python
COMP = "/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation"
env = dict(os.environ, JAX_PLATFORMS="cpu", OMP_NUM_THREADS="4",
           PYTHONPATH=COMP + "/kickmix:" + COMP + "/verifiers")
subprocess.run([sys.executable, COMP + "/verifiers/dqi/verify_submission_dqi.py", kmb],
               env=env, cwd=COMP + "/verifiers")
```

即：**解释器用默认的 `sys.executable`**（不是 `/usr/bin/python3`），
关键是 `PYTHONPATH` 里放 `COMP/kickmix`，并把 `cwd` 设到 `COMP/verifiers`。
`k_null`/`k_patch` 里早前用 `/usr/bin/python3` 的写法是错的（会在 verifier 启动时炸）。
