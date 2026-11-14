# 20261115 升级总结

## 已落地

| 项 | 值 |
|---|---|
| 第一次提交 | ref **58349843**，`maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2 输出，MCP **COMPLETE 27.30661** |
| 升级提交 | ref **58350759**，HW-26 invsqrt `1ba197b02771` + DQI `821bf8d1` + maoxin 4,033 chemistry，**COMPLETE 27.31193** |
| 包 | `submissions/20261115_public_2731/submission.zip`，SHA-256 `46d53bde…c933`，18 文件 |
| 独立验证 | HW-26：未修改官方 invsqrt verifier，200,540,928 shots **PASS**，78,673.56921101942，worst/tol 0.9986660009 |

第一次提交已把本账号从 **27.00209 → 27.30661（+0.30452）**；升级包 **58350759**
已 COMPLETE **27.31193**，MCP 名次 **159 / 3053**。

## 公开前沿扫描结论

- `manwithacat/vqcc-apache-public-circuits` v125（497 件）与 11-14 后新件中：
  - invsqrt 最低 Q = **46**；HW-26 `1ba197b02771` 是唯一更低 cost（78,673.57）。
  - DQI 最低 cost 仍是 `821bf8d1`（预期 360.947e9）；Q<889 的公开件全部更贵
    （最便宜 888Q 398.27e9，+10.56%）；无 840Q。
  - chemistry 最低 T = **14,728**（4,033 loader），最低 cost **294.984M**；
    没有 3,9xx loader 或更低 T。
- 公开可复现上限 **27.31214**（HW-26 + npz `e52b7cdd` + 821bf8d1）。
  排行榜第 31–146 名（27.40–27.61）使用未公开组件，公开件无法直接到达。

## 逐项判决

### invsqrt

- HW-26 是唯一确定正收益：−1 Toffoli，GM +0.00532。
- Q=45 需要补价 ≤38 Toffoli；公开最便宜覆盖 +196（4560ac0c）/+257（321aff83），
  GM −0.78/−1.05。当前 46Q 峰值段 77.7% 的 op 同时占 46 线，不建议继续。
- 64→32 行表、删旋转、divider 重写均不可行（详见 `invsqrt_plan.md`）。

### DQI

- cutoff 18 最优；19/20/21 负 EV；retention 的 241 个乘积已饱和，
  `max_hops=0/1/2` 均只宿主 241，输出逐字节等于 `821bf8d1`（本次 Kaggle 实测，
  官方 verifier PASS 360,209,905,486.02）。
- 840Q no-go；888Q 是唯一剩余结构杠杆（预算 ΔT≤862，预期 +0.01–0.02 GM），
  需要源码级单线重分配，未在本轮构建。

### chemistry

- 公开点已四面贴边（e2 余量 3.2e-8、E_gap 余量 4e-9、λ 距地板 0.26%）。
- 唯一 ≥1% 杠杆是 B=143→129（T −3.1–4.0%，GM 27.52–27.68），但闸门是
  B=129 的 8-bit e2 地板。Stage A 已完成：B=143 对照精确复现公开件
  （e2 19.99997 mHa、λeff 46.9070、cost 294.99M、PASS）；B=139 e2 64.31 mHa、
  B=129 e2 138.07 mHa，C=48 也救不回。截断+权重 refit 的廉价形式已关闭；
  要打开 B<143 必须重训 U/词表并重做 15 个 loader，属独立 factorization 研究线。

## 下一步（按收益/可行性）

1. 58350759 已 **COMPLETE 27.31193**，保留为当前最佳。
2. 用 `junmiaotiao` npz `e52b7cdd` 替换化学权重，可到 27.31214（+0.0002，零风险，
   但需要重新打包/提交；不建议为此单独消耗提交次数）。
3. 剩余唯一正 EV 的杠杆是 **DQI 889Q → 888Q**（源码级单线重分配，预期 +0.010–0.021，
   即约 27.321–27.333）。chemistry B<143 已由 `chem_b129/CLOSED.md` 实测关闭。
4. 不追公开榜第 31–146 名：其组件未公开，公开件天花板已确认。

## 2026-11-15 18:03 UTC 进行中

- `qingyu1232/qcc-chem-b129-full`（T4 GPU）已启动：从公开 (8,143,44) 表做 full-U
  L-BFGS shrink，schedule `139x44,135x44,131x44,129x44`，`--fit 2500 --final 8000
  --select impact --device`。这是 B=129 的关键判决；只看连续 error_2 是否足够低
  （目标 ≤15 mHa），不通过就关闭 B<143 线。
- `qingyu1232/qcc-chem-b139-shrink` 是 139 的快速闸门，但 B129 full 已覆盖它。
- 两 run 均在 Kaggle，未在本机跑模拟；结果出来后只对通过点做 8-bit rounding、
  loader build 和官方 78,080-shot 验证，且只有 GM ≥27.50 才打包提交。

## 2026-11-15 结论：B<143 已被实测关闭（不是时间盒）

`qingyu1232/qcc-chem-b129-full` **v1 已 COMPLETE**，full-U L-BFGS 实测连续 error_2：

| B | 连续 e2 (mHa) | 门槛 ≤12.5 | 预期 GM |
|--:|--:|---|---:|
| 139 | **16.173** | FAIL | 27.42 |
| 135 | 18.408 | FAIL | 27.52 |
| 131 | 20.713 | FAIL | 27.63 |
| 129 | **19.830** | FAIL | 27.69 |

上游 `recipes/finish_merged_b8.toml` 写明 "Rounding has cost 6-8 mHa on merged shapes,
so the fit should be <= ~12.5 mHa"。B=129 的 19.830 mHa 高出门槛 7.3 mHa，量化后约
26–28 mHa，超过 20 mHa 硬闸门。且 GM≥27.50 需要 T≤14,428（B≤135），B=135 的 e2 同样
不过。**两条约束同时否证**，详见 `chem_b129/CLOSED.md`。

未做 8-bit rounding / loader build / 官方 78,080-shot 验证（第 1 步未过门槛，后续无意义）。
当前最佳保持 **27.31193（ref 58350759，rank 159/3053）**。
