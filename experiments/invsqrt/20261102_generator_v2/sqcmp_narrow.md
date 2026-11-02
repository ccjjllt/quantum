# sqcmp_narrow.md：降宽收尾（square 与温度计比较器窄化）—— 双否决，生成器不动

分支 `invsqrt-generator-rebuild`。基线 `width_opt62.py`（HMR 版，Q=149，
SHA `0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d`，
官方 PASS score 2290413.64，见 `hmr_cleanup.md §4–§5`；变体线另有 BOTH/A18，
本任务只动主线 HMR 版，变体文件不动）。本轮只评估 square（S=U²，
U 由 D 重建→|U|→9 全加行进 S）与 lz 温度计比较器（21 flip + 优先编码），
不碰 A1/R1/S6/查表/窗口/恢复钩子；不读旧 KMB/tray；不数值拟合、不截位；
不跑官方 200M-shot 验证；产物只在
`experiments/invsqrt/20261102_generator_v2/`（本文一件新增）。
`artifacts/` 无新文件（kmb/stats 仍为 HMR 版产物，待送验时重建）。

## 0. 文件取舍（说明理由）

- **不新建 `sqcmp62.py`，延续 `width_opt62.py` 单线**：与 `a1narrow.md §0` /
  `s6narrow.md §0` 同一理由——`width_opt62.py` 已是带 STAGE 标记的工作线，
  `prescreen_width_opt.py` / `width_liveness.py` 均 `import width_opt62`。
  新建文件需复制 ~900 行并重接三处引用，double-build 谱系分叉风险 > 收益。
  延续单线，SHA 谱系清晰。
- **结论是不改生成器**（见 §3 双否决），故 `width_opt62.py` 本轮零改动，
  `narrow_proof.py` 零新增（§1 理由），`prescreen_width_opt.py` 零改动
 （REC_SHA 仍为 `0075e006…`，见 §4）。
- **单立本文，不并入 `width_opt.md` / `a1narrow.md` / `s6narrow.md` /
  `hmr_cleanup.md`**：前四篇分别是 R1 生效 / A1 否决 / S6 生效 / HMR 生效的
  审计定稿，改数字会破坏其证据链；本轮是收尾双否决记录，独立成篇保留。
- **探针脚本放仓库外 tmp**：`sqcmp_probe.py` 为手动证据命令（非测试/CI），
  按纪律不进产物；输出粘贴 §2 即证据链完整。

## 1. 证明（未新增，说明理由，先行结论）

工作流按 `a1narrow.md §1`：**证明只管等价性，不管宽度——宽度由 §2 孤立探针裁决**；
否决准则：**窄赢当且仅当 extra 更小，平局即否决**。

§2 实测 square 窄 extra 18 > 通用 17（最大行；短行更亏），lz 手写窄 extra 41 >
通用 21（峰值行；切片版峰值持平 21）。两项均未满足“明确降 extra”，
按准则直接否决，**不进入证明与生成器替换**。故 `narrow_proof.py` 本轮零新增；
原证明重跑仍 PASS（基线未动证据）：

```
uv run python experiments/invsqrt/20261102_generator_v2/narrow_proof.py
uncontrolled n=3: 64/64 ok
controlled-via-copy n=3: 128/128 ok
split noff=2 nlow=2 nhigh=3: 256/256 ok
split-reverse noff=2 nlow=2 nhigh=3: 256/256 ok
a1sub noff=3 nlow=3 nhigh=2: 512/512 ok
a1roundtrip noff=3 nlow=3 nhigh=2: 512/512 ok
s6inc n=6 k=3: 128/128 ok
s6dec n=6 k=3: 128/128 ok
s6roundtrip n=6 k=3: 128/128 ok
a1two-add 2+2+2: 2048/2048 ok
a1two-sub 2+2+2: 2048/2048 ok
a1two-roundtrip 2+2+2: 2048/2048 ok
NARROW-PROOF PASS
```

## 2. 宽度实测（孤立单行探针，先测量后决策）

探针方法沿用 `a1narrow.md §2`：单行独立成电路，
`extra = num_qubits − base`，全局峰 `= 115 + extra`
（基座 `x22+lz5+coef33+V55=115`）。探针代码在仓库外 tmp，不进产物：
`/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/sqcmp_probe.py`，
`uv run python` 实测原文：

```
generic sq c-iadd9->17: qubits=44 base=27 extra=17 global~132
generic sq c-isub9->17: qubits=44 base=27 extra=17 global~132
generic sq c-iadd9->13: qubits=36 base=23 extra=13 global~128
generic sq c-isub9->13: qubits=36 base=23 extra=13 global~128
generic sq c-iadd9->9: qubits=26 base=19 extra=7 global~122
generic sq c-isub9->9: qubits=26 base=19 extra=7 global~122
narrow-sq coh 9->17: qubits=45 base=27 extra=18 global~133
narrow-sq HMR 9->17: qubits=45 base=27 extra=18 global~133
narrow-sq coh 9->13: qubits=41 base=23 extra=18 global~133
narrow-sq HMR 9->13: qubits=41 base=23 extra=18 global~133
narrow-sq coh 9->9: qubits=29 base=19 extra=10 global~125
narrow-sq HMR 9->9: qubits=29 base=19 extra=10 global~125
abs isub256->U9 (uncontrolled const): qubits=17 base=9 extra=8 global~123
abs c-iadd1->U9: qubits=18 base=10 extra=8 global~123
generic lz flip x22<2^1: qubits=44 base=23 extra=21 global~136
generic lz flip x22<2^5: qubits=44 base=23 extra=21 global~136
generic lz flip x22<2^11: qubits=44 base=23 extra=21 global~136
generic lz flip x22<2^17: qubits=44 base=23 extra=21 global~136
generic lz flip x22<2^21: qubits=44 base=23 extra=21 global~136
sliced-generic lz x[1:22]==0 (m=21): qubits=43 base=22 extra=21 global~136
sliced-generic lz x[5:22]==0 (m=17): qubits=35 base=18 extra=17 global~132
sliced-generic lz x[11:22]==0 (m=11): qubits=23 base=12 extra=11 global~126
sliced-generic lz x[17:22]==0 (m=5): qubits=11 base=6 extra=5 global~120
sliced-generic lz x[21:22]==0 (m=1): qubits=2 base=2 extra=0 global~115
handwritten-zero m=21 (coherent tree): qubits=63 base=22 extra=41 global~156
handwritten-zero m=11 (coherent tree): qubits=33 base=12 extra=21 global~136
handwritten-zero m=5 (coherent tree): qubits=15 base=6 extra=9 global~124
handwritten-zero m=1 (coherent tree): qubits=3 base=2 extra=1 global~116
```

整理表：

| 探针 | qubits / base | extra | 全局等效峰 |
|---|---|---|---|
| 通用 square `c-iadd9→S17`（现 S3P_J0，最大行） | 44 / 27 | **17** | 132（与 `width_opt.md §1` 一致） |
| 通用 square `c-iadd9→S13`（中行） | 36 / 23 | 13 | 128 |
| 通用 square `c-iadd9→S9`（最短行） | 26 / 19 | 7 | 122 |
| 窄 square 9→17（R1 形分裂：copy9+cout+flip8，coh/HMR 同宽） | 45 / 27 | **18** | 133（反超 +1） |
| 窄 square 9→13 | 41 / 23 | 18 | 133（+5） |
| 窄 square 9→9（低 Cuccaro-only，无 high/flip） | 29 / 19 | 10 | 125（+3） |
| square 取绝对值杂项（`isub256→U9` / `c-iadd1→U9`） | 17/9，18/10 | 8 / 8 | 123（非瓶颈） |
| 通用 lz `flip(x22<2^k)`（k=1/5/11/17/21 全同） | 44 / 23 | **21** | 136 |
| 切片 generic `x[k:22]==0`（m=21/17/11/5/1） | 43/22，35/18，23/12，11/6，2/2 | 21/17/11/5/0 | 136/132/126/120/115（峰值持平） |
| 手写零检查 coherent 树（m=21/11/5/1） | 63/22，33/12，15/6，3/2 | 41/21/9/1 | 156/136/124/116 |

否决分析（`a1narrow.md §3` 准则复用）：

- **square 否决**：窄 extra 分解 copy(9)+cout(1)+flip-scratch(8)=18；
  通用 extra=len(target)（17/13/7）。**窄赢当且仅当 18 < len(target)**——
  最大行 18<17 假；越往后通用递减（13→7）而窄恒 18（9→9 行低-only 仍 10>7），
  越往后越亏。HMR 版（`init_and/del_and`）量子宽度与 coherent 同（temps 现配现释，
  经典位复用 b0），行 toff 虽降但宽度不降，仍否决。另 square 全局 132 已比
  全局峰 149 低 17，非瓶颈上加门换宽无意义。
- **lz 比较器否决**：通用 21 全 k 同（flip 内部 ripple 与阈值无关）；
  切片版峰值行（k=1，m=21）extra 21 精确持平——平局即否决，且需动 21 行换零收益；
  手写 coherent 树需 Cp(m)+chain(m−1)=2m−1 暂存，m=21 时 extra 41（峰 156，
  反超全局峰 +7），大败。flip 内部已是 HMR（`hmr_cleanup.md §1 T3`），
  手写树只是把内部优化重做一遍且更差。hot 编码（`h^=c_{i+1}&~c_i`，2+1 线滑动）
  无大暂存，非瓶颈，不单独探针（`hmr_cleanup.md §1 T3` 可转占比 ~1.6% defer 维持）。

## 3. 决策：生成器不动（双否决记录，非失败隐瞒）

`build_square2` / `build_square2_rev` 保持通用实现（U 重建→`isub256`→取 `|U|`→
9 全加行 `iadd(U→S[j:17),control=crow)` + `crow` 经 `coef[15]` 中转）；
`build_lz_norm` / `build_lz_norm_rev` 保持温度计实现（21 flip + 滑动窗口 2 线 +
1 编码线 + 优先编码）。**本轮对生成器零改动**。连带：

- double-build / 预筛 B/C/DUMP-V **免重跑**（电路文本未变，REC_SHA
  `0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d` 继续有效，
  **旧 SHA 作废项：无**——HMR 版 SHA 仍是现行值）；
- Q 峰值仍为 149（HMR 后 R1_J0/A1_J0 台阶；square 132 / lz 136 均退居 13+ 以下）；
- 门数变化：0（如下表）。`git status` 本轮仅本文一件新增。

| 口径 | 上轮（HMR 版，`hmr_cleanup.md §4`） | 本轮（双否决，实测） | 变化 |
|---|---|---|---|
| Q | 149 | 149 | 0 |
| SHA | `0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d` | 同左（有效） | 0 |
| `num_instructions` / CCX / toff_like | 130104 / 14700 / 15146 | 同左（未重跑，电路未变；`§4` 单机复核一致） | 0 |
| square_J0 行 extra | 17（通用保留；窄 18） | 17（通用保留；窄 18） | 0 |
| lz flip 行 extra | 21（通用保留；手写 41/切片 21） | 21（通用保留） | 0 |

## 4. 成本对比与同步证据（Q×C 实测，不用纸面）

单机复核（`width_opt62.resource_stats`，电路未变确认）：

```
Q 149 instr 130104 toff_like 15146 sha 0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
ops CCX 14700 CSWAP 446 CX 48876 HMR 10672
```

| 口径（静态实测） | HMR 版（基线） | 本轮（双否决，复核） | 变化 |
|---|---|---|---|
| Q（`num_qubits`） | 149 | 149 | 0（峰值不在 square/lz） |
| 文本 SHA（REC_SHA，已同步，无需改 `prescreen_width_opt.py`） | `0075e006…0235d` | 同左 | 0 |
| `num_instructions` | 130104 | 130104 | 0 |
| CCX / CSWAP / CX / HMR | 14700 / 446 / 48876 / 10672 | 同左 | 0 |
| `toffoli_like` | 15146 | 15146 | 0 |
| Q×toff（静态） | 149×15146=2,256,754 | 同左 | 0 |

预筛（电路未变，A 快检确认 + B/C/DUMP-V 沿用 HMR PASS）：

```
uv run python experiments/invsqrt/20261102_generator_v2/prescreen_width_opt.py --a
sha1=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
sha2=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
recorded=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
PRESCREEN-A PASS
```

B/C/DUMP-V 免重跑，沿用 `hmr_cleanup.md §4` 同 SHA 下 16 样本
`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`
全 PASS（B：x 恢复 + scratch 全零；C：16/16 dphase=0，最坏 x=2506015
margin 271129065.0；DUMP-V 16/16 t=8…19 全覆盖）。`narrow_proof.py` 重跑仍
`NARROW-PROOF PASS`（§1）。

## 5. 下一步（二选一建议：CSD 稀疏性优先，R 侧新拟合 defer）

1. **CSD 稀疏性回收（建议做）**：`refit_layout.md §2` 附带指出新 bind
   M237/B150/R133 比旧 190/80/57 更密——稀疏性未赢回，本轮靠位宽量化省门。
   CSD 精确重编码保持表值逐项相等（无合同风险，无需重跑全域整数合同；
   `btol` 仍 inf），布局无关，直降 QROM sweep CX（∝ popcount）与加法器位 CX。
   属 HMR 后顺手优化（`hmr_cleanup.md §6.4` 同类），每次只动表值表示、
   电路结构不动，double-build + B/C 即可确认。这是 square/lz 否决后
   唯一“只降门、不碰宽、不碰精度”的方向。
2. **R 侧新拟合（defer，非否决）**：`refit_layout.md §7` 已证 R 是硬瓶颈——
   R8 余量仅 2.1e7（2.6%）、DEEP（kA=4+kR=4）9 fails 超差。
   继续压 R 需新拟合思想（新坐标/新 digit 约束/新搜索），且每次重拟合需全域
   合同重验 + 变体独立谱系（`refit_variant62.py` 线），预算远超 CSD。
   待 CSD 回收落地、Score 企稳后再立项；A18（高余量 0.604）继续作为回退候选，
   主线 HMR SHA 不动。
3. 位宽截短继续禁止；`btol` 全程 inf；送完整官方验证前需先完成 CSD 回收并
   重跑 B/C + 全阶段 liveness（`width_liveness.py` 单线覆盖纪律维持）。

---

证据命令索引（本轮全部手动运行，非测试/CI）：
`uv run python /private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/sqcmp_probe.py`（§2）、
`uv run python experiments/invsqrt/20261102_generator_v2/narrow_proof.py`（§1）、
`uv run python -c "import width_opt62..."`（§4 单机复核）、
`uv run python experiments/invsqrt/20261102_generator_v2/prescreen_width_opt.py --a`（§4）。
官方 200M-shot 验证：**未跑**（门禁；HMR 版 PASS 记录见 `hmr_cleanup.md §6`）。
