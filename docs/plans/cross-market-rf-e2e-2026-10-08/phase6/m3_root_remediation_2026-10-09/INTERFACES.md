# 共用接口与排他责任（M1 施工输入）

状态：设计交付。以下新增字段/版本是实施合同，未标为运行能力。旧 raw、report、manifest、forecast/snapshot 保持原字节及 emitting version。

## Owner 与写集

| Card / owner | 允许写集 | 共享文件处理 |
|---|---|---|
| W01 source foundation / 原来源修复 owner | 已发布 R01/02/24/25 只引用；新 source qualification 证据经现有 public facts/import/query API 写自己的新隔离 catalog | 不施工已接受修复；CN date 没证据留空；不改 W02/03 源码 |
| W02 official JSON / 专属 CWP source-contract owner | 新 `source_catalog/official_json_*.py`、对应 tests；`source_contract/schema.py` 和 schemas、source catalog import/metadata/canonical writer、JSON DTO/export、AUTO 类型/JSON 路由的薄接线 | `official_source_flow.py` / `canonical_writer.py` / `automation/narrative_select.py` / 公共类型同一 owner 顺序提交；W03 只在 W02 接线合入后改其普通格式部分；模型 runtime 由 MAIN 保留 |
| W03 content / 独立 CWP normalization-selection owner | `document_normalization/` 普通格式、`source_catalog/narrative_evidence.py`/`narrative_group_candidates.py`/`narrative_context.py`/`transcript_layout.py`、相应 tests；`narrative_select.py` 非 JSON可用性 | 先读既有0.3/W05/W02，禁止重做 actor/DOCX；共用 EvidenceSpan DTO由W02先提交，再消费 |
| W04 runtime / MAIN 已有独占 owner | `scripts/config.py`/`llm_client.py`、`automation/narrative_http_model.py`/`narrative_batch_request.py`/`narrative_model.py`/`narrative_model_caller.py`、`automation/models.py`及既有 attempt store/compaction/public batch诊断消费者，新runtime summary validation和相应 tests | 不交给W02/W03。`models.py`公共enum/metrics及`narrative_batch_request.py`接纳JSON的薄接线也仅MAIN写，W02提交DTO/tests由MAIN顺序接线。source_catalog/narrative_evidence.py只归W03，W04消费其group/旧ID校验，不并写 |
| W05 audit execution / audit skill owner | audit仓 `skills/revenue-forecast-audit/{SKILL.md,references,scripts}`/tests及自己新 run executor 输出；本包 skill checkpoint提案 | W06定义 usage DTO，W05只消费到matrix/ledger。RF输入里quote/date/targets属W09作者，W05提供通用工具/检查，不跨写 |
| W06 acquisition transport / 三仓顺序 producer-consumer owner | CWP `source_catalog/dayu_sdk_cli.py`、`tools/dayu_sdk_bridge.py`及现有 acquisition usage producer；FF实际 `scripts/fetch_filing.py`/`ff_v2_envelope.py`/`filing_contracts.py`/`ff_process_transport.py`；RF `scripts/filing_fetch_client.py`/`filing_upstream_cause.py`/`source_preparation.py`成功观测投影及各对应tests | DTO先CWP后FF后RF；RF `company_wiki_source_reader_v2.py`刚发布H1的单文件修复不重做；禁止Dayu改动。实际入口CodeGraph确认后记录精确write set再改 |
| W07 RF contract / RF合同 owner + 原output/assurance owner | 合同owner独占 `scripts/research/drivers.py`、`contracts/constants.py`/`document.py`、期间flow相关纯计算/渲染与references；原output owner继续独占 `scripts/revenue_report.py`/assurance/output | 合同和输出 owner 不同时改 `revenue_report.py`；合同owner交测试与DTO，原output owner接线。R21/22既有施工只交现有接受证据，无重复整套 |
| W08 source coverage / 新独立来源执行 owner | 自己run资料ledger、public acquisition/import到自己的source catalog | 不生成CWP研究state，不改源码；公开原件主体仍由来源层检验；W09仅引用 |
| W09 research / 三家公司独立研究 executor | 自己新RF input/report/snapshot/研究notes；RF SKILL/references 的方法文案只由W07/审计skill owner统一提交 | 禁止CWP研究 writer、跨StockWiki目录/DB、IQS/其他PWF。评估不同公司独立原件推理，无公司if补丁 |

Owner 名称表示应分配的角色，未声称这些新agent已经启动。协调员在本包 `progress.md` 登记实际agent/worktree/branch/HEAD；目录不重叠可并行，共享文件严格依上述顺序。只需一次共用设计核对及最终大节点审查，不扩展逐文件签收。

## I01 raw → source projection → evidence

W02 直接采用 `../m3_source_research_2026-10-09/official_json_source_root/DATA_CONTRACT.md`，SHA `2d80afeeac0946f91e18dccc6008eab734dcb1d727aac6f2dbe2870e7b4f08b3`；其 `JSON_EVIDENCE_INDEX.json` SHA `4969a5239e15b71f2e8d83e3107dd7a9f80ab78b9673b710a2158906b35285fc`。不是另一个JSON方案。

- SourceRef2.0继续指向一份 immutable raw bytes。multi_issuer_event/unattributed不能强塞单issuer v1；`importrequest/2`、`rawsubjectmanifest/2`、`projectionref/1`以及显式 export版本按该合同实施，旧strict2不偷偷加必填。
- 投影保存parent SourceRef、adapter/parser版本、issuer proof与过滤、record ID、RFC6901 pointer、值hash、字节范围/解码转换；不复制raw_record全文或每公司整页raw。稳定 lexical ordinal与 decoded char locator有别，不把raw byte偏移塞进旧char字段。
- JSON中answer/question物理顺序可以相反：不同片段分别有locator，以语义组关联，不冒作连续quote。record36395的answer非空；actor/answer-time未知保留，800是成立以来累计，不改写年度出货。
- AUTO按内容类型/声明layout走official_json独立路径，复用现有lease/generation/outbox和预算。未知布局保留raw并typed unsupported/pending，不走假transcript/TXT，不新增数据库、常驻队列或授权档。
- live company filter API 尚未证实。下一大节点保留实际UI/网络请求方法/fields/响应，两个issuer和negative ID核对；没有真实发现就用sharedraw本地投影，不能猜companyId查询参数。POST capture用真实method/formencoding，不改历史GETreceipt。

## I02 selection → summary → RF consumption

Selection保证source version/parse/locator可重放；semantic group携带主体、动作、期间、范围、反证限定及所需片段。partial/unknown页面不等于整文失败，也不等于complete；已读有效正文可产partial bundle，未知业务页必须明确剩余影响。

摘要每个独立命题映射实际必要的group/span；不把同页关系强当支持。goodwill impairment不得扩大其他无形资产；3个月和6个月率分别保留；相对“今年”只有有证document目标年/预测vintage可解，访问时间不供推断。RF消费者要读取所需组全部片段，不能只取needle第一个span。

## I03 配置、失败final与meter

MAIN第一阶段policy wire候选272973eb，最新62770fea已包含reasoning贯通候选工程接受：policy21相关PASS、reasoning144PASS、publicCLI成功compaction/失败8194保真/两次0POST恢复、模型合同31PASS及四公共模块mypy绿（协调员真实交接）。支线正常push成功、ls-remote准确核对/clean；记录UTF8decode失败，丢stdout/prepush精确计数不编造、未重推；branchexact暂无run属workflow筛选，不称CI绿。已normalmerge本地master45533e881b98fe8782b0e496abf7a4bb2904114e，远端mainpush/精确CI待本包归总后执行。final16KiB正文仍未实现/真实收费未复验，不能关闭全runtime根。生产三配置SHA不变、未增加DS策略值。provider/purpose隔离，未配置省略；DS narrative显式disabled仅拟配置；adapter已支持其他provider显式合法thinking透传，DSadaptive现有限制。“未核实供应商”不增加白名单；真实API错误保留。

后续meter/诊断通过原 HandlerResult / attempt.result_json / HandlerMetrics。完整受界响应 `provider_response_sha256` 与 `final_content_sha256` 不混同。final diagnostic保存UTF-8长度、完整SHA、最多16KiB前缀、clipped标志（不拆坏UTF-8），只保留final content；不默认保存隐藏reasoning正文。reasoning_tokens可选整数：未返回=null，确证0为0，属于completion子集；总token和费用不得重复加。

失败、partial或有限provider错误仍settle一次；不发布有效summary、不盲重试。diagnostic写入/compaction/public batch/result reload都需同一可选字段兼容；计入原持久/输出空间，失败空间不足留可用量/hash和有限原因。诊断/清理异常不得覆盖原length/API错误，不建旁路日志库。

## I04 request scope 与采集观测

新run用当前scope生成实际request，冻结前后精确记录profile/model options/pricing及32MiB persistent、64MiB scratch、2MiB final（或当前已配置更小界）；取request/deploy剩余界的较小值，不能放宽。身份/字节/as-of在原责任层校验，新增scope一致性检查不成为许可条件。HK tool配置传入child按既有配置，值不进入argv/log。

实际业务status/reason/SourceRef与call_id一一对应，多个document可引用同一真实batch call但注明批次及各document result，不能复制同一capture冒充不同取得。usage保留 observed/incomplete/null lowerbound；success/failure/reuse各边界都投影同一现有acquisition_usage，计量metadata GET、实际响应，不以canonical raw长度替代network累计。费用cap0不是实际fee0。CWP先固定DTO，FF/RF不能独建MIME白名单或重复身份门。

## I05 RF研究与期间/角色合同

W07先列实际所有`time_basis`消费者，通过版本化合同表达半年/季度flow起止期间和计算/渲染；annual及point_in_time既有含义不变，H1+H2年度金额不变。旧schema/emitter产物原字节只读，pin旧验证，不能重写其annual标签。新半年flow不能通过仅字符串替换凑绿；需要3/6/12月与stock反例。

`triangulated`只用于真正同命题、同scope的机制支持来源角色；history_base、融资背景、peer analogy、contrary、仅方向不因两个文档类型就升格未来机制或幅度。保留所有node与披露；不删除证据或人为加confidence。未来数值幅度、转折、horizon仍由研究责任验证。

原output owner复用EXPERT001/002既有工程证据，补角色/constraint roundtrip测试；合法signed base adjustments和input tolerance、opening residual须被strong recompute保留，不改正确增量/敏感性链。

## 共同安装、提交、恢复合同

每条实现使用独立worktree，记录base HEAD和只读owner状态。tests先证明责任反例RED，再最小共用实现GREEN；绿色后按既有normal hooks commit/push，再核对**exact committed SHA** CI；不以另一个head的CI替代。记录clone/junction逻辑路径解析到物理target；RF/FF/audit技能只同步改动runtime闭包具体文件到 `.agents/skills/...`、`.codex/skills/...` 和实际第三逻辑根的唯一物理文件。不得复制tests/assurance/全仓/原件湖；未知文件、用户config/output保留，receipt列每文件before/after SHA。CWP主线本身是runtime，Dayu外部不安装改变。

TEMP先保存本root原状态及初始文件size/SHA/catalog/DB/config指纹，真实source-only原件按SourceRef读取/必要小集复用；清理只操作已核对绝对owned root，受保护初始根比较后恢复，其他owner/raw/config SHA不变。出错留新run与原始失败，不reset全仓或倒写历史。
