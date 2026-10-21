# R1 旧 NVDA 历史责任对账（2026-10-21）

旧四审的 **24 条发现不是今日已证的 24 个 bug**。W01–W07 已有工程实现、责任测试及并线记录；当前源码保留关键机制，所列旧功能提交在相应当前主线祖先链中。旧 NVDA 只有 W01/W07 工程回放，未发现完整 M2 新 attempt 和新版四审，因此不能记业务通过，旧 clean streak 仍为空。

本次仅只读核账并写本 MD/JSON。未启动公司、下载、模型、产品测试，未改代码、安装、配置、旧 campaign、抽样或进度；未访问正在运行的药明康德 execution。当前责任以 [CURRENT_STATUS](<C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md>) 为准。机器可读逐项映射、原根因机制与确切文件 SHA 见 [JSON](<C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/review/r1-nvda-carried-reconciliation-20261021.json>)。

## 已冻结的历史与当前观察

- 旧 run：[pool-20261009-001-us-nvda 诊断](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/diagnosis/root_cause_report.md>)；初始信息日 2026-10-09，4 报告/24 finding，另 COORD-001；14 共因/7 包。四份 JSON 当前 SHA 与 campaign 原 pin 全部匹配。本次未重 hash 139 个 execution artifact，不冒称再次全量原件验真。
- campaign 种子 `193701808470207586993231217228381019290`，selected 仍仅 US:NVDA，clean_streak=`[]`；candidate pool SHA、原 selection/算法均不改，不迁移 progress、不重抽。campaign 的 waiting 字段是旧快照，不能覆盖当前 CWP 入口。
- 当前本机 HEAD：CWP `45195e96cb15`；RF `9669c4d79cff`；FF `e8740748f919`；audit `a2f216bd8cc8`；ET `2584b7eed062`。只核本机与功能祖先，未重新联网签 remote/CI；CWP 会随协调员文档工作继续前进。
- 跨仓 Git 初次只读被沙箱拒绝，按明确授权经 require_escalated 只读成功；无 Git 配置更改。RF/FF/ET/CWP 已有 WIP 保留，凭据仅观察文件名，未读内容。今天没有重验全部安装字节。

## 已有工程证据

下列测试数量均是发生时的记录，未在本次重跑，也不相加冒充同一次独立验收。提交祖先只是可追溯性证据，必须与源码、反例和真实业务复验分开。

| 证据 | 已有实现与测试 | 仍不能据此声称 |
|---|---|---|
| E01 / W01 | 有限来源入口及安全 cause 已有工程修复；当前 allowlist 明确含 configured 入口。 W01记录 CWP156PASS/1真实数据SKIP；integration_final 实际 FF110、RF14与三仓公开CLI23checks通过，supplier0、owned TEMP恢复。各组独立记录，不相加冒充一次独审。 [收据](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/execution_replays/w01-main/integration_final.json>) | 入口分类和 cause 绿不证明 NVDA 正式摘要、内容覆盖或经济模型通过。 |
| E02 / W03 | 官方原件统一 import、按真实载体解析、版本/定位及有界发现已有实现。 W03交接113责任测试、17存储回归、21有限处理/1明确live-input skip；三格式公开import→原件open→configured loopback→reference/read→repeat，3模拟请求不增加。 [收据](<C:/Users/郑曾波/Projects/company-wiki/docs/implementation/pool-w03-official-flow/HANDOFF.md>) | loopback、synthetic HTML及已删除临时catalog不是 NVDA 持久可用来源；动态索引/音频/实际最新IR材料没有因此自动补齐。 |
| E03 / W04 | 已分离完整 FF result 与 filing 选择；latest 消费 resolved year、同次 reader manifest；NarrativeRef 有实际 span→claim→parameter/DAG 绑定入口。 W04交接145责任GREEN，后续HTML146、非财报nullable75分别留收据；campaign记录RF工程并线e688b0a2及CI成功、44安装物理文件/2smoke。新同节点独审25项关闭F1–F4，绝非完整业务复验。 [收据](<C:/Users/郑曾波/Projects/revenue-forecast/docs/implementation/pool-w04-w06-w04/HANDOFF.md>) | 未在本次运行 RF 或确认今天安装字节；读摘要元数据仍不算模型已消费。 |
| E04 / W02 | ET operation raw响应限额与正文限额分离，已读超限chunk先记实际使用量；FF当前传max_response_bytes。 131责任测试、supervisor/worker五种离线CLI、MAIN三仓公开18check通过；campaign W02状态为并线/推送/FF定点安装完成。 [收据](<C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/docs/implementation/pool-w02-response-budget/HANDOFF.md>) | 模拟HTTP不表示真实FMP entitlement恢复。硬杀仍按unknown；不得为此重复terminal请求或购买订阅。 |
| E05 / W05 | 季度区间/YoY目标比较、期间/单位/作用域与真实DAG绑定及沟通覆盖incomplete诊断已实现，后续DU6进一步修带符号目标与单位语义。 W05初版66、类别边界follow-up13；绑定修复owner201+167subtests，同节点独审25关闭F1–F4。DU6记录193+119subtests及合成公开CLI，均只为各自工程范围。 [收据](<C:/Users/郑曾波/Projects/revenue-forecast/docs/implementation/pool-w04-w06-w05/HANDOFF.md>) | target金额/同比在真实NVDA主报告中正确展示和解释仍待新attempt；源码能诊断incomplete不能证明最新沟通已取得。 |
| E06 / W06 | 可选operating-research/1内容清单、证据角色、范围转化及joint/delay recipe已实现；mechanism和magnitude分列。 W06105+167subtests，实际本地组装→native validate/compute/Markdown/snapshot；绑定修复集中201+167subtests、独立25；均是合成输入，不能合并当真实经营审查。 [收据](<C:/Users/郑曾波/Projects/revenue-forecast/docs/implementation/pool-w04-w06-w06/HANDOFF.md>) | 未找到新NVDA内容inventory、已独立校准主要驱动或重算联合压力后的四审。方法已修与研究实例已修须分开。 |
| E07 / W07 | legacy原生事件仅作观察，canonical事件保留权威映射；旧日志缺冗余头不再冒充身份错误。 9测试通过，定点安装记录；旧run check仍exit2/needs_remediation、24finding、0unmapped、0event_errors，quality_status=not_evaluated。 [收据](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/execution_replays/w07-main/acceptance.json>) | 工程观察问题有闭合证据；今天未再运行audit check，不提升旧预测质量结论。 |
| E08 / 后续DU11/C | 后续共享引擎、阅读策略/上下文引用和真实C开发回归已有交付，不能用旧W03待办重做整包。 当前唯一入口记录RF9669c4d7、FFe8740748交付发布。C三家真实开发回归有恢复/跨run缓存/FF复用及RF读取证据；不是holdout，也未在最新类型修复代码重新做真实C。 [收据](<C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md>) | CN获准8/10收尾；HK7/7；US所绑定独审2/8另1partial。不能转签NVDA、不能把后续不同实验汇总为一次业务PASS。 |

当前源码可直接复查：CWP [configured allowlist](<C:/Users/郑曾波/Projects/company-wiki/scripts/writer_policy.py:68>)、[official import](<C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:490>)；RF [resolved期间与完整result](<C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_preparation.py:185>)、[实际消费](<C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_narrative_context.py:103>)、[typed比较](<C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/target_measurement.py:227>)、[经营adequacy](<C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/evidence_roles.py:206>)；ET [超额chunk计量](<C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_budget.py:75>)、FF [raw响应预算接线](<C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_tool_transport.py:719>)；audit [legacy观察解析](<C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:235>)。JSON 为这些源码、测试及收据逐一记录本次字节 SHA。

## 每条旧发现的承接

根因编号沿用原诊断，不重新命名；多根因和原工作包全部保留。证据 E 编号指上表的源码、测试和收据；G 编号指后文共因复验。状态说明是本次证据边界，不是新增 finding 或逐项门禁。

| 旧 issue | 原根因 → 工作包 | 既有证据 | 当前剩余 |
|---|---|---|
| ANALYST-001 | RC-009, RC-010, RC-012 → W06 | E06 | 经营桥/证据角色方法已有；新NVDA主要量级校准未证，不能CI代签。（G4） |
| ANALYST-002 | RC-008 → W06 | E06, E08 | 内容inventory方法已有；已读CPU/新机制的实际覆盖处置待G3/G4。（G3, G4） |
| ANALYST-003 | RC-012 → W06 | E06 | 通用约束/delay recipe已有；新NVDA共享供给/融资/交付联合路径未证。（G4） |
| ANALYST-004 | RC-007 → W03, W05 | E02, E05 | 发现与覆盖诊断已有；当前as-of实质最新沟通仍未知。（G3） |
| ANALYST-005 | RC-011 → W05 | E05 | 正式typed比较/渲染已修；新NVDA主入口场景金额偏离及机制解释待G4。（G4） |
| FETCH-001 | RC-002 → W04 | E03 | latest工程反例已修；当前版真实复用FY26及manifest期间待G2。（G2） |
| FETCH-002 | RC-003 → W04 | E01, E03 | 完整信封/cause已有；新attempt filing/companion/use量实际留存待G2。（G2） |
| FETCH-003 | RC-006 → W03 | E02, E04 | 旧entitlement属external_limit；当前账号未重查，必要替代链待G3。（G3） |
| FETCH-004 | RC-007 → W03 | E02, E05 | 有界发现已有；旧NVDA招股/增发/可转债/8-K实质分流未证。（G3） |
| FETCH-005 | RC-007 → W03 | E02, E05 | 动态/通知诚实partial已有；Sep10正文/dated deck实际取得或gap待G3。（G3） |
| FETCH-006 | RC-004 → W03 | E02, E03, E08 | 统一import已有；旧官方IR/call的可复用SourceRef新attempt待G1。（G1） |
| FETCH-007 | RC-005 → W02 | E04 | raw限额/超额计量工程有131+18证据；当前运行用量边界待G2，非今日已证bug。（G2） |
| PROCESS-001 | RC-001, RC-004 → W01, W03, W04 | E01, E02, E03, E08 | 启动和consumer已修；完整来源摘要消费链待G1。（G1） |
| PROCESS-002 | RC-002, RC-003 → W04 | E01, E03 | resolved期次/完整错误信封已修；当前真实接口组合待G2。（G2） |
| PROCESS-003 | RC-009 → W06 | E06 | 声明角色及真实DAG绑定已有；新NVDA未来假设的语义支持待G4。（G4） |
| PROCESS-004 | RC-010 → W06 | E06 | 范围→转换→参数工具已有；主要增量经济量级尚无新NVDA独审证据。（G4） |
| PROCESS-005 | RC-011 → W05 | E05 | 季度/YoY typed比较和主报告工程已有；新NVDA实际benchmark路径待G4。（G4） |
| PROCESS-006 | RC-007 → W03, W05 | E02, E05 | 类别/区间incomplete诊断已修；真实最新沟通范围仍待G3。（G3） |
| PROCESS-007 | RC-004, RC-006 → W03, W04 | E02, E03, E04, E08 | FMP旧外限与官方替代分列；新canonical替代及消费充分性待G1/G3。（G1, G3） |
| STORAGE-001 | RC-001 → W01, W03, W04 | E01, E02, E03, E08 | 入口已修；NVDA正式摘要及真实RF消费待G1。（G1） |
| STORAGE-002 | RC-004 → W03, W04 | E02, E03, E08 | 统一import接口已修；旧六类补充原件的canonical新attempt尚无证据。（G1） |
| STORAGE-003 | RC-008, RC-012 → W06 | E06, E08 | 方法/清单已有；CPU/出租分成/融资限制在新NVDA输入的实际处置未证。（G3, G4） |
| STORAGE-004 | RC-013 → W03 | E02, E08 | parser/locator工程已接；新NVDA逐消费片段版本及精确定位待G1。（G1） |
| STORAGE-005 | RC-007 → W03 | E02, E05 | 发现及覆盖诊断已有；旧Sep10正文及材料相关性核查仍未复验。（G3） |
| COORD-001 | RC-014 → W07 | E07 | W07工程修复有闭合证据；仅随本轮封存观察，不把它再列今日缺陷。（G5） |

原 14 共因的机制和当时 implementation_status 逐项保存在 JSON `root_causes`；原始 [root_causes.json](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/diagnosis/root_causes.json>)、[issue映射](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/remediation/root_cause_map_event.json>)、[M1集中设计记录](<C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/pool-20261009-001-us-nvda/remediation/m1_review.json>) 仍只读。旧卡中“planned/未并线”是当时状态，不能抹去后续修复；新源码存在也不能抹去原业务失败。

## 合并到现有大节点的五组复验

这五组是证据索引，沿用当前 R1 的 N2/N3、四路独审及共因专家，不新增五道审批或 24 项小门禁。当前药明康德 → 药明合联 → Snowflake 顺序保持。其结果可以支持共用能力泛化；旧 NVDA 的公司特定业务责任仍须按当前实施细则另建新 attempt 承接，不覆盖 initial。

### G1 来源登记、解析与正式摘要消费

原根因 RC-001, RC-004, RC-013；已有 E01, E02, E03, E08。在当前既定完整RF节点观察真实 source→canonical SourceRef→versioned parse/locator→selected/context→正式原语言summary→NarrativeRef→RF实际claim/parameter/DAG。旧NVDA仍需单独新attempt与相关四审；原官方补充只复用既有原件，不以旧audit路径继续冒充canonical。共用一次有界恢复/跨run零POST及原件/空间证据，不逐issue重复付费。

### G2 采集期间、信封、失败与用量边界

原根因 RC-002, RC-003, RC-005；已有 E01, E03, E04。沿同一原生source_preparation→FF→CWP/ET保留latest resolved期间、same-call reader事实、filing/companion独立结果、完整cause和native usage。当前真实运行自然触发时核实；已证工程反例不另开逐项全套。FMP终态不盲重发，未知usage保持unknown；1024/oversized等工程能力沿已有责任测试，不要求额外收费反例。

### G3 材料发现、实质覆盖与外部限制

原根因 RC-006, RC-007, RC-008；已有 E02, E05, E06, E08。以实际as-of有界查最新官方/SEC材料及正文，通知/Loading不算全文或不存在。NVDA旧Sep10正文、dated deck、8-K/募资相关性仍缺本轮实证；对已读CPU/租赁/保证/融资约束登记modeled/included/unmodeled/unknown及理由。FMP旧entitlement保持历史外部限制、当前账号状态unknown；官方替代内容链是否足够独立判定，不要求买订阅、不把替代通过改写provider PASS。

### G4 模型语义、目标比较与经济校准

原根因 RC-008, RC-009, RC-010, RC-011, RC-012；已有 E05, E06。新NVDA输入/主报告逐条落实已读target/newcurve/constraint；历史表头只能支持基线，反证不标正机制。主要增长额要有独立最小经营桥/来源范围→明确转换假设→真实三情景参数；季度/同比比较出现在正式报告。共享供给/融资/交付延期按同一链重算、防双计；未知基期/净ASP/容量如实gap或条件化stress。独立process/analyst实读与复算才可处理业务问题，pytest或金额恰好等于旧预测不能代签。

### G5 封存、观察与历史状态

原根因 RC-014；已有 E07。在既定封存/四审汇总节点使用当前canonical event例子，legacy只观察、不承载费用或quality权威；保留旧报告/日志字节。W07无需另开新修复包或小门禁；若当前真实run再报身份问题，才给新反例归因。

## 未闭环、未知及下一责任

工程层已找到实现证据，故不将旧24条批量重开为当前代码缺陷。业务层仍未找到新NVDA的实际更正输入、正式摘要消费、最新沟通覆盖、主要量级校准与联合风险路径独审；这些保持待复验。FMP旧外限保持历史事实，当前账户状态未知，原套餐费用未知。动态IR/音频是否可得、未采用材料是否不重要，都不能由实现存在推断。

后续DU11/C已有真实开发回归，但当前绑定US独审仍2/8另1partial；CN允许8/10收尾只对CN有效。CWP R2实验性两attempt恢复、R3可移植证据、R5 contract债、RF/FF当前组合全套未复跑均沿当前入口处理，不借本对账签收或重做B2/已接收卡。

下一责任是继续已经启动的完整R1循环，封存后按四审实际问题做共因修复，再在约定节点完成旧NVDA新attempt及相关四审。仅出现新证据时更新处置；不为旧not_found重复开owner，不为工程绿额外重复收费调用。

## 后续八家公司与历史保护

[未来八家目标](<C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/followup_eight_company_audit.md>) 仍为“已登记、尚未激活”：**阿里巴巴 → 小米集团 → 药明生物 → 药明康德 → 药明合联 → 微软 → Snowflake → MongoDB**。只有当前目标实际达成后按原文件激活。本轮与名单重叠的公司不提前计入八家完成，不以三家clean提前结束、不重新create_goal或随机替换。

输出前后 campaign、四份初审JSON、旧诊断/映射及八家目标 SHA 一致；旧 initial、原报告、seed/selected/clean streak未写。本次 0 supplier / 0 model / 0 产品测试；仅生成这两份review文件。
