# Fix1: value-ID 用法 sweep + booleq62 重判（invsqrt §2-1）

范围：只扫 `experiments/invsqrt/20261102_hw06_opt/cone_scan62.json`、
`retain_chain2_62.json`、旧 `dataflow62.py` prefix 结论（ahmed 坐标，
结论经 gap_probe 平移到新基线）中“不同 ID 即反例 / 即不等”的用法；
不扩展旧扫描窗口（gap≤200、链 SRC/COPY、prefix 切片都不重划），
不跑官方 200M-shot 验证，不改 `data/competition/verifiers/`。

复现（2026-11-02 实测，exit 0；Z3 一条约 62s）：

```
uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test
uv run --with z3-solver python -c "<Fix1-Z3 段：retain_chain2 首分叉对，48 自由变量，timeout 60s>"
uv run python -c "<跨解释器段：同函数在两个 Values() 中得 5 vs 6；异函数跨 run 撞号 6>"
```

## 1. 判定规则（booleq62.py 工作区已提交版，git show HEAD 为准）

- 相同 value-id ⇒ 等价：成立（充分条件）。同一次 `interpret` 内
  `Values.vid` 按 frozenset 内容 hash-cons，相同 frozenset 在任何 env 下
  求值一致，故该方向可靠；`retain_chain62.py` 的 sig-equal 池上界
  （11 C / 9 parts）与 coherent `boolean-exact` 行不受本次修正影响。
- 不同 value-id ⇒ 不等：撤回。反例就是 booleq62 自检本身：
  `q14 AND NOT q21`（指定式） vs `q14 XOR (q14 AND q21)`（门级形式）
  是不同 value-id，但真值表判 EQUIVALENT。`Values.and_/xor` 不做分配律
  范式化，同一函数经不同构造路径必然分叉为不同 ID。
- 跨解释器直接比较 ID 数字：双向禁止。实测：
  同一函数在两个 `Values()`（构造历史差一个 `vid({99})`）中得 id `5 vs 6`
  （不等无意义）；`v1` 的 q7-singleton（id 6）与 `v2` 的门级形式（id 6）
  撞号（相等亦无意义）。
- 方法文档漂移（无 verdict 影响）：README 写“真值表/ANF（≤12 变量）”，
  代码只有 `truth_table_equiv`，无 ANF 函数；README 写自检“4 行”，
  实测 `truth-table over 3 vars, 8 rows -> EQUIVALENT`；`local cone:
  128/128 assignments match -> PASS`。ANF 缺失不影响完备性
  （≤12 变量真值表已完备），记为文档漂移，改记不改判。

## 2. 原结论 → 新 verdict 对照表

| # | 位置 | 原结论（含 ID 用法） | 重判方法与证据 | 新 verdict |
|---|---|---|---|---|
| R1 | `dataflow62.run_prefix`：`formula(25630) != zpow.value_id`，`first_id_gap.op=25623`（CCX），“公式未重写”；连带 cross/controls/horner/domain 全 refused | booleq62 自检正是该恒等式：不同 ID，真值表 8 行 EQUIVALENT（`uv run --with z3-solver … --self-test` PASS，见 §3）。所谓“最低失败 op”是 ID 比较的人工产物，不是语义反例 | EQUIVALENT（该恒等式）；prefix 阻塞理由撤回；cross 后各阶段改记“未进入”（此前 refused 的理由作废，不是失败） |
| R2 | `cone_scan62.json`：`pair_exclusions.value_no_shared=2208` 作排除主因；`trackB_discrete.md` 表述为“该窗口规则下无可合并对” | 2208 对从未跑过任何等价证明（screen 仅做值集交集计数）；按 R1 同理，不同 ID 不能读作已证不等。候选数 0、复解释 0 的数字不变 | TO-PROVE（screen 保留为启发式，2208 不得引用为“已证不等”；`pair_candidates=0`  verdict 方向不变，理由改为“screen 下无候选”，不是“已证无”） |
| R3 | `retain_chain2_62.json`：`first_signature_diff`（src controls 13619/12846 vs copy 18173/18146）记 “value FAIL（首个 CCX 签名即分叉）” | 同对第一控制位重判：`free_vars=48`，`booleq62.z3_equiv(..., timeout 60s)` 实测 `verdict=unknown, reason=timeout-or-undecided`（62.1s，见 §3）。签名不等≠函数不等（R1 已证表示非范式） | UNKNOWN → TO-PROVE；“零改写、零收益申报”保持（仍不改写），理由改为“未证”等价而非“已证不等”；fantasy −806 vs −5028.43（6.2×）仅为量级上界，不变 |
| R4 | `joint_phase62.json`：`instance_inputs_pairwise_distinct=true` ⇒ `joint_cleanup=INAPPLICABLE（不同数据）` | 12 个输入 ID 两两不同，但无任何一对跑过等价证明；同 run 内不同 ID 同样受 R1 非范式化影响，不能推出“函数不同⇒不可共享”。完整重算见 evidence_fix2 | TO-PROVE（INAPPLICABLE 撤回；联合清理仍无候选，但理由改为未证） |
| R5 | 跨解释器 ID 比较禁令 | 见 §1 实测（5 vs 6；撞号 6） | 即日起：任何跨 `interpret`/`Values` 实例的 ID 数字相等/不等比较一律无效；`check_cone_clean` 的 fresh-atom 守卫保留 |

## 3. 实际命令输出（粘贴）

```
$ uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test
identity: distinct ids, truth-table over 3 vars, 8 rows -> EQUIVALENT
local cone: 128/128 assignments match -> PASS
SELF-TEST PASS
```

```
$ <Fix1-Z3 段：全电路 interpret + 首分叉第一控制位对>
interpret 0.3s
src controls [13619, 12846] copy controls [18173, 18146]
free_vars 48
Z3 verdict: {'method': 'z3', 'verdict': 'unknown', 'reason': 'timeout-or-undecided', 'free_vars': 48} time 62.1s
```

```
$ <跨解释器段>
same function across different histories: id1=5 id2=6 equal=False
v1 q7-singleton id=6 == v2 gate-form id=6 -> numeric collision across runs: True
```

## 4. 附带修正：窗口端点与反向切片（verdict 方向不变）

- 窗口端点（`cone_scan62.py` 复解释，latent：候选数为 0 从未执行）。
  `merge_at=i1` 时 `new_ops = B[:i1]+patch(3)+B[i1+1:i2]+B[i2+1:]`，
  中段末在新坐标是 `i2+1`（`=B[i2-1]`），尾 `B[i2+1..]` 起于 `i2+2`；
  代码 `keep={i2+2}` 把新侧多执行了一条 `B[i2+1]` 再与旧 `snap[i2]`
  （`B[i2+1]` 之前）比较，端点差一。`merge_at=i2` 分支同理
  （窗端在新坐标 `i2+1` 即 patch 末，`keep` 同样多取了一条）。
  修正：`keep={i2+1}`（两分支），条件环境比较同步。旧脚本冻结为证据，
  不改文件；`pair_candidates=0` 结论不受影响。
- 反向切片遗漏目标旧值（`retain_chain62.py` / `retain_chain2_62.py` 的
  `reads_writes`：CX 记 `rd={c}`、CCX 记 `rd={c1,c2}`，丢了目标旧值；
  而 `new_target = old_target XOR f(controls)`，旧值是必需依赖；
  Z/CZ/NEG/Z_POW 记 `({}, {})` 作透明处理正确，HMR/R 记复位正确）。
  实例（Exp4 q21 切片）：旧 `[28870]`（`CCX q4 q51 q21`，`need={4,51}` 悬空）；
  修正 `rd` 含旧目标后切片为 `[28865, 28867, 28868, 28869, 28870]`
  （`HMR q21 b341` 复位 + `X` + 2×`CX` + `CCX`），含一次测量，
  per-slice “1 CCX” 口径作废。Exp4 veto 方向不变
  （值未证＋窗内 HMR＋条件环境 b457/b458 本已锁死），Exp2 的逐切片
  成本行标注“旧切片口径”，`pool_bound_sig_equal`（同 ID 方向可靠）不变。

官方验证：0 shots（未运行）。Kaggle 提交：无。
