# StockQA 最终发布候选独审

判定 **PASS**。在 `.planning/r25/wq` 实际执行，读回的基线为 `a4a81e5a818887835095f109e204f6d8a984fd17`。本轮判定绑定下表的工作区有效源码与 Git blob，供所属仓提交后核对。审查没有修改候选源码、正式工区或账本。模型调用、外部网络和计费均为零。

| 源码 | 工作区 SHA-256 | Git blob |
|---|---|---|
| `src/runners/llm_runner.py` | `7c79f015c3a829e4f335acc3121549409f8174802cde42ad054bc00542d47f34` | `2a3f4a2664cd7a5fad1e719035e10832b5769575` |
| `src/utils/execution_feedback.py` | `3b9e09a875b0b49b1c17238a4607c9110d683d177f65c610a334a3208d8990dd` | `292ac465420af124332c365db4da5c1929f64043` |
| `src/utils/quick_scan_feedback_owner.py` | `122b8916a1a6338f036c10fdb6773a4f10682c55098024a1d045ab4f2b936dde` | `0e6222f190305302e9d44db2f3d2343f3107404d` |
| `src/utils/quick_scan_work_store.py` | `37df81425a0fb92c5348cf74e96b9505f0fddf316f21fe5c9546e55eaea2854c` | `672cbf3ec6d49cb5bb5a23bc9821757a977f809c` |
| `src/providers/async_llm_provider.py`（异常传输复验） | `1ad8dbfbd9dbdca54a3a3897c3e53558e18057b3ef8ae5a211c36d973398996b` | `7eae6b9a897fc01cf62e9aec18a3c9e9d7d4e96b` |

对比暂存候选与实际源码的 AST，四个文件有类型或保护分支变化。Runner 从已验证的所属模块快照读取原请求、登记及问题列表，仅把有效工作 ID 交给公开读取。StockQA 自有存储继续用原尝试保存的收据来定位证据，连接留在所属层。手工核对 `cast(list[dict], ...)` 所指向的公开投影实际返回 list。运行历史的容器注解未改变按原 run、attempt 和 evidence 去重的规则。其余源码差异为导入和格式重排。127 源文件的官方 mypy 通过记录由责任 agent 提供。

## 定向复验证据

- `review-qa-final.xml` 为 4 项通过，18.95 秒。使用真实冷读进程确认异步两题各调用一次，并分别保留 `LLMTransportAttemptError → TimeoutError`、原请求号及题指纹。二次冷读字节一致。未知旧账目仍是未知，旧消费者的原生直查保留，账本字节不变。只实现公开证据读取端口的独立替身成功运行。
- `review-qa-final-paid.xml` 为真实已付账本组合 1 项通过，20.66 秒。实际 `inspect` 返回 0 次请求。原宿主身份、现代索引留存和旧 ready 留存均可读回同一已付记录。对照组只改 `run_id` 或只改 `attempt_id`，有无显式账本均得到 `cost_state=unknown`、`job_status=unconfirmed`。原账本、索引和 ready 逐字节保持。
