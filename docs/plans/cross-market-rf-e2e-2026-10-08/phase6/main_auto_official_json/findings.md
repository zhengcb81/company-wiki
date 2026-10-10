# Findings：AUTO 官方 JSON 共同接线

## 独立只读实证（2026-10-10）

`/root/m3_usage_acceptance` 用两家公司声明式 official-flat-list JSON 调用现有代码，无写文件、外部调用或费用：

- `source_class_for(application/json, investor_relation)` 返回 transcript。
- `detect_narrative_language` 在任务创建前报 SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED。
- 已验收 parser 正确选出目标公司 1 条记录，排除另一公司；分页完整、答复角色 management_answer。
- 原样投影 EvidenceSpan 交旧摘要 validator 被拒：新字段为 `structured_value.role`，旧消费读取 `source_role`；必须有明确薄适配，不将问题提升为管理层事实。

结构链：batch CLI → request → current_sources/events → scheduler → execution_context → select/summarize/verify → effect dispatcher → artifact store → transport read/replay。当前 document_id 同时用于去重、subject、generation、恢复和结果；同母页两发行人无法仅靠新增 source_class 区分。非 filing select/replay 均走 transcript，行定位不能重放 JSON pointer/编码字节定位。多页 projection 也不能由第一页冒充全部来源。

## 已有能力和版本

`source_catalog/official_json_projection.py` 已有 build/load/persist/replay/export、各字段 EvidenceSpan；复用它，不再写一套身份/字节校验。实际 structure/parser 为 **1.0.1**，layout 为 1.0.0。旧 1.0.0 投影不悄悄按新 parser 解释。SourceRef 2.0、SourceExport 2.0 原义保留。

投影绑定完整 parent SourceRefs、issuer/as-of、adapter、records、coverage、layout fingerprint。`source-projection-ref/1` 名称虽含 ref，实际含 records；不能整份反复复制到请求和事件。

## 独立存储边界审查的补充

`/root/m3_joint_acceptance_review` 已确认 `AutomationStore` terminal compaction 在 store.py 的两处直接从 event.payload.source_ref 比较 pin.document_id/source_id/source_sha，并要求旧 narrative-bundle:{document}:{source_sha} target。`NarrativeEffectDispatcher` 也按 bundle.source_ref.document_id 查 generation。只改 batch/select 会在终态签 receipt、压缩或发布阶段失配。

应由同一个 subject identity accessor 贯通 payload→generation→effect→artifact pin→terminal receipt→read。真实 parent 只作为原件和关联锚点，不能伪造投影 source_ref。尚须实施并由测试证明。

## 风险边界

provider timezone、答复首次公开时间和 live API 公司过滤未经本节点证明，未知仍未知。旧 raw 身份和合同不变。新投影字段的支持不是新增人工权限；不需要 review receipt 或按公司授权。公司预测和投资结论由 RF/下游承担，CWP 只保存来源、提取与工程记录。

## 最终独立只读审查：补充存储与构造不变量

Catalog narrative_artifact_versions 的 document_id/source_id 为真实 documents/sources FK，现有 prepare/activate/read_current 只验单 active primary。投影 ID/SHA 不填原件列；同一 artifact index 增显式 subject binding 或同 store 的多 parent 表示，真实 anchor 仅关联。投影读取必须以 subject ID + projection SHA + generation 精确查找，旧 latest_visible_version(document,source,sha) 不用于投影发现，所有 parents 由 source port 校验。终态压缩、effect target、pin、generation 和 public read 共用身份解释。

独立纯内存实证：同一合法两页集合倒序输入，complete 都 true，但 projection_id 不同。新建投影时对可证的声明页顺序规范化，不能重签已封存 ID；保持真实记录内顺序/定位，不把不明分页猜成完整。相同合法页集合不同枚举顺序必须生成相同新投影/generation，防止重复付费。SourceProjection 只有浅 frozen，issuer dict 可变而旧 SHA 不变；新的 verified view 必须深冻结或隔离复制，调用方后续变动不能污染 view 或缓存。

三项集中必测：①同页 A/B 独立 subject/DAG/artifact，原件一份，交叉读取拒绝；②两页同 pointer 仍各自母 SHA，第二页字节/状态/绑定变化、问题冒充答案均拒绝，partial/cutoff保持真实；③相同语义精确零调用复用，变任何绑定不能错复用，ACK前/激活前恢复一次结算/发布且旧lease不能完成新generation。首次验证不是永久许可证：publish/后来 public read 在所属 source 边界核当前父页集合，handler 不各自重复解析。仍用现有 AUTO DB，不新增任务账本。

只读审查：/root/m3_usage_acceptance 与 /root/m3_joint_acceptance_review；均未写源码/配置/原件/数据库/安装，provider/model/费用0。这是下一节点接口风险与TDD要求，不是本节点实现完成。


## MAIN foundation actual update (2026-10-10)

# MAIN 接线 Findings

2026-10-10恢复：canonical master a034b3eb，MAIN隔离树已仅文档fast-forward该HEAD，源码与三卡已验收基线相同。P7三包已备齐；MAIN不会修改它们的独占文件。三个内置agent仅只读研究store/transport/source adapter，为MAIN共享接线提供实际接口调查，不是重开外包。

当前实际batch/event/context/dependency均以document_id识别；同母页不同issuer必然需要统一item identity，并保留原件anchor与完整parents。旧2.0严格DTO只支持filing/transcript及单parent，不能假填projection进source_ref。source层build_projection_export可以一次验parents并返回selected field EvidenceSpan，不需handler反复replay。

public source_catalog.cli当前只识别旧subcommands，尚未dispatch官方入口；main在parse前改变stdout编码。必须最先识别首个official子命令并原样委托既有official_source_cli.main，不重复parser/importer/原件writer。真实read stdout bytes、末尾close及typed failure由既有入口负责。

先写公共入口RED，再引入统一subject契约；统一Worker全链仍未完成。本轮默认项目provider/model/费用0、临时测试与原件分离。


## 基础节点真实结果（2026-10-10T21:37:00.220175+00:00）

公共dispatch原11 RED后GREEN；subject首次module缺失RED，其后测试误假设issuer只有一个键造成1失败，修正为保留实际sourceproducer完整issuer而非删字段。最终164PASS含14subject、10dispatch、1realCLI及139既有source责任/兼容。Ruff0/mypy0。CLI公开语法official为首token，--config置其后，避免自造复杂argvparser。
