# invsqrt 已放弃方向总览（2026-11-12）

分支 `codex/invsqrt-research`。本文件是所有已关闭/不再做方向的唯一保留记录：
每个方向一行结论、关键数字、放弃原因。详细脚本与产物已删除
（可从 Git 历史找回；`artifacts/` 下 gitignored 产物不可恢复）。
系统性复盘见 `20261110_arch_review/README.md`（保留）。

## 旧 family（`7c10edba`，95430.78）局部改写：全部饱和
- 单删 / 仿射张成 / 辛秩 / HMR 窥孔 / 脏借用 / T 融合 / 重排序 / 跨守卫缓存
  （全电路 True+clean+同守卫 0/190）：0 可转。脏借用正确模型下每处 +1 CCX，
  做即亏（`20261109_dirtyfrag_proof` toy 实测污染）。
- 2 次 FAIL 仲裁：T 融合候选 B（误差恰为被搬移角 θ/2，2509×容差，
  零分支字仿真为假阳性来源）；A3 微角 L1 单删（`x=644` 超差约 1.1e-11 turns≈0.5%）。
- 窗口普查 / 大窗重综合 / 61Q 保值改写（scoped 旧门序列）：0 收益或不可迁。
- 整段查表 / 直接相位综合 / Newton-CORDIC：4.8×–28× 超预算证伪。

## 新 family（gengsr `26ebf39d`，94537.59）窥孔：全部关闭
- S1/S2 uncompute 对普查（`20261110_s1census`，S1 CCX 365 / S2 CCX 499）：
  k=2 13 对 + k=3+ 1 组，**可转 0 对**（最小 diff 266,255 输入；机制为累加/线复用，
  非 Bennett 冗余）。方向一 (a) 150–600 分区间未达到，0 分。
- A3 微角梯逐级敏感度：静态安全仅 L1/L2（tol_min=621138291 units），
  L1 已被官方验证器 FAIL 否决；L1+L2 联合位移超最小容差。方向一 (b) 关闭。
- S1 重算链 M1 降级首试点（`20261110_s1m1`）：0/13 可转，与普查逐数一致；
  再立项须先换着陆点，不沿重算链展开。
- S0 移位树两代 CCX 均为 191：已近下限，不做。
- A3（−72 中 −50 CCX−22 CSWAP）不可迁回旧 family（支撑集 `q18/21/23/27→q28+q52/55`
  完全不同，与 S1 分配/S2 相位窗耦合）。

## 旧基线系（历史，不再复跑）
- `20261103_one_ccx`（+1.06 CCX 期望，0.066%，已 PASS）、`20261104_*` 迁移/复核链
  （跨 HMR 合并 −2C，双 seed 98123.14）、Maoxin V2 迁移（≈98k 预测，未全量验证）、
  Syed V9（97747.22）、Public Frontier 谱系 −2316（5 步正交补丁）：
  均被 gengsr 新 family（−893）超越，不再回头。

## 2026-11-11/12 `6c6a734d` / `9c708f7b` 时代（全部关闭）
- 公开检索（`manwithacat/vqcc-apache-public-circuits` v115，73 个电路）：`6c6a734d`
  93,863.36 为当时最高；11-11 晚新 splice `9c708f7b`（WCao24 44-CSWAP normaliser
  + Thomas Gamet early prefix）官方 93,555.26，本机 200M PASS 93,555.3164，成为新公开前沿
  （已采用，不属放弃）。
- 均执行 Toffoli 普查（`6c6a734d`，400k MC）：模型 1,218.8324 vs 官方 1,218.8333；
  可用条件化池仅 6 门，上限 3 mean ≈186 分（低于 30 门立项线）→ 不做。
- splice 泛化：全 1,865 行 diff 逐 hunk 账，现有 S0 切点 −1.00 mean 已最优，最佳替代 −0.75；
  S2 合并块栈深不兼容；S2 后缀切点小域官方验证 **FAIL**（x=5，0.5 turn，非恒定偏移）。
- 62→61Q：峰点 62 线全活，纯重标号不可能；值级重算未立项。
- HMR 清理：X-basis 测量随机、无 Z 测量；14 门样本候选 **FAIL** x=3（0.5 turn）。
- 删除：`20261111_a15b0d73*`、`20261111_hybrid_census` 及 artifacts；保留本文件、
  `20261110_arch_review/`、`README.md`。

## 2026-11-12/13 追加关闭（详细目录已删除，数字保留）
- **经典查表**（`20261112_classical_lookup`）：kickmix 只有 X-basis HMR，没有独立 H、
  也没有 Z-basis 测量；无法把 x 读成经典比特再条件施加 Z_POW。只读检查，未跑 verifier。
- **`9c708f7b` 新 family 普查**（`20261112_newfamily_census`，1.2G artifacts）：
  S1/S2 uncompute 对 **0/305** 可转；41 个旋转删除/合并/重拟合 **0 个**；61Q 值级重算
  预算 +24.7C、实现 ≥52C；Q=63/64 需 ΔC −68.4/−90.9。没有任何 ≥2,800 分的候选。
  相位裕度 `worst/tol=0.99932377` 是结构性的。
- **`9c708f7b` 之后**（`20261112_next_family`）：公开 77 条无更好件；62Q 是该架构最优
  （x 自身比特已回收，mid/tail HMR 掉 241 个 x 比特实例）；插值/多项式家族 7.3×–28.8× 差；
  当前架构 C 的可挖上限 ≤5.4%，现实 2–3%；没有 ≥20% 的新家族。
- **小优化**（`20261112_small_opt`）：8 个重复权重融合 8/8 破坏相位，官方 verifier
  `x=1` FAIL（8191×）；6 门后移条件化 `x was not restored` FAIL；常量控制 0 个；
  prefix 重综合超时。五类机械改写实测局部最优。
- **prefix 审计/重综合**（`20261113_prefix_audit`、`20261113_prefix_resynth`）：
  63 T normaliser + 167 T 算术块 + 7 T 收尾 = 237 T；上一轮 “193 CCX / 22 bit → 省 83 C”
  归因撤回。167 T 块已有 6.5× AND 复用（1,081 单项式 / 21,904 关联），局部冗余 0。
  无候选；用精确定点模拟器对 3,133,452 个 x 逐点比对，0 差异。
- **retention planner**（`20261113_retention`）：只保留 `retain.py`（public retained-product
  planner）；未形成候选，作为可复用工具保留。

## 2026-11-13 停止研究
公开 46Q invsqrt `321aff83…35177` 已把成本降到 80,162.73，比自研 `9c708f7b`
（62Q，93,555.26）低 14.3%。62Q 局部面已饱和，剩余收益需要新算法家族，停止推进。
总览与放弃原因见 main `docs/abandoned-research.md`。

## 删除清单
- `experiments/invsqrt/` 下除本文件、`20261110_arch_review/`、`README.md` 外全部目录
  （含 classical_lookup/newfamily_census/next_family/small_opt/prefix_audit/prefix_resynth）；
  `20261113_retention/retain.py` 作为可复用 planner 保留。
- `artifacts/` 下全部 invsqrt 产物目录（含 `20261112_newfamily_census` 1.2G、
  `20261112_small_opt`、`20261113_prefix_resynth`）。
