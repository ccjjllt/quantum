# §2 8 位地址 unary QROM：顺序装载–使用–卸载 + 共享系数工作区

地址 `a = (parity<<7)|((m>>14)&127)`，8 位，256 项（定义来源 `trackA_semantics.md` §2）。
三表位宽（待主线程验证的合同）：B 33 位 / A 22 位 / R 12 位。

## 1. 首版方案：单 unary pass、六扫、分时 33 线工作区（bulky 但可接受）

```text
coef[0..33)  ← 全程唯一的系数工作区（33 线，B/A/R 分时复用）
with unary_iteration(addr8, range(256)) as it:   # 单 pass，+8 暂存（实测 P2）
    sweep1: for v,m in it:  B_table[v] 条件 CX → coef[0..33)     # 装载 B
    V[12..45) += coef                                            # 使用 B（见 arith.md）
    sweep2: for v,m in it:  B_table[v] 条件 CX → coef[0..33)     # 卸载 B（同 pattern 重放，0 Toffoli）
    sweep3: for v,m in it:  A_table[v] 条件 CX → coef[0..22)     # 装载 A（高 11 线保持 |0>）
    V -= 2·coef·D                                                # 使用 A
    sweep4: for v,m in it:  A_table[v] 条件 CX → coef[0..22)     # 卸载 A
    sweep5: for v,m in it:  R_table[v] 条件 CX → coef[0..12)     # 装载 R
    V += coef·S                                                  # 使用 R
    sweep6: for v,m in it:  R_table[v] 条件 CX → coef[0..12)     # 卸载 R
# pass 关闭（相干镜像 +254 CCX，估计）
```

要点：

- 每 sweep 解码成本 254 CCX（实测 P1，顺序 `range(256)` 下 `(a^b).bit_length()−1`
  移动费总和；与数据无关，数据只改免费的 CX 条数：B 表约 256×33/2≈4.2k CX，
  均为 Clifford-free，verifier 不计费）。
- 卸载 = 同 CX pattern 重放（`CX` 自逆），**0 Toffoli**，且把 `coef` 精确归零，
  下一表可直接复用（复用纪律：归零线才复用）。
- 迭代顺序固定 `range(256)`（确定性机制一部分，见骨架）；第二扫起起点续接
  （255→0 多约 7 CCX，已含在估计余量里）。

## 2. 成本估计（执行，正向；逆向镜像再 ×2，见 round_phase 逆转调度）

| 项 | 执行 CCX（估计） | 来源 |
|---|---|---|
| sweep×6（装载/卸载各 3） | 6×254 = 1524 | 实测 P1（254/扫） |
| 单 pass 相干关闭（HMR 关闭的镜像替代） | +254 | 估计（docstring 关闭 0 Toffoli 仅对测量式成立） |
| 正向小计 | 1778 ≈ 1.8k | — |
| 正+逆合计 | ~3.6k | 估计；以生成电路为准 |

备选（b）：并行 67 线工作区（B+A+R 一次全装、两扫共 508+254 正向，
正+逆 ~1.5k），省 ~2k Toffoli 但宽度 +34Q。首版选（a）（宽度优先），
（b）记为优化钩子 deferred。

## 3. dense-QROM XOR 写法排除理由（记录）

1. kickmix 生成侧**无独立 H 门**（`hasattr(builder,'h')==False`，实测）：
   把表值 XOR 进**非零**累加器的相干 dense-QROM 构造需 H 共轭做相位回踢，
   工具链不支持。
2. kickmix 自带的 `init_lookup/del_lookup` 要求目标先 `|0>`（内部 reset，
   非相干）且内部用 R/HMR（实测 P3：R≈267–288、HMR 255），`del` 为测量式清理——
   违反首版“不用 HMR/R”纪律。
3. 因此凡需查表处一律用本节 unary + CX pattern（目标零线 + 自逆卸载），
   全相干、无测量。结论：dense-QROM 在本工具链首版不可用，待 H 原语或
   相干 `del_lookup` 出现再重估。

## 4. 宽度影响

`coef` 33Q + unary 暂存 8Q。平方的 U/S、中段的 t8 借用 `coef` 空闲期
（`coef` 在 QROM sweeps 之外全程空闲为零，见骨架调度），.Workspace 复用总表：

| 寄存器 | 位宽 | 寿命 | 备注 |
|---|---|---|---|
| x/m（原地） | 22 | 全程 | 输入 + 归一化（含原地 D） |
| lz | 5 | 求值→逆移位 | p/s/addr 皆视图 |
| coef（B/A/R/U/S/t8 分时） | 33 | 分段 | 零线复用纪律 |
| V | 55 | 组装→相位后 | 首版容器 |
| unary 暂存 | 8 | pass 开→关 | 实测 P2 |
| 加法进位暂存 | ~2 | 加内 | builder 内部分配/释放 |
| **峰值估计** | **~125Q** | — | 22+5+33+55+8+2；以生成电路为准 |
