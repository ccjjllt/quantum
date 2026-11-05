# EEA重复内核I/O契约（2026-11-06，P2入口）

## 假设

DQI convert/unconvert联合改写（P2）需先为重复有限域内核建立
输入/输出契约 + 付费门 + 反向清理计数。最高频内核是 EEA `inverse12`
三件套（各169调用，贯穿2.7M~52.3M行）。

## 改动

- 只读：891Q kmx 单遍流式普查（`census_blocks.py`，嵌套感知）；
  不改候选，不跑验证。

## 观察（已执行，有JSON为证）

- `inverse12 products` ×169：全同构（30线 / 25 CCX / 835 CX / 无HMR），
  首例只读线 `[850, 877]`（2线），其余28线被写；169实例线集两两不同
  （169 distinct sets）——同构不同数据，跨实例共享需数据流分析，
  不能直接复用单例证明。
- `inverse12 norm` ×169：162×标准（22线/15CCX/202CX）+ 7×变体
  （23线/203CX，多1线1CX）；无HMR。
- `inverse12 scalar` ×169：7种形状（18~23线 / 18CCX / 437~442CX），
  **全含HMR**（125×主形18线437CX + 44×变体）；另含81 CZ + 1 X（首例）。
- 三块 paid 合计：products 4225 + norm 2535 + scalar 3042 = 9802 CCX，
  占全电路397177的 **2.47%**。即使50%优化 ≈4900T ≈4.1×回本线
  （1188T=+0.1%GM），但50%不现实；现实共享5~10% ≈500~1000T，
  在回本线上下——需真凭实据的跨实例公共子表达式，而非假设。
- `multiply v`/`full_head_product` 接口已证伪 drop-in（见 qq51 README）：
  20→7 与 (6+6)→(6+6) 双线性，非 24→12 全乘。

## 证据

- `artifacts/20261106_qq51_count/inverse12_contract.json`
  （三块调用数×形状签名×首例线集/只读集）。
- `artifacts/20261106_qq51_count/blocks.json`
  （全块 paid histogram，嵌套感知）。
- 脚本 `census_blocks.py` / `count_blocks.py` / `count_qq.py`。

## 下一步（P2 主攻，需立项）

1. 相邻 `inverse12` 实例边界抵消检查（上例尾CX vs 下例首CX，
   同线同控即恒等；CCX 同理，需全仿真确认中间无改写）。
   CX 免费，重点看 CCX 对。
2. 跨169实例公共子表达式（同构模板 + 数据流对齐）。
3. convert/unconvert 融合：共享 `norm`/`scalar` 前缀。
- 本轮仍无实质收益；以上是改写的必要地基，非收益本身。
