# QQ-51T 频次精确计数（2026-11-06）

## 假设

891Q 电路若用 kickmix `ixor/init_gf2_mul` 构建，则每个 GF 乘法器在 kmx 中
留下一对 `@enter:gf_mul` / `@exit:gf_mul` 标记（独立 `m=12` 构建实测 14 个
INFO_TAG，其中恰一对 gf_mul；`measure_qq.py` 复现：ixor/init 均为 63T）。
数标记对 = 精确调用点数；再按对内 CCX 数区分位宽
（63→m12，27→m8，9→m4，189→m24）。

## 改动

- 只读：`artifacts/20261105_maoxin_v2/release/dqi.kmb`（530MB）转储 kmx 到
  $TMPDIR（仓库外），`grep -c` 数标记，Python 流式统计对内 CCX；
  不改候选，不跑验证。
- 判定阈值：`1188 mean T` = 总GM +0.1% 回本线（`analysis.json`）；
  每 m12 乘省 12T → 需约 99 个可替换 m12 调用点。

## 观察（2026-11-06已执行）

- 全电路转储：`dqi.kmb`（530MB）→ kmx 756MB，58,390,266 行，
  静态 `397177 Toffoli-like` 与 `analysis.json` 一致（同一电路）。
- 零 `@enter/@exit:gf_mul` 标记（`balanced true`，17876 个 INFO_TAG 中无一例）：
  本电路**未使用** kickmix `ixor/init_gf2_mul` 构建器，
  不存在 63T Karatsuba 块。`w_sparsity` 式“965+995 个 63T 乘”的
  纯乘假设被证伪—— transplant 对象需重定。
- 实际含乘法器色彩的叶块（CCX/调用数）：
  `inverse12 products 25×169`、`norm 15×169`、`scalar 18×169`、
  `inverse24 products 70×29`、`norm 42×29`、`scalar 58×29`、
  `multiply v 99×12`、`full_head_product 126/168/210×2`、
  `head_phase 42×3`，合计约 17054 CCX（占全电路 4.3%）。
  另 `gf_iadd 0×8236`（免费加法）、`aligned_route/head_pivot 0`（路由）。
  见 `artifacts/20261106_qq51_count/blocks.json`（嵌套感知，全平衡无错位）。
- 阶段 span 精确计数：`convert 55947 / unconvert 56669 / extract 59403 /
  unextract 94480 / scan 44275 / synthesis 31613 / unsynthesis 40249`
  （火焰图估计 `unconvert 62711` 偏高约10%，span计数为准）。

## 证据

- `artifacts/20261106_qq51_count/count.json`（零 gf_mul + 全 tag 表）。
- `artifacts/20261106_qq51_count/blocks.json`（各块调用数×对内CCX）。
- 脚本 `count_qq.py`（标记对计数）、`count_blocks.py`（嵌套感知 histogram）。

## 判定（2026-11-06更新：接口分析后 transplant 已死）

- 可替换候选只剩 `multiply v`（99→51，×12≈省576）与
  `full_head_product`（均168→51，×6≈省702），合计 ≈1278 静态T，
  **前提是二者为纯 GF(2^12) 乘法且 mod 可桥接**（待证；`inverse12`
  系的 25/15/18 CCX 疑为比特串行/标量乘，用 51T 全乘替换反而更贵）。
- Q 罚致命：+2暂存 → `(893/891)²=+0.449%` DQI ≈ `-0.15%` GM；
  回本需 T 省 ≥1775（`396905×0.4473%`），而上限 1278 < 1775。
  **除非零Q集成（复用idle/workspace），否则 transplant 为负收益。**
- **接口否决（本轮新增，`block_interface.json`）**：
  `multiply v` 首实例 CCX 只触 27 线：20 纯控制 → 7 目标
  （`[48..59∖{52,57}]+[72..83∖{76,81}]` → `[843,844,845,847]+[880,881,882]`），
  不是 24→12 全乘；`full_head_product`（168门实例）为
  12 纯控制（`q0..q5`,`q696..q701`）→ 12 目标（`q744..750`,`q792..798`），
  呈 schoolbook 双线性 taper（69,33,9,6,6,3 / 23,11,3,2,2,1），
  12 实例 × 同构（bank 48/96/144 平移）、6 实例 × 前后向镜像对，
  亦非标准 12×12 接口。**51T（24入/12出）对二者都不是 drop-in。**
  transplant 需逐块重推函数并重综合 = 全新 EEA 块优化，非移植。
- 下一步：DQI 主攻转 (a) convert/unconvert 联合改写（先建重复内核的
  输入/输出契约+付费门计数，`maoxin_v2/README P2`），(b) 891→889
  宽度（六峰私有位存活审计，P3）；QQ-51T 按 drop-in 已关闭，
  仅当作“EEA块重综合”大方向保留。
