# 长招股书原生解析性能 — ROOT共因调查与实施顺序

2026-10-15；不与DU4新组件目录重叠。先调查，不改生产解析器，不提高原80秒限额。

## A：一次有界真实profile

原HK招股书 source SHA 33460fa3e02e115e7bd09e1c4c857e71afe54c332a22373d28a0d2e86c70b6d4，9,730,088字节，Dropbox原件只读。旧native parse80秒未完成，不能认证后续DU/选择。沿相同parse_pdf_bytes(selector_version=0.9.0)入口做一次最多60秒独立子进程观察，单次读原件、验证manifest SHA、保留实际text scan/table/page阶段耗时/计数与timeout时正在执行位置；不重新跑全矩阵、不复制PDF/MD或持久化全文。预算/超时使用现有有界进程owner，原件stat/配置/因果源码与sentinel前后保持，临时目录清理，0网络/API。

## B：根据证据写测试后修唯一责任层

目前源码可见：layout15秒仅限layout collector，_scan_pdf_pages仍遍历原件页，_emit_pdf_tables的find_tables未由该layout限额覆盖。此为调查方向，不提前断言80秒全部花在哪一层。根据A的实际观测，先写相应的操作计数、页/表工作边界、已完成有用文本不丢、partial/deferred诚实、停止/恢复与不重复副本反例，再在唯一native parser/现有有界运行责任层修复。不能把招股书页码或公司写成特判，不加第二解析器/任务库，也不能用表格全部跳过或增大时间遮盖。

## C：集中真实验收

同原件一次改后回放，比较实际文本/表覆盖、有用业务段落与parse时间；另一个长文档holdout、已选source ID/locator回开与配置/原件保持。与DU4表格binder的接线由ROOT单独统一，作者不编辑本性能责任层。只在A/B/C大节点审查，未知coverage不冒充完整、测试不放每次commit重跑。

当前：A真实profile完成；原准备描述保留为历史过程，B/C尚未实施。

## A 实证：2026-10-15 一次真实有界profile

- 原件675页，9,730,088字节，SHA匹配；仅读原件1次/parse1次，网络与供应商0。
- 全675页文字扫描已在4.292秒完成（逐页get_text合计4.036秒）。表格候选计划230页，选择候选耗时2.255秒。
- 截止前 native find_tables 已完成133次、累计50.163秒，单次最高4.579秒。父级emit时间是inclusive，不能再相加。第40秒实际Python/native栈在PyMuPDF find_tables→make_edges→clean_graphics→get_textbox。第60秒硬截止时外层正在第268页表格处理；后续业务页没有到达正式选择。
- 当前layout collector的15秒不覆盖native find_tables。廉价全文已有，但逐页文字+昂贵表格串行emit导致昂贵阶段耗尽时间时连已扫好的后段文字也未形成可返回材料。这是处理阶段/资源归属问题，不能归咎原件不可读，也不能只提高80秒或不区分用途把全表扫描做完。
- 原件stat、两生产配置与两解析源码hash/mtime保持，临时目录移除。该次partial不是route/摘要/表格质量通过。未证明230页都无用；不能因此全部删掉表格步骤。

## B 修订：一次源观察、按需增强、可恢复的共享引擎

先冻结ROOT接线细则再改生产代码；DU4作者继续各自纯组件，不增加接口依赖。

1. **先完成便宜的原文表示。** 原生页/段落/角色和真实字符范围先形成可用材料；完整文字状态与可选table/layout增强状态分离。不能让一张慢表抹掉已经读到的其他页，不改变原文/ID/locator或伪称表格完整。
2. **由唯一共享阅读策略请求增强。** 使用现有章节/业务facet/问题与原生页引用确定需补的表格/区域；格式parser只履行提取请求，不再靠另一套全文关键词无差别驱动昂贵工作。不得使用本样本页码/公司词或只读前N页；晚页业务与缺信息的情况必须有反例。首轮便宜结构与增强复用同一源观察及已有索引，不做两遍完整DU/第二排名器。
3. **native工作单独有界。** 明确实际完成、未尝试、失败/超时的table请求。复用现有work/deadline/子进程owner；layout预算不能冒充native预算。不可中断的native调用必须在可收回的执行边界内，剩余有用文字不随其丢失。不盲目每页重开PDF/传整份9MB一次，先比较native call开销与隔离成本，不能用大量小子进程制造新低效。
4. **只缓存有价值的完成单元。** source SHA+实际parser/策略请求因果定位完成的增强；沿已有AUTO/Store/outbox恢复，复用完成表，不再从第一页重复昂贵工作。不建第二任务库，不落第二份全PDF/全MD或每页全文副本；cheap scan约4秒可重算，持久缓存优先保留需复用的精确表/引用和显式deferred计数，遵守原空间/输出账。
5. **与DU4合流。** TABLE只消费真实槽/几何和原文refs，未知不补数；STATE供唯一业务谓词；FORM供唯一类型路由。ROOT接线时同步因果版本/历史parser重放/旧Ref/缓存失效规则。不能只把硬截止改为partial标签就宣布经营信息召回达标。

### B 的先行测试矩阵（尚未写/运行）

- 慢/故障早页table不能吞掉后段真实业务文字；计数/coverage/locators必须精确。
- 超时/失联/重启后，完成单元复用、未完成诚实保留，0重复付费；源变更或真实配置/版本变更失效。
- 文本型、dense图形型、单张native卡住、零/小预算、父子/跨页table、晚页经营表与纯财务附录；不使用公司页码特判。
- native实际调用次数/字节/截止/子进程清理可观察；测试应检测重复全parse和全量全文副本。
- 旧0.8与历史版本指定表页重放保持；新0.9才用新过程，默认切换仍需正式质量节点。

当前状态：A完成，B/C待实施。先完成正在推送的引用/配置节点；本profile不会引入额外全矩阵/付费回放。


## 独立架构调查接收：ROOT实施细则

以下为只读独审得到的拟议接口与大节点；不是已经实现的能力。源码16份hash前后保持，无供应商调用。不新增人工许可。

# 长 PDF：cheap observation → 策略驱动增强 → 可恢复选择

2026-10-15，独立只读架构调查，`attribution_release_review`。

## 结论

推荐做**同一个原生解析器的分阶段执行**，而不是换解析器、提高80秒、加全文缓存或把230页表格全跳过。先将便宜、已经读到的原文形成可用的 `DocumentStructure`；由共享阅读策略从这份观察请求必要的表格增强；native增强在独立有界子进程中执行；完成单元沿既有CAS和同一AUTO进行有界保存与恢复。原生解析负责字节、行列、几何和角色，阅读引擎负责需要读什么，AUTO负责进度/并发，模型只消费最终选中的材料。

**目前只能确认边界需要改，不能声称可恢复增强已经存在。** `JobExecutionContext.checkpoint()` 不是持久检查点；当前AUTO没有活跃select任务的增量解析checkpoint端口。完整的策略请求/增量完成接口也尚不存在。下面把可以先实现的边界与后续工程分开。

调查只读16个当前源码文件和已经保存的profile/计划；准确符号位置及字节SHA见 `source-inventory.json`。CodeGraph用于定位，个别结果滞后，实际结论以打开的当前文件为准。不因为符号搜索没有结果就判定接口不存在。没有读取原件、跑真实解析/API、修改源码/测试/PWF/Git或DU4目录。

## 1. 已有证据实际说明什么

- 同一份675页、9,730,088字节原件：廉价全页文字观察4.292秒完成，675次文字读取合计4.036秒；候选表页计划230页，形成计划2.255秒。
- 60秒截止前，native `find_tables` 完成133次、合计50.163秒，最慢单次4.579秒。40秒栈在 `find_tables → make_edges → clean_graphics → get_textbox`。
- 外层emit只到第268页。这里是既有观察的定位，不是新策略需要硬编码的页码。
- 已经扫描的后段文字仍在 `_PdfParseState.page_blocks` 内存中，却尚未变成可供选择/返回的units。native调用卡住，整个函数不返回。
- 这证明阶段/时限/结果归属有问题。**没有证明230候选页都必要，也没有证明它们都无用；没有证明所有长PDF都具有相同耗时分布。** inclusive父子耗时不可相加。

## 2. 当前调用链和真正的耦合

```text
source.narrative_select
  open_version + SHA/来源复核
  _select_pdf
    parse_pdf_bytes
      _scan_pdf_pages                 全部cheap文字已扫到
      _pdf_table_scan_pages            通用signal + 配置signal + 邻页 + 空页
      for page:
        _emit_pdf_text_units
        _emit_pdf_tables/find_tables   同步、未被layout15秒限制
        project_page
      _link_cross_page_qa
      return DocumentStructure
    selector -> understand_units -> final selected package
    没选到证据且存在deferred页：full_table_scan重新parse、重新selector
  finish_attempt                       这里才保存完整select结果
```

涉及的共因：

1. 结果只在全部逐页emit完成后返回；一个增强任务可以吞掉所有cheap成果。
2. layout collector的15秒只控制细几何采集，不控制 `find_tables`。
3. parser在共享阅读计划之前决定昂贵工作，虽然配置signal复用了一部分阅读词，但没有真实章节/业务facet/缺口责任。
4. `_select_pdf` 的空结果full-scan重试会重复全页文字和完整DU。它不能变成新0.9的恢复方法。
5. `table_scan_pages` 目前主要是**计划集合**。native失败时仍留在集合，`tables_scanned=len(...)` 不能直接沿用成“实际完成次数”。
6. `understand_units` 是完整组合面，没有prepare/finalize或增量结构更新入口；不能先跑它，再增强后又跑一次并称“一次DU”。

## 3. 可复用端口，以及确实需要新增的端口

| 已读当前实现 | 可以复用 | 不能假定已有 |
|---|---|---|
| `source_catalog/narrative_document.py::DocumentStructure` | 已读页、opaque、table_scan/deferred、errors、layout coverage；可用文本与partial表达 | 逐请求attempt/completed/timeout状态；持久恢复索引 |
| `narrative_evidence.py` 的scan/text/table emit | 同一PyMuPDF解析及原始坐标、片段、QA角色规则 | native硬取消；流式返回；增强完成缓存 |
| `document_understanding/pipeline.py::understand_units` | observation、layout、唯一route/profile、structure、strategy binding、packages | prepare/finalize、可复用section index、按需增强请求 |
| `structure::build_structure` 内部已有 `order_units`、`build_sections` | 拆出同一cheap hierarchy并供最终结构复用 | 当前外部不能注入这个prepared hierarchy，不能直接宣称支持增量 |
| `_bounded_process.run_bounded` + `_process_tree` | Windows Job/进程组、启动屏障、统一deadline、输出字节上限、杀整棵树、异常携带已读stdout/stderr | streaming on-record回调、外部checkpoint回调、持久化page完成语义 |
| `JobExecutionContext.checkpoint` | 现有取消/lease有效性检查 | **没有**进度payload/持久写入功能 |
| `AutomationStore.finish_attempt` | 活跃attempt/lease/generation检查、终态结果和outbox原子写 | **没有**运行中的解析单元checkpoint；不能写未完成 `attempt.result_json` 冒充结束 |
| `LocalNarrativeObjectStore.put/read` | 原子create-if-absent CAS、hash/size验真 | cache索引、容量保留策略、任务lease检查；`NarrativeArtifactDraft` 只允许最终 `narrative_bundle` |
| `narrative_selection_generation`、现有最终artifact reuse | 最终材料/选择/依赖digest、cache失效和公开回开 | 当前缓存是最终选择/产物，不是已完成表格单元缓存 |
| `narrative_replay::prepare_pdf_replay_bytes` | 从真实选中span推导准确table页和parser版本，重放不重新应用阅读策略 | 不应把选择时的cache命中替代真实原件重放 |

**不要**用新常驻worker、新queue数据库、新manifest许可/签收链、最终bundle artifact伪装解析cache。需要小端口就诚实新增到既有责任层。

## 4. 推荐接口与责任（拟议接口，尚未实现）

### 4.1 唯一native parser：cheap observation与table enhancement

在 `source_catalog` 的同一PDF实现内因职责拆文件，保留唯一文本/表行生成函数：

```text
observe_pdf(data, source binding, parser/language/limits)
  -> PdfObservation
     .document_structure             cheap text units + truthful coverage
     .page_order/native block index  transient，供原始顺序/geometry/native range
     .table_opportunities            observed references，不是完成证明

enhance_pdf_tables(data, exact requests, native work/deadline/caps)
  -> PdfEnhancementResult
     completed request records + bounded diagnostics + deferred request IDs

merge_pdf_observation(observation, validated enhancements)
  -> DocumentStructure               相同原文/locator/来源归属
```

`PdfObservation` 不写整份MD，不持久化每页全文；cheap重算约4秒只是本样本测量，不是对其他样本的承诺。增强结果只含实际表格的primitive rows/cells/boxes和所需精确引用，不重复全文。所有PyMuPDF `Rect` 等先在native owner转为有限JSON primitives，不能pickle原生对象/假bbox。

建议增强请求内部wire（名字为拟议，不伪装成现有合同）：

```json
{
  "schema_version": "pdf-enhancement-request/1",
  "source_id": "source-owned",
  "source_sha256": "64hex",
  "parser_identity": {"name": "actual", "version": "actual", "component_sha256": "actual"},
  "requests": [{
    "request_id": "hash(source, parser, operation, page, observed native refs)",
    "operation": "native_tables",
    "page_number": 1,
    "anchor_unit_ids": ["actual original unit"],
    "reason": "existing scoped reading need",
    "priority": 1
  }],
  "remaining_work_units": 0,
  "remaining_output_bytes": 0,
  "remaining_seconds": 0
}
```

页码1、零限额这里只是schema示例，不是默认值或样本策略。限额来自明确配置/请求及剩余总预算，不另造默认金额/令牌表。request ID中的**执行身份**不应包含排序/全plan hash：策略重排后相同原文/同parser/同页的已完成提取仍可复用；另记reading plan digest来审计为什么请求，避免无谓失效。

初版只做整页native tables，保持该页的原生 `table_index`。不能为了快偷偷裁页后把局部表号写成全页旧locator；将来支持clip/区域时要有明确locator/version语义。

### 4.2 唯一共享引擎：prepare/finalize，不跑两遍完整DU

在现有pipeline/structure/strategy-binding内部重构，继续让 `understand_units` 成为兼容的一次调用包装：

1. `prepare_reading(observation)`：只做一次adapter/layout/route/profile与cheap原生ordering/sections，持有同一prepared index。
2. `plan_enhancements(prepared, observed opportunities, existing limits)`：用同一profile、章节优先级、业务facet/reading questions与真实source refs生成有界请求。signal只是机会，不是新一套全文关键词排序器。QA shadow需要native角色恢复也应表达为明确阅读需要。晚页、高价值经营表必须能排在前段财务附表之前。
3. `finish_reading(prepared, enriched observations)`：一次完成QA/project/table/paragraph语义、relations、strategy/package/budget/finalize。补入的表根据实际page/section index归属；复用同一个section policy binder。不是对新全文再调 `understand_units`。

当前 `bind_reading_plan` 同时绑定章节与semantic信息；可从其现有实现抽出shared section-policy binding供prepare/finalize共用。当前 `build_structure` 先构造ordering/sections再构造semantic/relations；应把这个内部准备对象暴露给自身的finish阶段。不能在parser里复制 `build_sections` 或另一份业务规则。

第一阶段允许先完成native执行边界，但**没有策略请求接线时不能宣布按需阅读完成**。仅按原230候选顺序切一段+partial会保住文字，却仍可能错过真正有用的表，属于边界进展，不是最终效果。

### 4.3 native独立有界：复用现有进程owner

- parent保留cheap表示，在增强child卡住时仍可形成可用partial。
- 一批request在一个document child内打开源一次。9.7MB只随该批document传输一次，不是每页传9.7MB/重开675次。已持有验证bytes可用一次有长度上限的binary header+bytes输入；不要base64+每页JSON再复制一遍原文。是否有必要复用document session必须实测启动/IPC成本后决定，不先引入daemon。
- 用现有 `run_bounded`/Windows Job执行。一个absolute剩余deadline覆盖spawn、写入、读出、退出；cleanup是现有有限grace，不能每页刷新总时限。单个不可中断find_tables最多消耗所在批剩余额度；timeout后明确该请求未完成，其后request未尝试。
- child每完成一个请求flush一个有长度/hash/source/request身份的有限记录；parent只能接受**完整且校验通过**的记录。现有 `ChildTimeout.stdout` 可回收已经完整到达的记录，尾部半JSON必须丢弃并记未完成。不能把进程timeout当作所有已完成表格都失败，也不能把timeout页当empty table。
- 第一边界若只在child退出后解析stdout，可以抗child失败/超时，但**不能保证parent被杀后的完成记录保留**。这一限制必须报告，不能冒充持久恢复。
- 如要做到parent crash恢复，新增一个很薄的progress/adoption接口：child只写owned staging的原子完成记录；parent验真、受lease/generation约束后采纳到同AUTO checkpoint+CAS。只有确认采纳才清理staging；不能`finally`把尚未采纳的有效成果全删掉。或在现有owner加有限on-record回调，由parent实时验真采纳；仍使用同一个进程owner，不另写Popen杀树实现。
- 现有 `run_bounded`没有外部checkpoint callback。若需及时响应AUTO stop/lease-loss，可在同owner wait loop新增可选checkpoint，失败进入相同cleanup路径；不能另写每20ms查SQLite的第二轮询器。既有worker heartbeat由既有owner维护，不交给模型。

### 4.4 同AUTO的最小增强恢复端口

建议 `NarrativeRuntimeDependencies` 注入一个源处理cache/checkpoint协议，具体实现位于既有AUTO Store及catalog对象存储；不是parser直接打开数据库。接口语义：

```text
lookup_completed(source/parser/operation/page) -> exact immutable result ref | none
record_completed(active attempt + lease + generation, request identity, ref/size/hash)
record_incomplete(active attempt..., request identity, failed|timeout|deferred, observed work)
```

需要真实新增：同AUTO的一张小型processing-checkpoint索引或等价明确schema，复用现有active-attempt校验和write transaction。唯一键为真实提取身份，completion只能引用已经原子写好的有限CAS对象；CAS先落而事务失败可成为小孤儿，须有受界GC；事务不得先把未存在对象声明为complete。旧attempt/generation不得发布新checkpoint。并发同一内容去重；只有已验真完成项复用，timeout/deferred不是完成。

如果担心范围过大，可先只保留same-run checkpoints；不能因此暗称cross-run缓存已完成。最终实现须覆盖用户要求的重启只做未完成增强；不得用另一个JSON任务注册表永久管理状态。

cache字节也必须进入既有空间账（新增明确cache种类/配额实现即可），不拿“不是最终输出”绕过 `max_persistent_bytes`。索引只存source/request/ref/状态与小统计，不存每页全文。生命周期采用有限LRU/运行终结清理+受引用CAS GC，实际阈值由ROOT计划/配置决定；完成缓存损坏只退为该增强miss，不能删原件。整份PDF仍只有原始来源系统保存。

## 5. 必须保护的原生语义

### 顺序、locator与QA

- `_emit_pdf_text_units` 的段落序号在每页内生成；文本unit/坐标不要因后续table新增而重新编号。
- 当前 `_emit_pdf_page` 顺序是**每页文字、该页表，再下一页**。cheap-first可以先收集全部文字，但最终merge必须回到明确原生page/order桶，不能把所有文字放前面、所有表追加最后。DU adapter会把序列位置变ordinal，排序改变可能引发章节/关系/预算回归。
- 表内保持native table/row/column index、空slot、表头/单位/脚注的真实成员，不把coarse表bbox当成每个cell精确bbox；DU4-TABLE消费真实geometry/ref即可，不让它重parse。
- QA页文字当前会先标记 `qa_text_shadow`；只有真正表cell QA fragments拥有management/question等角色。native未完成时不能把shadow升为company事实。无可用回答就诚实defer，而独立业务散文仍应可用。
- `_link_cross_page_qa` 应在最终有序merge后按现有责任执行一次。前一页未完成增强时，不能让下一页回答跨过未知问题或source/父范围关联。
- layout collector当前会逐页 `project_page` 并消耗原生cache；分阶段时需要同一page observation的明确生命周期。不要第二次 `get_text` 重建fine boxes，更不能延迟太久让15秒layout预算被无关native等待耗完后所有后页geometry消失。

### coverage

至少保留：text observed/read/opaque、table opportunities/planned、attempted、completed-empty、completed-with-results、failed、timeout、not-attempted/deferred。外部兼容字段可继续保守映射，但不要把planned数写成completed。

`DocumentStructure.coverage_complete` 现在只看errors/opaque/deferred和pages_read；若加内部coverage对象，必须让公开selection与reading_context诚实传播，不只在diagnostic日志里保留。未请求/未知页不等于已验证“无表”；“本次所请求增强已完成”也不等于“全文表格完整”。

### 旧版本、缓存和回开

- 0.8及旧parser默认路径保持既有解释。新0.9切新阶段；默认仍0.8。不得为了新性能回归修改旧gold/放宽locator匹配。
- parser/组件实现、请求策略和merge/角色规则需要真实因果版本进入生成依赖。到底升parser版本还是独立native执行/coverage feature，须结合是否改变现有unit构造/locator语义确定；不能代码变了却复用旧“已完成”缓存描述。
- 新旧span的真实byte/locator/parser重放保持。`prepare_pdf_replay_bytes` 已从选中span推导准确表页；verify必须按其指定页/版本重放，不再跑当期全候选策略，不让一个未选中财务页阻断已有选中证据。
- table replay同样需要有界native owner。若所选表本身无法在界内真实重放，该表不能认证成功；独立prose的来源有效性不应被未引用表格拖垮。不可从旧cache直接伪造这次原件回放。
- selection冻结在模型调用前。增强结果若在该批selected generation冻结之后到达，不能把既有selection/paid input替换；形成下一generation才可进入新的摘要，防止重POST或账本伪造。

## 6. 建议实施顺序（只有大节点验收）

### B0：先让native故障不吞cheap材料

TDD：合成早页慢find_tables、晚页实际业务文字、完整table/QA对照、输出半帧、超限、进程孙子持句柄。重构同native owner：cheap units先准备好、table执行分离到有界child、按页有序merge、状态精确，旧0.8/明确页replay保留。这一节点不宣称策略驱动或parent-crash恢复完成。

### B1：打通共享策略prepare/finalize

复用现有ordering/sections/strategy binder，只有一个route/profile、一次最终semantic/package/selection。native机会由唯一阅读策略形成有界request，晚页经营表和无事件关键词经营矩阵需真实反例；移除新0.9空结果后的完整full-scan重跑。保持未知/缺失诚实，不全skip表。

### B2：同AUTO完成单元恢复与容量

先写lease过期/并发/掉帧/kill/重启/变更/损坏/空间边界反例，再加最小checkpoint/adoption索引和CAS引用。实现已完成单元0次重复native提取、只有未完成再次请求，cheap可重算，不增加第二队列。接入public回开、selection generation和空间回收。

### C：集中真实与泛化节点

一次原HKIPO改后profile，再一次不同长文档holdout；比较实际文字/表格完成与deferred、业务片段/定位/摘要可用性、native调用数/传输量、真实总时限、原件/配置/sentinel/Temp保持。合并DU4组件后的真质量由ROOT验收。仅有parse变快或partial返回不证明信息召回已达标。

## 7. 复用测试包与新增矩阵

现有可直接扩展的责任测试：

- `tests/unit/test_bounded_process.py`：read cap/进程树/deadline。
- `test_shared_reading_pdf_layout.py`、`test_shared_reading_layout_coverage.py`：同native观察/geometry/partial。
- `test_shared_reading_pdf_table_policy.py`：无近期事件词经营矩阵、旧路径不变、指定页重放。
- `test_narrative_pdf_language_replay.py`、`test_narrative_native_ranges.py`：language/原文/native range/parser。
- `test_narrative_partial_source_admission.py`、`test_narrative_select_handler.py`：partial但闭合材料可用、真正empty/opaque拒绝。
- `tests/unit/document_understanding_selection/test_reading_native_continuity.py`及table/QA成员测试：顺序/上下文不丢、禁止拼接生成新原文。
- `test_shared_reading_cache_precheck.py`、`document_understanding_decision_dependencies/*`：因果变更失效与不重复选择。
- `test_automation_store_atomic.py`、`tests/integration/test_automation_store_races.py`：同Store事务/lease/generation。
- `tests/integration/test_narrative_generation_reuse.py`、`test_narrative_generation_outbox.py`、`test_shared_reading_production_e2e.py`：same/cross-run无重复付费、真实公开回开/最终账本。

新增矩阵至少覆盖：

1. 早页native卡死，晚页真实业务prose仍返回；0/小/正常增强预算都诚实。
2. 完成前几页后卡死，完整帧复用，半帧/foreign source/duplicate冲突/越界页拒绝。
3. parent进程结束前后两个故障窗口：CAS落盘前、落盘后索引前、索引后Temp清理前；不丢原件、不伪造complete。
4. restart只重做未完成；策略仅重排不重提取；源/真实parser变更失效；损坏某一缓存仅该项miss。
5. 早财务附表、晚经营表、无明显标题/无近期事件词的真实经营矩阵、跨页表头/脚注；无全前缀策略。
6. QA shadow/native问答、跨页continuation、缺失上页问题、父子附件边界、混合语言；不能靠prose fallback洗角色。
7. merge前后原文unit ID/locator/每页段落序号稳定，ordinal及section关系符合原生顺序；fine几何未知仍未知。
8. 实际整份源传输量按document batch计，不随page数乘9MB；native调用只对请求页，cheap扫描/完整route/semantic/selector计数各有断言。
9. 原有80秒仍是总外界，不按页重置；native超时、停止、lease-loss和孤儿子进程清理可验证。
10. cache及staging真实byte全部入既有空间账，容量耗尽保住cheap partial；最终摘要调用前selection冻结，补表不能修改旧paid ledger。
11. 0.8、历史parser、显式table_pages、same/cross-run旧Ref回开不重新套当前策略；合成PDF与至少两个真实长文档的集中验收分开记录。

## 8. 与DU4的接口边界与未证明事项

ROOT负责native执行/共享pipeline/AUTO/回放接线。DU4-TABLE只消费真实表槽、period/单位/几何与原文refs；DU4-STATE只负责业务对象/动作/否定/阶段；DU4-FORM只负责真实form/speaker信号。不要让作者改以上公用文件，或强迫他们依赖一个还未合入的新parser API。

本调查没有实现新接口，没有跑synthetic/真实性能测试，不能提供速度提升百分比、最终内存峰值、每批最佳请求数量、全230页必要性或预测质量通过的结论。batch大小/时间/结果cap需从已有limits和实施时操作计数/holdout证据确定；不因当前样本跑得快就硬编码9.7MB、675页或某公司页号。
