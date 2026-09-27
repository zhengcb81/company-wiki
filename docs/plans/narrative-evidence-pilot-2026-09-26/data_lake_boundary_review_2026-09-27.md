# 数据湖边界复核：目录、来源与消费者（2026-09-27）

> **状态：设计修订，未授权实施。** 本文只修订叙述证据专项与跨仓接口的实施口径；不修改产品代码、生产资料、数据库、Worker 或 revenue-forecast 的计划。虚拟数据湖的唯一通用实施编排仍是 [R4](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md) A/B/C；本专项复用其合同与 [L01–L12、P01–P03 测试](../painpoint-outcome-audit-2026-09-05/simplified-test-matrix.md)，不另造一套数据湖或逐文件审批流程。2026-09-27 用户澄清 RF 后续工作是本地未提交改动：不以其并入 main 为技术前置，CWP 产品代码暂停仍不变；RF 适配前须锁定可复现候选快照或支线提交。

## 1. 判断：哪些目录差异合理，哪些不合理

**用户的抽象目标成立。** 已批准的 company-wiki、dayu 和 Dropbox 目录是同一来源目录册的不同物理位置。调用者按公司/证券、文档类型、期间、公开时点和所需能力找资料；不能因文档移到另一个已批准 root，就改变文档身份、业务字段、叙述证据、预测输入或是否必须重新下载。相同字节的多个位置是副本，真实修订是新版本。无需把所有文件搬入一个目录或合并仓库。

**目录仍有受控的操作含义。** 适配器需解释布局与 sidecar，Dropbox 可能是未水合的云占位，外部 root 可只读，canonical 新下载只写 company-wiki 指定收件区。来源许可、公开时间、身份可信度、隐私和 LLM 外发资格按具体来源与动作判定，不能由 `root_id` 或“同 SHA 的另一份副本”洗白。读已获准的原文、联网下载、加工、外发、删除是不同能力；读不到返回明确状态，不在纯查询中偷偷水合/联网。固定一个受控写入目的地是所有权决策，不是读取抽象失败。

## 2. 本轮代码核对：已有骨架与仍泄漏的边界

| 观察 | 本轮定位 | 架构含义 |
|---|---|---|
| `sources/documents/locations` 与 `root_id/location_id/source_id` 已区分逻辑来源和位置；配置注册多个 root | `scanner.py:79-88,997-1002`，`models.py:87-109`，`config/source_catalog.yaml:13-39` | 沿用现有目录册和适配器，不创建第二套索引。 |
| resolver 已调用统一 reusable policy，候选选择也逐份探测/尽力验真并回退；但仍可能返回依赖旧 catalog 声明的 `unverified_*_on_pre_b02_canonical` handle | `resolver.py:1367-1377,1789-1874,2012-2054` | 2026-09-07 诊断中“只查首选副本”“policy 与 resolver 不一致”两项已过期；**resolve 命中不等于交付字节已硬验**，须走受控 read。实施前按当前版本重核，不为旧红例重复造候选回退。 |
| 生产配置仍是 schema 1.0，前三根未配 adapter_id；扫描器按 root kind 给默认类型、分 `dayu_meta/acquisition` 容器，按 root priority 选择元数据更新 | `config/source_catalog.yaml:13-29`，`scanner.py:848-865,170-184,1022-1031,1734,1861-1864`；`resolver.py:1195-1200` | 物理位置可能影响业务元数据。先用同 SHA、不同 sidecar/扫描顺序的隔离夹具证明影响，再将字段级来源可信度与副本 I/O 优先级分开。不得盲改生产 metadata。 |
| normalizer 自行选最高优先级路径；SourceHandle 暴露 `canonical_path` | `normalizer.py:1709-1743,2160`，`resolver.py:1935-1955` | 内部解析和外部消费应共用受控选择/读取；路径是诊断或临时传输参数，不是来源身份。 |
| ArtifactHandle 自行做本地 Path/allowed_roots 检查；SourceManifest 保存 `original_path`，现有 export 对单 root 作检查 | `artifact_handle.py:105-132`，`source_contract/source_manifest.py:171,315-326`，`source_contract/source_export.py:200-236` | 不应把所有路径字段一删了之：不可变 capture path 可保留为历史 provenance，当前可读位置须另由 location 解析；工件/导出和原文共用同一受控读取与版本边界。 |
| `read_verified_bytes` 已有一次读缓冲并按 SHA 验字节的进程内原语，但代码明说直接打开 `canonical_path` 可绕过它；CLI 尚无对应跨进程读取合同 | `resolver.py:2012-2054` | 不能简单让 filing-fetch 改调 Python 方法；R4 B07 要定义跨进程流/受控短期物化、版本协商、并发替换防护和清理语义。大文件不应塞进 JSON。 |
| filing-fetch 和 RF 直接依赖本机绝对路径并重读/重验；RF 还导入 CWP 内部 DAG | `filing-fetch/scripts/filing_contracts.py:440-515`，`revenue-forecast/scripts/company_wiki_source.py:113,275-300,439-449` | 消费者做了存储选择与上游生产编排。独立信任边界所需校验可以保留，但根目录分支、重复整文件 I/O 与 DAG 推导应在版本化合同后退出。 |
| CWP DAG/SourceBundle 角色白名单包含下游 `consumer_analysis`，但生产 generator registry 并无其生成器 | `artifact_dag.py:10-16`，`source_bundle.py:40-57` | 属职责边界疑点，**不据此声称生产已保存/复用 RF 分析工件**。CWP 只生产/保存来源解析工件，RF 分析角色及其失效/任务归 RF；先核现有调用者和兼容性，再经版本化边界迁出。 |
| 当前 narrative pilot resolver 仍需调用方给 `source_id → raw path` | 本专项 `implementation_plan.md:30` | 仅允许隔离试点；G2 正式 reader/export 不得要求 StockWiki/RF 知晓 company/dayu/Dropbox 的路径映射。 |
| StockWiki v1 manifest 的相对 `original_path` 参与 `export_id` 哈希，v1 sync 按 `source_root/original_path` 打开原文 | `StockWiki/stockwiki/company_wiki_contract_v1_records.py:91-102`，`company_wiki_contract_v1.py:97-126,272-289` | 只修 CWP resolver 不足以实现跨仓位置透明；旧 v1 留受控稳定兼容视图，新逻辑身份与字节读取另做版本化 export/reader 合同。当前 production provider disabled，v2 CLI 仅支持 sample/delta，全量同步不借 G2 放行。 |

上述是代码路径核对，不等于全部已在生产样本证明。尤其 scanner 元数据与优先级的实际输出差异，须在隔离夹具和真实只读样本上验证。`policy_3x.py` 的 external-root 私有规则不能无审查地覆盖当前生产配置的 public roots；具体读取/外发权按来源与动作裁决。

## 3. 唯一合同与仓库责任

| 层 | 对上层承诺 | 可知道/可改动 |
|---|---|---|
| company-wiki catalog | 用 `document_id + source_id/版本哈希` 查询身份、期间、公开时间、质量、撤回状态和可用工件；保留字段级 provenance | 知道来源与多个 location；不保存预测结论。 |
| company-wiki storage/open | 选择同版本的可读副本，按实际交付字节验 hash；失败明确区分 unavailable、需水合、权限拒绝、字节漂移；提供只读流或有期限的受控物化及收据 | 内部可用 root/path、I/O priority；不得换另一个 hash/修订冒充成功。跨进程 API 形状由 R4 A03/B07 冻结，不能把内部 `Path` 直接当通用合同。 |
| company-wiki producer/export | 只生产 normalized、sections、选定证据/来源摘要等来源工件，输出版本化 ID/hash/locator/质量及撤回语义 | 处理文档格式；不计算 RF 的 `consumer_analysis` 或 StockWiki 的投资结论。 |
| filing-fetch、dayu、earnings-transcripts | 提供 provider 候选、期次/身份线索、来源许可与原始响应；filing-fetch 编排用户显式请求和 discovery/fetch 时序，provider 执行获准的获取 | CWP 集中签发/复核具体来源与动作的 `DownloadAuthorization`、retain/derive policy 和 canonical admission；provider 与 filing-fetch 不另建第二权限中心或 catalog，也不自行规定“某 root 才有资格作财报”。新下载按用户要求交给 CWP canonical 收件区；历史只读位置可继续注册。 |
| revenue-forecast / StockWiki / quick-scan | RF/StockWiki 消费版本化来源与定位，分别拥有预测/研究状态；quick-scan 只用可选身份映射 | 不按路径前缀作业务判断，不写 CWP 数据库，不导入 CWP 内部 DAG。 |

跨仓实施的硬边界是：**StockWiki、RF、filing-fetch 等上层业务代码都不直接操作 CWP/dayu/Dropbox 的来源原文文件，也不接受需要自行打开的原文路径。** 它们只调用版本化查询、受控 `VerifiedContent` 与 EvidenceRef；必要的本地传输缓存由 CWP read broker/薄客户端按租约封装。各仓自己的数据库、预测工件和测试临时文件仍由其 owner 管理。StockWiki v1 的 `original_path` 路线只作限期兼容层，正式 source-provider reader 必须升级；见[R4 优先实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)。

目标操作最少三类：`query_local` 只查已索引资料、零网络/零写/零 Worker 控制；`open_version` 只打开指定版本并返回已验证字节或受控物化；`request_work` 显式申请缺失来源/派生工件，交唯一持久任务入口。`latest` 默认是**湖中截至时点的最新版**，线上搜新资料是另一个需授权动作。对外证据引用使用来源/文档版本加 locator；路径可在诊断或本机短期物化收据出现，但不得决定业务身份或下游权限。跨进程物化的时限、私有目录、回收、竞态和是否需要消费者独立复验，由 R4 合同与真实大文件量测决定；不能为了“去重校验”删掉独立信任边界。

## 4. 改动预算与实施顺序（沿用 R4 和本专项大节点）

1. **先冻结跨仓事实，不要求 RF 并线**：区分 RF 已推送 `ee0a82bfd` 与本地未提交后续候选；对照 owner 冻结的候选工作树快照/支线提交、CWP 当前 dirty 文件、filing-fetch 工作树和 R4 现状；不把 `accepted_scoped` 当生产入口已实现。形成一页 call graph/字段归属表，标出每个直接 `canonical_path` 读取、root 特例和 `consumer_analysis` 调用者。CWP 代码暂停单独有效。
2. **R4 A 目标合同裁决 + 本专项 G0**：冻结来源身份/版本/locator、按动作能力、字段级 provenance、写入 owner 和跨进程 `open_version` 的目标及 B07 待验条件。G0 仅在此基础上决定 narrative role/export/唯一 job owner；它是设计冻结，**不以前置要求 B07 已实现**，也不把 RF 的 DAG 搬入 CWP。无需完成 R4 全部实现才能写叙述选择器，但不能把试点路径映射当正式消费合同。
3. **R4 B 受控读取**：先复用现有同 SHA fallback，修 scanner/normalizer 的根特例与元数据优先级耦合，再提供跨进程版本化读取/短期物化。每一项以当前代码差分和失败夹具为依据，若已有功能就直接保留。新 root 为已支持格式时，只改注册/适配配置；不改 RF/StockWiki/filing 的业务判断。
4. **R4 B 阶段验收后，R4 C 瘦消费者 + 本专项 G1c-b/G2**：filing-fetch 先本地 query/reuse，缺失时经用户显式请求及 CWP 来源/动作授权再调用 provider；RF/StockWiki 读只读 export/受控原文，不直接打开 canonical path 或导入内部 DAG。narrative pilot 的显式 raw-path map 在正式 G2 reader 中删除；`consumer_analysis` 迁出 CWP 需旧合同兼容与真实 caller 回归。G1e transcript acquisition 仍是上游独立工作，不能借其成果放行 G2/Worker。
5. **G3/G4**：Worker、并发和原文处置只消费稳定的 source/version/job 身份，保持已有暂停与精确删除门。目录迁移本身不触发预测或来源重算，原文删除须按 SourceDisposition 和下游引用另审。

只有缺少**跨来源通用原语**（如受控读取、格式 adapter、统一 provenance/权限）才建议改 CWP 底层；新 provider、新目录、RF 新预测需求先在各自 adapter/消费者层解决。跨仓请求若确需改 CWP 核心，在 G0/相应 R4 设计审查一次写明缺失的抽象、受影响调用者和反例，不对每个文件另设签字。不要把“零 CWP 改动”当机械指标：真正的目标是新增同格式 root 不改消费者、业务逻辑零路径特例、变更只有一个 owner。完整的优先顺序、真字节候选和两次大节点 E2E 以[R4 优先实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)为准。

## 5. 集中验证，不增加逐节点门禁

沿用 R4 的 L01–L12、P01–P03，在 A 设计审查、B 隔离结果、G2 真实 reader 这三个大节点各复核一次受影响内容：

- 同一报告同 SHA 放在 company/dayu/Dropbox（及第五个已支持格式 root）后，身份、期间、来源说法、selected evidence ID/locator 与摘要引用相同；改变 root priority/扫描顺序不改变业务元数据。若 sidecar 信息冲突，显示字段来源和待裁决，不静默用目录优先级定真伪。
- 首选副本失踪或 Dropbox 占位时，只能切到已验证的同 SHA 可读副本；全部不可读返回 unavailable/需水合，零隐式联网；不同 SHA 的修订绝不回退冒充。目录移动后旧来源/证据引用仍能重放。权限拒绝、过期授权或 LLM 外发禁止不能通过另一 root 绕过。
- 使用真实 filing-fetch 与 RF reader/adapter 各一次隔离 E2E：本地 query→受控 open→原文/证据消费；新 root 只改配置，消费者零代码改动；读取不 pause Worker、不写生产库、不触发下载。StockWiki 用其真实严格 reader 做版本协商；quick-scan 只验身份映射。测试资料置独立 run root，结束恢复原状。
- 把“CWP 的 `consumer_analysis` 角色退出”和“消费者不再直接打开路径”列为迁移验收，而非先删旧字段。若性能上必须交付本机临时路径，收据与生命周期由 CWP 控制，业务结果仍与路径无关；对大文件测一次 I/O、临时峰值和重复 hash 成本，不能只凭设计推断加速。

**停机条件：** RF 最终合同未稳定、同 SHA 跨根身份/权限冲突、读接口不能证明交付字节、旧引用无法重放、真实 consumer 尚无可运行 adapter，均保持相应 G0/B/G2 关闭；已完成的上游样本试点不因此作废。上述节点之外不新增小卡独立复审。
