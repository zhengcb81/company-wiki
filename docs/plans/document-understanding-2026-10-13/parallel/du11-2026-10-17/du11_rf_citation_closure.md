# DU11-RF-CITATION-CLOSURE — 把来源引文的支持/上下文接到实际RF消费

状态：READY_FOR_DISPATCH。可以与DU11-FF-TRANSCRIPT-REUSE及ROOT CWP生产接线同时开工。

## 仓库、基线与工作目录

- 主仓：`C:/Users/郑曾波/Projects/revenue-forecast`。
- 明确基线：`568fb9256885eb31a0f76d9ead59fd0f98575073`；制作卡时HEAD/main/origin/main三者相同。
- 专用新worktree：`C:/Users/郑曾波/Projects/revenue-forecast-du11-citation-closure`。
- 新分支：`codex/du11-rf-citation-closure`。
- 命令：在主仓执行 `git worktree add -b codex/du11-rf-citation-closure C:/Users/郑曾波/Projects/revenue-forecast-du11-citation-closure 568fb9256885eb31a0f76d9ead59fd0f98575073`。只创建新checkout，不带主仓WIP。
- `PLAN_ID=du11-rf-citation-closure-2026-10-17`、`PWF_PLAN_ROOT=docs/plans`；PWF在新工区 `docs/plans/du11-rf-citation-closure-2026-10-17/`。

主仓已知WIP：`assurance/runs/daily_alert.jsonl`、`weekly_alert.jsonl`、`weekly_manifest.json`和未跟踪output/。这些与本卡无关，任何reset/clean/stash/提交都不得碰。不得把它们移到新worktree。

## 问题、依据与目标

CWP是原文/来源/解析/策略责任层；RF只消费已验证、带SourceRef/locator的证据并用于收入模型。共享引擎生产装配仍由ROOT写CWP；本卡解决RF读入之后的语义丢失。

实际基线证据：`scripts/company_wiki_narrative_contracts.py::_reading_context`已验证du-production-reading/2的group/citation_views，明确support_evidence_ids和context_evidence_ids，并限制同parent、分区与已传输span。`tests/test_citation_attribution_narrative_contract.py`验证了reader接收与summary claim归因。可是 `scripts/source_narrative_context.py::narrative_read_receipt`仅保存selection/quality/dependencies；`consume_narrative_input`的binding只接受span_id/claim_id/parameter_id/support_type，直接将单span raw_text写claim，未保存其group/view闭合或unread/deferred/layout诊断。`scripts/research/input_evidence.py::_bind_narrative_span`还有另一条实际参数绑定入口，必须调查调用并统一适用语义，不能只修便于测试的一条。旧测试 `test_source_preparation_complete_result.py`、`test_architecture_dependency_uses.py`、`test_w04_public_consumer.py`覆盖了合法旧消费，可作兼容锚。

目标：复用来源所有者给出的支持/上下文视图，在RF实际claim/参数/公式依赖中保留闭合关系和有限覆盖诊断；防止把问题、表头、单位、脚注等上下文自动当作支持该结论的独立事实。不得重新路由/切片/解析原件或推导新投资结论、参数数值。reading coverage不足只作明确诊断，不因此新增预测许可门禁。

## 输入输出契约与兼容

输入仍来自已验证NarrativeContext和显式bindings：现有revenue-narrative-context/1与/3、reading_context缺省、du-production-reading/1和/2均按原公开wire兼容；不能升级/改写CWP schema。无reading_context的合法单span路径保持行为及原字段兼容。

当有reading/2 groups时，消费适配器从现有citation_views确定support与context；若多个view对同binding均合法，必须由显式可选选择字段（A节点固定命名/规则）或具名歧义结果表达，不偷偷取第一条。view选择只引用既有group/span，不自己生成来源知识。未归组合法span仍按原路径消费，不能要求所有span都有group。对Q/A有两个方向的view必须尊重source_role/claim含义；context不能“洗成”支持事实。对多parent投影，所有依赖必须仍绑定实际captured parent和原source_locator/pointer，不跨parent拼证据。

输出保留既有claims、source、parameter关联与formula refs；新增上下文/coverage信息优先位于版本化消费收据/独立trace对象，不向原claim塞入未声明字段。两条入口共享同一纯消费逻辑或明确复用的适配器。不得为了重构改变假设/公式/预测数值。A节点在自有INTERFACES.md冻结具体选view字段、trace schema和错误码，附旧/新最小JSON。不存在reading_context也不能声称完整覆盖。元数据read或无binding保持not_consumed；只有实际依赖到已使用参数/公式才consumed。保持结构/字节界限、未知/null和现有asof/身份错误语义。

## 精确写白名单

- `scripts/source_narrative_context.py`
- `scripts/research/input_evidence.py`
- `scripts/company_wiki_narrative_contracts.py`（只为本卡RF消费trace/版本兼容所需；不放宽上游wire或字节/身份验证）
- 新纯模块 `scripts/narrative_citation_context.py`
- 新 `tests/test_du11_narrative_citation_*.py`
- 新专属 `tests/fixtures/du11_narrative_citation/`（小型合成或既有公开wire的有限fixture，不含真实原件）
- 本卡PWF `docs/plans/du11-rf-citation-closure-2026-10-17/**`

其余文件只读。尤其禁止forecast/模型公式、research targets、发布门禁、安装目录、现有gold重写、CWP/FF/ET任意代码。现有测试作为验收执行，不为实现重写其期望；如发现其确实错误，先写明证据给ROOT，不暗中扩白名单。

## A — 调查与真实行为RED

核基线/主仓WIP不变；CodeGraph对已初始化RF做structural查询，若索引未含新函数则记录缺口，用已定位文件读源码，不创建/改索引。明确两条实际入口调用链，调查格式/claim validators如何承载新trace，避免重复validator。保留公开合法bundle经validate_narrative_response→实际consume的行为RED：能形成consumed claim但丢失上下文依赖/覆盖信息；不要仅检验源码是否包含某字符串。另为问题span被当管理层事实、多个view任取首条、表行丢单位/脚注设置独立手算反例。固定接口和兼容矩阵，无需ROOT对A签收。

## B — 共用根因实现与集中回归

实现一次纯view/上下文闭合适配，两条入口同用；参数/公式和已有source capture不复制第二权威状态。至少覆盖：旧无reading合法单span；reading/1；reading/2 Q/A双方视图与明确错误归因；table row+unit/header/footnote；同parent多group；ambiguous view；缺/重复/交叉support-context ID；foreign parent/source SHA；投影v3 source_locator/pointer；unread/opaque/deferred及采样counts/limited；空binding/not_consumed；context唯一选择与实际公式依赖。

不将所有“未读”当拒绝条件；真正绑定错误具名拒绝，不自动读更多原件或调用LLM。精确对照相同输入参数/公式/预测结果不变。集中跑新本卡tests和现有source_preparation_complete_result、architecture_dependency_uses、w04_public_consumer、citation_attribution_narrative_contract、shared_reading_narrative_contract、source_clock、与input_evidence的实际既有邻域，按仓库当前文件确认命令。

## C — 隔离E2E与交付

在独立临时树运行真实RF public reader→字节验证→consume→既有输入验证/计算公开入口，使用可复现、合法的冻结公开bundle和本地fake reader进程；fake只在公开CWP进程边界，不能mock掉RF reader validator、消费主体或公式依赖。另跑 `narrative_source_preparation.py` read CLI，确认实际导出上下文仍完整。用同一旧输入对照预测值不变和新trace语义正确。覆盖坏字节/SHA、wrong parent/asof、source不可用、读超时的反控，禁止额外来源下载/解析/模型调用。记录真实层级，不能把fake来源说成真实公司质量验收。恢复测试目录后执行下方独立agent最终审查并交接。

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
