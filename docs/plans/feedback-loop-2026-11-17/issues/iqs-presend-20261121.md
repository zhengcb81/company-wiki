# 中微重评发送前故障

IQS 于 12:16:31 UTC 启动 `run-5305efa0a466482fa2a187ed2b37699e` 的第 1 次启动。原准备为 `prepare_a862db6646ce4fd3b8b148f407231063`，两题同属 `PACK_95995090e3d54b89a04714c45873f5a2`。13:09:05 写入的原结果中，IQS_13、IQS_14 为 error，只有 `QuickScanWorkPersistenceError`。同次现场快照保存的进程退出码为 1。两题各有成功主体登记、当时租约有效、无 send intent、无预算尝试、无响应。未留存底层 cause。事后不能判为 SQLite 锁、权限拒绝、模型拒答或一小时超时。[IQS 正式事故报告](../../../../../invest-quick-scan/docs/implementation/reviews/PRESEND-SIMPLIFY-20261121/report.md)

| 实际失败题 | 原生工作项 | 反馈归属 |
|---|---|---|
| IQS_13 | WORK_5a5c082d0095430e889605fbad848f85 | 发现方 IQS，异常发生在 StockQA 的发送前本地路径 |
| IQS_14 | WORK_7a7f9ffd24804d4dac80527ba79b1865 | 同一进程和 pack，单独原生工作项 |

两条追溯观察使用原 IQS `launch_attempt=1`，各由题号区分。`attempt_id` 表示这次 IQS 启动，不代表一个模型发送尝试。状态库只做 observe 与冷 lookup。历史原响应、答案正文、生产库不复制。[追溯记录](iqs-presend-20261121.jsonl)

封存后 10 个检查点保留，8 题有分、2 题按规则为空。两道失败题经原状态 owner 的 release_unsent 回到 pending；0 新尝试、0 API。14:05:35 的原 delivery 作业对这 10 题全部 ACK，整体仍为 partial。后续另存的结果属于后续尝试，不能反推本次原因。

## 另行验证的根因与交接

* 两题包的独立计数从 26 次 StockWiki CLI 降至 3 次，分别是两次主体登记、收费发送前一次实时权限核对。未发送恢复、显式与隐式异常链的费用语义已在 StockQA 支线 `f69913c5` 签收。该优化未证明 13:09 故障由重复核验引起。
* 日常 F4 日志候选另存。StockQA 的 14 个候选用例及 IQS 的 8 个红测保留；旧补丁 SHA-256 为 `5f95c365c27e25d5cd0775784dbb45446040c0aa98ac505666605066a515da2a`。独立复核在 `f69913c5` 上重新 dry-run，旧补丁已不能原样应用。StockQA 要从当前 owner 接口修复诊断构造自身抛异常会跳过失败收尾的问题；IQS 要保证日志 open/write/flush 失效仍会排空子进程输出、执行 wait 并保留原终态。分别冷读本仓产物后，由 ROOT 用同 run/attempt/question 复核整个链。旧补丁不作为上线证明。[原 F4 交接](../../../../../invest-quick-scan/runs/amec-rescore-20261121/f4-handoff/README.md)
* StockWiki 同组材料指向刷新、主体登记和评估 CLI。意外错误在本仓单独记录关联信息，同时保留既有 stderr 单 JSON 接口。历史日志缺失不阻止使用已付结果，也不重新启动原业务。
