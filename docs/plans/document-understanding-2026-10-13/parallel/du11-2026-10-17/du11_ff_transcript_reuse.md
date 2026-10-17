# DU11-FF-TRANSCRIPT-REUSE — 先复用已登记电话会，再决定采集供应商

状态：READY_FOR_DISPATCH。可以与DU11-RF-CITATION-CLOSURE及ROOT CWP生产接线同时开工。

## 仓库、基线与工作目录

- 主仓：`C:/Users/郑曾波/Projects/filing-fetch`。
- 明确基线：`f1a939e522c22b23659712a8bd2b344f5eb0a364`；制作卡时HEAD/main/origin/main三者相同。
- 专用新worktree：`C:/Users/郑曾波/Projects/filing-fetch-du11-local-transcript-reuse`。
- 新分支：`codex/du11-ff-transcript-reuse`。
- 命令：在主仓执行 `git worktree add -b codex/du11-ff-transcript-reuse C:/Users/郑曾波/Projects/filing-fetch-du11-local-transcript-reuse f1a939e522c22b23659712a8bd2b344f5eb0a364`。不要复制主树未跟踪文件。
- `PLAN_ID=du11-ff-transcript-reuse-2026-10-17`、`PWF_PLAN_ROOT=docs/plans`；PWF在新工区 `docs/plans/du11-ff-transcript-reuse-2026-10-17/`。

主仓存在未跟踪 `config/FMP_API_KEY.txt`，它是已知用户凭证，不读内容、不复制、不删、不提交。只按stat/路径说明其非本卡改动，不将其纳入源码hash清单。

## 问题、依据与目标

FF是请求/复用/采集编排客户端；原件位置、来源登记、identity/asof、字节SHA仍由CWP所有者负责。本卡不改CWP策略/解析/存储或ET抓取，不启用新供应商。

真实基线：`scripts/transcript_tool_transport.py::_source_request`连本地exact查询也固定provider='fmp'，`lookup_exact`成功返回provider同样写死fmp；`scripts/transcript_companion.py`的选项允许省略provider，但resolve_companion_transcript把省略值转fmp。故默认电话会请求查询不到已由CWP以motley_fool等真实provider登记的相同期次原文，可能再次走ET/FMP；采集供应商选择与现存原文复用耦合。DU10已验证41矩阵与TXT保真，不能重开它们或改其oracle来规避本问题。

目标：未显式限定provider时，先通过公开CWP exact query查已登记的合格电话会，不因其来自其他真实provider而忽略。唯一合格来源由CWP reader实读验证后复用；真缺失才调用原配置FMP采集。忠实返回真实候选provider/publication元数据，不能改标签使已有原文假装FMP。重复下载、未知费用、错误期次不能被吞掉。

## 输入输出契约与兼容

FF现有filing request与可选companion_transcript schema保持。A节点明确provider省略/显式fmp的差别：省略表示本地来源中性、缺失后仍只用现有FMP；显式fmp继续作为选择约束，不擅自拓展为通用provider开关。保持现有不支持provider的具名错误；不把motley在线provider加入选项。

必须区分固定CWP的两个真实公开入口，不能把原`_query`的专用lookup envelope直接改provider=None：

1. **未指定provider的跨来源本地查询**：执行 `python -B -m company_wiki.source_catalog.source_query_cli --config <合成config>`，stdin直接发送普通SourceRequest对象，`schema_version="1.0"`、`document_kind="investor_call_transcript"`、准确entity/market/security_id/fiscal_year/fiscal_period、`mode="exact"`、`as_of_date`、`provider=null`、`allow_download=false`。**不包**`company-wiki-transcript-import-lookup-request/1` envelope。该CLI直接构造SourceRequest，调用`SourceVersionReader.query_local`；result schema为2.0，含status/matches/reason/request_id/candidates/source_read_policy_sha256，并在非空时提供excluded_candidates。普通query_local不会返回unknown_publication成功候选；它会把不满足asof的候选放入excluded_candidates。
2. **显式provider=fmp与原下载去重路径**：继续现有 `company-wiki-transcript-import-lookup-request/1` envelope，`source_request.provider="fmp"`，调用`lookup_transcript_import`。此入口要求provider非None；**禁止**向该envelope传null并声称跨来源查询已支持。保留其unknown_publication去重语义与原下游采集FMP约束。

source_ref仍2.0/pathless；复用前仍由公开source_reader_cli输出原bytes与成功stderr JSON receipt验证SHA/byte_size。真实provider取**成功reader receipt.manifest.provider**（该manifest由CWP公开describe_version产生），不能假设query candidate顶层已经暴露provider，也不能用请求默认值伪造。无真实provider时保留unknown/具名诊断，不能把它改成fmp。不得新加CWP接口或为方便复制一套source-query函数。

复用查找状态与后续采集供应商分开表达于FF内部，避免第二“身份/来源数据库”。普通query结果按以下语义固定：

- `found`：只有唯一准确FY/Q、身份、asof合格候选且reader实读验真后才复用；已有合格match优先，不因同时存在未知日期excluded候选而丢掉合格结果。provider忠实取已核reader manifest。
- `ambiguous/blocked/unavailable`或结构/bytes不合法：保留具名原因，0 ET/0GET；不能转not_found。
- `not_found`且`excluded_candidates`里有`qualification.publication_status="unknown"`：保留其SourceRef与source-qualification/1诊断用于重复抑制，**不表示历史可用来源，也不能当真缺失重下**。不能给它套as_of_cutoff_verified=True。单个可表达的unknown可沿用现有unknown_publication语义；若现有wire不能忠实表达多个/受限unknown，则返回既有upstream_error/gap具名原因`publication_date_unknown`，不要加上游能力、伪造历史资格或等ROOT改CWP。
- `excluded_candidates`可能还有`after_as_of`/`invalid`资格；按固定qualification原字段报告，不吞成可复用。保守实现可将仅有受限/未知excluded的结果收窄为具名gap且0GET，不能假装来源不存在。只有真正无候选且无此类本地受限证据的`not_found`才进入原FMP采集。

`excluded_candidates`项真实shape是`{"source_ref": <SourceRef2>, "qualification": <source-qualification/1>}`；qualification含publication_status/as_of_date/local_bytes_status/historical_date_eligible/historical_reuse_eligible。它是查询观察，不是已读bytes证明。JSON字节/字段异常按既有上游错误处理。结果provider与source_ref实际来源一致；零ET/零GET必须由调用计数证明，不能根据标签推导。

## 精确写白名单

- `scripts/transcript_companion.py`
- `scripts/transcript_tool_transport.py`
- `scripts/ff_v2_envelope.py`（仅保持本卡真实provider结果兼容；不能弱化来源/费用/SHA检查）
- 新纯辅助模块 `scripts/transcript_reuse_selection.py`（如确需；不得加入存储/缓存）
- 新 `tests/test_du11_transcript_reuse*.py`
- 新专属 `tests/fixtures/du11_transcript_reuse/`
- 本卡PWF `docs/plans/du11-ff-transcript-reuse-2026-10-17/**`

其他路径只读，尤其禁止fetch_filing主编排、filing_contracts现有外部请求schema、config/、密钥、tools/offline_contract_matrix/、原41 CaseSpec/oracle及其预算、CWP/ET源码、技能安装目录。先调查当前validator是否已容纳真实provider，优先不改无关文件。

## A — 调查与真实行为RED

核固定HEAD与主仓无本卡外改；CodeGraph结构调查已初始化FF对lookup/resolve的调用范围，按已定位文件核当前公开源码。以独立CWP临时config/db登记一份合成motley_fool电话会，准确实体/FYQ/公开日，走真实FF companion与CWP query/reader的离线入口，复现默认查询provider=fmp看不到已有来源，触发不应发生的ET调用或not_found。RED必须是实测行为，不只断言源码字符串。核固定CWP `source_query_cli.py`的普通SourceRequest与专用lookup envelope两条分支、`source_reader.py::query_local/lookup_transcript_import`和`qualification.py`真实字段；分别跑合法中性普通request、provider=None的专用lookup被blocked、显式fmp专用lookup正例。明确unknown只在普通query的excluded_candidates里、真实provider来自成功reader manifest，不能以mock假定普通query返回unknown成功。固定输入/输出兼容矩阵，不等待A签收。

## B — 共用根因实现与集中回归

使用现有query/reader与bounded transport；把“复用范围”与“采集provider”解耦，不增加重复发现/全目录扫描/身份认证/缓存。至少覆盖：未指定provider的唯一motley本地hit、唯一fmp本地hit、unknown provider元数据处理、显式fmp有/无匹配、同FYQ多provider有歧义、blocked/unavailable；unknown-only excluded、多个unknown excluded、已知合格match+unknown excluded、after_as_of/invalid-only excluded；显式fmp原专用lookup的unknown_publication；candidate没有provider但reader manifest有真实provider；manifest provider缺失；错误issuer/期间、坏source_ref/SHA/byte_size、畸形excluded qualification与非法返回status。所有非真实缺失路径断言0ET/0供应商调用；费用与计数未知保留null。

真缺失分支仍一次原配置FMP下载→CWP导入；第二次同request零GET复用。保留请求限额/统一deadline/输出字节限与失败回收，不能新增无界重试。集中跑本卡tests和现有 `test_transcript_companion.py`、`test_transcript_companion_transport.py`、`test_transcript_launch_contract.py`、`test_transcript_response_budget.py`、FFv2 envelope实际邻域（以仓内真实文件名为准）。保持原测试断言；不为了绿把旧FMP约束全改成中性。

## C — 真实离线契约E2E与交付

固定CWP源码快照，只创建合成临时公司原文/manifest与SQLite。用真实FF CLI→普通source_query_cli的query_local→真实reader证明不同provider的已知公开日现存原文能直接复用；另用真实普通query产生unknown-only excluded证明保留unknown且0ET/0GET、known+unknown优先合格match、真无候选才采集。显式fmp原专用lookup的unknown分支与中性普通request分支分别实测；禁止把假的unknown查询返回或null-provider专用lookup当E2E通过。ET边界放可记录调用的fixture进程，收到本应零调用即失败。再用缺失来源+fixture ET response→真实CWP import→reader→重复reuse验证1次下载与0次复用链；只有ET供应商边界合成，不mock整个FF或CWP。命令入口可以是最窄公开companion对应路径，必须如实记录测试调用层级，不能只拿自定义helper代替完整链。

测试必须无真实网络/LLM/密钥，不提高case/batch/workers/原proof reserve；本卡不重复完整41矩阵。收据核调用次数、provider真实归属、SourceRef/SHA、asof与未知费用。覆盖response坏SHA、ambiguous和超时的无下载反控，恢复临时根/进程后执行下方独立agent最终审查。交接不宣称新provider上线或真实供应商数据质量通过。

## 共同执行与交接规则（本卡上下文自足）

本卡状态 READY_FOR_DISPATCH：计划已准备，用户尚未派发；不要将工作区或实现标成已完成。任务开始后按本卡固定提交在指定新worktree开工；不继承主仓未提交状态，不checkout/reset/clean主仓或他人工区。目标目录若已存在，先读其HEAD/status/PWF判断是否本卡重入；不覆盖未知内容。新分支名使用本卡codex/前缀。独立worktree只隔离源码，不是第二生产数据仓。

冻结上游CWP公开接口依赖 `34a7dd71aaa49d18c13fcdd300ce79581114ca5b`，ET参考接口 `2584b7eed062a9a30254bc06b4f19ab5471b414e`。ROOT会继续改CWP生产装配；作者不得直接用漂移主仓的新源码当固定依赖。需要真实CLI联调时，从指定commit只提取必需源文件（如src/、确实被导入的scripts源文件、pyproject.toml）到本卡owned TemporaryDirectory并记录路径和SHA；不整库复制，不提取companies/、transcripts/、真实config或历史收据。只在临时树创建合成config、SQLite与微型测试原件。冻结公开wire可作为紧凑fixture；不能为适配新实现去修改CWP wire、源读取校验、locator语义。缺少上游能力时提交精确复现与接口需求，ROOT统一处理；不能跨仓偷偷加能力或加手工签收。

资源与文件边界：0真实网络、0付费API、0LLM、0翻译、0密钥内容读取；不检查环境中的密钥值，不读FMP_API_KEY.txt。测试使用可记录调用的离线供应商边界；联网函数一旦被调用即测试失败，只有本机fixture明确允许。不得复制或改动真实公司原文，不能把生产资料放进fixtures或报告。不得改Dayu、IQS或StockWiki，不写CWP生产代码与生产tests。不得整套覆写.agents/.claude/.codex技能；ROOT并线后按差异定点同步。不要增加第二缓存、任务库、来源库、权限JSON、private/public分类、人工签收或小节点审批。

恢复要求：每个测试从新owned临时根开始，先记录目录相对路径清单，并放一个固定小sentinel和一个既存输出条目，记录字节SHA与mtime。执行后精确核对初始清单/bytes/mtime，无意外残留；测试新造的原件/sidecar/db/out/日志/子进程全部清理，最后owned TemporaryDirectory也必须删除。如故意测试中断残留，只保留在owned树里，验证恢复后按同样规则清理。不能删除或恢复他人工区文件，清理前验证绝对目标仍在本卡owned树。需要保留的证据为精简JSON、RED/最终测试摘要与小fixture，不留整份原件或数千个逐行日志。

只在A调查、B根因实现、C端到端三个大节点集中验证；不设A人工签收等待。遇到旧测试与事实相悖时，先以公开契约/独立手算或真实调用证明根因，保留RED；不能为绿改弱断言、删用例或提高既有预算。复用现有process transport和validator，避免另造CLI/身份/重试管理器。计数未知保留null，不能用缺字段推导0调用。

### 必须执行独立最终质量审查

作者实现与集中测试完成后，冻结源码实现提交，**必须调用另一位独立agent**，全面检查本卡任务完整度、所有源码diff、分层和写范围、真实RED、反控、最终E2E、恢复收据、兼容性及是否引入冗余门禁。作者不能兼任审查员。发现的每项问题要找到共用根因、全部修复、相关测试通过，再由同一独立审查agent复核最终受审源SHA。0未解决问题才可写COMPLETE并交接；这是一项质量审查，不是人工权限审批。不用另请用户签收A/B小节点。若工具确实不能调用独立agent，状态保留IMPLEMENTED_REVIEW_PENDING，不伪造PASS。

交付本卡自有PWF task_plan.md/findings.md/progress.md、handoff.md/json与receipts/。JSON至少包含：card_id/status、base_commit、branch、implementation_commits、final_delivery_commit（允许交接提交自身用后补记录方式）、精确changed_paths/允许范围、输入输出schema与兼容说明、tests的完整命令/退出码/用例计数/耗时、A-RED与B修复映射、C端到端真实层级与mock边界、固定CWP/ET commit和实际依赖源码SHA、sentinel/清单/清理前后收据、network/provider/LLM计数、独立reviewer身份/报告/受审源码SHA/0未解决、局限与ROOT接线说明。不能循环为记录自身HEAD再提交：先冻结源码commit并绑定所有源SHA，最后纯文档交接commit由ROOT核实际HEAD及源码未变即可。

只在作者分支提交本卡白名单内容，STOP交接；**不要自行合并或推main，不清理作者worktree**。ROOT保留完整历史、按最终源码验收后统一并线/推送/安装同步。简洁更新自有PWF，不写母PWF。任务卡路径在母CWP，实际施工在下列各自仓库。
