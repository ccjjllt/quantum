# Fix3: coarse/物理地址结论降级为采样证据（invsqrt §2-3）

范围：只复核 Track A（`trackA_semantics.md` §5–§6、`gap_probe.py/json`、
`physaddr.py/json`）的 coarse 控制字与 physaddr 变化类结论；
不写显式布尔函数（仍 open），不跑官方验证，不改 verifier。

复现（2026-11-02 实测）：

```
uv run python -c "<Fix3-coarse 段：gap_probe.json 前 15（Hphase）vs 后 26（Lphase）的 addr/delta/s varies>"
uv run python -c "<Fix3-scope 段：input_coords.decompose 对 addr/delta/s 三组样本的坐标覆盖>"
uv run python -c "<Fix3-phys 段：physaddr.json 各切点变化类汇总>"
```

## 1. 降级声明

`trackA_semantics.md` §5 “coarse 控制字：基本解决……是 `(address, s)` 的
纯函数”与 §6 物理地址编码结论，自即日起降级为**采样证据**（directed-sample，
非证明）。采样范围（三种单坐标样本，全在 `lz=0` 附近单线上，见 §2）之外
的任何 `(address, s, delta)` 组合行为均未测定；显式布尔函数形式仍待写；
`LUT_c` 仍 open（无 256 项系数表值级解码）。

## 2. 采样范围（实测，`decompose` 逐点验证）

| 样本组 | 点数 | 实际覆盖 | 未覆盖 |
|---|---|---|---|
| address-only | 128（`x=2^21+(t<<14)`，t=0..127） | `lz=0, delta=0` 单线；a 128 个互异 | 非零 delta、lz≠0 处的地址行为 |
| delta-only | 17 条目→**16 个互异**（`x=2^21+d`，d=`[0,1,1,2,4,…,8192,16383]`，`1` 重复：字面 `1` 与 `1<<0` 撞车） | `lz=0, a=0` 单线；16384 个 delta 中只测 16 个 | a≠0 处的 delta 行为；delta×address 交互 |
| s-only | 22（`x=2^(21-lz)`，lz=0..21） | 尾数固定（`(a&127)=0, delta=0`）；**parity 随 lz 奇偶交替**（a=0/128，见下） | parity 固定时纯 s 行为（样本设计即混杂，见 R2） |

Hphase 15 条（ops 15253…15573，q28）复核：128 地址全变、22 s 全变、
17 delta 全不变（deltaOnes 为 0 或 17 即常量，与旧结论一致）。
Lphase 26 条（ops 25687…，q50）复核：41/41 地址变、41/41 s 变、
**19/26 delta 变**——delta 依赖在电路中确实存在，故 coarse 的
“与 delta 无关”不得外推到 Hphase 之外，更不得读作一般性质。

## 3. 已登记反例逐一复核

- R1（delta 样本缺陷）：`physaddr.build_samples` 的
  `delta_vals=[0,1]+[1<<b]+[16383]` 含重复 `1`（17 条目 16 互异），且整组
  钉在 `(lz=0,a=0)` 单线上。修正：计数改记 16 互异 delta；
  “delta 全不变”结论限缩为“在该单线上 15 条 Hphase 控制不变”
  （Lphase 反例见 §2：19 条变）。
- R2（s-only 空类混杂）：`physaddr.json` 中 `post_complement_23` 有
  s-only `[21,22]`，而 `addr_probe_1200`/A/B/Lphase 各切点 s-only 为空——
  “s-only 无纯类”只是切点相关现象。更根本的是样本混杂：s 组 22 点的
  `(a,parity)` 为 `(0,0),(128,1),(0,0),(128,1)…`（`s=0` 同时出现在
  lz=0/p=0 与 lz=1/p=1），任何在 s 样本上变化的线都可能响应的是 parity
  而非 s。修正：`mixed(a,s)`/`s-only` 分类改记“s/parity 未解混”，
  不得归因于 s；`gap_probe` 的“s 全变”同样只在该混杂样本上有意义。
- R3（A 入口/出口混淆并修正）：`gap_probe.json` 的 `lut_c_candidates`
  键是 `addr_probe_1200`、`A_entry_16127`、`B_entry_20738`、
  `Lphase_entry_25687`——根本没有 A 出口数据；`trackA_semantics.md`
  §5–§6 却写“A 出口 address-only 19 线”“A 出口 delta-only 8 线”。
  查 `physaddr.json`：`A_entry_16127` address-only 恰为 19 线
  `[14,15,16,17,18,19,25,31,33,38,40,41,43,44,45,47,53,55,58]`，
  与文本“A 出口 19 线”逐线一致——文本把**入口**数据标成了出口。
  真出口即 `B_entry_20738`（A 区止于 20738）：address-only 16 线、
  delta-only 6 线 `[7,8,9,10,11,12]`。修正命名：A_entry 19 线 / A_exit≡B_entry
  16 线 / Lphase_entry 3 线 `[15,43,44]`；“A 出口 19 线与 B 入口 16 线并列”
  的表述作废。M 解码 8 线候选 `[0,1,7,8,9,10,11,12]` 实为 **A_entry**
  视角的 delta-only（`A_entry_16127` delta-only 逐线一致），不是出口数据；
  到 B_entry 时 q0/q1 已不在 delta-only 类中（缩为 6 线），到 Lphase_entry 为
  `[1,7,8,9,10,11,12]` 7 线——M 候选的切点依赖性即此，同样降级为采样证据。

实际命令输出（粘贴）：

```
vary counts {'addr': 41, 'delta': 19, 's': 41}
15253 q28 addrV= True deltaV= False sV= True deltaOnes= 0
15269 q28 addrV= True deltaV= False sV= True deltaOnes= 17
...（15 条 Hphase 全为 addrV=T, deltaV=F, sV=T；25687 起 Lphase 19 条 deltaV=T）
delta coverage: [0, 1, 1, 2, 4, 8] ... total 17 of 16384
s_xs: x=2097152 lz=0 a=0 / x=1048576 lz=1 a=128 / ...（parity 逐点交替，s 每值占两种 parity）
cuts: Lphase_entry_25687 address-only 3 / B_entry_20738 address-only 16 / A_entry_16127 address-only 19 / post_complement_23 s-only [21,22]
```

官方验证：0 shots（未运行）。Kaggle 提交：无。
