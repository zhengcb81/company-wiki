# T3 结构上下文设计调查（中途暂停，尚非实施卡）

状态：2026-11-02，按 ROOT 最新优先级暂停；CI41364303788的22项失败优先。不修改源码、测试、Git或主PWF。此文仅保存已查证设计，不能按它直接开工。

候选基线只读核对为 tmp/architecture-r2 HEAD=9f575810ca92620a6fb6ff63cfd326a5b9f076fa；工区唯一既有dirty .githooks/pre-push，未触碰。主索引含历史.planning副本，不能当候选源码事实。已读R4-context-investigation.md及候选实际owner。

已核实：observation_adapter._heading_level和structure/layout.is_heading各有编号+终止规则；后者只检查末字是否句号，因闭引号而把编号正文当标题。native_continuity._terminal、operating_states.relations.closed_source_statement、native_materials内部source_statement_closed又各有闭引号集合，qa._ends_sentence还混用“含终止符”与逗号/冒号语义。这些函数不能从业务语法owner倒灌给结构层，也不能简单将QA软分隔符当完整句。

候选最小共同owner：DU下纯text_boundaries（拟名，尚未实施），独占“剥离末尾闭包装符后是否有既有终结标点”的低层事实，不认主体/经营/公司、不修改原文/locator。adapter/layout的隐式编号标题推断共用；explicit HTML/native heading的优先级保留。后续迁移terminal wrappers只复用同一原语，各自保留硬终止/QA软分隔的责任，不能新建第三套punctuation集合。

复用调查：_display_heading_groups只处理一行table中Item编号+标题，不能当作长/多行备注引介owner。_native_list_scopes严格要求原生bbox、缩进、括号数字/bullet parent、bullet/roman child及跨页page_neighbour proof；真实N、赔偿尾句/备注N不匹配，不能据此把首错归给它。sections已有native_frames、SectionDraft.heading_ids、source/context/proof映射，适合接收局部source-marked scope；不能只把“备注”塞进短标题正则，不能在native_materials按赔偿词或公司删context边。

拟定局部scope原则：明确编号备注prefix+delimiter是来源边界，intro原unit IDs是scope原话限定；不识别/缓存真实actor实体、不把company_filing当issuer。新scope用原unit身份结束旧scope，同actor新承诺与甲→乙→甲也不能复用旧局部frame。长于60/80或换行的intro不靠增加heading长度上限，按source-marked introduction局部scope。正文“见备注N”、table note/furniture与无物理证明跨页都必须有反控。跨页intro必须仍绑定本备注并保留page_neighbour provenance，不能仅凭相邻页或相同actor推延。

原始最小结构反例（u0–u8）及九对真实unit oracle已在R4-context-investigation.md，不复制原件。后续TDD先锁：正文句号+不同闭引号不变heading分类；真正编号业务标题不退化；备注17甲/18乙/19甲各自intro正向继承；长/换行、同actor新承诺、跨页本公司不跨scope；无proof/超预算显式partial而非删边后complete。测试必须逐member/context owner检查，九条禁边消失不等于引介恢复；未选行政低值段须记未选，不能说关系正确。

recipe：DU新纯module将通过existing AST closure进入reading recipe，无需手工全仓hash。需要验证PDF/非PDF actual manifest stale→current mismatch；adapter/continuity feature版本按真实调用变化显式递增，wire字段不变则不无故升schema。尚未形成最终文件边界、完整TDD命令/清理/失败语义清单；待CI源语义节点收口后恢复，不能冒称设计已完成。
