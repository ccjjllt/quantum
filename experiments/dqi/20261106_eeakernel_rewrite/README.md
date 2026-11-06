# P2 联合改写第一步：全文件自逆对消 peephole（2026-11-06）

## 假设

EEA 重复内核（`inverse12` 三件套各169调用，`multiply v`×12，
`full_head_product`×6）内部或边界若存在相同双量子比特门紧邻重复
（中间无实质操作），`U^2=I` 可删一对。先做全文件精确扫描
（CCX 382636 + CSWAP 13064 + CCZ 1477 = 397177，恰等于官方
`operation_statistics().num_toffoli_like`，解析覆盖率自证）。

## 方法（已用合成电路验证）

- 单遍流式，倒排索引（`by_wire`/`by_swap`），约2分钟。
- 精确对易守卫（`U^2=I` 对必须可交换才能删）：
  `P=CCX(a,b,t)` 遇 `CCX(c,d,e)` 当且仅当 `e∈P` 或 `t∈{c,d}` 才杀；
  控制线读取不杀（已证交换）；CZ/Z 只杀 swapped/target 线；
  CCZ 对不进 `by_swap`（对角恒交换）；R/其他按写杀。
  合成小电路（控制读 + 对角 + R 阻挡各一例）5对全中、1杀正确。
- 假阳性教训：初版写杀伤报214对，实为读控制线的合法对易
  （例 `CCX q866 q887 q847` 读 `q887`）→ 一律显式仿真/对易证明，
  不只看末态。

## 观察（2026-11-06已执行）

- 全文件 `n_cancelable = 0`（三类门合计零可消对）。
- `dirty_kills = n_scanned` 恰相等：经查为活集长期规模~1的
  计数恒等式（`live_end = adds - pairs - kills = 0`，末尾被测量清理），
  非 bug；小测试已证逻辑正确。

## 证据

- `artifacts/20261106_eeakernel_rewrite/peephole_all.json`
  （`n_scanned 382636/13064/1477, n_cancelable_pairs 0`）。
- 脚本 `peephole_scan.py`（CCX版，审计用）、`peephole_all.py`
  （CCX/CSWAP/CCZ精确版，验证用）。
- 合成验证：`/tmp/mini*_peephole.json`（仓库外，5对+1杀与手工一致）。

## 模板级公共子表达式（2026-11-06新增，最强阴性结果）

- 169× `inverse12 products` 经逐线重命名后**全同构**（860 ops/例，
  25 CCX + 835 CX），单模板结论 ×169 生效。
- ANF 精确提取（GF(2) 多项式，无采样）：最高二次；
  18 线纯线性 + 12 线含二次项；125 个不同二次单项式中 111 个被
  ≥2 个输出共享（最高一单项式供 10 个输出）。
- 精确删除 ladder（删 k 重算全 ANF 比对，非采样）：
  1-gate：25/25 必需；2-gate C(25,2)=300：0；3-gate C(25,3)=2300：0；
  4-gate C(25,4)=12650：0（10.2秒）。
- norm 模板（15 CCX，纯 CX+CCX）：单删 0 冗余，
  双删 C(15,2)=105 为 0，三删 C(15,3)=455 为 0
  （`../20261106_eeakernel_fusion/norm_redundancy.json`、
  `template_triples_norm.json`）。
- `multiply v` 模板（99 CCX，纯 CX+CCX，20→7 接口）：
  单删 0 冗余，双删 C(99,2)=4851 为 0（169.7秒）。
  见 `multiplyv_redundancy.json`。
- `multiply v` 三删（C(99,3)=156849）已全量完成：156849/156849，
  0 冗余 0 blowup（`multiplyv_triples.json`，12 片累积，后台 nice 运行；
  `multiplyv_triples.py`）。
- `full_head_product` 三模板（126/168/210 CCX，纯 CX+CCX+SWAP）：
  单删全部 0 冗余（`fhp_redundancy.json`）；双删三模板全量完成
  （fhp126 7875 / fhp168 14028 / fhp210 21945，全部 0 冗余 0 blowup，
  `fhp_pairs.json`，fhp210 因单轮超时分 4 片累积完成）。
- `full_head_product` fhp126 三删（C(126,3)=325500）已全量完成：
  325500/325500，0 冗余 0 blowup（`fhp_triples.json`，10 片累积，含后台
  nice 运行；`fhp_triples.py`）。
- 有界 2→1 替换（7 个窄差异对 × 对内+差异线三元组 × 2 插入位，
  `tried 2460`）：14 个原始命中经核查**全部是平凡自替换**
  （`ins=j` 分支实际测的是 1→1 恒等：被换门与候选门逐字相同，
  如 `q840 q880 q870`；实验设计 bug，已修正口径并保留原始记录
  `template_2to1_raw.json`）。**真实 2→1：0。**
- 结论：products/norm/multiplyv/fhp126-168-210 模板在删1（fhp/norm/products/multiplyv）、
  删2（products/norm/multiplyv/fhp全模板）、删3（products/norm/fhp126/multiplyv）
  删4（products/norm）及有界 2→1意义下精确最小；125 单项式由 25 门高度共享已是紧的。
  进一步压缩需 3→2/更大联合重综合（非删除型）或跨实例数据流融合。

## 下一步

- (a) 模板级公共子表达式（跨169实例，需数据流对齐，非句法）；
- (b) convert/unconvert 融合（`norm`/`scalar` 前缀共享）；
- (c) `full_head_product`（168T）重综合（非 51T drop-in，已证接口不符）。
- 本轮仍无实质收益。
