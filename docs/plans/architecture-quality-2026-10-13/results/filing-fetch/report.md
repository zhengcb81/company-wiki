# filing-fetch 架构与代码质量独立审查

基线：64b4d294；施工分支 codex/aq-ff-20261013。阶段 A/B 完成，代码与测试均已交付；阶段 C 由ROOT集中接收并线。

## 入口与职责图

公开 scripts/fetch_filing.py CLI / resolve_filing → request contracts → configured CWP root → verified identity → DB-only source query (exact reuse) 或 CWP ensure (missing/latest) → pathless SourceRef result；原文最终验真由 CWP reader。电话会独立结果经 transcript_companion → configured EarningsTranscriptsTransport → ET original-language acquisition → CWP import/read。所有 subprocess 使用 ff_process_transport 的有限字节/共享 deadline/process-tree cleanup。

## 已读范围

读取全部十个 scripts 模块的结构/入口和关键实现，两个 transport 与错误分类、v1/v2 contracts、reuse/query/ensure dispatch、ET import/credential launch；读取配置模板、config_doctor、selective installation、CI runner/workflow、两个 hooks、pre-commit/type/lint 配置和相关 unit/E2E fixtures。CodeGraph context/impact 用 canonical FF 索引定位调用关系（索引行号早于当前实现，读取指定文件用于修改），原始生产 checkout 不写。

## 已确认改造

- FF-AQ-01（高）：配置不是单一职责。fetch_filing.py:168 的 root loader、transcript_tool_transport.py:229 的有界快照与 token path、tools/config_doctor.py:61 独立 JSON/schema/token 验证各自实现；doctor 与 runtime 对未知小写/不完整 token 及非法 UTF-8 的处理不同，root/doctor read_text 无有界读取。提取仓内 ff_configuration：仅原有 SKILL_ROOT/USER_PROFILE，真实 stream.read(limit + 1)，统一 JSON object/schema/路径规则、ET保留独立凭证优先级与当前 launch snapshot。doctor复用 runtime 同一 root loader，不增加配置或授权门。
- FF-AQ-02（高）：SourceRef query 与 ensure 的绑定/投影重复且分叉。query 原样返回 candidate，只有顶层 substring 检查，未知 nested metadata 可外泄；ensure 递归检查后白名单投影。同一 logical candidate validator/projector 统一两路径，并复用已经存在的 SourceRef validator。物理字段按明确契约字段识别，不把 growth_path 业务名称当路径。已有 validate_handle_metadata 实际已检查 content_sha256/snapshot，不把它误报成遗漏。
- FF-AQ-03（中）：filing_contracts.py:223/586 日期仅 regex，不存在的 2026-02-30 也接受，as-of 和 publication 需要 calendar validation。保持 YYYY-MM-DD 合法格式，非法 request 在调用任何 provider 之前拒绝，非法 producer publication 是 upstream_error。
- FF-AQ-04（中）：tracked .githooks/pre-commit 硬编码 C:\Miniconda\python.exe，且 #!/bin/sh 下写 bash 数组；在不同安装/平台上可能无法启动。改为普通 POSIX sh + PATH 当前 Python 调用既有 pre_commit 配置，不增加慢测试。

## 架构保留与暂缓

provider 路由由 CWP 配置所有，不在 FF 引入第二套 CN/HK/US/provider 注册表；StockInfoDLSimple 是现有 A股入口，Dayu 是只读外部工具。fmp/协议版本/MIME/有限错误枚举/ET 公共 body 上限是协议常量，不是部署硬编码，不随意配置化。两套 v1 path-bearing / v2 SourceRef 是仍有真实调用的兼容边界，不能按“看起来旧”删除；worker flags 已是 inert no-ops，不恢复审批。整仓 exception boundary 不一刀切删除，保留 child failure isolation 与未知用量诊断，不让 transcript failure 破坏成功 filing。现有 process tree 与共享 deadline 已解决真实资源边界，避免为了行数再建 transport 引擎。安装器保留未知文件/配置/credential；不是整树覆盖。

DU 不在 FF 独占范围，本次不动 document routing/profile/原件/生产配置/密钥/他仓。测试不进行付费模型或真实下载，临时目录由 pytest / TemporaryDirectory 清理。完整契约矩阵与真实 G2/G4/G5 由 ROOT 集中运行，不在每个小修复重复跑。

## 实施与兼容结果

ff_configuration.py统一有界JSON/路径token/root loader；doctor真实调用load_company_wiki_root，ET复用其JSON和path解析但保持既有配置快照与key来源优先级。ff_source_ref.py把纯SourceRef契约从serializer抽出为validate_source_ref；ff_v2_envelope._reference别名保留，避免break既有导入。ff_source_candidate.py只处理逻辑引用/metadata，不读原件，query和ensure用一个绑定/投影函数，未验证candidate保持byte_verified=false。不重新检查CWP根许可或创建hash签收。

日期同时修正request/metadata/legacy publication，不存在日历日期在source工具调用前被拒绝。tracked hook按当前PATH Python执行同样pre_commit配置；真实POSIX shell用隔离fake python验证argv与失败退出7，不安装或触发第二重行为套件。SKILL不再把退休worker写成执行步骤，也不再让消费者推导特定raw子目录；CLI原样兼容，修正模块docstring缺schema的失效例子。

## 测试证据

初始34项先写后跑：31失败、3通过/0.48s。改后相关298通过、5既有skip、39subtests/21.75s；原CI快套件742通过、7既有skip、78subtests/66.21s。这个广测发生在最后pure SourceRef模块移动与新增hook replay之前；最终move的受影响174通过、3既有ETskip/2.39s，新反例35全部通过/0.64s。ruff全工程、mypy公开契约、host-assumption新违规0及diff-check均通过。ROOT最终接收跑现有集中CI（会多出新增hook case），不谎称较早广测是最终SHA的远端CI。详细命令与真实阶段在本分支docs/plans/architecture-quality-2026-10-13/checks.json。

7 skip是可选CWP隔离source、3个显式真实ET工具测试、2个生产身份快照不在隔离fixture、1个平台symlink，不是把业务失败改skip。没有删测试或降低预算/hash/来源断言。第一次集中runner发现稀疏worktree缺e2e文件，零测试exit4，展开tracked e2e后真实通过；这是ROOT创建checkout的漏选目录，已说明而不改CI来掩盖。

## 交接与剩余风险

无需DTO/公开JSON/schema/CLI接口变更，新增公共仓内helper。runtime安装必须包含全部scripts新增三个模块（现有manifest安装器会发现它们），并更新SKILL与受影响旧脚本；保留现有用户配置和凭证。ROOT负责接收commit、跨仓C节点、定点安装、push与精确SHA CI；本agent未push、未安装。

公开controller依然约1600行，transport/error wrappers各自有不同的返回码/未知用量/回收语义，未为减少行数强行合并。v1深验原件与v2 provisional candidate仍有真实消费者，不移除v1。未来provider或源质量能力改进由所属CWP/ET层负责，不复制到FF；DU不受本次改造影响。公司真实摘要/预测质量G2/G4/G5没有在本离线架构验收中声称完成。原件、生产配置、密钥、canonical WIP及DU三worktrees均未写。

最终平台反例补齐Path.resolve的OS/ValueError差异（1FAIL/1PASS RED）：非法路径在Windows/Linux均映射到config_error，避免本机绿而CI裸异常。包含这3个新增case的最终受影响套件177PASS/3既有ETskip/2.54s，其中新增架构回归共38项。此前35/174/742均是已实际运行的历史阶段计数，未改写成最后SHA广测。

新imports闭包：fetch_filing → ff_configuration → filing_contracts；fetch_filing → ff_source_candidate → ff_source_ref → filing_contracts；ff_v2_envelope、ff_local_source_prepare、transcript_companion、transcript_tool_transport均复用ff_source_ref；ET transport复用ff_configuration。不导入CWP实现internals，不增加第三方依赖或跨仓mutable文件。

需要同步的runtime文件是SKILL.md和scripts/{fetch_filing.py,filing_contracts.py,ff_configuration.py,ff_source_candidate.py,ff_source_ref.py,ff_v2_envelope.py,ff_local_source_prepare.py,transcript_companion.py,transcript_tool_transport.py}共10个。engineer-only hook/tools/tests/PWF不放入技能安装；public resolve_filing/load_company_wiki_root、fetch __all__版本/异常等导出不变，旧ff_v2_envelope._reference与内部root wrapper保留alias；v1/v2 envelopes/CLI kwargs保持兼容。

正常commit：`5cfad11b4ea533b4b1fadd081945e52018eb96e1`，ruff/mypy/host-assumption pre-commit全绿，无skip/绕过。分支已停写待ROOT；未push/安装。

## FF-AQ-06 部署责任根因收口（ROOT真实安装发现后）

ROOT已将5cfad11接收main并推送、同步，随后fresh CLI发现.codex旧ff_provider_cause缺build_request_diagnostic，虽然本次10文件SHA一致；ROOT已定点补该依赖。本lane在原独占branch增加工程层工具诊断，不写canonical/安装副本。

plan/result目标行增加full_runtime_drift、outside_scope_runtime_drift、runtime_diagnostic_errors、runtime_byte_complete、runtime_execution_validation=NOT_EVALUATED。共享现有manifest；它以同一installable规则定义所有权，诊断排除用户配置，目标不rglob、不读unknown或keys。结果在写入后重新读取当前canonical和实际目标，所以不能沿用计划时的绿状态。copy status completed、needs_update、written/not_written及--check退出码仍只描述selected scope；外scope读取失败只降低byte-complete诊断，不阻断已选copy，不自动扩大写入，不增加任何许可/人工门。人类文本也显示full runtime bytes状态与NOT_EVALUATED。

6个真实RED反例6FAIL/1.20s；实施后加旧安装scope、cfg/unknown、alias、partial retry、race和实际3临时安装CLI测试共33PASS/8.59s，一次集中验收，owned tmp彻底恢复，Ruff/host guard/diff-check绿。新增6个快行为case并入现有ci_tests，不另建重测试门；未跑真实provider或模型。此engineering-only commit不改变技能runtime文件，不需要安装新的FF技能文件；由ROOT正常并线推送，fresh运行仍由ROOT大节点实测。

这三个状态各自有明确含义：selected bytes复制成功、full owned runtime bytes与canonical一致、真实fresh执行成功；工具只计算前两项，绝不伪造第三项。需要通过实际入口运行发现的source包装缺失、配置或lazy依赖行为依然由发布验收负责；不建立第二套AST importer。

部署诊断收口正常commit：`e2efa81d7995836d457479eb528fa6f8cd5dc3f3`（parent5cfad11），Ruff/host guard通过，mypy因无公开契约代码变更而正常skip。本次engineering-only，无新增runtime同步文件，ROOT接收push；工作树clean，未写实际安装目录。
