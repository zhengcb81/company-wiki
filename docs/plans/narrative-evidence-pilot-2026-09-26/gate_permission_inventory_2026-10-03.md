# 门禁与权限现状：逐项审查清单（2026-10-03）

> 本次是静态只读审计和计划收口，未改变产品门禁、启动Worker、调用provider或读取API key。文档发布沿用现有快速Git检查。**P0主调用链已实质简化，P1/P2尚未全部完成**；不能用旧方案的“尚未执行”或某个历史函数名推断现状。下面每个编号对应一项可独立裁定的规则，重复实现合并说明。建议尚未变成新的执行门；由用户裁定后并入现有大节点。

## 1. 简化进度与审计基线

| 已取消/已放宽 | 当前实际状态 |
|---|---|
| private/public及外部LLM逐文档许可 | 配置根均可读，privacy_class只剩兼容标签；没有per-document外发review receipt前提。 |
| prompt injection/manual remediation 全局消费阻断 | pending proposal/not_reviewed/review store问题不再挡正常读、复用、摘要；状态可诊断。 |
| RF prompt人工复核 | not_reviewed允许；不再要求人工签收才能预测。 |
| RF缺fixture hash不可闭环 | 缺hash=pending诊断且可闭环；已有hash错配仍失败。旧09-29严格裁定已被用户10-01放宽覆盖。 |
| RF发布授权文件 | release_authorization/issue-auth已取消，改机器readiness。 |
| FF/ET双下载授权 | FF新v2单一filing_intent，ET新API单一download_authorized；FF旧v1残留见12。 |
| IQS递归工程签收/部署approval_ref | task_receipts入口retired；部署用明确一次执行和budget，不要重做独立reviewer链。 |
| StockWiki重复pytest | check_all只跑一次coverage-wrapped pytest，阈值仍见46。 |
| 每提交自动全coverage/full Contract/多Python CI | 已取消，CWP单job快速CI。 |

CWP审计代码`master@9eacbea`；RF`rf-impl/main@6fb2def7`；FF最新交付线/origin/main`c47c397`（仓根仍`fcap@d35b6f5`，不改该owner树）；ET`main@4924d57`；StockWiki`master@d4779e6`（含他线W06）；IQS`master@bfaf04c`。本次相关仓只审来源集成/工程签收范围，不宣称审完下游投资评分全部规则。

安装核对：`.agents`和`.codex`两份filing-fetch的fetch_filing.py、filing_contracts.py、transcript_companion.py都与FF交付worktree同字节SHA。fetch入口71873B/SHA`281512fd9e52c87458ae59dd03eb7f1db7da19af134367088202eafc94c68161`，所以v2不只存在于远端。SKILL.md仍有v1示例；本次没执行安装CLI，未冒称所有安装依赖已重新E2E。StockWiki正常用户核实core.hooksPath未设置、默认pre-commit不存在，check_all目前是手动脚本/文档要求。

## 2. 建议清理的人工或历史残留

| 编号 | 规则 | 实际生效范围/触发 | 保留理由 | 建议 | 代码证据 |
|---:|---|---|---|---|---|
| 1 | 启用/回滚/恢复必填 reviewer | 显式维护 CLI/库仍严格 | 过去用于记录修复审核人；当前只检查非空，未证明第二人身份。 | 去掉必填审核人，自动记录 actor/run；保留事务和改了什么。 | [source_catalog/cli.py · 672](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/cli.py:672)；[source_catalog/restore.py · 59](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/restore.py:59) |
| 2 | 可选 prompt-review 记录的签名/信任根 | 只在主动写这种 receipt 时严格 | 保护可选审核记录的声明；读取与模型调用不依赖它。 | 简化成诊断记录，退役人工签名/TTL链。 | [source_catalog/prompt_injection.py · 94](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/prompt_injection.py:94) |
| 3 | AUTO gold 的 BLOCKED_HUMAN、八阶段 readiness | 库占位/shadow，无当前来源生产接线 | 历史人工 gold/shadow 评审设计。 | 归档 shadow 模块；取消 placeholder 与无人使用的人工审批槽位。 | [handlers/gold_review.py · 59](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/handlers/gold_review.py:59)；[source_catalog/readiness_graph.py · 15](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/readiness_graph.py:15) |
| 4 | Work Unit 候选→独立复跑→reviewer及 gold 二审 | 独立旧工程工具，不在日常 hook | 过去要求不同 implementer/reviewer、复跑和一致工作区摘要。 | 退役强制工程签收；保留有价值的测试/语料和历史结果。 | [scripts/reviewer_gate.py · 26](C:/Users/郑曾波/Projects/company-wiki/scripts/reviewer_gate.py:26)；[scripts/gate_state.py · 30](C:/Users/郑曾波/Projects/company-wiki/scripts/gate_state.py:30)；[scripts/gold_review_gate.py · 459](C:/Users/郑曾波/Projects/company-wiki/scripts/gold_review_gate.py:459) |
| 5 | deletion_manifest 的 commit_blocked/independent_review_required | 主动调用旧清单 verifier 才严格 | 过去的派生文件删除审批；会拒绝已暂存删除。 | 去掉人工签收和禁止提交字段；保留非原件、精确集合、Git事实。 | [scripts/deletion_manifest.py · 165](C:/Users/郑曾波/Projects/company-wiki/scripts/deletion_manifest.py:165)；[scripts/deletion_manifest.py · 231](C:/Users/郑曾波/Projects/company-wiki/scripts/deletion_manifest.py:231) |
| 6 | 兼容脚本双环境变量许可 | 部分 legacy CLI 仍严格 | legacy 写模式与 legacy-writers=allow 同时为真才能执行。 | 逐脚本正规化或退役，不继续维护双布尔授权；研究 writer 冻结见33。 | [scripts/writer_policy.py · 102](C:/Users/郑曾波/Projects/company-wiki/scripts/writer_policy.py:102) |
| 7 | 旧退役流程：90日/archive-first、双 smoke 相隔600秒、固定10GiB余量 | 旧库/一次性运维工具；非日常 Worker 自动删 | 过去完整备份/回退设计；weekly prune目前只dry-run。 | 已完成工具移历史；未来只保原件/必要事实，不重新启用全量派生备份链。 | [source_catalog/prune_retired_evidence.py · 445](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/prune_retired_evidence.py:445)；[scripts/cutover_source_catalog_db.py · 338](C:/Users/郑曾波/Projects/company-wiki/scripts/cutover_source_catalog_db.py:338)；[scripts/retire_source_catalog_db.py · 74](C:/Users/郑曾波/Projects/company-wiki/scripts/retire_source_catalog_db.py:74) |
| 8 | secret_audit 将 ignored 本机 .env 候选也计 blocked_external | 可选旧审计工具，不是日常 LLM 门 | 历史泄露排查把本机、工作树、Git历史候选合并。 | 合法 ignored 凭证仅诊断；阻断范围限真正待发布的密钥，不因凭证存在要求轮换。 | [scripts/secret_audit.py · 249](C:/Users/郑曾波/Projects/company-wiki/scripts/secret_audit.py:249) |

## 3. 当前可放宽、可重构或需明确选择的规则

| 编号 | 规则 | 实际生效范围/触发 | 保留理由 | 建议 | 代码证据 |
|---:|---|---|---|---|---|
| 9 | 整份 runtime/root/read-policy hash 绑定 | 当前读取、叙述 event 机器阻断 | 防执行时根/配置/来源可见性被替换。 | 保留真正影响该操作的版本/字段；缩成最小 fingerprint，减少无关配置变化造成失效。 | [source_catalog/source_reader.py · 149](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:149)；[automation/narrative_source_guard.py · 48](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/narrative_source_guard.py:48) |
| 10 | latest-as-of 必先 GapPlan，再 close-gap binding-file | 当前补采机器门；无第二人签字 | 绑定候选 provider/accession、gap/policy hash、expiry、数量和字节上限。 | 一次明确请求自动编排两步；不给用户手工搬 binding。 | [source_catalog/acquisition.py · 356](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/acquisition.py:356)；[source_catalog/close_gap.py · 218](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/close_gap.py:218) |
| 11 | 暂停时采集还需 allow-acquisition-while-paused | 当前 ensure/close-gap 真实额外开关 | 旧设计把后台暂停同时当采集禁令。 | 暂停后台与主动采集分开；一次明确下载请求足够，消除相互抵触的 flags。 | [source_catalog/cli.py · 777](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/cli.py:777)；[source_catalog/cli.py · 1237](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/cli.py:1237) |
| 12 | FF v1 的 allow-download + authorization 双门 | legacy v1 保留；新 v2 已移除 | 兼容旧请求/响应。两安装技能入口已是最新交付字节，旧仓根仍fcap。 | 正常入口统一v2；有真实v1调用者才留适配，避免第二套授权规则。 | [scripts/fetch_filing.py · 1255](C:/Users/郑曾波/AppData/Local/Temp/ff-source-reader-v2-20260927/scripts/fetch_filing.py:1255)；[scripts/filing_contracts.py · 114](C:/Users/郑曾波/AppData/Local/Temp/ff-source-reader-v2-20260927/scripts/filing_contracts.py:114) |
| 13 | filing_reuse 必有采集资格证明 | 当前仅此 purpose 阻断 | 要求发布日期、可证明期次、HTTPS来源URL、collector/retrieved provenance等。 | 身份/期次冲突仍拒绝；缺采集字段降 qualification warning，允许原文预览/定位。 | [source_catalog/source_reader.py · 667](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:667) |
| 14 | 仅 active 来源可 query_ref，坏/冲突元数据拒绝 | 当前机器阻断 | 避免正式消费撤回、隔离或身份冲突来源。 | 正式消费保留；另允许带状态的历史/不完整来源预览，不把预览锁死。 | [source_catalog/source_reader.py · 203](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:203) |
| 15 | as-of 同时限制发布日期与 retrieved_at | 叙述 transport 当前严格；普通查询也排未知发布日期 | 同时证明文档已公开和当时本机已收到。 | 默认依发布日期；后来补录的旧公开材料可用。严格历史已收集快照作为独立可选模式。 | [source_catalog/source_reader.py · 313](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:313)；[automation/narrative_transport.py · 62](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/narrative_transport.py:62) |
| 16 | normalized 产物只接受当前 NORMALIZER_VERSION | 旧派生 reader 当前阻断 | 避免无法解释的 parser/lineage版本混用。 | 改明确支持版本表；兼容旧可验证产物，失配才重建。 | [source_catalog/normalized_artifact_reader.py · 213](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/normalized_artifact_reader.py:213) |
| 17 | 摘要 exact JSON 字段、研究词正则禁令 | 现行摘要校验 | 绑定来源角色，防模型产出投资判断；词级过滤可能误拒原文事实。 | 引用/必填结构保留；容忍无害额外字段，按输出用途判断研究语义。 | [source_catalog/llm_summarizer.py · 137](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/llm_summarizer.py:137) |
| 18 | parse error/opaque page/无可回放证据可使整份终态失败 | 叙述 handler 已实现库层；正式N4未上线 | 避免把无法定位的正文包装为有效证据。 | 坏片段丢弃并记coverage，尽量partial；整份无可靠证据才失败。 | [automation/narrative_select.py · 374](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/narrative_select.py:374) |
| 19 | root kind/来源类型/状态/单文件大小准入 | 当前配置型机器门；没有private/public读禁令 | 约束adapter能力和实际可处理范围。 | 缩到真正能力约束；目录位置由存储层解释，不再让业务层各自建白名单。 | [source_catalog/source_reader.py · 638](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:638) |
| 20 | 旧Worker禁电池处理 | 当前配置false；scan不被该分支阻止 | 节电偏好。require_user_idle目前false；CPU IDLE/nice是降优先级，无CPU/RAM硬阈值。 | 可直接允许电池；优先级设可配置，不将用户闲置作为默认开工条件。 | [config/source_catalog_worker.yaml · 14](C:/Users/郑曾波/Projects/company-wiki/config/source_catalog_worker.yaml:14)；[source_catalog/worker.py · 598](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/worker.py:598) |
| 21 | 解析失败退避900秒、LLM全局冷却60分钟 | 旧Worker当前严格 | 减少重复失败/费用和provider限流压力。 | 按429/认证/超时/单文档错误分类；取消单文档失败影响全部模型任务的长冷却。 | [config/source_catalog_worker.yaml · 27](C:/Users/郑曾波/Projects/company-wiki/config/source_catalog_worker.yaml:27)；[config/source_catalog_worker.yaml · 51](C:/Users/郑曾波/Projects/company-wiki/config/source_catalog_worker.yaml:51) |
| 22 | 旧运行限额：小batch/输入输出/解析期限/日估算费用 | 当前旧Worker配置和LLMClient；部分是截断非拒绝 | normalize3/fingerprint3/sections5/LLM1；解析3600s、产物256MiB；LLM120000chars/2400tokens、间隔1s，日估算$15。CSV不是原子预留。 | 保留可配置资源上限；批次并发/持久预算按N4实现，不能把CSV当严格费用保证。 | [config/source_catalog_worker.yaml · 18](C:/Users/郑曾波/Projects/company-wiki/config/source_catalog_worker.yaml:18)；[scripts/llm_client.py · 201](C:/Users/郑曾波/Projects/company-wiki/scripts/llm_client.py:201)；[source_catalog/normalizer.py · 292](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/normalizer.py:292) |
| 23 | 全局catalog锁包住完整解析和LLM网络等待 | 旧source service真实运行路径 | 避免两 writer冲突；持锁过长限制多文档吞吐。 | 耗时计算移锁外；只在提交时锁定并重验source/version。此处需重构，不直接删锁。 | [source_catalog/service.py · 193](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/service.py:193)；[source_catalog/service.py · 278](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/service.py:278) |
| 24 | LLM provider固定五品牌、fallback usage_scope仅general | 旧Config/LLMClient路径 | 对应已有SDK/协议支持，不是文档外发权限。 | 按协议/adapter能力配置；只增加实际支持的能力，不简单删校验冒称支持所有provider。 | [scripts/config.py · 318](C:/Users/郑曾波/Projects/company-wiki/scripts/config.py:318) |
| 25 | SourceExport v2 span只支持TXT UTF-8字符定位 | 现行实现能力限制；PDF仅manifest | 还没有通用PDF span exporter定位实现。 | 保留诚实能力声明；另扩parser-owned定位，不靠放宽校验宣称支持PDF。 | [source_contract/source_export_v2.py · 165](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_contract/source_export_v2.py:165) |
| 26 | RF自动发布工具固定三仓HEAD/197场景/容量/backup可写 | 独立机器readiness工具；人工release_authorization已移除 | 发布一致性及回退记录；backup检查只是目录写探针，不要求本轮完整备份恢复。 | 大发布节点按需；去掉固定197和不相关仓强耦合，保留真正依赖产物/版本验证。 | [tools/release_readiness.py · 164](C:/Users/郑曾波/Projects/rf-impl/tools/release_readiness.py:164) |

## 4. 建议保留的正确性与运行规则

| 编号 | 规则 | 实际生效范围/触发 | 保留理由 | 建议 | 代码证据 |
|---:|---|---|---|---|---|
| 27 | RF可选host_signed/Ed25519声明校验 | 普通无签名不被阻断；声称签名时严格 | 避免伪称机器来源已签名。 | 保留声明一致性；个人普通分析不要求签名凭据。 | [contracts/evidence.py · 313](C:/Users/郑曾波/Projects/rf-impl/scripts/contracts/evidence.py:313)；[scripts/revenue_publication.py · 34](C:/Users/郑曾波/Projects/rf-impl/scripts/revenue_publication.py:34) |
| 28 | immutable raw及真实字节SHA/版本绑定 | 当前采集、open、派生和消费者的机器底线 | 防串文件、损坏或同ID内容替换，保护用户原件。RF闭环缺fixture hash已是诊断，但给定hash仍核一致。 | 保留；消除重复存正文和重复全库hash，不放宽已证明的字节错配。 | [source_catalog/source_reader.py · 725](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:725)；[uc/scenarios.py · 161](C:/Users/郑曾波/Projects/rf-impl/assurance/unified_completion/uc/scenarios.py:161) |
| 29 | 公司/证券/期次、IQS主体/perimeter/revision绑定 | 当前来源链/身份消费机器门 | 避免母子公司、上市地、年报期次和并表范围错配。IQS owner receipt绑定来源修订，非人工签名。 | 保留；缺字段可provisional/partial，不能伪装verified。IQS full G2b范围仍partial。 | [source_catalog/source_reader.py · 266](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:266)；[scripts/contract_validation.py · 471](C:/Users/郑曾波/Projects/invest-quick-scan/scripts/contract_validation.py:471) |
| 30 | 路径包含、原件写入归属、跨仓只读 | 当前存储/CLI边界 | 避免路径逃逸/误覆盖外部原件；保证上层用SourceRef而不改他仓数据库。 | 保留底层统一实现；消除上层重复目录判断。配置根都可读，无私有公司权限。 | [source_catalog/source_reader.py · 725](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/source_reader.py:725)；[company-wiki/AGENTS.md · 6](C:/Users/郑曾波/Projects/company-wiki/AGENTS.md:6) |
| 31 | 公开日期不得晚于分析as-of | 当前来源查询/消费者数据门 | 防未来信息污染历史分析。 | 保留发布日期原则；具体retrieved_at额外限制由15裁定。 | [automation/narrative_transport.py · 62](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/narrative_transport.py:62) |
| 32 | citation/evidence ID/locator/角色与回放一致 | 叙述验证库及已发布reader严格 | 模型摘要须能回到真实原文；needs_review/partial标签本身不阻发布/读取。 | 保留有效引用；坏片段降级范围按18处理，不增人工批准。 | [source_catalog/narrative_evidence.py · 1441](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/narrative_evidence.py:1441)；[automation/narrative_verify.py · 264](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/narrative_verify.py:264) |
| 33 | 公司资料source-only职责，研究型legacy writer永久退休 | 当前真实CLI退出78，环境变量不能恢复永久退休命令 | AGENTS要求研究判断由StockWiki独占；避免第二套研究状态。 | 保留职责边界；旧混合命令拆成正规来源操作，减少大allowlist维护。 | [scripts/writer_policy.py · 58](C:/Users/郑曾波/Projects/company-wiki/scripts/writer_policy.py:58)；[company-wiki/AGENTS.md · 6](C:/Users/郑曾波/Projects/company-wiki/AGENTS.md:6) |
| 34 | 暂停/唯一后台实例/PID身份/旧新Worker互锁 | 现行legacy控制；当前paused | 尊重暂停、避免重复worker和PID误杀。--once当前跳过pause和后台open_session互斥。 | 保留一个清楚运行开关；单次批次行为明确。只剩新Worker后移除旧新双系统互锁。 | [source_catalog/control.py · 929](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/control.py:929)；[source_catalog/cli.py · 1530](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/cli.py:1530) |
| 35 | AUTO lease/generation/attempt幂等、迁移backup hook | 已实现库层；无生产start入口，N4未接 | 多进程丢包/重试正确性、避免过期worker提交与数据库坏迁移。v1升级需显式backup hook。 | 保留事务/lease事实；提供默认一次性小库备份实现，减少调用者注入；不备份全资料。 | [automation/store.py · 197](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/store.py:197)；[automation/migrations.py · 634](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/automation/migrations.py:634) |
| 36 | API/SourceExport版本、schema、count/hash协商 | 当前producer/consumer自动检查 | 让不同仓明确解码能力，不吞字段漂移或坏包。 | 保留必要版本和内容绑定；去掉无真实消费者的兼容层/重复包字段。 | [source_contract/source_export_v2.py · 49](C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_contract/source_export_v2.py:49)；[company-wiki/README.md · 110](C:/Users/郑曾波/Projects/company-wiki/README.md:110) |
| 37 | 一次网络意图、provider开关、key/HTTP状态、URL/MIME/大小期限 | CWP/ET/FF真实外部调用边界 | 默认不意外下载/收费；ET modern禁用Motley，FMP缺key/402不可用。 | 保留一个请求与配置上限；已授权不反复问。FF请求预算接线和ET旧scraper需收口，见缺口。 | [earnings-transcripts/transcript_api.py · 191](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_api.py:191)；[scripts/transcript_companion.py · 219](C:/Users/郑曾波/AppData/Local/Temp/ff-source-reader-v2-20260927/scripts/transcript_companion.py:219) |

## 5. 工程检查：当前触发与简化方向

| 编号 | 规则 | 实际生效范围/触发 | 保留理由 | 建议 | 代码证据 |
|---:|---|---|---|---|---|
| 38 | Ruff | 相关Python提交、CI自动阻断 | 发现导入、语法和常见编码问题。 | 保留快速检查，不增加格式签收。 | [company-wiki/.pre-commit-config.yaml · 12](C:/Users/郑曾波/Projects/company-wiki/.pre-commit-config.yaml:12) |
| 39 | 限定合同模块mypy | 相关模块提交、CI自动阻断 | 保护跨层类型/DTO接口。不是全仓严格类型门。 | 保留并按真正公共接口缩小维护清单；不新加人工合同验收。 | [company-wiki/.pre-commit-config.yaml · 20](C:/Users/郑曾波/Projects/company-wiki/.pre-commit-config.yaml:20) |
| 40 | config doctor | 目前每次commit都structure-only；CI也检查 | 过去测试配置写穿生产YAML造成真实事故。 | 保留校验，按config/loader改动触发，减少纯文档提交负担。 | [company-wiki/.pre-commit-config.yaml · 102](C:/Users/郑曾波/Projects/company-wiki/.pre-commit-config.yaml:102)；[scripts/config_doctor.py · 23](C:/Users/郑曾波/Projects/company-wiki/scripts/config_doctor.py:23) |
| 41 | host assumption guard | src/tests Python变化自动检查 | 发现测试硬编码机器路径/能力/机器特定digest，避免Windows绿而Linux红。 | 保留或并成少量portable测试；只拦新增真实问题，不扩大baseline签收。 | [company-wiki/.pre-commit-config.yaml · 118](C:/Users/郑曾波/Projects/company-wiki/.pre-commit-config.yaml:118) |
| 42 | push精选测试、CI Unit+同一精选集合 | 当前真实Git/CI门 | 已缩至12个显式node IDs，CI单Python3.12/job5分钟硬上限；最近62秒绿。Markdown计划提交不触发CI。 | 保留廉价业务回归；完整Contract/coverage为按需，不恢复每提交长测。 | [tools/pre_push_gate.py · 48](C:/Users/郑曾波/Projects/company-wiki/tools/pre_push_gate.py:48)；[workflows/ci.yml · 24](C:/Users/郑曾波/Projects/company-wiki/.github/workflows/ci.yml:24) |
| 43 | CI硬编码密钥扫描 | CI代码范围自动失败 | 防密钥被提交到远端。 | 保留一个轻量待发布内容扫描；与08旧本机凭据审计分开。 | [workflows/ci.yml · 104](C:/Users/郑曾波/Projects/company-wiki/.github/workflows/ci.yml:104) |
| 44 | 测试无真实网络/密钥、独立根恢复、短basetemp校验 | 普通pytest严格；pre-push要求<=60且stdout决策不relocate | 避免普通测试收费/污染生产目录；短根解决Windows长路径。 | 保留隔离/恢复；本地HTTP或live E2E显式独立fixture。短根自动生成，简化stdout receipt硬绑定。 | [tests/conftest.py · 29](C:/Users/郑曾波/Projects/company-wiki/tests/conftest.py:29)；[tools/pre_push_gate.py · 111](C:/Users/郑曾波/Projects/company-wiki/tools/pre_push_gate.py:111) |
| 45 | 每文件复杂度ratchet，新文件max10；全Contract/coverage | CWP旧完整手动gate严格；日常快速路径不跑 | 控制函数复杂度，过去作为工程质量门。 | 降诊断/按大节点检查；不要因数字拆出无意义helper，日常不跑全套。 | [contract/test_fc1204_complexity_ratchet.py · 1](C:/Users/郑曾波/Projects/company-wiki/tests/contract/test_fc1204_complexity_ratchet.py:1)；[tools/pre_push_gate.py · 146](C:/Users/郑曾波/Projects/company-wiki/tools/pre_push_gate.py:146) |
| 46 | StockWiki total73%/ui40% coverage+check_all | 独立脚本仍严格；本机未配置pre-commit hook/core.hooksPath | 工程覆盖率；已把两次pytest并为一次。AGENTS仍有before commit全量文字。 | 改大节点按需；数字可降报告，以实际功能测试验收。修正文档节奏。 | [scripts/check_all.sh · 35](C:/Users/郑曾波/Projects/StockWiki/scripts/check_all.sh:35)；[StockWiki/AGENTS.md · 53](C:/Users/郑曾波/Projects/StockWiki/AGENTS.md:53) |

## 6. 本次发现的收口缺口

1. **P1未完成：**1–6所列旧reviewer/审批工具和compat门仍有代码；未接主链的也要清代码/文档，不能仅声称运行不挡就算项目简化完成。
2. **FF请求预算接线需补：**v2 acquisition_limits在filing_contracts.py:143/258被校验，但fetch_filing.py:208–241并未消费/向CWP转发这些单请求上限；目前是CWP配置默认限制。应在G-A相关节点验证request/config取min与零预算0网络，不能宣称单请求费用上限已严密落实。
3. **ET provider入口不一致：**modern API三入口默认disabled Motley，但旧scraper.py:445默认fool、509–518直接discover。应退出旧默认入口或共用同一provider配置；不加逐文档rights审批。
4. **旧archive/prune CLI有调用缺陷：**CWP cli.py:1143–1157漏必需now参数，按静态调用会TypeError；不是权限拒绝。若保留就修正式入口，否则随旧运维链退役。weekly prune apply=False，与config“auto-recycles”文字不符。
5. **N4仍未实施：**限定job scope、真实模型composition、持久费用预留、终态去重以及新增空间预算都在计划。2MiB单份最终正文/1GiB累计新增持久/2GiB批次临时峰值是拟议默认值，当前未生效；用户可调。没有原文配额删除或新的人工许可。
6. **文档漂移：**旧09-29总清理卡标“尚未执行”及“RF无hash不能闭环”、StockWiki before-every-commit全量、旧idle/自动prune/RequestPlan pending文字应按本清单覆盖。历史测试/收据保留，未来执行动作以当前入口为准。

## 7. 项目规则与运行环境

项目内没有多用户角色/私有公司访问系统；privacy标签不构成权限。当前仓无`.claude/settings*.json`及项目`.codex/config.toml`权限配置。Codex管理的workspace sandbox、`.git`写入需正常用户执行、auto-review属于harness运行环境，本仓代码不能取消它们；已授权Git/网络用正常用户上下文执行。此前pytest owner-only临时ACL是不同OS账号创建临时树造成，24根已清完，不是原文私有权限；未来创建/测试/finally清理同账号。

## 8. 后续执行方式

用户可按编号指定取消/保留/降为诊断/改默认。整合成三块既有工作：人工/历史残留收口；读取规则与兼容收口；N4运行与预算/锁改造。每块只在原有大节点集中验证，复用已签收P0/G-A/G-C结果，不给每个编号加独立审查或重新跑全仓。审计清单不是又一套人工授权文件，不能把它加进产品CLI的准入条件。当前主线下一实施动作仍N4A，审计裁定并入对应owner的同一节点。
