# 通用三腿集成 kernel — 已端到端跑通（2026-11-17）

## 结论

`qingyu1232/qcc-deep-integrator-re-verify-28-15083` **v3 COMPLETE**：18 个成员全部按
(size, sha256) 定位/解包成功，三条**未修改官方 verifier** full shots 全部 `PASS`。

| task | status | 官方 cost | 关键量 | 耗时 |
|---|---|---:|---|---:|
| chemistry (`a73b25d2` + 15 SMALL loader) | PASS | 294,643,137.73357135 | T 14,706 / Q 427 / λ_eff 46.921716818 / e2 0.0199999985 / 78,080 shots | 28.6 s |
| DQI (`61c8348d`, 890Q) | PASS | 348,004,440,260.464 | T 367,120.004 / R 1.1967315 / 1 value error / 102,400 shots | 172.4 s |
| invsqrt (`0af21cb8`, 44Q) | PASS | 74,797.36535717871 | Toffoli 1,459.3749 / 33 rot @ 1.6406055e-13 / worst-tol 0.9995606 / 200,540,928 shots | 666.1 s |

`kickmix.so` sha256 `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`
（官方件）。默认盐下 DQI 抽到 dirty draw，因此本次 GM = **28.10786705**；
公开榜 `58454232` 的 28.15083 用的是 clean draw（346,413,579,540.50），
与 `intel/RESULT_public_salt_model.md` 的两种公开 cost 一致。

## 用途

这是后续所有候选的**唯一出包口**：
`make_main.py` 换 manifest → `kgpu.py push` → `receipt.json` 给出三腿 JSON、GM、
18 成员 SHA-256、`submission.zip`；只有 `decision == "SUBMIT"`（GM > 28.15083）才提交。

## 踩过的坑（已修）

1. 竞赛挂载在 `/kaggle/input/competitions/<slug>/`，且 `kickmix` 必须用
   `PYTHONPATH=<comp>/kickmix:<comp>/verifiers` + `cwd=<comp>/verifiers`，否则
   Kaggle 镜像里另一个 `kickmix` 会先被导入（`module 'kickmix' has no attribute 'Circuit'`）。
2. staging 必须放 `/tmp`：放 `/kaggle/working` 会让 500 MB 的 `dqi.kmb` 变成 kernel 输出，
   `kaggle kernels output` 会挂住。
3. 官方 verifier 的 JSON 是整段 pretty-print 的多行文本，解析要 `json.loads(整个 stdout)`，
   不能逐行找 `{`。
