# 2026-11-18 并行研究总结（Round 2）

## 已交付并验证的包

`submissions/20261118_281806/`：invsqrt `563d0583` + DQI `575b043f` + chem（18 成员）。
官方 verifier 全量 PASS，**GM 28.18065942104198**，zip 85,016,504 B
sha256 `2271b861eb44628f45e2bcbf836c1f41b8bc34446389849776817328ba800eb5`。
该分数与公开前沿 `atakanaldemir/qcc-shared-products-and-controlled-refits` 的 observed
28.18070 相同——**我们已处在公开前沿**，榜首 29.98–31.43 是私有代际。

## 各轴实测结论（决定性数字）

| 轴 | 结论 | 决定性测量 |
|---|---|---|
| chem `brot` 8→7 | **关闭** | error_2 0.426（21×）、λ_eff 72.67；5 万参数 L-BFGS 只降 0.02% → 网格问题 |
| chem `C` 43/42 | **关闭** | 冻结 U 联合 refit：C=44 19.8276、C=43 21.2264、C=42 23.2501 mHa；且 C<44 不 λ-lean（Λ 534） |
| chem 形状 R=5/4 | **关闭** | 连续误差 127–177 mHa（门 20），结构合并损失 0.16–0.39 Ha/次 |
| chem loaders | **关闭** | 真实块秩 75 → 150 cuts → products≥188；k4–k8 已在 149 cuts/263 T；k0/k1 投影秩 [35]×15 无关系；L=5 分割 0 配对候选；行/树/列置换不改变块秩 |
| chem `J`/workspace | **关闭** | Q=387+J·brot，J=5 最优；ANGLE 工作比特免费到 128 上限 |
| invsqrt Toffoli | **关闭** | 1,479 个乘积原子、仅 4 个重复、1,277 由 HMR 回收 → **无任何 compute→CCX-uncompute 对**；phase-fold 0 处 |
| invsqrt rotations | **关闭** | 33 个已在局部最优（λ≡1.0）；去掉最小一个即 1.2495 FAIL |
| invsqrt 宽度 | **关闭** | 42Q 需 Toffoli≤1,534.7（+80.7）；公开 46Q 电路 1,480.8 但被 485 个单 wire spike 钉在 46 |
| DQI 宽度 | **关闭** | 26 个持久 EEA 字 + 24 pool；866Q 的 pool 重建下限 116,894 T vs 打平 +20,630 T |
| DQI tape cuts | **关闭** | 条件块内配对查找器：4,184 对→仅 3 个可服务（−3 T），且 2/3 salt 掉拍；自由门 0、plain cancel 0；加 wire 曲线 14 条 +2.5% 成本 |
| DQI 公共件 | **确认最优** | 575b043f 346,409,762,292.72（0/1/0）；61c8348d 在 3 个 salt 全掉拍 |

## 新增的结构性认识

1. **EEA 占 DQI T 的 88%**（A 153,186 + C 170,539），Chien 只有 12%（44,264）；所有块都触发，
   无门控节余。EEA 每日志约 2,700 个乘法块（42 CCX/块），即每遍约 50 次迭代；参考生成器
   用 222 次（`3(n+1)+9`），所以 tape 已比参考紧 4×。截断是否有余量由 `dqi_algo` 线在测。
2. **loader 的硬下限**：乘积架构下限 products≥38（dim 75/2），现役 cut/pairing 只能到 188；
   通用 GF(2) 乘积分解是唯一可能到 113 T/loader 的路线（`gendecomp` 线在测）。
3. 公开前沿即我们的包；公开件再无可导入的增益。

## 提交计划

名额 UTC 00:00（北京 08:00）重置后提交
`qingyu1232/qcc-integrator-281806` v1 的 `submission.zip`，并记录 ref + public score。

## 如果要把分数推到 31+

只有一条路：新的 DQI 解码器（Q=890 下 mean T 从 367k 降到 ≤265k，或 Q≤840 且 T≤300k）。
本轮测得的区域分解（EEA 88%、42-CCX 乘法块）就是这项工作的起点；这不是字节重排能完成的。

## Round-2 additions (02:20 Beijing)

| 轴 | 结论 | 决定性数字 |
|---|---|---|
| chem 通用乘积分解（全 h 复制向量） | **关闭** | `qcc-chem-span-rep`：k=4/2、\|L\|≤5 共 4,943 子集，nullspace 全 0、**dim W = 0**；“~75 products” 捷径不存在 |
| DQI EEA 迭代 | **关闭** | tape 每遍 34–35 轮（deg 69→<35 的下界），参考的 222 是 4 相计数器的松界；mean/static 99.76%，无可截断余量 |
| DQI 算术 | **唯一杠杆** | 3,969 个乘法块、均值秩 40.1、众数 42（Toom-4）；整个 DQI 的算术替换上限 **68,022 T = +1.99 GM**，全在 12×12 乘法的双线性秩（42→23）；需要重生成或原地改块 |
| DQI 区域 | 实测 | EEA 前 153,180 / Chien 44,217 / EEA 反 169,719；EEA 87.9% |
| 公开前沿 | 已到达 | atakan 28.18070 = 我们的 28.180659（同一组 18 成员） |

**正在跑的最后两条大杠杆线**：`dqi_mult`（把 42-CCX 乘法块原地换成 ≤35 秩的双线性算法，+0.55～+1.5 GM）与
`gendecomp`（非 cut 导出的矩形覆盖，若 <188 products 则 chem +up to 2.4 GM）。其它全部实测关闭。

## 提交执行清单（UTC 00:00 / 北京 08:00 名额重置后）

1. 确认 zip：`/tmp/int_correct/submission.zip`，85,016,504 B，
   sha256 `2271b861eb44628f45e2bcbf836c1f41b8bc34446389849776817328ba800eb5`，
   18 成员；receipt `submissions/20261118_281806/receipt.json`。
2. 提交：
   `kaggle competitions submit -c google-verifiable-quantum-circuit-compilation \
      -k qingyu1232/qcc-integrator-281806 -v 1 -f submission.zip`
3. 记录 ref / publicScore 到 `submissions/20261118_281806/README.md`；
   若 DQI 在榜单 salt 上掉拍（score ≈ 28.13），用当天剩余名额重提（salt 可能按提交抽取）。
4. 若 `dqi_mult` 线在截止前交付通过验证的低秩乘法候选，重建 manifest + integrator
   并优先提交该包（预期 +0.55～+1.5 GM）。
