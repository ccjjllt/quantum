# `9fcda0c1` 同形残余扫描（相对 `e9f54be3`）

日期：2026-11-11；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**纯静态**——只读两电路 kmx，不构建候选、不运行验证器。
方法复用 `experiments/dqi/20261110_e9diff/` 的 `stage_census.py` + `residual.py`
（kmx 解析 + `INFO_TAG @enter/@exit` 栈顶阶段标记；付费门 = CCX/CCZ/CSWAP/CCX_CARRY；
模板 A：CSWAP 后 80 行内双目标均 HMR；模板 B：CCX…单 CZ…同 CCX sandwich，15-op 窗）。
e9 的模板 A/B 0 残余结论不继承，本轮在 9f 上重跑确权。

固定输入（只读，未复制/修改）：
- `e9f54be3`：`/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmb`
  （SHA-256 `e9f54be3…ee969bc4`，892Q；即主仓库 `artifacts/20261110_public_candidates/ozer_v91/submission.zip` 内 `dqi.kmb`）。
- `9fcda0c1`：主仓库 `artifacts/20261111_ozer296/release/dqi.kmb`
  （SHA-256 `9fcda0c1…cbf36701`，892Q，只读）。
- kmx 中间产物（非仓库）：`e9.kmx`（既有）、`/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_9f/ozer296_9f.kmx`
  （本轮新落盘 792,824,704 B；e9.kmx 792,824,608 B；差 +96 B）。

## 1. `stage_census`：−2 落在 unextract（CCX −2）

`stage_census_9f.py` 输出（`artifacts/20261111_newcirc_residual/stage_census_9f_vs_e9.json`）：

| 指标 | e9 | 9f | Δ |
|---|---|---|---|
| total paid | 395,586 | 395,584 | **−2** |
| total ops | 58,269,417 | 58,269,423 | **+6** |
| qubits | 892 | 892 | 0 |
| `unread_ccx_before_hmr` | 0 | 0 | 0 |

分阶段 Δpaid / Δ门类 / Δops（其余六阶段全 0）：

| 阶段 | e9 paid | 9f paid | Δpaid | ΔCCX / ΔCCZ / ΔCSWAP | Δops |
|---|---|---:|---|---|---|
| unextract | 96,881 | 96,879 | **−2** | **−2 / 0 / 0** | **+6** |

e9 侧 unextract：ops 5,794,499，CCX 94,295，CSWAP 1,536，CCZ 1,050；
9f 侧 unextract：ops 5,794,505，CCX 94,293，CSWAP 1,536，CCZ 1,050。
静态计分（沿用 `20261110_arch_review` 口径 −1 门 ≈ 947,843 分）：−2 门 ≈ −1,895,686 分
（≈ −0.0005%；与任务给出的作者侧 374685006335.94 vs e9 低约 0.0005% 同量级，本机未重跑验证器）。

−2 形态（paid 对齐 + 行号窗核验，非 A/B）：
paid 对齐 unextract 4 hunk（del 4 / add 2，净 −2；归一化 CCX 控制可交换，lookahead 500）：

| # | E9（del） | 9F（add） | 行号 |
|---|---|---|---|
| 1 | `CCX q886 q862 q868` | `CCX q886 q862 q840` | E:52197194 / N:52197194（替换目标线） |
| 2 | `CCX q851 q841 q867` | —（删；N 侧对应 `CX q840 q867` + `HMR q840` + `CZ q851 q841 if`） | E:52199574 / N:52199575–52199577 |
| 3 | `CCX q872 q870 q860` | `CCX q872 q870 q868` | E:52755199 / N:52755202（替换目标线） |
| 4 | `CCX q880 q863 q843` | —（删；N 侧对应 `CX q868 q843` + `HMR q868` + `CZ q863 q880 if`） | E:52760675 / N:52760679–52760681 |

两对联动（新模板 C，非 A/B；CCZ 总数不变，ops +6）：
- 对 1：`CCX q886 q862 q840`（目标改线）+ `CX q840 q868`（E:52197195 行位）
  …23k 行间隙 q840 零触碰（全区间 `q840` 仅 4 行：CCX 目标 / CX q868 / CX q867 / HMR）…
  + `CX q840 q867` + `HMR q840 b600000` + `CZ q851 q841 if b600000`
  替换 `CCX q851 q841 q867`。每对净 −1 paid、+3 ops。
- 对 2：`CCX q872 q870 q868` + `CX q868 q860`（N:52755202–52755203）
  …q868 间隙零触碰（仅 4 行：CCX 目标 / CX q860 / CX q843 / HMR）…
  + `CX q868 q843` + `HMR q868 b600001` + `CZ q863 q880 if b600001`
  替换 `CCX q880 q863 q843`。每对净 −1 paid、+3 ops。
- 合计 −2 CCX、+6 ops，与 census 精确 reconcile。无 CSWAP 参与（≠模板 A），
  无 CCX…CZ…同 CCX sandwich 且 CCZ 净 0（≠模板 B，每位点 −2 CCX +1 CCZ / −1 op）。

## 2. 两模板残余扫描：0/0（closed）

`residual_9f.py` 单遍流式扫描 9f 全电路 58,269,423 ops（`artifacts/20261111_newcirc_residual/residual_9f.json`）：
- (a) 模板 A 同形残余（CSWAP 后 80 行内双目标均被 HMR，其间无其他触碰）：**0 处**（分阶段亦 0）。
- (b) 模板 B 严格同形残余（CCX…单 CZ(c,t)…同归一化 CCX，t 无其他触碰，15-op 窗）：**0 处**。
- 分阶段宽度画像（同遍统计）：extract/synthesis/unsynthesis/unextract 均为 892 distinct（max 891）；
  convert/unconvert 891；scan 851（max 890）；initial/uninitial 840。与 e9 画像一致，无宽度变化。

判据（任务口径：残余 ≥1 处且静态 −1 门以上 ≈ ≥947,843 分即输出位置+改写，否则关闭）：
**残余 0 处 → 关闭**。e9 的 0 残余结论未继承，本轮已在 9f 上重跑确权。
−2 本身是已落盘的新模板 C（§1），不是 A/B 残余；模板 C 的泛化残余不在本轮两模板口径内。

## 3. 验证范围声明

- 本实验**未构建候选、未运行官方验证器**（DQI 102400-shot 未触发；
  `data/competition` 验证器未改动、未调用；任务给出的作者分 374685006335.94 为输入引用，本机未重跑）。
- 数字来源：本工作区 `artifacts/20261111_newcirc_residual/stage_census_9f_vs_e9.json`、
  `residual_9f.json`（+ 本 README §1 行号窗 `awk`/脚本核验）。
- 谱系引用：`experiments/dqi/20261110_e9diff/README.md`（模板 A/B 定义、e9 0 残余、计分口径）。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix）；中间 kmx 落盘
  `/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_9f/`（非仓库），仓库内仅
  `experiments/dqi/20261111_newcirc_residual/` + `artifacts/20261111_newcirc_residual/`。

## 复现

```bash
.venv/bin/python experiments/dqi/20261111_newcirc_residual/stage_census_9f.py
.venv/bin/python experiments/dqi/20261111_newcirc_residual/residual_9f.py
```
