# MAIN 来源资格调查与后续责任测试

状态：只读调查完成，尚未实现。该工作归 MAIN，不占用 R6-FORMAT、R6-RF-INPUT、R6-FF-CAUSE 的写目录。

## 已核实机制

- `query_ref/query_local/lookup_transcript_import` 是 catalog 查询；命中索引不能证明物理原件现在可读。最终字节证明来自 `SourceVersionReader` 实读 SHA。
- 普通历史查询排除未知/晚于 as-of 的公开日；电话会导入去重允许未知日。派生/当前预览与历史资格必须分开。
- `SourceResolver.resolve` 在检查位置/本地字节前累计未知公开日匹配。待 RED 验证：只有索引、原件不存在的未知日 placeholder 是否误阻断合法采集。不能因调查发现就直接宣称已复现。
- 已有 `SourceCatalog.record_source_facts` → assertion_service：实读目标原件，追加 SHA 绑定 assertion、更新查询投影，不改 raw/capture。应复用此链，不建第二份修正状态库。
- 现有每字段 evidence 只验证 locator/value 和结构，不认证官方正文或发布日期。因此接口接受请求不等于出版事实已经独立核实。
- `NarrativeTransportReader` 未指定 as-of 可当前读；指定 as-of 的未知/未来公开日仍拒绝。现有 49-span TXT 不必因补元数据而重复付费生成。

## 出版证据调查

微软 [FY2026 Q4 官方电话会页](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4) 可见会议日期和原文，但页面说明 prepared remarks 与完整 transcript 的提供时间不同。会议日不能自动作为完整 TXT 的发布日期；当前页面可读也不能证明更早日期已公开。仅核实到可用上界时保留未知日，不能填成下载日。

腾讯 [官方财务报告页](https://www.tencent.com/zh-cn/investors/financial-reports/) 有报告入口。旧 URL 的替换仍需下载官方原件、核同一 SHA；不同语言或修订 PDF 不可绑定旧 SourceRef。URL 路径日期、董事签署日期不单独构成出版日证据。尚未完成此原件/出版日核对。

## 实施顺序与集中测试

1. 先责任测试区分 indexed、verified local bytes、历史资格、派生可用、provider 实际执行；覆盖未知/合法/未来/坏日期及不可读 placeholder。
2. 沿现有查询/resolve/ensure 输出附加资格诊断，保留历史 matches 定义；retrieved_at/call_date 不用于推定公开日。
3. 原件与官方证据强绑定后走已有 append-only 修正接口；测幂等、原件/capture 不变、坏 SHA/投影失败回滚。
4. 一次集中真实当前读取/历史拒绝→合法修正→历史读取及 0 模型重跑验证；缺证据仍具名 gap。不得修改冻结第一组基线以掩盖旧问题。

三张外包卡写范围维持 README；MAIN 改现有 source_catalog/automation，不写新 document_normalization，不改 RF 工程或 FF 诊断线代码。
