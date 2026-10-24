# RF / CWP 共享阅读接口独立复核

**结果：PASS（代码接口与真实消费链）**
**审查方式：** 独立 agent 只读审查最终 RF 提交 `c48f86bd0d56f0a2be67a71348cf05d8544b6cdd`、对应契约测试和 v6 离线消费收据；审查者未修改文件、未调用模型/API、未下载原件。

## 覆盖内容

- RF 保持对 `du-production-reading/1` 与 `/2` 的既有兼容；`/3` 要求 selection trace，并只接受 CWP 已发布的裸诊断码 `DECISION_DEPENDENCIES_UNAVAILABLE`。
- RF 与 CWP producer 都校验 target 的 `used <= limit` 且 `used + requested > limit`；`budget_full`、`character_budget`、`group_exceeds_limit` 三类均有拒绝越界测试。
- 非字符串 `schema_version` 在 RF 侧作为契约错误拒绝，不会因 set membership 抛出未处理的 `TypeError`。
- 真实 v3 reading context、112个 evidence span、69个 group 与69个 citation view在 RF 消费端逐字节/引用闭合；RF adapter 保持 `source_owned_views`。
- 真实上下文为195,794字节；合同上限196,608字节，余814字节（约0.4%）。样本通过，但后续增长需观察，不应因单样本放大通用上限。

## 结论与边界

独立审查未发现剩余接口阻断。真实 v6 E2E 为离线重放：provider调用0、下载0、临时catalog已删除。该结论只覆盖接口和原文/引用传递，不代表68条摘要claim的业务内容质量通过；内容审查与不同市场/文种样本仍待完成。真实 proof-bearing v3 样本目前只有CN H1一份，proof正向结构另由合成契约测试覆盖。

## 绑定验证

- RF commit：`c48f86bd0d56f0a2be67a71348cf05d8544b6cdd`（`main` 与 `origin/main` 相同）
- RF focused regression：85 passed
- RF pre-push：Ruff、公开契约 mypy、host assumption guard 通过；595 passed、1 skipped、36 subtests passed
- CWP transport tests：54 passed
- 离线真实E2E：[v6机器收据](rf-consumer-e2e-official-store-v6/e2e-summary.json)
