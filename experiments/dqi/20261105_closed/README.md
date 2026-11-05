# 已关闭方向总表（2026-11-05，DQI worktree，分支 codex/dqi-research）

说明：以下方向均经实证关闭（无可提交门数）。原脚本/文档/方案已按要求删除；
每条保留结论、关键证据数字与重开条件。并行线程目录（`20261106_*`）未动。
`experiments/dqi/20261030_public_audit`、`20261105_maoxin_v2` 为既有研究记录，未动。

## 0. 总基线（证据，非方向）

- fd0ef：891Q（840 syndrome + 51 私有），58,336,266 ops，**397,177 Toffoli-like**
 （382,636 CCX + 13,064 CSWAP + 1,477 CCZ），52,166,276 CX 不计费。
- 上游均值 T 396,904.59（Kirill V7 102400-shot 只读报告）；静态-均值 +272.4。
- 总 GM +0.1% 需 **1188T**；0→1 失败 DQI +0.459% / GM −0.153%，需约 1814T 对冲；R0=1.19126。
- convert+unconvert 123.5k/31.1%，unextract 97.6k/24.6%；六峰全 891（scan ~890）。

## 1. QQ-51T standalone 替换（CLOSED）

- kickmix 默认 `ixor/init_gf2_mul(m=12)` = **63T** @0x1053（m4=9T，m8=27T，m24=189T）；
  mod 0x1009 下仍 63T（instr 579→515），故必须手动内联。
- Zenodo doi:10.5281/zenodo.17301475 `gf2_mul_12.txt`（21KB，可重下）：
  1506 CNOT + 51 广义 Toffoli，poly x^12+x^3+1（0x1009）。
  2000 随机 vs 经典 `F.mul` **0 失配**（解出可逆输出置换）；
  m=2/m=4 全量通过；m=3 需输出旋转 `(1,2,0)`（各文件 C 编号有偏移，不影响计数）。
- 发射器（2 瞬态 ancilla + 输出 SWAP）：**51 CCX + 2652 CX + 6 SWAP，Q=38**；
  m=4 量子级 Simulator 64 随机 0 失配 PASS（该测试曾抓到多目标扇出顺序 bug，
  证明其敏感性；修复：CCX 前后各扇出一次，CCX 数不变）。
- 基变换 0x1053↔0x1009：58/59 CNOT，往返 + 同态各 200 PASS（纯 CNOT，0 Toffoli）。
- 否决证据：fd0ef 细块 inverse12 products **25 CCX ×169（全同）**/norm 15/inv24 42/70、
  multiply v **99 CCX ×12**、full_head_product 126/168/210；
  **全电路无 63-CCX kickmix 形核**（kickmix `gf2_mul` 标记 0 个，并行线程独立确认）；
  multiply v 最密 600 行仅 10 CCX / 72 线（分布式 tower 算术，非通用乘法器）；
  25T products 块已在 Winograd 下界（2m−1=23）附近，优于 51T；
  +2 ancilla 在 Q 峰 891 下无零代价位（+1Q 需 ~889T 回本）。
- 结论：无 drop-in 目标，关闭。
- 重开条件：生成器级重建（整段转表示 + 重综合），或 EEA 块重综合（并行线程方向）。

## 2. strict 乘积复用（CLOSED）

- 58M 行扫描：去重控制对 21,560；复用对 16,513。
- 2 次 × 跨度 [133k, 367k] 候选 111 个 → **111/111 DIRTY**（11.5 秒全量）。
- 短跨度 [100, 133k) 1969 候选抽 300 → **0 CLEAN**。strict 规则全尺度死亡。
- 111 候选与 R41 的 45 个对零重叠（全是新机会，但全脏）。
- 结论：无需重扫。重开条件：无（需 solver 证明，见 3）。

## 3. 跨时间乘积证明 / 锥枚举（CLOSED）

- K12 窗 [50421627, 50581695]：665 触线（CCX 20 / CX 540 / CZ 103 / SWAP 2），
  0 guarded 改值；后向切片 **27 AND + 25 入口线**，全挤在窗口前 601 行（0.4%）；
  方法（无条件片段回走 + HMR-clean 载体 + 闲置检查）已验证可行。
- 但全锥 nổ：`q861 q847` → 885 线 / 21.5 万 AND / 1 万 guarded；
  16M 浅候选同样 885 线 / 14.5 万 AND。**解码器全程 ~885 线存活，任何回溯锥 = 全电路**。
- 结论：穷举证明结构性不可行。重开条件：R43 式单链 + CP-SAT（缺 Busy 管线）。

## 4. 死门删除（CLOSED，附机制验证）

- 全电路 liveness DCE：382,636 CCX 中 **156 死 + 48 死 CSWAP**（`X` 翻转保持跟踪修正版）。
- naive 删 12 站候选（CCX/…/HMR 三行结构，断言 pattern 全过，静态 −12）：
  配对 probe（256 固定 w=18 + 256 ordinary，同 seeds）：value 0/0，
  **phase 130/256 + 112/256**（base 全 0），mean T Δ −12.0。
  恰为 m=1 kickback 丢失的理论预言——证伪"无需纠正"版，证实 kickback 模型。
- CZ 纠正版（删 CCX + `CZ a b if m`，−1 billed）：156 中 taint 干净 7 个，
  但 a/b 在纠正前全被自身 HMR 销毁；m_a/m_b 各下游用 22 次（HMR→R 不可）；
  无干净 ancilla 可借（dense 区）；移 HMR 级联 22 个立即使用。**0/156 可提交**。
- 附带定论：全电路门类型普查（58M 行全覆盖）无 H 门，初态 |0> 下全局恒为基矢态，
  X 测量恒均匀——CZ 纠正成立的前提成立；卡在 a/b 即时销毁。
- 结论：微观删除路终结。重开条件：无（除非 solver 级证明或生成器）。

## 5. fhp / mv / inverse / aligned / head 剖解（CLOSED）

- full_head_product：126/168/210 × 转换/反转换镜像对（#0≡#3 等，跨镜像共享 6 对），
  每块 24 线，块内仅 6 不同对（如 `(q792,q804)×72`，目标轮转）——扇出假设已否
  （控制全程 churn，相邻 71 间隙 0 干净）；常量假设已否（q0 累加器跨度内写 1104 次）。
- multiply v ×12：99 CCX + 6294 CX，27 线，top `(q72,q48)×40` 同上 churn（0/39 干净）。
- inverse12 norm/products ×169：15/25 CCX（全实例门数完全一致）；
  inverse24 norm/products ×29：42/70；aligned_route ×52 CSWAP bank
  （单稳定控制如 `q23`×192，192 distinct 对——per-pair 独立 AND，CSWAP 已是紧的下界实现）；
  head_pivot ×24 同构（12 CSWAP 单控制）；head_phase ×3（42 CCX + 12 HMR + 1452 条件 CZ，
  R41 签名区但 top 对 dx=dy=263，23 间隙 0 干净）。
- 结论：全系生成器级已极小（循环展开 distinct products / 紧路由）。重开条件：生成器。

## 6. peephole 对消家族（CLOSED）

- CCX 0/382,636（并行线程，精确对易规则，含 guard 稳健性自检）。
- CSWAP 0（2517 间隙全杀）、CCZ 0（609 全杀）（span 上限 200k，INFO/APPEND/BIT 不杀，
  PUSH 作用域保守杀，PUSH 内端点视为条件即作废）。
- 结论：闭合。重开条件：无。

## 7. e87b 叠加（REJECTED）

- Atakan V9 五个失败 fixture + Busy 复核 1 个失败 shot；已知不干净的近似编辑。
- 结论：不移植。重开条件：无。

## 8. QQ 频次（上限口径，仅供参考）

- kickmix `gf2_mul` 标记全电路 0 个（并行线程独立确认）；convert 60.8k/63 ≈ 965 只是
  纯乘假设上界，不可作数（实际为 tower 件）。

## 未动 / 阻塞项（需外部输入，非本轮可解；无保留脚本）

- R52 15 链移植（−15 exact，已有官方背书）：缺链条明细或 748b KMB（本地无 Kaggle 认证）。
- convert/unconvert 融合 + MBU 化反向 EEA：需生成器。
- 宽 891→890：需 liveness/生成器（并行线程在跟，勿重复）。
- 近似剪枝（R50 式）：需失败风险预算 + 全验证 salt。
- P1 十四乘积证明：K12 方法已验证可行（单窗界定 27 AND + 25 线），缺 solver 规模证明。

## 方法备忘（可复现，无保留代码；3–5 行/项）

- KMX 导出→文本分析→重载：`Circuit.from_file(kmb)` → `to_file(kmx)`（~58M 行，
  内存 ~0.8GB，~5 秒）；INFO_TAG `@enter/@exit` 即 mark 边界，可定位块并数门。
- 候选构建：KMX 文本按行删/插 → `from_file(kmx)` → `operation_statistics` 对数；
  配对 probe：`sample_shots` 同 seeds 跑 base vs 候选（固定 w + ordinary 各 256），
  比 value/phase/mean-T；通过后才值得跑全验证（`scripts/manual_verify.py dqi <path>`）。
