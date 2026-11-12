# DQI direct-phase/MBU family bet：第一实验（2026-11-12）

## 假设

DQI 的 uncompute 三段（unextract + unsynthesis + unconvert）占 ~51% T。若
phase 是一个可在 uncompute 之前施加的独立块，则可用 X-basis MBU / direct
phase bit 替代一部分 uncompute，目标 T 394k → 300k 以下（GM +5% 以上）。

## 第一实验：eae396ba 的 stage/phase census（只读）

输入：`artifacts/20261112_eae_candidate/dqi.kmb`（SHA `eae396ba…785bd`）。
方法：转 `.kmx`，按 `INFO_TAG @enter/@exit` 栈顶分阶段，统计 paid 与
`Z_POW/CZ/CCZ/Z/NEG`。脚本：`stage_census_eae.py`、`phase_census_eae.py`；
JSON：`artifacts/20261112_direct_phase/`。

### Stage map（static paid）

| stage | paid | CCX | CSWAP | CCZ |
|---|---:|---:|---:|---:|
| extract | 58,742 | 58,550 | 192 | 0 |
| synthesis | 31,635 | 31,611 | 24 | 0 |
| convert | 60,663 | 56,095 | 4,568 | 0 |
| scan | 44,275 | 44,275 | 0 | 0 |
| unconvert | 62,534 | 56,794 | 5,668 | 72 |
| unsynthesis | 40,429 | 40,146 | 24 | 259 |
| unextract | **103,035** | 98,587 | 1,536 | 2,912 |
| total | **401,313** | | | |

uncompute 三段 = 205,998 / 401,313 = **51.3%** static。

### Phase 分布

`CZ/Z/CCZ/NEG` 不是末尾独立块，而是贯穿所有阶段：

- extract: CZ 110,866 / Z 8,398 / NEG 103
- convert: CZ 185,727 / Z 2,976 / NEG 2
- scan: CZ 92,575
- unconvert: CZ 198,696 / Z 6,568 / CCZ 72 / NEG 104
- unsynthesis: CZ 107,805 / Z 8,159 / CCZ 259 / NEG 47
- unextract: CZ 125,333 / Z 25,117 / CCZ 2,912 / NEG 318

## 判决：简单“phase 提前 + MBU 清理”不可行

- unextract 的 125,333 CZ + 25,117 Z + 2,912 CCZ 说明 phase 在 uncompute
  内部逐点加载；没有可整体搬移的末端 phase 块。
- 这与仓库此前的 liveness 结论一致（unextract 目标全程 live；无 Z-basis 测量），
  但本轮给出了 phase 门级的直接证据。
- **no-go**：不做局部 phase 搬移/局部 HMR 清理。
- **仍可做的 family bet**：换一个直接由 syndrome 计算 phase 的新解码器
  （paper arXiv:2610.22367 的 direct phase / X-basis MBU 思路），目标是把
  uncompute 从“逆电路”变成“测量 + 相位反馈”。这是新的架构，不是局部重写。

## 下一步（2 周 checkpoint）

1. 读 paper 的 discovered circuit 与 direct-phase 构造，列出其 phase 依赖的
   syndrome 子集；与本电路的 70 个 12-bit syndrome 对比。
2. 选一个可独立测试的子块（例如 GF(64) inverse-character phase 的 28 个
   call site），写出 direct-phase 版本并切片验证相位。
3. Go 条件：子块 T 降低 ≥10% 且 4,096 输入/mask 全过；否则关闭该 family bet。

范围：本轮只读 eae `.kmb`/`.kmx`，未构建候选、未跑 102,400-shot verifier。
