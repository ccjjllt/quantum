# 提交运行手册（2026-11-17 起）

只有 **严格高于 28.15083** 的候选才提交。提交前必须有一个 Kaggle CPU kernel 用
未修改官方 verifier 全 shots 跑出三件 PASS，且 `receipt.json` 的 `gm` > 28.15082863。

## 1. 候选件与基线

| 腿 | 当前件 | 官方 cost | 说明 |
|---|---|---:|---|
| invsqrt | `0af21cb8`（44Q，嵌入 b64） | 74,797.36535717871 | `pipeline/invsqrt_0af21cb8.kmb.b64`，sha `0af21cb8…` |
| dqi | `61c8348d`（890Q） | 346,413,579,540.50（clean） | dataset `grantprater/vqcc-dqi-61c8348d-merged-closings` |
| chem | `a73b25d2` + 15 SMALL loader | 294,643,137.73 | kernel `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` |

18 个成员的 SHA-256 清单：`pipeline/members_2815083.json`。

## 2. 集成（Kaggle CPU）

```bash
cd experiments/frontier/20261117_deep/integration
# 换 manifest / label / 期望 GM 后重建自包含脚本
python3 make_main.py --members <新 members.json> --label "<说明>" \
    --expected-gm <预测GM> --min-gm 28.15082863 \
    --invsqrt-b64 ../../20261116_push/pipeline/invsqrt_0af21cb8.kmb.b64
cd /Users/zhaohuaxiang/ccjjllt/quantum
python3 scripts/kgpu.py push --dir experiments/frontier/20261117_deep/integration --account qingyu1232
python3 scripts/kgpu.py status --kernel qingyu1232/qcc-deep-integrator-re-verify-28-15083 --account qingyu1232 --wait 5400
python3 scripts/kgpu.py fetch  --kernel qingyu1232/qcc-deep-integrator-re-verify-28-15083 --account qingyu1232 \
    --out /private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/deep_int
```

kernel 只在 `/kaggle/working` 写 `receipt.json` 和 `submission.zip`（staging 在 `/tmp`，
避免 500MB 文件进输出）。`receipt.json` 记录每条腿的完整官方 JSON、GM、18 成员 SHA-256。

## 3. 提交（code-competition 形式，避免 GCS 上传挂住）

只在 `receipt.json` 的 `decision == "SUBMIT"` 时执行：

```bash
export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)
~/.local/bin/kaggle competitions submit \
  -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-deep-integrator-re-verify-28-15083 \
  -v <kernel version> -f submission.zip -m "<描述 + Apache-2.0 归属>"
~/.local/bin/kaggle competitions submission <REF>
```

## 4. 记录

提交后把 ref、public score、状态写入 `submissions/<日期_方案>/README.md`，并在
`README.md`（本目录）更新「进行中的 kernel」表。
