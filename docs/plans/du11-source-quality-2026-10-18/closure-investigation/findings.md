# F2 三处真实来源闭合缺口：只读调查与通用 TDD 接口

状态：ROOT_CAUSE_IDENTIFIED_NOT_IMPLEMENTED。这不是源码修改或整体质量C签收。入口证据为同目录 `native-observation.json`（原生结构）和 `findings.json`（归因/TDD）。

只读取中微2026半年报物理页16、17、31；使用现 `_pdf_text_blocks`、原单元发射/字体投影和已有共享reading/continuity函数作局部观察，共102单元。未运行整报告解析、测试、新模型、下载或新PDF副本。原件前后SHA均为 `182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe`。每处仅保留103/186/229字原文上下文，其他为定位/哈希/字体/框/包种类事实。

重要边界：历史正式bundle是原实际全报告包种类的证据；本次3页局部pipeline明确另标为局部观察，不能冒称完整原production routing。两者在三处分别是risk/native_continuity/native_continuity，局部也实际复现；新ROOT probe的同文本SHA仍进入canonical是另外一份既有事实。

## 1. 不利影：risk绕过审计，且真实短尾不能通过旧重叠条件

- 物理p31/paragraph21，原block18，字范围0–40；紧接p31/paragraph22、block19只有两个字“响。”。原章节标题为政府支持与税收优惠政策变动风险。
- `_prose_reading_packages.prose_kinds`只有background/paragraph_event；risk进入other_members，被改成continuity_boundary，expanded又原样放回。故新singleton/open-start检查根本没有审核它，当前blocked=false。**不能只继续给finish加检查而不打通输入。**
- 两块均实测10.45regular，物理相邻、同原件/页面/风险scope。前行bbox x110.88..530.76，下一行x89.88..110.77，y间隙9.95；x0差-21.00，是真实首行约两汉字缩进加短末行。横向重叠实际为**-0.11**，不是正重叠。现edge还会拒绝它；把risk加入prose并不自动得到合法拼接。
- 原文确实提供完整句子的两个独立字节片段；程序必须保留这两片和真实定位，不能自动补一个“响”。如果共享几何owner不能证明正文同列/首行缩进/短末行流向，就应如实defer。

## 2. 求的同时：新页block0并不表示新断言起点

- p17/paragraph2，原block2范围0–34；同block下一小片34–42及block3起始组成原selected range38–108。p17首两个原块是页眉和页脚；block2是首正文块。
- p16末正文block33明确金属栅系列Preforma Uniflash ALD氮化钛/钛铝/氮化钽；block34末为“可满足先进逻辑客户性能需”。p17首正文直接继续“求的同时…”。这不是完整新句，亦不是可以靠通用“薄膜沉积设备研发”标题补主语。
- 当前left_closed把每个block_char_start=0当充分闭合；edge又完全禁止跨物理页，页眉/页脚会打断流。于是页内可找到句号形成window，却丢了上一页尚未闭合的正文和产品范围。
- 两页同595.30×841.90、rotation0、正文主字体10.45regular、左右边界相容；p16产品块有真实小号®上标，不应因此凭空换角色/产品。当前layout.column=None，**没有已通过的跨页native edge/列证明**。应新增真实多原span闭包或明确unknown/defer，不能制造跨页native_page_view，也不能把相容几何称为现已验真的完整关联。

## 3. 该系列产品：有句号和字符边界，仍缺外部先行词

- p17/paragraph12起始于原block9 char35，上一段char0–35刚好以句号结束。现left_closed因前一片terminal=true而放行。
- p17/paragraph9–11真实描述金属硅化物集成系统Preforma Uniflash，列出SA/SU、SPTi、ALDTiNM产品；paragraph12–14才是“该系列产品…客户端验证…高生产效率”。两者在本次真实continuity里落入**不同window**。4block窗口截断选了前一个句号；后续statement_members只保护各自window内部，无法带回前窗的依赖。
- 上下文可以保留为原文集体产品系列的依赖；它**不证明某个单独未命名产品独占所有验证状态**。现generic标题不够，不能由模型替换成猜测产品名。
- 即便物理片段完整，标点也只证明句法切点，不证明“该系列/these products”指代闭合。应绑定有界原先行上下文refs；多个竞争先行词、源证据不足或现限额容纳不了时，明确unknown/defer。

## 通用设计：在现source owner接线，不另造解析/门禁

1. **统一prose入口。** 以真实原生paragraph材料为闭合审计对象，risk/project/background/paragraph_event等语义包种类不能绕过。QA/table继续各自有结构的责任层，不与prose强行混成一段；保留原语义kind/role。
2. **分清三个证明。** 原字节与坐标连续、物理句子左/右边界、语义actor/object/先行依赖是不同维度。现native continuity提供物理证明；现source operating关系owner提供真实主体/修饰依赖；source reading统一决定完整support/context或deferred。不要让native字号算法再实现第二套业务语义引擎，也不要让摘要decoder补源文。
3. **复用现有端口。** 原units/provenance/sections/unit_profiles进入既有continuity；有限windows、required_unit_ids/required_context_unit_ids与citation_views携带真正上下文；原deferred_unit_ranges/reading诊断保留不足。闭合上下文必须来自相同source真实span和locator；仍遵守当前单元、字符、block、工作和摘要限额，不能借外接context暗中绕过窗口限额。
4. **窄短末行。** 仅在实测同source/scope/frame/font、正文列与相邻行流向证明、有限缩进/间隙和终止符同时成立时，接纳首行缩进后的短收尾。保留列/表格/heading/role/方向的阻断；不能全局删除overlap检查，不能按两个汉字或这几个字符串特判。无法证明就defer。
5. **真实跨页carry。** 只有相邻物理页实际尾/首正文、未终止上文、同活动section/frame/font/已证明列，且中间仅有原source已证明的页眉页脚时，组成多span闭包。上一页未读、换章节/列/来源/角色不能借block0宣称完整。多个原页分别保留其native_page_view，绝不造一个伪跨页range。
6. **窗口边界依赖。** 资源切窗之后仍须检查原source依赖。使用原关系owner的先行词/actor/object引用保留唯一或明确集体范围；不把句号当充分语义终止。缺闭包时报告该task不足，原件/原片段仍可查询，无需人工许可。

## 有意义的 TDD 行为包

- **A1**：同一原句被risk/project/background分别包装，首行缩进、短末行，原片段完全相同。三个种类都进入同一审计；有真实行流向证明则整句引用，否则统一deferred。反控邻列、不同frame/font/source/section、穿过表格或QA、独立新heading。
- **A2**：上一页末句未终止，下一页首正文block_char_start=0，中间是已证明页眉页脚。跨页多span必须保持原ID/页码/字节/限定语；只读下一页、不同正文列或新章节均不能称闭合。保留“不在同native_page_view”断言。
- **A3**：明确产品系列枚举随后“该系列/these products”，强制4block或8unit切窗。有限原先行context能纳入则引用完整；多候选主体、缺前文和超限都unknown/defer。不得把某一个产品硬填成主语。
- **A4**：负面/尚未/计划/日期/数量单位跨断点，校验原support/context与字节SHA；不裁词/不补词/不放宽验证。实际算法版本/源码进入原缓存依赖，不重签旧paid run。

以上只是调查和实施建议。ROOT仍需先行为RED、按同owner实施、集中工程与真实C复验；本报告不签F1/F2源码或整体资料质量通过。
