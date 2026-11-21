# 调查记录

## 组合接线与真实来源

- 两张作者卡分别通过冻结样例。实际 FF 配置初态允许空名单和空有效部署限额，运行计量与调度状态也比样例丰富。Dashboard 改读实际 owner 合同。保存修订号绑定编辑基线，`off` 档位在 OpenAPI 保留字符串含义。
- CWP 接入 StockWiki 挂牌坐标，使用自身来源身份核验。`DownloadAdapter` 维持既有能力，独立的元数据能力承接时间窗、分页和已证 accession。元数据预算与新原文下载预算分别记录。
- 腾讯同一期年报的两个中文正式链接分别以 `2026040900888_c.pdf` 和 `2026040901232_c.pdf` 结尾。以完全匹配的官方链接补足旧来源的 accession 证据。不同链接仍各自处理，避免按企业和期次误合并。
- 实测 CNINFO、HKEX、SEC 均返回真实候选。美国窗口有完整证明，A 股工具缺覆盖证明和交换计数，港交所 SDK 只给每期选中的公告。前两市场依据实际能力报告部分覆盖，避免提前推进完整水位。
- `schtasks /Query /XML` 在本机中文 Windows 经管道输出系统代码页字节，同时声明 UTF-16。适配器在系统边界修复解析并保持收据 stdout 为 JSON。停用态原生安装、重复安装、启动并返回 0、移除均已实测。
- 正式摘要的可恢复配置随原 AUTO admission 保存。原作业账本未建立前允许重试，已登记的同一运行使用原范围和原账本。自动复用需要实际能打开结果字节，已观察费用在账本暂不可读时作为已知下限，余量标记未知。

## 现有入口与缺口

| 所属方 | 2026-11-21 读回的事实 | 对本计划的影响 |
|---|---|---|
| FF `fcacf2e` | `scripts/ff_job.py` 已有 submit/run/status/reconcile。作业记录与日志持久存在，实际 `ff_job_store.py` 已使用提交锁、原子写和死写者指针恢复。根计划旧 F-08 描述是历史风险。 | 复用原有作业库，新增小批次节拍、覆盖和候选续做记录。无需再造一套作业/费用库。 [FF 公开协议](../../../../filing-fetch/docs/ff-job-protocol.md) |
| CWP 来源 `de136b99a` | `config/source_acquisition.yaml` 的 CN provider 是 StockInfoDLSimple `v2-clean-rewrite` 的有界 `stockinfo-cninfo/1.3.0`。HK/US 为 CWP 内现行适配器。底层适配器已有 discover，普通 ensure 选择适配的候选。另有官方网页元数据发现入口，调用者需已知索引页输入。 | 复用市场选择和下载机制。公开“给名单/时间范围、列全部或具名部分候选”的口仍需补。官方索引读取不等同于这个后台作用范围。 [生产路由](../../../config/source_acquisition.yaml) · [官方索引口](../../../src/company_wiki/source_catalog/official_source_cli.py) |
| ET `61fe94e` | 工具的实际代码根是 `earnings-transcripts/earnings-transcripts`。现代 `transcript_tool.py` 可从能力输出核对 provider。FMP 当前只支持精确 FY/Q fetch，默认未启用 Motley Fool。配套请求不翻译，但 FF 仅在该财报已可取得源引用时执行伴随流程。 | 放开周期任务对财报命中的依赖。直接复用 ET 获取期次确切的原语言内容、用量回执及 CWP 导入。无权访问或无精确期时保留真实覆盖缺项。 [ET 公开说明](../../../../earnings-transcripts/earnings-transcripts/README.md) · [FF 配套约定](../../../../filing-fetch/SKILL.md) |
| CWP 旧 worker | 本机旧 `.source_catalog/worker_control.json` 为 `paused`。公开启动、恢复、整库 normalize/summarize 和 startup 安装入口已退役。旧 worker 配置还包含周期全库扫描/Markdown 转换，当时单轮工件和模型批量小。 `scripts/scheduler.py` 另外含冻结的历史研究写入。 | 派独立卡接回有限阅读，避免启动旧 worker 调度与全库 Markdown 派生。 [旧入口移除记录](../narrative-evidence-pilot-2026-09-26/n4_production_batch_implementation.md#2026-10-03-旧-worker-入口退役状态) |
| CWP 正式阅读 | `scripts/narrative_batch_configured.py` 使用现有配置，交给有限共享阅读批次。AUTO 有稳定输入、lease/outbox、缓存和费用恢复。 `processed_document` 可按原 SourceRef 做局部实时读取，翻页时可能重解析，不能当作后台持久批次结果。名称为 extractive 的实现仍可能用模型排序。 | 本地阅读需要单独验证零调用，并复用共享解析和既有工件；正式摘要复用已配置执行方式。W12 一次真实生成与复用通过，更新的 /8 发生过实际模型超时与未知费用，不能作为常态恢复已验收的结论。 [批次入口](../../../scripts/narrative_batch_configured.py) · [W12 线上回执](../du11-source-closure-2026-10-18/review/w12-wuxi-resume-20261120/README.md#w04-正式请求与原作业查证) |
| Dashboard `007787aa` | M8 有 FF owner adapter、公开 Jobs 路由和前端。现役公开 Universe 列表及分页接 IQS 产品口。Dashboard 工作区有约 30 处在途计划与交接改动，读时未见产品文件的对应修改。 | 控制面可独立做。复用既有名单选择、CLI 传输和命令防护，在隔离环境测试。生产进程、别人的 PWF 和名单写入由原 owner 持有。 [FF 适配器](../../../../investment-dashboard/backend/dashboard/adapters/m8_owner_jobs/ff_job.py) · [名单读取](../../../../investment-dashboard/backend/dashboard/adapters/iqs/universe.py) |

## 已有恢复证据和基线红灯

- F4 的实际宿主已验证 FF 原件提交后进程被杀，再用原 `ffjob` 只读查回，外部动作没有重发。正反馈沿原请求记录拒绝原因和是否应调整门禁。此证据覆盖恢复原作业，新功能还须覆盖调度、名单、各来源和阅读组合。 [F4 恢复验收](../feedback-loop-2026-11-17/f4-acceptance.md) · [拒绝审视约定](../feedback-loop-2026-11-17/interfaces.md#拒绝先审视门禁)
- 本轮短路径隔离复验，FF `test_ff_job_cross_process.py` 的同键重放、提交时强退、运行锁 3 项通过。CWP 已配置 MiMo 的回环阅读和恢复 1 项通过。混合 PDF/TXT 稀疏语言回归两次复现，完整批次报告 failed，单份为 `dead_letter / PARSER_INCOMPLETE`，其他三份完成。独立复现已在 [CWP 卡](harness_lanes/cwp-incremental-reading.md) 固化。该错误码还需追到实际解析步骤及根因。当前基线不足以直接启用自动阅读。
- 本轮复验只执行现有隔离测试、留存夹具和本机模拟服务。正式目录、provider 配置和原件没有测试写入。正式模型、真实下载和 Windows 计划任务尚待实现后验收。

## Windows 调度机制

Microsoft 文档中的 `StartWhenAvailable` 针对支持的时间触发任务，错过后执行会入队并有延迟。计划任务只做唤醒和判时。登录与漏跑补齐仍以 FF 持久时间和覆盖状态为准。 `IgnoreNew` 合并同一任务的并发触发，进程间和重启后的实际作业去重由 FF 验收。 [StartWhenAvailable](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable) · [LogonTrigger](https://learn.microsoft.com/en-us/windows/win32/taskschd/logontrigger) · [并发任务设置](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-multipleinstancespolicy-settingstype-element)
