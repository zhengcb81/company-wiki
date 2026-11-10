# 失败与误拒根因核对 — 2026-11-10

## 结论

本次以冻结的 [H01–H10 历史审计](architecture-quality-20261101/implementation-results/gate-rejection-followup-20261102/tools-history-audit.md) 和后续 [R7 收口记录](architecture-quality-20261101/implementation-results/gate-rejection-followup-20261102/closure.md) 为准。H01–H10 是归并后的 **10 类根因**，不是 10 次失败，也不是全部尝试次数；历史日志没有形成可核对的逐次运行计数，不能把重跑重复计数。

曾经有 **4 个有真实结果的误拒/误报事件**：H01、H03、H04、H05；另有 **1 个有效的 unavailable/error DTO 被旧消费者拒绝**（H06）。其中：

- 严格按“设计上多加了不必要门槛”计，能明确确认 **2 类**：同字节只改 mtime 仍被拒（H01），以及观察器任意 300 KB 上限拒绝已成功保存的 388,583-byte 结果（H03）。这两类限制已移除或降为诊断。
- 若把有错误判定条件的审计器也计为门禁，另加 H05：registry audit 用不同表示比较同一 generation，误报“未登记”。该误判已修；R7 又移除了由 registry audit 充当任务许可的重复职责，只保留实际内容和 hash 的 owner 校验。
- H04 是观察器字段 `KeyError` 在付费成功和 artifact 已落盘后遮住 native 成功。它是可选观察与业务结果耦合的实现缺陷，不是有意设计的许可门。修复后恢复复用同一 artifact 为 0 次额外 POST。
- H06 是 CWP/FF 公共 DTO 版本错配：新 producer 的合法 `blocked/local_preparation` envelope 被旧 reader 当成无效响应；并伴随候选期次范围先计入无关旧文件的搜索问题。它是合同和数据范围根因，不是费用或原文校验过严。

因此，用宽口径把所有“观察/审计错误挡住正常结果”都算作过度门禁时是 **4 类误拒行为**；用窄口径只算明确冗余/错误校验门时是 **3 类**（H01、H03、H05）。再加 H06 才是 5 个已记录的真实错误拒绝/误读结果。不能据此声称知道历史上一共失败了多少次尝试。

## 其余红灯不是过度门禁

| 类别 | 根因 | 当前处理原则 |
|---|---|---|
| H02 | producer/consumer 对合法 `source_processing_complete` 消息版本不同步 | 修公共合同与消费路径；不能删除版本语义或把未知状态冒充成功 |
| H07 | 预估请求 81,880 tokens 超过当时剩余 60,974；未发 POST | 这是配置预算真实停止；真实 token/费用/时间/字节边界保留 |
| H08 | 目标遗漏、增长假设无校准、币种标错、旧年报选择、供应商 401、来源无业务附件 URL | 数据/研究/provider 缺陷，需由对应 owner 修正；删门槛不能补事实 |
| H09 | 隔离合成样本证实大 DTO、日志、深度、可选诊断等上限会拒绝合法结果 | 是过度设计的实证类别，不是额外的历史真实公司失败；R7 已按 owner 移除这些人为许可帽 |
| H10 | 测试 oracle、fixture、协议版本或期望已过期 | 修测试与生产合同对齐；不删真实反控以求通过 |
| 环境/测试 | Windows `os.link` 权限错误、NUL 设备误识别、测试 monkeypatch 仍针对退役 helper 等 | 属于平台能力/测试耦合问题；与模型、原文或用户许可无关，按根因修复，不计作生产误拒 |

## 当前实现复核

- R7 收口表已覆盖 CWP 输出/CLI/storage、工具日志与事件、StockWiki 表示/可选 review、RF 公式、ET 二次顶帽、FF 字节钳制等重复表示门。完整 native 结果与诊断观察分开；观察器故障不能推翻业务成功或触发重发。
- 当前 `tools/document_understanding_benchmark/holdout_acceptance.py` 以完整 stdout 读取 JSON 协议，stderr 只保留配置的诊断 tail；观察不完整作为 receipt 诊断。`holdout_acceptance_observer.py` 对事件大小和可选写盘失败不阻止 native 操作。
- 现有 `tests/unit/test_holdout_observation_isolation.py` 包含历史事件超过配置日志显示量仍允许唯一一次 POST、事件/模型输入观察写读失败不覆盖成功、真实请求体不一致仍拒绝、durable paid pin 与 native 错误仍有效等反控。本轮读取了代码和测试，没有重新运行全套测试。
- `phase_c_runner.verify_preparation` 用内容 SHA-256 与 byte size 判断原件/配置是否变化；mtime 差异只进入 `metadata_changes`。未冻结的样本由 `declared_holdout_qualification` 标为不具备 clean-holdout 资格，但 `load_manifest` 仍允许普通测量运行。这两者不再是运行许可门。

## 明确保留的必要边界

真实原文字节 SHA、公司/来源/期间/as-of、locator、费用/token/时间/空间上限、已知/未知付费状态、同请求单 POST、恢复账本、数值/单位和坏协议反控继续保留。它们属于事实、资源、协议或恢复正确性；把它们一起删掉会制造错源、错期、错币种、超预算或重复付费，并不能解决误拒根因。

**状态：**本轮确认的是文档历史与当前代码/既有回归相符；没有声称本轮重跑了真实付费公司流程。新版真实摘要、跨运行缓存恢复、RF 实际采用和固定公司循环仍按主计划开放。
