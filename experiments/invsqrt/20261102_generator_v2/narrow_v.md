# narrow_v.md：窄 V 容器（结构性重设计第一步，电路实现）

分支 `invsqrt-generator-rebuild`。本任务动**主线 HMR 版**（`width_opt62.py`，
SHA 0075e006，Q=149，官方 PASS 2290413.64），另有 BOTH/A18 变体线
（`refit_variant62.py`，BOTH SHA da9d…，Q=149）**未动**——两线关系见 §0。
系表用 BOTH 系 `int_tables_R10_A20_quant.json`（只读，未改拟合表；
不读旧 KMB/tray）。本轮止于预筛（A/B/C+DUMP-V 16 样本 + 全域整数合同），
**未跑官方 200M-shot 验证**（门禁）。

新文件：`narrow_v62.py`（生成器）/`prescreen_narrow_v.py`（手动预筛，非测试文件，
非 CI）/本文件。产物：`artifacts/20261102_generator_v2/invsqrt/narrow_v62.kmb`、
`narrow_v62_stats.json`、`narrow_v_contract.log`、`narrow_v_prescreen.log`。

## 0. 动哪条线（说明）

- 主线 HMR 版 = `width_opt62.py`：全宽度 A(22)/R(12) + 窄行内核（A1 两级/R1 Cuccaro/
  S6 分级，copy 对已 HMR 化）+ V55 容器。本任务派生自它：行内核（HMR 结构）
  全部复用（`W._narrow_*`、`Q._qa1_*`），不动其文件（fallback 保留）。
- BOTH 变体线 = `refit_variant62.py`：只改 A/R 拟合位宽（wA=20/wR=10，sA=sR=2）+
  行移位；V 容器仍 55。本任务**复用它的 BOTH 系表与移位参数**
  （`Q.load_qtables("BOTH")`、`Q._qa1_*`），但 V 容器维度是独立正交改动，
  故新文件而非改变体线（同 `refit_variant62.py` 头注的 single-line 论证）。
- 主比较基线 = BOTH 变体（**同表**，Q=149/toff=14144/SHA da9d9491）；
  HMR 主线（异表，Q=149/toff=15146/SHA 0075e006）作次对照。

## 1. 重映射表（逻辑 V[0:55) → vd[0:46)/Vn[0:30)，Vn=vd[16:46) 视图）

vd 一次分配常驻（具名 x22+lz5+coef33+vd46=106）；Vn 是 vd 的视图，
行/QROM 全进 Vn；vd[0:16) 自分配至 S6 恒零（行片全在 Vn 内，square 不碰 vd）。

| 逻辑位 | 容器位置 | 处理 |
|---|---|---|
| V[0:16)（低 16，stream_vdrop 已证可丢） | 无（vd[0:16) 为零区，非数据） | 行低位不算（下）；S6 商低位真零（§2） |
| V[16:45)（29 有效位） | Vn[0:29)=vd[16:45) | B/A1/R1 全进此区（下表） |
| V[45]（恒零，V<2^45） | Vn[29]=vd[45) guard | 永不写入（B 只到 Vn[0:29)，行进位经全片传播但真 Vn<2^29，合同已验无回绕） |
| V[46:55)（恒零） | 无 | S6 wrap 目标 vd[0:16) 恒零 = 真值恒零（同主线 t+36≤55 论证） |

行放置（sA=sR=2，o=偏移；目标一律 Vn[0:30) 全片，进位向上传播到顶）：

| 行 | 逻辑贡献 | 窄实现（drop=16-o 位不算） |
|---|---|---|
| B 直装 | (B<<12)[12:45) | B[4:33)（29 位）→Vn[0:29)（位偏移 QROM `mini_pass_off`，表值未改） |
| A1 j=0..12（o=j+3≤15） | 减 Ahi<<(j+1+sA)（D_j=1 时） | 减 Ahi>>(16-o)（高 w'=20-(16-o) 位=coef[drop:20)）进 Vn[0:)；两级内核 n0'/n1' 按 w' 取半 |
| A1 MSB j=13（o=16） | 加 Ahi<<14 | 加全 Ahi（20 位）进 Vn[0:)（恰对齐容器底，不断位） |
| R1 j=0..9（o=j+2≤11） | 加 S<<(j+sR)（Rhi_j=1 时） | 加 S>>(16-o)（高 wp=17-(16-o) 位=coef[16+drop:33)）进 Vn[0:)；`_nvr1_row`（W 内核的 nS 参数版，HMR 原样） |
| S6（t∈8…19） | P=((V+2^(t-1))>>t)&mask | vd 即 Vd[0:46)（低 16 真零）：barrel 旋转量**同为 t**（vd 位序=Vd 位序，别名设计零偏移）；舍入控制 vd[45]（=旧 Vd[t-1]；t≤16 落零区→无操作，与模型一致）；商 vd[0:36)；t+36>45 高位 wrap 进零区按零处理；增量复用 `W._narrow_s6_inc_fwd`；逆向只逆数据不动 z_pow（D4 不变） |

断言重写（`assert_tables_nv`）：BOTH 形状（Ahi<2^20/Rhi<2^10/B<2^33）+
B 下界（逻辑值不变）+ 行静态断言（A 行 o<16、MSB o==16、R 行 o<16、
B 位偏移 W_B-B_LO==W_VN-1）+ Q_CAP=134（实测收紧，初值 160）。

## 2. diff（vs 主线 HMR 版）与一次失败记录

diff（`narrow_v62.py` vs `width_opt62.py` + `refit_variant62.py` 复用）：
- `create_regs_nv`：vd46 常驻 + `vn=vd[16:46)` 视图（替代 V55）。
- `mini_pass_off`/`qrom_sweep_off`：B 位偏移装载（表值只读移位，拟合表未改）。
- `build_a1_nv[_rev]`：截短 Ahi 高位 + `Q._qa1_*`（n0'/n1' 取半，HMR 内核不动）。
- `_nvr1_row_fwd/rev` + `build_r1_nv[_rev]`：`W._narrow_r1_row_*` 的 nS 参数版
  （S 取 coef 高位，HMR init_and/del_and 原样）。
- `build_s6_nv[_rev]`：vd 全片 barrel（量=t 不变）+ 同 inc/z_pow；逆向无 vd 分配。
- A/R QROM（全 Ahi/Rhi 进 coef）、square2、lz、地址、D、t 计算：**全未动**。
- 整数 oracle `nv_model_phase`（逐行截短累加，S6 由 Vd=Vn<<16 经
  (Vd+2^(t-1))>>t）：供 C/DUMP-V/全域合同用。

失败记录（诚实记，不硬凑）：初稿 S6 用 transient 46 位扩展 + 30 位 CX 拷贝
（正/逆各一、forward 不释放），实测 **Q=201**（>160 断言直接失败）。
原因：双容器常驻（Vn30 + vd46×2 期）。改别名设计（vd46 常驻、Vn 视图、
零拷贝、旋转量零偏移）后 Q=134。transient 方案已删，教训：barrel slack
用的扩展位必须与数据容器合并分配，拷贝式扩展必超。

## 3. 成本对比（实测）

| 口径 | HMR 主线（异表对照） | BOTH 变体（同表基线） | 窄 V（本任务） | 变化（vs 同表基线） |
|---|---|---|---|---|
| Q（num_qubits） | 149 | 149 | **134** | −15（−10.1%） |
| num_instructions | — | 122388 | 105708 | −16680（−13.6%） |
| toffoli_like | 15146 | 14144 | 11776 | −2368（−16.7%） |
| Q×toff（静态） | 2256754 | 2107456 | 1577984 | **−25.1%** |
| 文本 SHA | 0075e006… | da9d9491… | c1116ede… | 新 REC_SHA（下） |
| maxrel（全域） | 0.6096 | 0.6168 | **0.8712** | 仍 <1 PASS（最坏点迁至 x=1796095） |
| min_margin 全域 | 271129065 | 278774151 | 105643461 | 仍 >0（薄 2.6×，如实记） |
| min_margin 16 样本 | 271129065（x=2506015） | 539564521（x=2506015） | 524594562（x=2097151） | 全 >0 |
| 官方验证 | PASS 2290413.64 | PASS（refit 线） | **未跑**（门禁，止于预筛） | — |

REC_SHA 同步：`prescreen_narrow_v.py` REC_SHA=c1116ede…（A PASS）。
作废声明：旧 SHA（0075e006 主线、da9d9491 BOTH）**对其各自文件继续有效、
不被取代**；作废含义仅为“旧值不适用于本电路”（本线 double-build 从不产生旧值，
A 门用新值比对）。Q 构成：具名 106（22+5+33+46）+ 行/inc 暂存峰值 28=134
（峰值不在 S6：106+19=125；行 TH 长尾 iadd 主导）。

Q 未达 stream_vdrop “省 ~25Q”预估（-15 vs -25）：差额 10Q 在 S6——barrel
wrap-to-zero 论证要求 Vd[0:46) 全 live（16 零区常驻），容器只能 55→46
（名义 −9），行暂存 44→~28（−16），合计 −15 中 S6 零区占 +16 回吐。
如实记，不 claim 预估。

## 4. 预筛证据（命令 + 输出要点，全 PASS）

```
uv run python experiments/invsqrt/20261102_generator_v2/prescreen_narrow_v.py --contract-full
  checked=3133452 fails=0 maxrel=0.8712321494 worst=(1796095, 3.87e-11)
  min_margin_units=105643461.0
  Vn_range=(189812578,379625054) out_of_[0,2^29)=0 max|Vn-(Vtrue>>16)|=10
  CONTRACT-FULL PASS   #（逐行截短比 Vd 整体截短多丢低位进位：maxrel 0.62→0.87，仍<1）
uv run python .../prescreen_narrow_v.py --a
  sha1=sha2=c1116ede…=recorded → PRESCREEN-A PASS（Q_CAP=134 收紧后重验亦 PASS）
uv run python .../prescreen_narrow_v.py --b
  checked 16 samples x 134 qubits: x-recovery ok, scratch all zero: True → PASS
uv run python .../prescreen_narrow_v.py --c
  16/16 dphase=0，余量全>0（最小 x=2097151 margin 524594562）→ PASS
uv run python .../prescreen_narrow_v.py --dump-v
  16/16 Vn 精确一致（含 t=8…14/18/19；t=15/16/17 由全域合同覆盖）→ PASS
```
完整输出：`narrow_v_contract.log`、`narrow_v_prescreen.log`。
16 样本同各线：`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`。

## 5. 下一步

1. 送完整官方验证（200M-shot，门禁外，需主线程确认；余量最坏点已迁，
   送验前重看 min_margin 105M 是否够厚）。
2. 行 TH 长尾：Tslice 全片 30 致 `iadd(c2→TH)` 暂存 ~23（新峰值 134 主导项）；
   TH 高位恒 B-主导零区？若证 Vn[20:29) 行和恒零贡献，可缩 Tslice→再 −5~8Q。
   （需整数先行，禁令遵守，本轮未做。）
3. coef 33 未动（S17 全精度保留，平方/R 行正确性所系）；vd 低 16 零区
   常驻 16Q 是 barrel 精确性的代价，动它需先改 S6 结构（mux 方案已论证否决，
   见 §2 失败记录的反向教训——复杂度换 6Q 不值）。
4. 远目标仍远（Q×toff −25%，非量级解），如实记。
