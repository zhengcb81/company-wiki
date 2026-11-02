# R7 最终核心扫查：实施与冻结

状态：**16 文件冻结，待 ROOT 独立大节点审查**（11 源码、5 测试）。不自行提交、推送或安装；不冒称远端 CI、H1、真实摘要/cache/RF 采用已通过。最终 SHA 以同名 JSON 的 `delivery_files_sha256` 为准；原只读报告保留修复前证据。

## 完成的共同根因修复

1. **显式预算取代隐藏许可**：batch 要求非空、类型正确且身份一致的显式 work item，去掉 100 个固定帽；用户 `max_final_bytes` 不再受另一个 2 MiB ceiling 否决。默认值未提高，用户所有 final/persistent/scratch/time/token/fee 配额继续执行。真实 `_BudgetedObjects` 能写入在显式 5 MiB 额度内的 3 MiB 数据，超过实际 5 MiB 时仍在写入前拒绝。
2. **合法 provenance 不因诊断规模丢原件**：去掉 optional extension 的 16 KiB gate，仍完整验证 canonical JSON 和 namespace、原件身份及安全入库。真实隔离 catalog 写入大 provenance 后，原件字节与完整诊断逐项保留；非 JSON/NaN、错原件 SHA 仍拒绝且不删除 staged 原件。
3. **正文与存储元数据归单一 pathless owner**：通用 JSON 遍历增加有限 owner context，同一实现继续处理循环、非法类型及 nonfinite；按已知 wire schema 的精确 span raw_text/summary claim text 槽保留正文，未复制全祖先路径，仍线性遍历。任意 metadata 字段叫 text/raw_text 不取得正文例外。独立 claim 统一在 typed owner 校验，两个模型 decoder 不再另做正文路径禁词。存储字段、未知结构、错误引用与品质/fidelity 仍由原责任层校验。
4. **availability 与原件入库采用相同资源责任**：ROOT 随后发现的 64 KiB sidecar/inline、128 KiB metadata、64-location、source-fact evidence 64 KiB 同族门也已清除。元数据读统一经既有 LocalReadBudget，分块真实 read/charge，保路径归属、hydration、前后 stat、源/HTTP/date/真实字节 hash；同 sidecar alias 不重复读取。fallback 只有一个同类默认预算，可注入父预算；local_reconcile 两处、resolver 一处现有父 budget 薄透传，不能重置额度。

inline 已读 JSON 也在同账户计量；source facts 保 JSON/字段/locator/事实值对应校验。已观察到的真实 capture 在后续 byte/discovery 工作限额触发时仍可作为独立证据返回，**不声称全部 location 已检查**，同一 budget 保留 triggered_bound 与实际消耗。显式取消、硬 deadline、其它真实错误不被这个保留策略吞掉。没有可用 proof 而耗尽时仍明确 unavailable，不能把未知变成历史可用。

## TDD 与有界验证

| 阶段 | 实际结果 |
|---|---|
| F1–F3 新 RED | 8F10P / 5.18s，准确命中隐藏 count/final cap、optional provenance cap、正文路径误判。 |
| F1–F3 初绿 | 18P / 4.97s。 |
| 一次受影响集成 | **144P / 19.20s**：新增扩展控制、job 合同、真实 canonical writer、post-model native usage、citation-unit、JSON/corrupt-cache 及 batch 资源。没有重复此组。 |
| availability 同族新 RED | 7F / 1.14s。 |
| 同族首次相关域 | 21P1F / 2.05s；唯一 F 是旧 65-location 全部丢 proof 的退休期待。 |
| 同族最终短域 | **34P / 4.02s**：长 sidecar/inline、同 budget read bytes、错误 SHA/HTTP/时间、真耗尽、deadline/cancel、known proof 与 local source 邻域。 |
| 最后三个父预算调用透传 | 既有 local-source 9P / 2.55s；不重 34/144。 |

源码 mypy 分别 6、3、2 文件均绿；Ruff 14 文件及最后 2 个薄 caller 均绿。完整命令、XML、日志及 SHA 在 JSON。关闭非必需插件的既有 asyncio_mode warning 未隐去。

两个旧正文-path 负控透明迁移到真实逻辑 claim_id 元数据路径：`test_narrative_post_model_failure_diagnostics.py`、`test_narrative_citation_unit_model_boundary.py`。原 JSON/语言/引用/使用量/不完整上下文反控完整保留。旧 64-location 期待改为实际 discovery budget + 无合法 capture 时明确停止，没有恢复任意新上限。正文 URL 本身不是世界事实，仍不替代 source/fidelity 审核。

## 身份、恢复与交接

wire shape 未改变，正常合法 payload 的输出值未更改；仅撤销多余拒绝条件。模型 boundary 的现有 module-byte 身份覆盖变更的 contract/decoder；没有引入签收、override flag、另一任务库或全仓 hash。原件字节/ID/期间/as-of、有限数字、context closure、lease/outbox、未知费用及显式冻结 cache 仍保留。

本增量有意更新此前 CI followup 中 post-model 文件的 SHA；之前的 5 文件签收是历史证据，不能直接当当前 16 文件版通过。主 PWF 及独审由 ROOT 统一更新。

所有 source/catalog/object 写入为独立合成测试目录，未读取真实原件、key 或调用模型。五个显式自有 basetemp 已按精确绝对 containment、fresh stat、无 reparse 清理，移除 82 文件 / 10,424,955 字节，均 absent；integration 和最后 caller 实际被 pytest hook 迁到独占 TEMP 且 removed=true。没有删除历史运行目录、pip cache 或他人文件。未为最早 pytest basetemp 收集单独的初始内容快照，因此只声明本次 own 运行目录已清理，不捏造 preexisting 内容恢复证据。

H1 父节点已知 P2 未动。本线代码/测试已停止修改，先交 ROOT 独审，再接其安排的 invest 独立审查。
