# Round 3 总索引（2026-11-18）

**一句话：公开件已到算法下限；今晚提交 28.1807（银牌）；金牌 28.71339 需要新一代解码器或新的化学因子分解。**

## 1. 今晚在提交什么

| | |
|---|---|
| 包 | `submissions/20261118_281806/`，GM **28.18065942104198** |
| 成员 | 18 个，sha256 全部与 manifest 一致，zip sha `2271b861…`（85,016,504 B） |
| 三腿 | invsqrt `563d0583` 74,560.91 / DQI `575b043f` 346,409,762,292.72 / chem `a73b25d2` 294,643,137.73 |
| 验证 | 未改动的官方 verifier 全量 PASS（686 s / 160 s / 32 s），DQI 0 value / 0 phase |
| 提交 | `submit_at_reset.sh`，UTC 00:02（北京 08:02）自动提交；失败自动改走本地 zip |
| 预期 | LB **28.1807**（银牌线 28.14702 之上；金牌线 28.71339 需要单腿 −5.46%） |

salt 实测（`zhuating/qcc-dqi-salts`）：4 个 salt 里 3 个 0/0，`s2` 有 1 个 value error
（rep_factor 1.1913→1.1967，整腿 +0.46%）。58464076 用同一个 `dqi.kmb` 拿到 LB = 本地 default GM，
所以预期榜单干净。

## 2. 本轮实测关闭的 14 条轴

| # | 轴 | 决定性数字 | 记录 |
|---|---|---|---|
| 1 | 两个大 T 簇 = initial shift | 参考 loop 30,912 T 但 CX/CCX=30.3 vs 簇的 61.8；tape CSWAP opcode=0 | `dqi_refshift/`、`dqi_align/` |
| 2 | 块级冗余 | 342/626/140 块内容全不同，可删 T=0 | `dqi_align/` |
| 3 | 乘法秩 <42 | μ₂(12)=42 最好已知；33 是 F₄ 的数；张量实测=GF(2¹²) 乘（0x1053） | `dqi_multrank/` |
| 4 | 归一化 divstep | 原型与 textbook EEA 一致率 0%；真实参数贵 12× | `dqi_normeea/`、`dqi_gen/` |
| 5 | 数组冗余（2 数组） | 每个 word 都被读（最少 798 次）；参考 2 数组 3,672 行/趟 ≈ tape 3,647 | `dqi_arrays/` |
| 6 | qubit 换 uncompute | 反向 EEA 170,528 T，打平上限 +326 q，最小可持有 420 q → 差 2.4–2.7× | `dqi_gfree/` |
| 7 | 参考 2 数组更便宜 | 每行贵 1.5×（63/75 vs 42 T），行数相同；照抄 960k T（GM 19.0） | `dqi_arrays/` |
| 8 | Chien 更便宜 | 4,025 ×(10 CCX + 1 CCZ)，12-control 合取下限 | `dqi_chien/`、`dqi_surgery/` |
| 9 | chem brot/C/J/loader | brot=7 error_2 大 21×、λ +54%；loader 乘积下限 188 | `chem/`、`loaders/` |
| 10 | `reset` 省 uncompute | `reset`=`R`(Z 基)；纯数据 0/16 翻转，`flip_if_*` 的 flag **12/16 翻转** | `dqi_gen/` |
| 11 | chem loader uncompute | 已是 MBUC（77 HMR + 77 CZ_IF，0 T） | `dqi_patch/`（现场分析） |
| 12 | 反向多出的 367 行 | = pool（word 70–73）清理，契约要求 | `SUMMARY_R3.md` §9 |
| 13 | chem 形状 (R,B,C) | 秩 ≥1,144 下 (8,143,44) 的 T·Q 最低（6.279e6） | `SUMMARY_R3.md` §准 |
| 14 | chem C=45 / 其它因子分解 | 公开 (8,143,45) 10.413×；`M8x156x60_b8` 1.137×、`B239_b8` 1.353×（都更差） | `chem_pub/`（`zhuating/qcc-chem-pub-eval`） |

**tape 的 Toffoli 已 100% 闭合**：CCX 362,012 = EEA 两趟 321,762 + Chien 40,250；
CCZ 5,977 = Chien 4,025 + 反向 1,952。没有第 4 类。
EEA 的模型：`3 数组 × 35 步 × 36 字 × 42 T = 158,760/趟`，实测 3,647 行/趟 × 42 = 153,174 —— **差 1.3%**。

## 3. 榜单结构（反解，Q=890，另两腿用我们的）

| 名次 | LB | DQI T | vs 我们 |
|---:|---:|---:|---:|
| 1 | 31.42723 | 264,691 | −27.9% |
| 3 | 30.28512 | 295,780 | −19.4% |
| 6 | 29.97900 | 304,934 | −16.9% |
| 10 | 28.92557 | 339,478 | −7.5% |
| 公开件 | 28.18066 | 367,116 | 0 |

即使进前十也要 EEA 再省 28,511 T（9%）。公开负结果台账（295 条、16 位参赛者）也停在 28.0–28.5。

## 4. 下一轮唯一还有量级的事

**A. 新一代 DQI 解码器**（数周）
公开 BM（arXiv:2610.22367）是 440k T / 1,837 Q，Q²T 比我们差 2.47×；参考 5.7M T。
要 31.4 需要：**每步 2 个逻辑数组、35 步（t=35 是下界）、无每步除法、Chien 11 T/位置、Q≤890**。
落地通道已就绪：`dqi_patch/splice.py` + `k_patch`（null-splice 逐字节相同），25 分钟打包。

**B. chem 的 λ 已证明不可动**
`Λ = lambda_h1 + lambda_h2`，`lambda_h1 = Σ|eig(h1_prime)|` 由 Hamiltonian 的 LCU 归一化决定。
三份公开因子分解实测 Λ = 283 / 287 / 290，**精度好一倍也压不下来**。关闭。

## 5. 工具与坑

* **跑官方 verifier**：`sys.executable` + `PYTHONPATH=COMP/kickmix:COMP/verifiers` + `cwd=COMP/verifiers`。
  系统 python 的 kickmix 没有 `Circuit`，`/usr/bin/python3` 也不行。
* **Kaggle script 内核只带一个文件**：辅助模块要内联或运行期写出。
* **内核退出前删 479 MB tape**，否则 `kaggle kernels output` 会超时。
* `scripts/kgpu.py`（CPU-only 内核）、`scripts/gm.py`（三腿 GM）。

## 6. 目录

* `FINAL_R3.md` —— 本轮完整判定（14 条轴、Λ 分析、ceilings）
* `FINAL_NOTE.md` —— 行数模型的最终对账 + 2 数组假设的裁决
* `SUMMARY_R3.md` —— 逐节记录（含每条轴的决定性测量）
* `WORKPLAN_31.md` —— 31.4 路线工作单（含已否证的假设）
* `RECORD.md` —— 逐条实测日志（631 行）
* `*/RESULT.md` —— 25 条研究线的独立结论
