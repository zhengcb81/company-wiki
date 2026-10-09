# Provider failure boundary — coordination record of independent review

2026-10-09，报告来源 /root/provider_cause_boundary_review；只读调查，未产品写入或真实provider调用。本记录细化已有 r6_provider_cause_integration.md，不另建费用账或审批门。

## 真实断点
CWP bounded HTTP/Dayu SDK → final error/checkpoint → JsonCommandAdapter._run/AdapterProcessError → discover/fetch_bounded共享AcquisitionBudget → SourceAcquisitionService._ensure → source_catalog structured_error只有四字段 → FF diagnose_stderr/upstream_cause → RF _ClientError/_emit_error没有保留cause → source_preparation把stderr压成800字text。
FF任意OSError判producer_start_failed(False,True)不充分，ff_process_transport._cleanup可在目标执行后抛OSError。CWP journal二次失败可能遮蔽原provider异常，需先RED验证。

## 向后兼容公开DTO（producer定稿仍需集中测试证明）
在现有 status/error_type/error/retryable旁附可选 acquisition_failure：schema_version="acquisition-failure/1", code闭集安全机器原因, retryable bool/null, provider_started bool/null, usage_complete bool/null, acquisition_usage existing schema1.0 {response_bytes integer,cost_usd finite nonnegative decimal string}或null。只在有producer/accounting证据时附。
公开数字定义为整次ensure operation累计，复用已有共享AcquisitionBudget；discovery/fetch/retries都计，不发布最后一次subprocess用量冒充总量。没有实际usage证据时保持null，预算初始零不证明最终零。usage checkpoint单调用累计取最新完整匹配条目，不把多个累加。超额费用保留，不clamp。
FF公开filing-upstream-cause/1仍六字段：schema_version,operation,code,provider_started,usage_complete,retry_scope。只投影验证过producer DTO，不复制message/stderr/path/URLquery/credentials，不改变generic catalog contention自动重试。RF传播同一对象，不重新猜原因或读底层DB。实际数字用量仍由CWP公开DTO和原预算记录给出，不新造费用账。

## 可证明启动边界
provider_started表示目标外部adapter程序运行，不等于HTTP。目标identity/version匹配final result或checkpoint证明true；Dayu开始就发zero progress只能证明程序运行；bootstrap/Popen活不等于目标执行。真正pre-targetlaunch失败才false，普通OSError不猜。timeout有checkpoint true/lowerbound incomplete；无checkpoint started null，hardkill明确时usage_complete false，普通未知传输 null。成功下载后receipt/import失败仍保留已知执行和累计usage。

## 原因词汇
transport adapter_timeout/adapter_output_limit/adapter_process_failed；CN upstream_unavailable/budget_exceeded及真实typed code；Dayu provider_failed/provider_not_configured/invalid_request/invalid_budget/invalid_candidate/missing_scratch/invalid_scratch/unsupported_language/unsupported_sec_form/unsupported_hk_period/identity_mismatch/invalid_provider_metadata/primary_missing/fiscal_period_unresolved/missing_response/staging_conflict/sdk_asset_mismatch；预算deadline_exceeded/byte_budget_exceeded/cost_budget_exceeded/unsupported_content_encoding/incomplete_response。按实际producer代码闭集定稿，未知安全归unknown/adapter_process_failed。不把ET独立结果塞入filing原因。

## 一次大节点责任验证
CWP旧generic精确四字段兼容；finalfailure和多checkpoint坏identity；敏感body恶意code/invalidusage；discovery+两fetch operation合计；超额改抛budgeterror/receipt及import后失败；journal二次异常不遮原cause；cleanup执行后OSError不假false零。
FF只解析一次；嵌套诊断有效优先/畸形保持旧catalog分类；unknownusage不启重试；固定六字段/后启动OSError/concurrency正常正例。
RF→FF→真实CWP CLI→fakeprovider隔离链，handled failure/hard timeout/outputlimit/导入后失败/复用成功。逐跳cause一致、原件和Dayu树不变、测试恢复。先RED→实现→GREEN，集中测，不每个小节点签收或全量。
