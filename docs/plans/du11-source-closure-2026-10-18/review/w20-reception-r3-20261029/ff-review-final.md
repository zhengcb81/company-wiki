# W20-FF ROOT最终独立验收（2026-10-29）

**APPROVE，范围内OPEN=0。** 最终受测/受审源码提交：`5ec54e02b8db69d0f38adfd0d7cee58f04f3a2b8`，工区`C:\Users\郑曾波\Projects\filing-fetch-w20-root-final`，当前tracked/untracked clean。

## 最后漏接已修

唯一owner改读`durable_state_public_readback`，仅精确`not_found`可支持pre-durable负证。独立重放实际handler：not_found→PASS；probe_error/confirmed→FAIL。独立7参数短测**7 passed／0.17秒**，None/unknown/legacyFalse/missing均不能签过。ROOT之前6RED/1控制及203P/10.20秒收据保留，不假称由本审查重新跑203。

## 原关键两项维持通过

同次新增采集的harness边界lostreply样本dd7884e1已真实1GET入库并公开query+reader实读同Ref/SHA，首次恢复和再次复用0GET。此为明确的输出边界丢回复仿真，不声称外网断包或微秒服务器kill。旧prior-delivery新重试kill保留CONTROL ONLY，不能替代主场景。最终新版完整oracle重新核验该原始报告及control248e9d19均**0 findings**，未重跑采集。

新探针仍一调用一受界子进程，父全局stdin/stdout与共享last_error已移除。最终独立并发边界probe确认A/B公司请求/Ref不串、父stdio不变；非零child仍probe_error，不冒明确not_found。

## 边界与发布

改动仅W20矩阵断言及小回归，产品FF scripts、provider、CWP/ET源码、原件/生产配置不变；base41权威、supplemental11及selected-only语义保持。旧报告保留历史，不重签当日全41或项目大循环。原初审与反例另存ff-review-initial.md/json；精确SHA、命令、探针结果和报告SHA见同名JSON及[evidence/ff/final-probes.json](evidence/ff/final-probes.json)。

ROOT自有final-pytest临时树已删除恢复不存在；作者工区未写，0新外网/下载/收费，无全41/404秒全仓重复。**可由ROOT继续合线推送**，本审查不代签尚未发生的远端发布/CI。
