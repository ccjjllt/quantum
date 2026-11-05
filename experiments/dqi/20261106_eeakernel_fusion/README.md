# convert/unconvert 融合分析（2026-11-06）：边界联合冗余检验

## 假设

相邻 EEA 块（norm→scalar→products）若在边界处重复计算，
删多余门即省。先做精确 ANF 删1/删2检验（无采样）；
含 R/HMR 的 span 超出经典精确范围，明确标出，不硬算。

## 改动

- 只读：kmx 流式提取边界 span；ANF 精确比对（全输入恒等）。
- norm 模板（首实例，纯 CX+CCX，217 ops/22线）：
  单删 15/15 必需，C(15,2)=105 对删 0 冗余。
  见 `artifacts/20261106_eeakernel_fusion/norm_redundancy.json`。
- products 模板：单删 25/25 必需，双删 C(25,2)=300 为 0，
  三删 2300 为 0，四删 12650 为 0，有界 2→1（7窄对）为 0
  （14个原始命中已证伪为平凡自替换，见 eeakernel_rewrite/README）。
- 边界 span 审计：norm→scalar 间隙纯 CX（24条）；
  scalar→products 间隙含 HMR×4 + CZ×28 + SWAP×13（309 CX），
  scalar 块内含 R×6 + HMR×6 + CZ×81 + Z×21 ——
  凡涉及 scalar 的联合检验超出经典精确范围（R 产生叠加，
  HMR 坍缩），需量子验证（官方 verifier 打补丁电路）或 Z3，
  本轮不做，明确记为 open。

## 证据

- `artifacts/20261106_eeakernel_fusion/boundary_audit.json` +
  `boundary.log`：三间隙审计（norm→scalar：24 CX纯净，可经典精确；
  scalar→products：309 CX+13 SWAP+4 HMR+28 CZ，不可经典精确；
  products→norm2：16588 ops含112 CCX+43 HMR，非局部边界）+
  norm 模板（15门单删0冗余，105对0冗余）。
- `experiments/dqi/20261106_eeakernel_fusion/boundary_fusion.py`
  （间隙审计 + norm 模板精确删除）。
- `experiments/dqi/20261106_eeakernel_rewrite/` 全套精确否定证据链。

## 判定

- 纯经典 EEA 核（products+norm）在删1/删2（products 扩至删4与有界2→1）
  意义下精确最小；跨块边界融合因 scalar 含 R/HMR 而无法用经典 ANF 判定，
  需升级验证手段（官方 verifier / Z3）。
- 本轮仍无实质收益。P2 剩余：scalar 块的量子感知重写（大投入），
  或 convert/unconvert 级数据流融合设计。
