# joint_decode.md：QROM 联合解码（B+A 同 decode，双 pattern）—— 省 2 次 254-CCX 解码

分支 `invsqrt-generator-rebuild`。基线：二分 lz 版 `narrow_v62.py`（Q=132，
SHA `813ba1ad…`，官方 PASS 1307880.53，见 `bs_lz.md §6`）。
本轮只做 QROM 联合解码一事：正向 `F_B + F_A_LOAD` 合并为一次 unary decode
下的双 pattern 装载；逆向 `R_A_UNLOAD + R_B` 合并为一次联合 pass。
`F_A_UNLOAD` 保持独立（A1 在中间）。不动拟合表（只读 BOTH）、不读旧 KMB/tray、
不截位；止于预筛，未跑官方 200M-shot。
产物只在 `experiments/invsqrt/20261102_generator_v2/`（本文 + `narrow_v62.py`
单线续改 + `prescreen_narrow_v.py` dump-v 联动 + REC_SHA）与
`artifacts/20261102_generator_v2/invsqrt/`（`narrow_v62.kmb`、
`narrow_v62_stats.json`、`joint_proof.log`、`joint_prescreen.log`、
`joint_contract.log`）。

## 0. 文件取舍（延续 narrow_v62.py 单线，理由）

- 本任务与 TH 收窄/二分 lz 同属“同一容器、同一系表、同一调度上的增量块替换”
  （只把两处相邻 mini-pass 并为联合 pass，不动 V 容器 `vd46/Vn30`、A/R 位宽移位、
  B 位偏移、S1 二分、S6、合并、整数 oracle）。同 `bs_lz.md §0` 论证：
  另起文件会分叉 double-build 谱与 REC_SHA；单线新旧 SHA 直接对比证明“只并了解码”。
- 旧 SHA `813ba1ad…`（二分版）对其对应电路继续有效、不被取代；作废含义仅为
  “旧值不适用于本电路”（A 门用新值 `6f6a144d…` 比对）。Q_CAP 保持 **132**。

## 1. 配对论证（前提任一不成立即否决该配对）

mini-pass 结构（`qrom.md`）：现配 addr → 显式形成 → 单 sweep → 解散；
同 pattern 重放即卸载（CX 自逆，0 Toffoli）。`window_qrom.md` 实测：
每 sweep 解码费 254 CCX（`range(256)` 下 `(a^b).bit_length()−1` 移动费总和，
与数据无关），数据只改免费的 CX 条数。

### 1.1 正向对：F_B（目标 Vn 零初态）+ F_A_LOAD（目标 coef 零）→ 联合装载

- **J1 零初态**：联合点前 coef 全零（S1 二分/S2 归一化/D 原地变换皆不碰 coef，
  `build_forward_nv` 顺序保证）且 Vn 全零（vd 新分配，行尚未作用）。
  零初态是关键前提：XOR 即整数加仅在零初态成立。小例反例（`joint_proof.log`）：
  `init=31, tab=8` 时 XOR=23 ≠ ADDmod=7。代码不断言量子零（静态不可见），
  以调度顺序 + 预筛 B（全 scratch 归零）+ DUMP-V（Vn 逐点精确）为证据。
- **J2 目标独立**：Vn=`vd[16:46)` 与 coef 分属不同寄存器，无交叠；
  同 match qubit 下两组 CX 可任意序（均为对合且目标不交），联合 sweep
  = 两次独立 sweep 的异或效果（小例 32/32 穷举证）。
- 否决记录：`F_A_UNLOAD` 不参与——A1 在中间（Vn 已脏，B 驻留待 R1 继续用）。
  R 对不参与——square-2 在中间（coef 已脏，S 驻留）。

### 1.2 逆向对：R_A_UNLOAD（coef 回零）+ R_B（Vn 回零）→ 联合卸载

- **J3a coef 自洽**：联合点前 coef 恰为 A 表值。`R_A_LOAD` 重装后 `A1_rev`
  只读 coef（`_tha1_*` 以 coef 切片为源 S，不写），故回放精确归零。
- **J3b Vn 自洽**：联合点前 Vn 恰为 `B>>4`。`A1_rev` 精确撤销 A1 贡献
  （A1 子行已由 `th_carry_proof` + 全电路 B/DUMP-V 覆盖），回放即 B 卸载。
- **J3c addr 自洽**：D 恢复、S2_rev、S1_rev 均在联合之后；A1/square/R1/S6
  皆只读 x/lz、不写，故联合点 addr 重算值与正向同，同一 match 语义。
- 以上三项分别论证（非一句“镜像故成立”）：J3a 由内核读写表得，J3b 由
  A1 可逆性 + DUMP-V/预筛 B 得，J3c 由调度顺序得。若任一不成立则否决该配对
  （本轮三项皆成立；若只正向成立则只做正向——实际双向皆 PASS）。

## 2. 证明（小例先证，PASS 后进生成器）

脚本仓库外 tmp（不进产物），4 位地址 16 项穷举，B 切片带 lo 偏移
（`W_B=5, B_LO=1`，与真机 `B[4:33)` 同构），A 全宽：

```text
seq load:   q=17 instr=340 ccx=28 toff=28
joint load: q=17 instr=201 ccx=14 toff=14
joint rt:   q=17 instr=402 ccx=28 toff=28
joint==seq==table: 32/32 ok
joint roundtrip unload-to-zero: ok
nonzero-init: init=31 table=8 xor=23 addmod=7 got=23 XOR-confirmed (ADD would differ)
JOINT-PROOF PASS
```

读法：联合装载 = 两次独立装载的异或效果（32/32：16 地址 × B/A 两表），
重放即卸载归零；解码费减半（28→14，小尺寸 N=16 下每 decode 14）；
非零初态反例钉住 J1 的必要性。见 `joint_proof.log` 全文。

## 3. diff（vs 二分版 `813ba1ad…`）

- `narrow_v62.py`：新增 `qrom_sweep_joint_ba`（单 decode 双 pattern，
  B `B_LO+29` 切片断言 `==W_B` + 双目标宽度断言）与 `joint_pass_ba`
 （装载与卸载同体，CX 自逆）；`build_forward_nv` 的 `F_B + F_A_LOAD`
  双 mini-pass 并为 `F_BA_JOINT` 单 pass；`build_reverse_nv` 的
  `R_A_UNLOAD + R_B` 并为 `R_AB_JOINT` 单 pass。`mini_pass_off` /
  `qrom_sweep_off` 保留（B 位偏移 sweep 原语，无活跃调用者；`W.mini_pass`
  仍供 F_A_UNLOAD / R_A_LOAD / R 对用）。STAGE 名新旧对照：
  `F_B/F_A_LOAD → F_BA_JOINT`，`R_A_UNLOAD/R_B → R_AB_JOINT`。
  整数 oracle `nv_model_phase` **未动**（数学终值不变，合同 maxrel 同值）。
- `prescreen_narrow_v.py`：`dump_v` 前缀联动换联合装载（与生成器同路）；
  `REC_SHA → 6f6a144d…`。

## 4. 成本对比（实测）

| 口径 | 二分版（`813ba1ad…`） | 联合解码（本任务，`6f6a144d…`） | 变化 |
|---|---|---|---|
| Q（num_qubits） | 132 | 132 | 0（addr/unary 暂存现配现释，峰值仍在行） |
| `toffoli_like`（CCX+CSWAP） | 9676 | **9168** | **−508（−5.25%）** |
| CCX / CSWAP | 9288 / 388 | **8780** / 388 | −508 / 0（纯 decode，符合预期 −2×254） |
| CX | 36800 | **36258** | −542（两 pass 的 addr 形成/解散 + unary 开销） |
| `num_instructions` | 90354 | **85720** | −4634（含每 move 的 PUSH/POP 等开销） |
| Q×toff（静态） | 132×9676=1277232 | **132×9168=1210176** | **−67056（−5.25%）** |
| 文本 SHA | 813ba1ad… | 6f6a144d… | 新 REC_SHA（A PASS，double-build `str` 相等） |
| maxrel 全域（合同重跑） | 0.8712321494 | **同值**（模型未动） | 仍 <1 PASS，最坏 x=1796095 不变 |
| min_margin 全域 | 105643461 | 同值 | 仍 >0 |
| 16 样本 C | 全 >0（最小 524594562 @2097151） | 全 >0（逐点同值，dphase 全 0） | 全 >0 |
| 官方验证 | PASS 1307880.53（二分） | **未跑**（门禁） | — |

预筛证据（EXIT=0，全 PASS）：

```text
uv run python .../narrow_v62.py
  sha256=6f6a144d… qubits=132 double-build str 相等（A 门前置）
uv run python .../prescreen_narrow_v.py --a --b --c --dump-v
  sha1=sha2=recorded=6f6a144d… → PRESCREEN-A PASS
  checked 16 samples x 132 qubits: x-recovery ok, scratch all zero: True → PASS
  16/16 dphase=0，余量全>0（最小 524594562 @2097151）→ PRESCREEN-C PASS
  16/16 Vn 精确一致 → DUMP-V PASS   # joint_prescreen.log
uv run python .../prescreen_narrow_v.py --contract-full
  checked=3133452 fails=0 maxrel=0.8712321494 worst=(1796095, 3.87e-11)
  min_margin_units=105643461.0 ... CONTRACT-FULL PASS  # joint_contract.log
```

16 样本同各线：`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`。

## 5. 下一步

- 送官方 200M-shot 验证（门禁，需主线程确认；静态 −5.25% 的 score 跟进幅度
  以实测为准，不 claim；预期 ~124w 量级）。
- 剩余 QROM（现共 8 扫：每方向联合 1 + A 单扫 1 + R 对 2）已无同类相邻可并：
  凡有算术夹在中间的对（正向 A 卸载↔R 装载隔 square-2；逆向 R 卸载↔A 重装隔
  square-2 逆）皆目标脏，不并。R 表 12 位分包线已由 `window_qrom.md §3` 否决，不重开。
- 若官方 score 口径下 HMR/R 权重稀释 toff 收益，回退只需把两处联合 pass
  换回双 mini-pass（STAGE 名 revert，REC_SHA 回 `813ba1ad…`），diff 局部。

## 完整官方验证 PASS（2026-11-02，主线程，seed 20261031）

`artifacts/20261102_generator_v2/invsqrt/verify_joint_seed20261031.log`（EXIT=0）：
`status=PASS`，200,540,928 shots，`score=1240824.5265214771`
（相对二分 lz 版 1307880.53 **−5.1%**，与静态 −5.25% 吻合；约为基线 12.3 倍），
`num_qubits=132`，`toffoli_count=9168`，`worst_error_over_tolerance=0.8712321628530258`
@ x=1796095（不变），`circuit_sha256=c258ec72…`。
