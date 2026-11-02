# hmr_square.md：square 块 HMR-native 测量反算试点 —— 否决（机制通、经济不通）

分支 `invsqrt-generator-rebuild`。基线 `narrow_v62.py`（联合解码版，Q=132，
SHA `6f6a144d1115bef0f3c6546c77c22bd803556c34dbd26830d0d57fd32fd9dc3f`，
官方 PASS 1240824.53，见 `joint_decode.md §5`）。
本轮只试点 `R_S3P`（square 逆向，302 toff）：正向保持，逆向镜像改为测量式清理
（temps 逐个 HMR + outcome-adapted 确定性修正，NEG 归属明确）。先小例穷举证明
（全部测量分支的输出/恢复/总相位）PASS 后再进生成器 —— 小例 PASS，
全尺寸计数下界证否，**未进生成器**。不建测试目录/CI；不提交 Kaggle；
不改官方 verifier；不跑官方 200M-shot 验证；不读旧 KMB/tray；不改拟合表；不截位。
证明脚本放仓库外 tmp（`/tmp/hmr_square/`，按 `hmr_cleanup.md §0` 纪律不进产物，
输出同时存 `artifacts/.../hmr_square_*.log` 备查）。

## 0. 结论前置与单线说明

- **结论：否决**（单块试点失败，不牵连 HMR 主线）：square 逆向的逐比特 HMR 修正
  需要 ≥654 Toffoli-like（CCZ），而被省对象仅 302。净增 ≥352 toff（Q×toff +3.8%）。
  `narrow_v62.py`、`prescreen_narrow_v.py` **未动**，REC_SHA 仍为 `6f6a144d…`，
  预筛 A/B/C+DUMP-V + CONTRACT-FULL 在原电路上全部重跑 PASS（§4）。
- **延续单线、无需 fork 的理由**（同 `joint_decode.md §0`）：试点未进入生成器，
  无新电路、无新 SHA、无谱系分叉；另起文件只会制造空线。diff 为空（§3）。
- **对 `uncompute_upside.md` 的修正**（只注释，不改原文）：其 2.1x 上限假设
  "逆向全部改测量式清理（HMR 免费）"。本试点证明：凡携带**进位链**的整数求和块，
  修正非免费且下界可超被省对象 2 倍以上（§2.3）。全反算真实上限 < 2.1x，
  需逐块 ANF 计数重估（§5）。

## 1. 靶子结构（为什么是 square，为什么难）

`W.build_square2`（`width_opt62.py:234`）：U 由 D 重建（CX 免费）→ `isub 256` →
取 `|U|`（CX + 受控 +1，内部 ripple 暂存已 HMR）→ 9 全加行
`cx(U[j],crow) + c-iadd(U → S[j:]) + cx` → 镜像恢复 → 解散重建。
孤立实测：F_S3P `CCX=302` / R_S3P `CCX=302`（`R/HMR` 各 116 为 `iadd` 内部
测量式 uncompute，已 HMR，无再省空间；`hmr_cleanup.md` T2 的 `CCX×2 → init/del`
结构在此**不存在** —— 行内 MAJ/UMA 已是半价，剩下的 302 是 Bennett 级
"由 U 还原 S" 的 coherent 减法，不是门级 AND 镜像）。

HMR 逆向方案：S 的每比特 `hmr(S[j], b_j)` + 修正 `(-1)^{b_j·S_j(U)}`
（论文式 (4) 的 syndrome 相位，`S_j(U)` 为平方第 j 位关于 U（9 位，`|U|≤256`）
的布尔函数；U 在逆向点仍 live（由 x 重建），故修正可表为 U 上的对角门；
`push_condition(b_j)` 包裹，NEG 零引入 —— 见 §2.2）。
`del_and` 的 `CZ` 是一次函数的特例；平方的 `S_j` 含进位链，高次项需 CCZ 级联。

## 2. 证明

### 2.1 机制证明：小例穷举 PASS（先证，证过）

与真块同构的 schoolbook 行（`cx` 中转 + `c-iadd` 行，`proof_sq_hmr.py`）：

- `n=2`（修正全 Clifford；ANF：`S0=u0, S1=0, S2=u1+u0&u1, S3=u0&u1`）：
  4 输入 × 256 shots = 1024 shots，16/16 联合 pattern 全观测，
  输出（u 保留、S 归零）+ 相对相干版总相位差 0，`bad=0`；HMR 逆向 0 toff
 （相对相干逆向 −18/−100%）；块文本无 NEG；double-build `str` 相等。
- `n=3`（首个 3 次项 `S4 ∋ u0&u1&u2 → 1×CCZ`）：8 输入 × 256 shots = 2048 shots，
  64/64 pattern 全观测，`bad=0`；HMR 逆向 1 toff（相对 −35/36）。

```text
n=2: HMR rev toff=18 ops={...} | coherent rev toff=36 | NEG_free=True
n=2: inputs=4 shots=1024 patterns_seen=16/16 bad=0
n=2 SQ-HMR-PROOF PASS
n=3: HMR rev toff=37 ops={... 'CCZ': 1 ...} | coherent rev toff=72 | NEG_free=True
n=3: inputs=8 shots=2048 patterns_seen=64/64 bad=0
n=3 SQ-HMR-PROOF PASS
OVERALL PASS
```

（上表 `toff` 为 fwd+rev 合计口径的同构对比：fwd 同，故差值即逆向差；
`n=2` 逆向由 18→0，`n=3` 由 36→1。全文见
`artifacts/20261102_generator_v2/invsqrt/hmr_square_proof.log`。）
小例与真块的差异声明：小例略去 `|U|` 符号处理与 D 重建——二者皆为
CX/受控±1（Clifford 或内部已 HMR），不改变修正的 ANF 次数结构；
行求和语义一致，故次数下界论证（§2.3）对真块成立。

### 2.2 NEG 纪律

修正门全为对角门（`Z/CZ/CCZ`，`push_condition` 包裹），无 `NEG/neg_if`；
小例块文本断言 `'NEG' not in text` 通过；全尺寸方案同样不引入 NEG
（与成本否决无关，归属明确：NEG=0）。

### 2.3 否决证明：9 位全尺寸 ANF 计数下界（省不出）

`S=U²`（9 位无符号，17 位输出）的逐位 ANF（GF(2) Möbius 穷举，`2^9=512`，
`anf9.py`，全文见 `hmr_square_anf.log`）：共 706 项，其中 deg≥3 项 **654 个**
（`{3:19, 4:87, 5:196, 6:195, 7:115, 8:38, 9:4}`；d1=9 → Z 免费，d2=43 → CZ 免费）。

计费口径（本机实测：`CCZ → toffoli_like=1`，`CZ/Z → 0`，与 `CCX=1` 同权）：

| 口径 | HMR 修正下界 | 被省对象 R_S3P | 净 |
|---|---|---|---|
| 每 deg≥3 项 ≥1 CCZ | **≥654** | 302 | **≥−352（净增，≥2.2x 反超）** |
| 级联口径每项 ≥(d−2) CCZ | ≥2392 | 302 | ≥−2090（~8x 反超） |

```text
TOTAL terms: 706 bydeg: {1: 9, 2: 43, 3: 19, 4: 87, 5: 196, 6: 195, 7: 115, 8: 38, 9: 4}
independent-correction CCZ lower bounds: >=1/term => 654; >=(d-2)/term => 2392; coherent reverse costs 302
```

下界无自适应逃逸（已核验，非一句"镜像故成立"）：
(a) HMR 是 X 基测量，syndrome `k_j` 随机且**不揭示 S 值**——LSB-first
没有经典信息可用（与 `del_and` 的 `CZ` 即时消费同理，但此处无低次可消费）；
(b) 多比特联合 X 测量（先 CNOT 压缩再单 HMR）的修正代数同构，总量不变；
(c) `del_gf2_*_with_scaffold` 式逃逸不适用：GF(2) 乘无进位，而此处高次项
正来自整数进位链，scaffold 去不掉次数。`hmr_cleanup.md` 的 copy 组能省，
恰因 AND 是二次单项式（`CZ` 一次覆盖）；平方是 9 次进位多项式，不可比。

结论：square 块 HMR 逆向全尺寸成本 ≥302+654=956（F+R），相对相干 604
净增 ≥352。**试点否决，不进生成器。**

## 3. diff

无。`narrow_v62.py`、`prescreen_narrow_v.py`、拟合表、QROM/行/S6 调度均未动。
（否决项的 diff 为空是预期状态，如实记录。）

## 4. 成本对比与预筛（实测）

| 口径 | 现状（相干 square，原电路实测） | HMR-square 投影（下界） | 变化 |
|---|---|---|---|
| Q | 132 | 132（修正为对角门，不增宽） | 0 |
| `toffoli_like` | 9168 | ≥9520（+352） | **≥+3.8%（恶化）** |
| `num_instructions` | 85720 | 只增不减（HMR+R+CZ/CCZ 指令） | 增 |
| Q×toff（静态） | 132×9168=1210176 | ≥1256640 | ≥+46464 |
| 文本 SHA / REC_SHA | `6f6a144d…`（不变） | 无（未进生成器） | — |
| maxrel 全域（合同重跑） | 0.8712321494 | 同值（模型未动） | 仍 <1 PASS，最坏 x=1796095 不变 |

预筛证据（EXIT=0，全 PASS；生成器未动，故为"基线 intact"确认，
`hmr_square_prescreen.log` / `hmr_square_contract.log`）：

```text
sha1=sha2=recorded=6f6a144d1115bef0f3c6546c77c22bd803556c34dbd26830d0d57fd32fd9dc3f
PRESCREEN-A PASS
checked 16 samples x 132 qubits: x-recovery ok, scratch all zero: True
PRESCREEN-B PASS
16/16 dphase=0，余量全>0（最小 524594562 @2097151）
PRESCREEN-C PASS
16/16 Vn 精确一致
DUMP-V PASS
checked=3133452 fails=0 maxrel=0.8712321494 worst=(1796095, 3.87e-11)
min_margin_units=105643461.0
CONTRACT-FULL PASS
```

16 样本同各线：`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`。

## 5. 下一步

1. **square 维持相干**：本块关闭 HMR 试点，不重开；`R_S3P` 302 视为整数
   datapath 的诚实代价（与 `gen2_build.md §3` bug-1 的精确性要求一致）。
2. **`uncompute_upside.md` 上限修正**：2.1x（HMR 免费假设）改为分块记账——
   AND 型 temps（copy 组，已兑现 −15.8%）与进位求和型（square 已证负收益；
   A1/R1 行体、QROM decode、温度计待各自计数）分开估计；全反算真实上限 < 2.1x，
   后续任何"逆向改测量"立项须先附 ANF 次数计数（本文件的否决模板）。
3. HMR 主线不受影响：`hmr_cleanup.md` 的 copy 组结论（−2846 toff 实测、
   官方 PASS score 2290413.64→窄线沿用）与本否决正交——copy 组是二次型，
   square 是高次型，机制不同。
4. 若未来 datapath 重写为进位暴露/冗余表示（修正可 Clifford 化），可重估本块；
   属新模型族工作，不在本轮范围（沿用 `uncompute_upside.md` 结论）。

---

证据命令索引（本轮全部手动运行，非测试/CI）：
`uv run python /tmp/hmr_square/proof_sq_hmr.py`（§2.1，日志 `hmr_square_proof.log`）、
`uv run python /tmp/hmr_square/anf.py + masks.py`（§2.1 ANF 表）、
`uv run python /tmp/hmr_square/anf9.py`（§2.3，日志 `hmr_square_anf.log`）、
`uv run python experiments/invsqrt/20261102_generator_v2/prescreen_narrow_v.py --a --b --c --dump-v`（§4，日志 `hmr_square_prescreen.log`）、
`... --contract-full`（§4 maxrel<1，日志 `hmr_square_contract.log`）。
官方 200M-shot 验证：**未跑**（门禁；生成器未变，原 `verify_joint_seed20261031.log` PASS 1240824.53 继续有效）。
