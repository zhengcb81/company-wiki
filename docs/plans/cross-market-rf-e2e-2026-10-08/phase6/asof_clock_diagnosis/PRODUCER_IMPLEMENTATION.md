# MAIN：最小来源时间事实生产接口

## 范围和单一责任

实现文件：`src/company_wiki/source_catalog/source_availability.py` 与 `source_reader_cli.py`。默认 receipt 2.1 与 SourceRef 2.0 不变；显式 `--include-availability-evidence` 返回 2.2，多一个 optional `availability_evidence`。这是事实格式协商，不是下载或读取许可。RF owner 独占消费者与共用时钟。

不新增数据库、人工签收、签名链或旧资料迁移。known publication 的修复不依赖这项 extension。unknown 仍保留 null publication，可靠 proof 只提供 available_by 上界。

## 已识别的证明格式

仅解析既有 canonical writer `.source.json` 中的完整 `DownloadReceipt`，实际打开 exact-version 已登记 location 的 sidecar。HTTP 2xx、原件 SHA/字节/MIME、UTC时间必须有效；top/candidate/receipt 的来源 URL/provider/document ID 及 top 的时间/字节必须一致。公开读原件已验 bytes，proof lookup 不再次读原件、OCR 或扫描全库。

DTO 使用 `prior_verified_capture`；evidence_ref 是 document ID + 实际 sidecar SHA，不含物理路径；locator 指向原有 receipt 的 SHA/time/status。每版最多64 locations，每份metadata最多64KiB。异常、跨根、裸collector、local_document或未知格式返回 null；不把文件mtime、文件名、自报 as-of、未实现primary archive格式作为证明。

主PWF此前拟议支持多种proof格式；当前采用有真实生产格式依据的一种。以后仅在实际新样本有需要且能证明时间+exact bytes时扩展格式，不为将来假想需求加 resolver/身份机制。

## TDD与验收

先写15个责任用例，实际RED为新模块不存在（collection error，0.87秒），不是15个逐项断言RED；实现后与既有reader契约集中26PASS/12.32秒，Ruff发现一个测试unused import已修。再补默认2.1/opt-in2.2真实CLI、裸sidecar null、实际capture proof、无写/无物理路径泄漏用例，最终集中结果以实际执行记录为准。

所有资料均合成隔离fixture，不称真实公司或供应商PASS。测试根短路径、开始不存在，结束核对绝对路径和reparse后删除；生产配置和原件不写。下一重大跨仓验收同时检验RF实际known publication late-read链和unknown proof链；旧固定71报告不重写。
