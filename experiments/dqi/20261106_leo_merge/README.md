# DQI 合并收益：fd0ef + Leo Tang 编辑 = −42 mean Toffoli（2026-11-06）

## 收益（官方验证器全量 102400 shots，默认 salt）

| 文件 | sha256 | Q | mean T | value err | phase err | cost |
|---|---|---:|---:|---:|---:|---:|
| fd0ef（基线） | `fd0ef09e` | 891 | 396,904.5561 | 0 | **1** | 377,084,094,889.30 |
| **merged** | `b99bf233` | 891 | **396,862.4383** | 0 | **0** | **375,320,367,805.64** |

- **等 k 的纯收益：−42.1178 mean T = −0.010612% DQI cost = −0.003537% GM**
  （cost ∝ R(k)·Q²·meanT，Q 不变，故 Δcost = ΔT/T）
- 本次默认 salt 抽签另有 k: 1→0 的红利（−0.459%），合计实测 −0.46773%；
  这不是可复现收益，单独列出。
- 三独立 seed（12345/999/424242，1024 shots）meanT 差恒为 **−42.000**，
  错误剖面与基线逐项相同（0/0, 0/1, 0/0）——增益是纯门数，不是抽签。

### 全量 102400 两额外 seed（决定性）

| seed | fd0ef ve/pe, meanT | merged ve/pe, meanT | ΔT |
|---|---|---|---|
| 7 | 0/0, 396904.3382 | 0/0, 396862.3382 | **−42.000** |
| 11 | **2/0**, 396904.6540 | **2/0**, 396862.6540 | **−42.000** |

seed 11 上两份文件都出 2 个 value 错误（继承自基线的固有失败），
**错误剖面逐位相同**，ΔT 仍精确 −42.000：编辑保语义，不是靠改变
错误分布换门数。默认 salt 的 0/0 vs 0/1 是抽签差异，单列不并入收益。


## 怎么做的（新方法：公开改进的 diff 合并）

1. Kaggle CLI 可访问（`~/.kaggle/access_token`，用户授权）。
2. 发现 `alexchilton/24-80-lb-verified-three-task-portfolio` 的已验证缓存里
   有更便宜的 891Q DQI：Leo Tang `1c43b7ff`，cost 375,333,812,679（0/0）。
3. `kaggle kernels output leotang09/vqcc-t7421-submission` 取回该文件
   （sha256 校验 = `1c43b7ff`）。
4. 与 fd0ef 逐行流式 diff（98 个 hunk）：
   - fd0ef 的 **14 处 R41 缓存补丁在 Leo 文件里被还原**（+12 T）；
   - Leo 另有 **7 处 `unextract` 编辑，每处 −6 T**（合计 −42 T）；
   - 净 −28 T（与静态计数 397,149 vs 397,177 一致）。
   - 两者**区域不重叠**（R41 在 46.9M–50.8M，Leo 在 52.7M–55.7M）。
5. 按 hunk 取边合并：R41 区取 fd0ef 侧，其余取 Leo 侧 → 两者叠加。
6. 静态 T = **397,135**（= 397,177 − 42），CCX 382,594（−42）。
7. 官方验证器：3 seed 差分 + 全量 102400 shots PASS，0 value / 0 phase。

## 复现

```bash
# 1) 取 Leo Tang 输出（需 Kaggle token）
kaggle kernels output leotang09/vqcc-t7421-submission -p leoout
unzip -o leoout/submission.zip -d leo_x
# 2) kmb -> kmx（两个文件）
python -c "import kickmix as km; km.Circuit.from_file('leo_x/dqi.kmb',format='kmb').to_file('leo.kmx',format='kmx')"
python -c "import kickmix as km; km.Circuit.from_file('artifacts/20261105_maoxin_v2/release/dqi.kmb',format='kmb').to_file('base.kmx',format='kmx')"
# 3) 流式 diff 得 hunk，R41 段（<= 50732751 行）取 base 侧，其余取 Leo 侧
python experiments/dqi/20261106_leo_merge/merge_public.py base.kmx leo.kmx merged.kmx 50732751
# 4) kmx -> kmb，并用官方验证器
```

## 产物

- `merge_public.py`：通用 hunk 合并器（本方法可复用于任何同源近邻电路）。
- `artifacts/20261106_leo_merge/dqi_merged_b99bf233.kmb`（本地，不in git）
- `artifacts/20261106_leo_merge/diffhunks.json`：98 个 hunk 全文（审计用）
- 基线 R41 补丁文本即 hunk 中 `a0 <= 50732751` 的 `a` 侧。

## 判定与边界

- 这是**真实、可复现、等 k 的门数收益**（−42 T），非近似、非抽签。
- 未提交 Kaggle；未发布数据。salt 由文件字节决定，提交后是新的抽签。
- 方法学结论：**竞争公开文件的编辑互不重叠时可直接合并**，比从零搜索
  成本低得多、收益确定。下一步可把同一方法用到其它同源 DQI 变体上。
