# 撤回：loader 门级「省 T」全部是 z=0 假象；官方 verifier 判 no-go，T/pass 仍是 4,089

2026-11-13 · 分支 `codex/dfthcsos-research` · 工作区
`experiments/dfthcsos/20261112_loader_productset/`、`artifacts/20261112_loader_productset/`

## 0. 撤回声明（先读这段）

**上一版本文件写的「4089 → 3881 T/pass，cost 288.90M，15/15 kickmix 验证通过」是错的，现予撤回。**
错因：我的 `words_equal` 检查把 word 寄存器当成 **z = 0** 初态，而 loader 是
`|a>|z> → |a>|z ⊕ delta[a]>`——**z 是任意输入**。官方 verifier 正是这么用的
（`scoreinfra/circuits.py: reset_between_circuits` 在跑 `ANGLE_k` 前把 `batch_{k-1}` 写进 word 寄存器）。
在 z = 0 下「恒零」的门，在 z ≠ 0 下全都不零。

官方 `dfthcsos.verify.evaluate_circuits(..., shots_per_address=1)`：

```
原 14,840 电路： PASS   score = 297,237,044.95   toffoli 14840  qubits 427  λ_eff 46.907378
slim（3881）  ： REJECTED  InvalidCircuits: ANGLE_1: uncorrected phase (measurement kickback)
```

现按官方口径逐项定位、修复、复验，结论是 **no-go**。

## 1. 结论

1. **根因不是「漏了 phase」，是整套替换在 z ≠ 0 时不成立。**
   我原先归为「恒零」/「已被别处持有」的门，全部是**读 word 位**的门：
   - 5 个「恒零 cache CCX」= `CCX w0.7 sel2 q120`、`CCX w0.7 sel3 q121`、
     `CCX w1.7 sel3 q123`、`CCX w2.7 sel3 q124`、`CCX q120 sel3 q125`
     ——控制位是 **word bit 7**，只在 z=0 时为 0（这就是 Maoxin 的 flag 技巧）。
   - 428 个「恒零 CX」= `CX q17 q18`（`w0.6 → w0.7`）这一类，同样只在 z=0 时为 0。
   - 193 个 product CCX **全部**有一个 z 相关的控制位（pivot 里带 flag monomial）。
2. **官方口径下的逐项二分（`bisect_official.py`，`shots_per_address=1`，phase_flipped / 1220）：**

   | 变体 | ANGLE_1 | 其它 |
   |---|---:|---|
   | 原电路 | **0** | 全 0 |
   | 只删「恒零 CX」(428) | **565** | ANGLE_10 305、ANGLE_11 320 |
   | 只删「恒零 CCX」(5) | **206** | 其余 0 |
   | 两者都删（= 上一版 slim） | **565** | ANGLE_10 334、ANGLE_11 303 |

   完全对应「删掉的是 z-相关的门」。
3. **不是 phase 而已，words 也错。** 把 phase 检查临时关掉再跑官方 verifier：
   - 只删 5 个 flag CCX：电路契约过、`toffoli=14,830`，但 **score = inf**（精度门失败，words 错）；
   - 只删 428 个 CX：`ANGLE_1: the selection register changed` ——selection 都被改坏。
   所以「加免费 CZ/CX 修 phase」根本无从谈起：**替换本身不是恒等式**。
4. **只保留 z-safe 的替换 ⟹ 一个都做不了 ⟹ 0 T。** `rebuild2.py` 只允许动
   「控制位全部与 word 无关（address-only）」的门，并要求替换源也是 address-only：
   ```
   15 电路 CCX 4089 -> 4089（saved 0），输出 .kmx 与原文件**【逐字节相同】**
   k=4：268 个 CCX 中 198 个因控制位 z-相关而必须保留（= 193 products + 5 flag cache）
   ```
5. **因此上版所有收益作废**：没有 3881，没有 288.90M，没有「168 products」侧的任何构造。
   **T/pass 仍是 4,089；官方 PASS；score 297,237,044.95。** 最小额外 T = 0（不需要修，只要不改）。
6. 这一结论与 `20261112_loader_opt` §1 的独立实测一致：**gate-level 可删 T = 0（0.0%）**。
   本轮用另一条路径（z-safe 重写 + 官方 verifier）复现了它。
7. 上版 §2 的「精确最小 product 数 = 2799」仍然成立，但**只能当作 z=0 松驰下的上界论证**：
   它说明即使在「z≡0、只看 1220 地址」这个最宽松的松驰里，也丢不掉超过 30/193 个 product。
   它**不能**用来构造电路（本轮已证明 z=0 成立不等于电路成立）。**不作为收益。**

## 2. 定位细节（`phase_debug.py` / `phase_repro.py` / `phase_bisect.py` / `official_probe.py`）

复现链路上踩了两个坑，记录以免重犯：

1. **verifier 的 seed 由电路哈希导出**（`initial_seed(submission_sha256(circuits,...))`），
   改一个门 → seed 变 → HMR 采样序列变。所以「同一个换法有时过有时不过」是假象，
   真正的判据是 phase 是否是 **0/1220**。原电路的每一次 HMR 都有确定的 kickback 抵消，
   任何 seed 下都是 0。
2. **`ANGLE_k` 的初态不是 z=0**：`reset_between_circuits` 在跑第 k 个电路前，
   把 `batch_{k-1}`（数据）写进 word 寄存器，且每跑完一个电路都重写一遍。
   我最初的 per-circuit 检查（z=0）因此得到 `phase_flipped=0/1220`，
   而官方同一电路在 1,220 个地址里有 **580** 个 phase 翻转。
3. 判定口径（`scoreinfra/circuits.py::_check_state`）：
   `read_phase_flipped_across_shots()` 必须全 0、selection 不变、
   **所有非 public qubit 必须回到 |0>**。三条都要过。

## 3. z-safe 重写（`rebuild2.py`，本轮的正确版本）

定义 `zflag[q]`：该 qubit 的函数是否可能依赖 word 寄存器（word 位 → True；selection → False；
`CCX/CX` 的目标取控制位的 OR；`R/HMR` → False）。只有下面三类替换被允许，
每一类都是**对所有 z 成立的恒等式**，且 phase 中性：

| 情况 | 替换 | phase 为什么不变 |
|---|---|---|
| `CCX a b t`，a、b 都 address-only 且 `a&b ≡ 0` | 删除 | t 停在 \|0>；它的 `del_and(a,b,t)` 修正是 `CZ a b if b`，而 `a&b ≡ 0` 使 CZ 永不触发 |
| `CX a t`，a address-only 且 `a ≡ 0` | 删除 | 无测量参与 |
| `CCX a b t`，a、b address-only 且 `a&b` 已被某个**活着的 address-only** qubit 持有 / 或等于若干 address-only monomial·地址位·1 的 GF(2) 和 | 换成 1 个或多个 `CX`（常数项用 `X t`） | 纯 XOR，无测量参与 |

结果（`rebuild2.py` 输出）：

```
k= 0 CCX 292 -> 292   k= 4 CCX 268 -> 268   k=14 CCX 267 -> 267
TOTAL CCX 4089 -> 4089 (saved 0)
k=4：zeroCCX 0 + cx1 0 + cxN 0；zeroCX 0；kept-because-z 198
输出 kmx_slim2/ 与原 kmx_maoxin/ 逐字节相同
```

即：**Maoxin loader 里没有任何一个 T 能靠「换免费 Clifford」拿掉。**

## 4. 官方验证（`official_check.py`，`shots_per_address=1`）

```
原 15 电路 + submission.npz:
  status: PASS
  score        = 297237044.95
  toffoli      = 14840.0        (= 2 * 4089 + 6662)
  qubits       = 427
  lambda_eff   = 46.907378
  verified_shots = 1220
  sha256       = 8cd07c7cbb8dae37
slim(3881)  : REJECTED  InvalidCircuits: ANGLE_1: uncorrected phase (measurement kickback)
```

## 5. 仍然成立 / 已被推翻 的清单

| 上版说法 | 状态 |
|---|---|
| 193 products + 75 cache；`dim V=35`、`dim G0=82`、`dim(V+G0)=117`（z=0 口径） | ✅ 成立（`repro.py`） |
| `min products = \|supp(ker φ)\|`，15 电路合计 2799（k=4 是 163） | ✅ 作为 **z=0 松驰**成立；仅作「上界论证」，**不是构造** |
| 157 个 product 在 G0 里 → 换 CX 省 157 T | ❌ 推翻：那 157 个的控制位 z-相关 |
| 51 个 cache CCX 恒零 → 删 51 T | ❌ 推翻：全是 `w?.7 ∧ sel?` flag monomial，只在 z=0 为零 |
| 37 个 cache monomial 函数重复 → 别名省 37 T | ❌ 推翻：`w0.7∧sel2` 与 `w0.7∧sel3` 只在 `w0.7=0` 时相等 |
| `4089 → 3881`、cost `288.90M` | ❌ 撤回 |
| `words_equal=True` 15/15 | ⚠️ 只在 z=0 下为真，**不是** verifier 的判据 |

## 6. 验证范围

- **做了**：官方 `evaluate_circuits(..., shots_per_address=1)` 跑原电路（PASS，297,237,044.95）
  与上版 slim（REJECTED，ANGLE_1 phase）；用官方路径二分四种变体并给出 phase 计数；
  关掉 phase 检查后确认 words/selection 也被破坏；z-safe 重写生成 15 个 `.kmx`（逐字节等于原文件）。
- **没做**：没有跑 78,080 shots；没有提交；没有 push；没有留下后台进程。
- **不再声称**：任何 loader 的 T 收益。loader = 4,089 T/pass、297.24M。

## 7. 文件

```
experiments/dfthcsos/20261112_loader_productset/
  README.md           本文（已撤回上一版收益）
  loaderlib.py        精确 GF(2) + .kmx 符号重放
  repro.py            复现 193 products / 75 cache / dim V,G0,π(V)（z=0）
  exact_min.py        z=0 松驰下的精确最小 product 数（上界论证，非构造）
  rebuild.py          ❌ 上一版错误的 z=0 重写（保留作反面记录）
  rebuild2.py         ★ z-safe 重写：只动 address-only 门 → 0 T，输出与原文件逐字节相同
  verify_kmsim.py     ❌ 上一版 z=0 的 words_equal 检查（漏 phase、漏 z）
  phase_debug.py      z=0 分类 + 单电路 phase 检查（说明 z=0 为什么看不出来）
  phase_repro.py      复刻官方「预载 batch」序列的尝试
  phase_bisect.py     用官方 seed 做单电路 phase 检查
  bisect_official.py  ★ 走官方 evaluate_circuits 的四变体二分
  official_probe.py   ★ 打桩 `_check_state`，打印每个 ANGLE_k 的 phase 计数
  official_check.py   ★ 官方 verify/evaluate_circuits 跑一个目录，打印 score/T/Q
  extra_checks.py     负对照 + never-read cache + 「加 monomial 套利」穷举（z=0，仅供参考）
  select.py / select_existing.py / droppable.py / alias.py  早期尝试（均基于 z=0，已作废）
artifacts/20261112_loader_productset/
  exact_min.json      z=0 松驰的每电路 min products
  kmx_slim2/          ★ z-safe 输出（与原 kmx_maoxin/ 逐字节相同）
  kmx_slim/           ❌ 上一版被官方拒绝的电路（保留作反面对照）
```

## 8. 一句话给决策层

**loader 门级没有任何「免费」余量：word 寄存器是任意输入 z，凡是我之前当成「恒零/重复」的门
都读 word 位，z ≠ 0 时全部有效**；只允许动 address-only 门时省下 **0 T**，输出电路与原文件
**逐字节相同**。官方 `evaluate_circuits(shots_per_address=1)`：原电路 **PASS，score 297,237,044.95，
T_total 14,840，Q 427**；上一版 slim 被判 `ANGLE_1: uncorrected phase`，而且关掉 phase 检查后
**words 也是错的（score=inf）**，所以不存在「加免费 CZ/CX 修好」的路径。**loader 仍是 4,089 T/pass，
297.24M；本轮收益为 0，不设新目标。**
