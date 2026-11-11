# `e9f54be3` −55 差分审计（相对 Public Frontier `4432ec5f`）

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**纯静态审计**——只读两电路 kmx，不构建候选、不运行验证器。
方法沿用 `20261108_frontier_audit`（kmx 解析 + `INFO_TAG @enter/@exit` 栈顶阶段标记，
付费门 = CCX/CCZ/CSWAP/CCX_CARRY），实现改为流式（58M 行不驻留内存，不改变计数口径）；
复算 frontier 侧与审计表逐门一致（见 §1）。不重复六项 closed 切口
（仿射/结构/脏借用/广播/scan/R，见入口 README），本轮是静态差分新切口。

固定输入（只读，未复制/修改）：
- `4432ec5f`：主仓库 `artifacts/20261108_public_frontier/release/dqi.kmb`
 （SHA-256 `4432ec5f…ce431`，892Q，505M）。
- `e9f54be3`：主仓库 `artifacts/20261110_public_candidates/ozer_v91/submission.zip`
  内 `dqi.kmb`（SHA-256 `e9f54be3…e969bc4`，529,242,404 B；gengsr/Ozer-v91/Maoxin
  三包同字节，见主仓库 `references/public-baseline.json` 与
  `submissions/20261110_gengsr_252268/README.md`；作者数静态 395,586，均值 T 395304.76，
  作者日志 DQI 374686873086.94，102400 shots 0/0 失败，本机未重跑）。

## 1. 阶段差分表（精确到门类）

`stage_census.py` 输出（`artifacts/20261110_e9diff/stage_census.json`）：

| 阶段 | frontier paid | e9 paid | Δpaid | ΔCCX / ΔCCZ / ΔCSWAP | Δops | 落点说明 |
|---|---:|---:|---:|---|---|---|
| convert | 60,687 | 60,663 | −24 | 0 / 0 / **−24** | +48 | 模板 A ×2 位点（§2） |
| extract | 59,169 | 59,169 | 0 | 0 / 0 / 0 | 0 | 无变化 |
| scan | 44,275 | 44,275 | 0 | 0 / 0 / 0 | 0 | 无变化 |
| synthesis | 31,635 | 31,635 | 0 | 0 / 0 / 0 | 0 | 无变化 |
| unconvert | 62,558 | 62,534 | −24 | 0 / 0 / **−24** | +48 | 模板 A ×2 位点（convert 镜像） |
| unextract | 96,888 | 96,881 | −7 | **−14** / **+7** / 0 | −7 | 模板 B ×7 位点（§2） |
| unsynthesis | 40,429 | 40,429 | 0 | 0 / 0 / 0 | 0 | **无变化**（任务预期外） |
| **总计** | **395,641** | **395,586** | **−55** | **−14 / +7 / −48** | **+89** | e9 文件大 773 B（+89 净免费门） |

复算校验：
- 本轮 frontier 侧各阶段 paid（convert 60687 / extract 59169 / scan 44275 /
  synthesis 31635 / unconvert 62558 / unsynthesis 40429 / unextract 96888）与
  `20261108_frontier_audit` 审计表逐项一致；门类细分一致
  （如 unsynthesis 40143 CCX + 262 CCZ + 24 CSWAP）。
- cross-check：convert +48 / unconvert +48 / unextract −7，加总 +89，
  与总 ops 差 58269328 → 58269417（+89）一致；与 kmb 文件 +773 B 方向一致。
- `unread_ccx_before_hmr` 两侧均为 **0**（Kirill 窥孔在 frontier 已清零，
  e9 无新增该类；见 `20261108_frontier_audit/README.md` §1.2）。
- 与任务预期的差异：**−55 不在 unsynthesis**（0 变化），而在
  convert/unconvert（对称 −48 CSWAP）与 unextract（净 −7）。

计分换算（`20261110_arch_review` §0 口径）：静态 −1 门 ≈ 947,843 分；
−55 门 ≈ −52,131,365 分（≈ −0.0139%）。作者分差
374686873086.94 − 374735446628.53 = −48,573,541.59（≈ −0.0130%），
与静态估计同量级（差约 3.6M，来自均值 T vs 静态口径；R 同为 1.19126046）。

## 2. 差分位点形态分类（11 hunks，全为新模板）

`paid_diff.py` 按阶段对付费门序列贪心对齐（编辑量小，O(N)重同步），
11 个 hunk（`artifacts/20261110_e9diff/paid_diff.json`；convert/unconvert 的 E 侧
自动锚点落在 66k 行无付费门沙漠之后的重同步门，已人工按同行号窗口核验修正，
见 §2.3）。**无一处属于四类旧形态**（字面复用 / 测量窥孔(Kirill类) /
规范对匹配(Syed类) / 旧模板复现）：

### 模板 A：CSWAP-双目标测量消除（4 位点 × 12 门 = −48 CSWAP，新窥孔类）

谱系定位：Kirill 谱系的新变体。Kirill 窥孔是
`CCX a b t; HMR t` → 条件 CZ（单目标测量）；本模板是
**CSWAP 双目标都被紧邻测量** → CX + 条件 CZ + 经典 XOR。
与 Ozer/Isabe 字面复用无关（无跨位点双胞胎复用），与 Syed 仿射无关。

精确改写规则（每对 `(x, y)`，控制 `c`；4 位点控制线均为 `q18`）：
```text
旧：CSWAP c x y
    …（同组其他对的 CSWAP/HMR 交错，其间无门触碰 x/y）
    HMR x bx
    HMR y by
新：CX x y
    HMR x bx;  CZ c y if bx
    HMR y by;  BIT_INVERT bx if by
```
每对净：−1 付费 CSWAP，+1 CX +1 条件 CZ +1 经典 XOR（净 +2 ops）。
每位点 12 对：−12 paid，+24 ops（与 census §1 的 +48 ops/阶段吻合：
旧体 60 ops → 新台 84 ops）。

4 位点（F=frontier kmx 行号，E=e9 kmx 行号；convert 内漂移 0/+24，unconvert 内漂移 +48）：
| # | 阶段 | F 旧侧 CSWAP 行 | E 新侧对应行 | 备注 |
|---|---|---|---|---|
| A1 | convert | F:16137584–16137595（12×`CSWAP q18 …`） | E:16137584–16137667（12×CX + HMR/CZ-if/BIT 序列） | 首窗：`CSWAP q18 q857 q22` 等；E:16137584 `CX q857 q22` 起 |
| A2 | convert | F:16287848–16287859（同 12 对逆序） | E:16287872–16287931（同模板，漂移+24） | A1 的逆序镜像（uncompute 侧） |
| A3 | unconvert | F:42154384–42154395（12×`CSWAP q18 …`，不同线号） | E:42154432–42154515（同模板，漂移+48） | convert 的镜像阶段 |
| A4 | unconvert | F:42304623–42304684（A3 逆序镜像） | E:F+48 对应行（同模板） | A3 的逆序镜像 |

上下文签名（旧侧 62 行窗）：`CX` 24 + `CCX` 1 + `CSWAP` 12 + `HMR` 24 + `BIT_STORE0` 1；
新侧把 12 CSWAP 换成 12 CX，并在每个 HMR 后插入条件 CZ / 经典 XOR，
共享的经典 tail round（12×BIT_STORE0 + 12×BIT_INVERT-if）两侧相同。
等价性说明：经典比特重映射（`bx⊕=by`）与相位前馈（`CZ c y if bx`）联合作用；
完整切片证明超出本轮静态范围，实证锚点为作者 102400-shot 0/0 PASS 日志
（本机未重跑，见 §5）。

### 模板 B：相位回踢吸收 sandwich（7 位点 × 净−1 门 = −7，新模板）

谱系定位：新模板，不属于 −38 谱系任一类。被删两 CCX 字面相同是
compute/uncompute 对（同位点内配对消除），不是 Ozer/Isabe 跨位点保留复用；
无 HMR/R 参与，不是 Kirill 测量窥孔；字面已相同，无需 Syed 仿射规范化。
本质是相位多项式共轭恒等式（与 `decoder_struct` §1 窄返回擦除同家族，不同位置）：
```text
CCX(a,b;t); CZ(c,t); CCX(a,b;t)  ⟺  CZ(c,t); CCZ(a,b,c)
```
（`CCX` 自逆，共轭把 `CZ(c,t)` 映为 `CZ(c,t⊕ab) = CZ(c,t)·CCZ(a,b,c)`。）
每位点净：−2 CCX +1 CCZ（−1 paid，−1 op）。

7 位点（全在 unextract；F/E 漂移 +96；旧侧窗签名 `CX`19+`CSWAP`6+`HMR`3+`X`12+`R`2+`CCX`6+`CZ`3，
新侧 `CCX`6→4、`+CCZ`1、`CX`19→18）：
| # | 被删（F，2×同 CCX） | 新增（E，1×CCZ） | F 行 | E 行 |
|---|---|---|---|---|
| B1 | `CCX q874 q856 q881` ×2（夹 `CZ q846 q881`） | `CCZ q874 q856 q846` | F:52712906–52712908 | E:52713001–52713003 |
| B2 | `CCX q863 q877 q854` ×2（夹 `CZ q852 q854`） | `CCZ q863 q877 q852` | F:53305438–53305440 | E:53305533–53305534 |
| B3 | `CCX q891 q890 q842` ×2 | `CCZ q891 q890 q885` | F:53862198+ 窗内 | E:53862292+ 窗内 |
| B4 | `CCX q888 q870 q886` ×2 | `CCZ q888 q870 q861` | F:54381951+ 窗内 | E:54382044+ 窗内 |
| B5 | `CCX q855 q840 q865` ×2 | `CCZ q855 q840 q873` | F:54864140+ 窗内 | E:54864232+ 窗内 |
| B6 | `CCX q858 q882 q862` ×2 | `CCZ q858 q882 q860` | F:55308652+ 窗内 | E:55308743+ 窗内 |
| B7 | `CCX q883 q848 q871` ×2 | `CCZ q883 q848 q853` | F:55715870+ 窗内 | E:55715960+ 窗内 |

注：`paid_diff.py` 启发式曾把 B2/B6 标为“字面复用”（窗口内字面双胞胎计数把
compute/uncompute 对自身计入），已人工核验 7 处为同一 sandwich 并在
`paid_diff.json` 中统一更正为新模板（`by_label: {新模板: 11}`）。
完整窗口对照见 §复现（`inspect_windows.py`）。

### 分类汇总

| 形态 | 数量（位点/门） | 示例行号 |
|---|---|---|
| 字面复用（Ozer/Isabe 类） | 0 / 0 | — |
| 测量窥孔（Kirill CCX-HMR 类） | 0 / 0 | —（`unread_ccx_before_hmr` 两侧=0） |
| 规范对匹配（Syed 仿射类） | 0 / 0 | — |
| 新模板 A（CSWAP-双目标测量消除） | 4 位点 / −48 CSWAP | F:16137584, F:16287848, F:42154384, F:42304623 |
| 新模板 B（相位回踢 sandwich） | 7 位点 / −14 CCX +7 CCZ | F:52712906, F:53305438（+5 处见上表） |

### 2.3 方法注记（对齐锚点）

convert/unconvert 的 4 个 hunk 与其后最近付费门之间各隔一片约 66.9k 行的
无付费门沙漠（`awk` 核验 F:16137644–16204526 内 0 个 CCX/CCZ/CSWAP，
E 侧对应区间亦 0 个），故 `paid_diff.json` 初版 E 自动窗口落在沙漠后重同步门。
报告中 E 替换窗均改用**同行号（+阶段漂移）直接对照**并逐窗验看
（A1/A2 全窗、A3 前 74 行、B1/B2 全窗），计数与 census  reconcile。
`inspect_windows.py` 可复现全部 11 窗对照。

## 3. 差分模板在 e9 上的残余空间：closed（0/0）

`residual.py` 单遍流式扫描 e9 全电路 58,269,417 ops（`residual_e9.json`）：
- (a) 模板 A 同形残余（CSWAP 后 80 行内双目标均被 HMR、其间无其他触碰）：
  **0 处**（分阶段亦 0）。frontier 的 48 处同形位点已全部改写，无同类未改位点。
- (b) 模板 B 严格同形残余（CCX…单CZ(c,t)…同CCX，t 无其他触碰，15-op 窗）：
  **0 处**。7 处已全部改写。
- 净省估算：无残余 → **0 门（closed）**；若将来出现同类位点，
  每门仍按 ≈947,843 分计（模板 A 每对 −1 门≈−0.95M 分；模板 B 每位点 −1 门）。

扫描器召回验证：同一脚本跑 frontier kmx（`residual_frontier_check.json`），
找回 **(a)=48（convert 24 + unconvert 24）、(b)=7（unextract 7)**——与改写数精确一致，
且 (b) 预测的 7 个 `CCZ a b c` 与 e9 实际新增逐字相同
（如 `CCZ q874 q856 q846`）。严格谓词下召回率 100%，e9 侧 0/0 残余为真 closed，
不是扫描器漏报。（放宽谓词如允许 t 被 CX 触碰则超出本模板语义，不在本轮口径内。）

## 4. 892Q 宽度冗余判断（对照 SomeJoint 889Q 画像）：无冗余

e9 分阶段 qubit 触及（`residual.py` 同遍统计，正则 `q(\d+)`）：
extract/synthesis/unsynthesis/unextract 均为 892 distinct（max 891）；
convert/unconvert 891（max 891，缺一线）；scan 851（max 890）；
`initial`/`mask_projection`/`uninitial` 840。**全电路 892 线均有触碰，
峰值 892 由 extract/synthesis/unsynthesis/unextract 四阶段共同顶住**——
与 `20261106_syed_v9/README.md`“六个阶段都达到 892Q，scan 峰 891Q”一致
（本轮 scan 实测 distinct 851/max 890，guide 峰口径略异但结论同：峰值非局部）。

SomeJoint 889Q 画像（文献对照，非同族）：
- SomeJoint `quantum-circuits-22-77-local-gm-889-qubit-dqi` 是 streamed decoder
  路线（research-map；CREDITS：SomeJoint streamed decoder → hengck23 近似解码器
  → Kirill 组合），带嵌入生成器，适合从源码研究 DQI，但**与当前 892Q Syed 系
  不是同一解码器族**。
- 同族 889Q 重建实测（`20261106_phase_recovery/README.md` §2）：
  prior backhalf 889Q 静态 459,792（+9.2%）、decode_q8q9 889Q 486,571 等，
  T 高 10%–16%；−3Q 省 ≈3×8.41亿 ≈ −25亿，远抵不过 T 惩罚（+400亿量级）。
- 宽度下探 closed 史：`20261106_closed` §1.14（891→890：`true_peak_live=891`，
  `never_live=[]`，无死线）；`syed_v9` §“892→891 简单载体回收”37/584 区间无
  全程闲置私有线；入口 README 汇总 52/52 全忙。本轮 e9 画像一致：无死线。

结论：**892Q 无宽度冗余**；−55 全部来自门模板（Q 保持 892），无宽度变化；
889Q 是另一解码器族的存在性参考（−3Q 可行但 T 代价高），不是当前族的压缩目标。
`arch_review` 方向 D（Q 高水位＋串行化）仍是唯一未经系统探索的区域，
但本轮差分未提供 −Q 切口。

## 5. 验证范围声明

- 本实验**未构建候选、未运行官方验证器**（DQI 全量 102400-shot 未触发；
  `data/competition` 验证器未改动、未调用）。
- 数字来源：本工作区 `artifacts/20261110_e9diff/stage_census.json`、
  `paid_diff.json`（人工核验修正）、`residual_e9.json`（+ frontier 召回对照）。
- 作者数引用：主仓库 `references/public-baseline.json`（e9f54be3，静态 395,586，
  均值 T 395304.76）、`submissions/20261110_gengsr_252268/README.md`、
  gengsr 包内 `verify_results.json`（DQI 374686873086.94，0/0 失败；本机未重跑，
  沿用作者日志）。
- 谱系引用：`20261108_frontier_audit/README.md`（−38 拆解）、
  `20261110_arch_review/README.md`（定价/方向）、入口 README（六项 closed）、
  `20261106_phase_recovery/README.md` §2（889Q 重建）、
  `20261106_syed_v9/README.md`（892Q 达峰/891 尝试）、
  `artifacts/20261108_public_frontier/source/`（Syed V10/V11 方法链）。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix）；中间 kmx 落盘
  `/private/var/folders/.../T/dqi_e9diff/`（非仓库），仓库内仅
  `experiments/dqi/20261110_e9diff/` + `artifacts/20261110_e9diff/`。

## 复现

```bash
.venv/bin/python experiments/dqi/20261110_e9diff/stage_census.py
.venv/bin/python experiments/dqi/20261110_e9diff/paid_diff.py
.venv/bin/python experiments/dqi/20261110_e9diff/inspect_windows.py  # 11 窗全对照（输出大）
.venv/bin/python experiments/dqi/20261110_e9diff/residual.py
```
