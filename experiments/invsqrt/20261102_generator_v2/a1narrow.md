# a1narrow.md：降宽第二步（A1 窄化）—— 证明通过，生成器不改（实测平局）

分支 `invsqrt-generator-rebuild`。上一步（`width_opt.md`）：R1 窄化，Q=159，
SHA `55b829c9…4341`，预筛 A/B/C PASS，`--dump-v` 欠账（本轮已补，见 §4）。
本轮只动 A1，不碰 S6/查表/窗口/恢复钩子；不读旧 KMB/tray；不数值拟合；
不截位；不跑官方 200M-shot 验证；产物只在
`experiments/invsqrt/20261102_generator_v2/`（本文 + 证明/预筛脚本修改）。

## 0. 文件取舍（说明理由）

- **不新建 `a1narrow62.py`，直接延续 `width_opt62.py`**：`width_opt62.py`
  已是带 STAGE 标记的工作线，`prescreen_width_opt.py`/`width_liveness.py`
  均 `import width_opt62`。新建文件需复制 ~670 行并重接三处引用，
  double-build 谱系分叉风险 > 收益。延续单线，SHA 谱系清晰。
- **结论是不改生成器**（见 §3 实测），故 `width_opt62.py` 本轮零改动，
  工作区 `git status` 仅 `narrow_proof.py`（+证明）与
  `prescreen_width_opt.py`（dump-v 读路径 bug 修）两处。
- **单立本文，不并入 `width_opt.md`**：`width_opt.md` 是第一步（R1）的
  审计定稿，改数字会破坏其证据链；本轮是否决记录，独立成篇保留。

## 1. 证明（先行，已 PASS）

`narrow_proof.py` 新增两项（A1 形状：源宽==低宽，22/22 按 3/3 缩比）：

- `test_a1_split_sub(3,3,2)`：窄减正向（copy→flip 置 cout→解 copy→高
  `isub`→重算 copy→UMA逆→CX 清 cout→MAJ逆→解 copy）vs 整数 oracle
  `(tv-sv·ctl) mod 2^ntgt` 穷举；
- `test_a1_split_sub_roundtrip(3,3,2)`：窄减后紧接窄加回，一电路 roundtrip
  恒等（逆正确），暂存两侧均 free。

实测输出（`uv run python .../narrow_proof.py`）：

```
uncontrolled n=3: 64/64 ok
controlled-via-copy n=3: 128/128 ok
split noff=2 nlow=2 nhigh=3: 256/256 ok
split-reverse noff=2 nlow=2 nhigh=3: 256/256 ok
a1sub noff=3 nlow=3 nhigh=2: 512/512 ok
a1roundtrip noff=3 nlow=3 nhigh=2: 512/512 ok
NARROW-PROOF PASS
```

构造正确（含 J13 加行：与 R1 加 pattern 同形，已由 split 项覆盖）。
**证明只管等价性，不管宽度**——宽度由 §2 孤立探针裁决。

## 2. 宽度实测（孤立单行探针，先测量后决策）

探针脚本在仓库外（tmp，不进产物）：
`/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/a1_probe.py`，
单行独立成电路，`extra = num_qubits - base`，全局峰 = 115 + extra。
`uv run python` 实测：

| 探针 | qubits / base | extra | 全局等效峰 |
|---|---|---|---|
| 通用 `c-isub22→V[1:45)`（现 A1_J0） | 111 / 67 | **44** | 159（与线上一致） |
| 窄 SUB 行（A22/T44，同架构） | 111 / 67 | **44** | 159（持平） |
| 窄 ADD 行（A22/T31，J13 形） | 98 / 54 | **44** | 159（持平） |
| `flip22×22` 内部 | 66 / 45 | 21 | —（瓶颈） |
| `iadd(1q)→22`（高部件） | 45 / 23 | 22 | —（非瓶颈） |
| 窄 R1 ADD 行（校准，S17/T45） | 97 / 63 | 34 | 149（`width_opt.md` 149 断言复验成立） |

## 3. 决策：生成器不动（否决记录，非失败隐瞒）

窄 extra 分解（flip 相主导）：copy(nlow) + cout(1) + flip scratch(nlow−1)
= 2·nlow；通用 extra = len(target)。**窄赢当且仅当 2·nlow < len(target)**：

- R1：2·17=34 < 45 ✔（故第一步有效）；
- A1_J0：2·22=44 < 44 ✘（精确平局——源 22 位相对目标 44 位太宽）；
- A1 后排（目标 43→32，J13 目标 31）：通用 extra 逐行递减，窄恒为 44，
  **越往后越亏**，另加每行约 +60 CCX（估算：copy×2 + MAJ/UMA×22 + flip22，未实装故无实测值）×28 行。

应用它 = Q 不变（159，全行封顶）、门数涨、Q×C 恶化。故 `build_a1` /
`build_a1_rev` 保持通用实现，本轮对生成器零改动。连带：

- double-build / 预筛 A/B/C **免重跑**（电路文本未变，REC_SHA
  `55b829c9…4341` 继续有效，**旧 SHA 作废项：无**——上轮 SHA 仍是现行值）；
- Q 峰值仍为 159 @A1_J0（ acres, 无新实测项，探针表即证据）；
- 门数变化：0（如下表）。

| 口径 | 上轮（R1 窄后） | 本轮（A1 否决，实测） | 变化 |
|---|---|---|---|
| Q | 159 | 159 | 0 |
| SHA | `55b829c9…4341` | 同左（有效） | 0 |
| `num_instructions` / CCX / toff_like | 100618 / 12278 / 12724 | 同左（未重跑，电路未变） | 0 |
| A1_J0 行 extra | 44（通用） | 44（通用保留；窄亦 44） | 0 |

## 4. `--dump-v` 本轮重跑（上轮欠账结清 + 附带 bug 修）

首跑失败 `IndexError: 'v'`：`create_regs` 把 v 分配为匿名 scratch，
`read_within_shot("v")` 按名读恒错——基线 `prescreen_gen2.py` 同病，
`gen2_build.md:81` 的“dump-v 一致性”声明实无可运行证据（基线文件不动，
如实记）。仅修本轮文件读路径（V 稳居 q60..q114 = x22+lz5+coef33 之后，
逐索引 `read_across_shots(km.q(..))` 重组整数；电路零改动）：

```
x=       1 ... OK / x=       2 ... OK / ... / x= 3133452 ... OK（16/16，t=8…19 全覆盖）
DUMP-V PASS
```

（全行 `Vwant==Vgot`，含 t=19 的 x=2097152/2506015/3133452。）

## 5. 下一步

1. **S6 经典增量优先**：`iadd(1)→V[0:36)` 通用 extra=35（峰 150）是改 A1
   否决后的全局次峰。增量是常数加——无需 copy 源寄存器（省 22 线），
   手写进位链仅需 ~1–2 暂存，窄不等式天然成立（§3 准则）。先孤立探针
   测常数增量行 extra，再证小例，再换。
2. A1 备选（**新架构，非同窄**）：两级分裂（低 22→11+11，每级
   copy11/flip10，高通用），预估峰 ~140；需独立证明与门数核算，
   在 S6 完成后评估。本轮不启动。
3. 位宽截短继续禁止；`btol` 全程 inf；送完整官方验证前需先完成 S6 窄化
   并重跑 B/C + 全阶段 liveness。
