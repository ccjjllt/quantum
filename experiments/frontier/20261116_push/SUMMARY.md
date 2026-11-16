# 2026-11-16 大幅提分推进：阶段总结

日期：2026-11-16（北京时间）。当前落地：**public 28.09486**，ref **58424363**，
rank **188 / 3160**（185+ 队并列 28.09486，银线 rank 156 在并列内部）。
上一版：28.09090（ref 58420406）。

## 已落地

| 项 | 结果 |
|---|---|
| invsqrt | `f2cdab0b` 44Q，75,006.3765，官方 verifier 200,540,928 shots PASS，worst/tol 0.99956056 |
| DQI | `ccc2ab84` 890Q，347,375,470,571.73，102,400 shots PASS，0 value / 0 phase |
| chemistry | `sub1` 427Q，T=14,712，294,762,697.44；e1/e2 0.0199999985，E_gap 3.9148980015 |
| 本地 GM | 28.0948733；public 28.09486（并列） |
| 提交 | ref 58424363，2026-11-16 09:06 UTC，COMPLETE |

公开最好三件是同一 invsqrt/DQI + `bdae290f`（294,762,632.08，本地 GM 28.0948754），
但只比 sub1 便宜 65（−0.22 ppm），仍落在 28.09486 并列内，**未提交**。

## 已关闭的轴

### invsqrt
- `f2cdab0b` 的 Q=44 是硬地板：5,790 个操作在 445 个区间同时占满 44 线；唯一 idle 的
  `q22..q25` 无仿射/≤3-AND 重建；全域名扫描 0 个可删 Toffoli。
- v12 46Q 源码的 Q=42 新 body：cap-17 first loader 证书已证 exact（80 T，work_peak 17），
  但 `coefficient_forward` 43（−1）、`product_forward`/`divider_cleanup`/`coefficient_inverse`
  46（各 −4）、`seed_forward` 45（−3），共 13 条线要 ≤1.3 T/线；identity library 已耗尽。
  无 Q≤42 候选。

### DQI
- 890Q 是 3.59M op 的结构平台，50 ancilla 同时活；`peak_without=890` 对每个 ancilla 成立。
- T 面：v12 与 890 磁带的 exact scan 都是 0 cancel / 0 dead / 0 |0>-control。
- 864Q 需要 out-of-place division（`direct_carry_arithmetic.py:35-43` 的 in-place 24-bit multiply
  硬阻塞），BM-style 需 8× 乘法（≈1.4M T），decision machine 需 3–6 周。无候选。

### chemistry（现有 shape）
- T=14,712 = 8,050 loader + 6,662 heuristic；loader don't-care 全扫描 0 改进；
  B/C/J/Q 均在硬门/最优。
- λ refit：列旋转 0.0000%、offset 投影无可行步、w 改幅被 e2 门挡住；−330 不可得。
- loader code search（CODE2）：145-cut basis 并不比 shipped 好（shipped products 189/190/191，
  不是 193）；k9 亏、k10/k12 平、k14 −1 不可发射；混合包 e1=61,130 mHa、e2=11,659 mHa。负结果。

## R=5/B=143/C=75：真实 fit 已关闭

- 公开 `dfthc_refit` 的 merge→shrink 路线：`B10c54` (10,120,54) → merge(p,2,108) →
  (5,240,108) → shrink (5,143,75)。
- 真实全预算结果：`(5,240,108)` pre-fit 13.709；`240x100` 14.171；`200x90` **27.839**；
  `170x82` 39.987；`143x75` **53.653 mHa**；8-bit quantization **73.1 mHa**。copy shrink 108→100
  几乎免费，但 basis 240→143 每步都放大误差，是 RESULT2 的 projector 墙。
- 唯一可用的中间点 `(5,240,100)` 14.17 mHa，但 rows 1,276、T_heur 9.2k ⇒ T≈17.7k，比 14,712 更差。
- 791 行 loader 端口已做出并验证 **238 T/loader**（189 products + 43 high + 6 low，T=14,029，
  +0.45 GM），但没有可用 shape。**R=5/6 关闭，化学冻结在 294.76M。**

## 提交策略

- 今天剩 2 次提交。只提交 local GM **>=28.09490** 的候选；28.09486–28.09489 是并列，
  晚提交会恶化 tie-break。
- bdae 已复核但 hold；CODE2 无候选；invsqrt/DQI 无候选。
- R=5 候选一旦 full PASS，由 `pipeline/` 复用 18 成员 CPU 管线复核并提交。

## 证据入口

- `pipeline/RESULT.md`：28.09486 三件官方 JSON、zip hash、提交回执。
- `invsqrt/RESULT.md`、`RESULT2.md`、`RESULT3.md`：Q44 硬地板、v12 Q42 阻塞、cap-17 证书。
- `dqi/RESULT.md`–`RESULT4.md`：890Q 结构地板、T 面、864Q 阻塞、BM/decision 评估。
- `chem/RESULT.md`、`RESULT2.md`、`RESULT3.md`、`LOADER_R5.md`、`LAMBDA.md`。
- `intel/RESULT.md`、`RESCAN.md`：公开前沿、28.09487 阈值、top-score 反推。
