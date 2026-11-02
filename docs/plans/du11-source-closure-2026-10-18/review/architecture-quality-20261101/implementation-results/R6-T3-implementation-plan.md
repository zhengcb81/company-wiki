# T3 实施细则：来源局部 scope 与编号完整句

状态：**只读实施细则已完成，尚未实施或验收**。本文件续接原 T3，不是新外包卡；ROOT 仍唯一维护主 PWF。调查基于 `tmp/architecture-r2` 的实际共享引擎及 `R4-context-investigation.md`、`R6-T3-design.md`，本轮没有修改 src/tests/Git/index，没有运行原件、解析器或模型。下面的新增接口、测试名、版本及命令均是待实施方案，不能当成现有能力或测试收据。

## 已冻结的设计约束

- 统一低层编号完整句的终结符与 closing wrappers 事实，不从来源业务 grammar 反向 import，不把 QA 软分隔符当完整句。
- source-marked 编号备注是局部结构 scope；长/换行引介不靠放宽通用标题长度上限。边必须指向原始引介 unit，保留来源限定。
- 新 scope 必须结束同层旧备注，甲→乙→甲与相同 actor 的新承诺均不得复用旧局部 frame；不能以 company_filing 推断 issuer。
- 跨 unit 延伸须有所属来源 owner 的真实顺序/成员证据：可为原生段落/字符邻接、已验证DOM/文本成员，或PDF几何/page proof。只有该项推断关系确实缺证或预算不足才局部 abstain/partial，不能把缺bbox变成所有格式的门禁，不能借前主体或全局宣称 complete。
- explicit HTML/native heading、真实编号业务标题保留；table footnote、furniture、正文提到备注作为反控。

## 调查日志

2026-11-02：已读两份现有调查、候选 layout/observation adapter。确认 `is_heading` 只查末字，adapter 另有终结符集；`-I`/测试隔离不属于本 T3。CodeGraph 用于结构入口定位，但主索引并非候选全部新 owner 的最终依据，下面以实际文件为准。具体接口、文件边界和 RED/真实 H1 检查点待本文件余下部分收敛。

现有可复用接口已核对：`SectionBuild` 已有逐 target context/source/proofs 映射；`NativeSourceContext` 已有一次性索引、source/paragraph/block/column/font/frame/coverage 的物理邻接证明，跨页通过 `page_neighbour` 输出 `observed_adjacent_page_flow`。`structure._coverage` 当前并不因普通 section diagnostic 自动降 complete，因此 T3 不能只追加诊断而仍把缺 scope proof 的关系当完整。`narrative_native_materials` 沿 section parent 合并所有祖先原始 heading，再消费逐 target 依赖；正确的上层导航可以保留，但旧 local note 不能仍是新 note 的祖先。

计划定位器在候选工区调用时因项目 containment 不匹配没有选择结果；已回 ROOT 主工区用明确 `PLAN_ID` 与绝对 `-PlanRoot` 成功解析到本计划，没有回退到别的计划。一次读取候选不存在的 `.planning/.../cases.json` 仅是只读路径选择错误；真实 oracle 应取 ROOT 的既有冻结文件，不在候选新造替代。

## 1. 实施基线、目的与不做的事情

只读核对 HEAD 为 `9f575810ca92620a6fb6ff63cfd326a5b9f076fa`。当前源语义作者仍有不相交在途改动，因此 HEAD 不是整个工作树的最终冻结；正式实施前应由 ROOT 收取同 owner CI 修复，记录当时 HEAD 和实际文件 SHA，不把本设计调查的旧 SHA 当新代码签收。

调查时三个关键 owner 原始字节 SHA-256：

| owner | SHA-256 |
| --- | --- |
| `document_understanding/structure/sections.py` | `8ff70fc94b5af97d856a651235577d85087fbdd2c0b42863f6701b3517dc6b4d` |
| `document_understanding/narrative_continuity.py` | `d8c8be3d1556fed569fb825db3d0541f806ebb39cfb72008ee952772712db32d` |
| `source_catalog/narrative_native_materials.py` | `c764cb7340d8b893e9e11c5414cfd3e616d8e5f901410550e8ab684385beba55` |

目的不是让承诺段获得更高投资价值分数，而是：同一句正文不会因尾随闭引号变成章节标题；原文明确的新备注成为自己的局部来源范围；每个下游 support 只能继承本范围可证的引介及独立合法依赖。来源关系与投资判断分开。

不改原文/locator/原始 unit 身份，不新建 actor 实体解析或公司词库，不改 facts/statement grammar/POS/来源语言识别，不扩摘要名额、费用或工作预算，不改下载/身份许可，不建第二任务库或 scope 数据库，不迁移旧缓存和封存。

## 2. 唯一责任层与数据流

```text
parser 已产出的 immutable units + native provenance
  -> observation_adapter：投影来源字段，显式 heading 优先
  -> DU text_boundaries：只观察尾部终结标点/闭包装符
  -> 既有 source provenance/成员 proof；需要PDF物理推断时借 NativeSourceContext
  -> structure.source_scopes：来源标记、有限局部备注成员与证据引用
  -> structure.sections：唯一 parent/局部 frame owner
  -> semantic 的逐 target context/source/proofs + 未证范围诊断
  -> narrative_native_materials：按 owner 结果闭包；未证 target 阻断
  -> 既有 selection/summary compiler：support/context 原始成员与预算
  -> 公开 handler：真实严格 DTO，source_processing_complete 与依赖状态
```

跨页物理相邻只是“有这条来源流边”，不等于同一主体、完整句未结束或相同业务。`NativeSourceContext` 不调用 grammar；结构标记不解释“本人/本企业/本公司”；材料层不根据赔偿词、真实公司、备注编号或页码删除 context。

现有 `NativeSourceDependencies` 三个可选字段保持原 shape：

```python
required_context_by_unit_id: dict[target_original_id, list[original_id]]
required_source_unit_ids_by_unit_id: dict[target_original_id, list[original_id]]
native_source_proofs_by_unit_id: dict[target_original_id, list[NativePageProof]]
```

不在这三个字段中混入新 actor 或审批状态，不把 same-page proof 伪装成 `observed_adjacent_page_flow`。same-page 证据留在本次结构构建的内部 scope record；跨页继续用真实既有 `NativePageProof`。`sections.heading_unit_ids` 和 `parent_id` 仍是可重放的来源引介路径，不另造竞争的父子系统。

## 3. 统一低层完整句终结：先 RED，后窄迁移

### 3.1 拟新增的最小原语

文件：`src/company_wiki/document_understanding/text_boundaries.py`。只用标准库，无 source_catalog、profiles、grammar 或运行时 import。

```python
TEXT_BOUNDARY_FEATURE_VERSION = "source-text-boundaries/1"

def terminal_punctuation(text: str) -> str | None:
    """返回尾部闭包装符与空白之前的硬终结标点；原字符串不变。"""

def ends_complete_sentence(text: str) -> bool:
    return terminal_punctuation(text) is not None
```

硬终结集合统一为现 continuity 已使用的 `。！？.!?；;`。冒号、逗号、顿号不属于完整句终结。尾包装字符只包括实际 closing quotes/brackets（中英文引号、圆/方括号、书名号等），不包括开引号、任意汉字、项目 bullet 或数字。用索引从尾部单次后退，交替跳过 whitespace/closing wrappers；不要反复复制长字符串或 normalize 全文。返回值不能被写回原文或用于重算 source 身份。

先冻结明确表格化 case：

- `3、甲方承担损失。` 与末尾追加 `”`、`’`、ASCII 双/单引号、`）`、`)`、`]`、`】`、`》`、`」`、`』` 以及嵌套/包装符间空白后的分类一致；中文编号 `一、…。”` 同样不成为隐式标题。
- `3、经营进展`、`（二）海外业务`、`1.2 主营业务（2026）` 不因尾括号被剥离就变为完整句；小数/版本 `1.2` 不视为有末尾句点。
- `报告期内：`、`收入增长，`、空白/只有引号/只有括号不是完整句。
- 引号内部有句号、但后面仍有真实文本的 `甲方称“已完成。”但仍需验收` 不是“末尾完整句”；不使用全串 search 代替 ends 判断。
- 显式 HTML/native heading 的文本即使带完整句标点，仍由显式结构证据优先；这是 positive source hint，不是一个标题词例外。

### 3.2 消费者边界

第一批迁移 adapter `_heading_level` 与 layout `is_heading` 的**隐式编号**路径，共用 hard-terminal veto；不统一两者的全部编号目录或 60/80 字符上限，不把长备注塞进普通 heading 正则。显式 `heading_level`/`h1..h6` 和 native 优先级保留，form response/tabular tail、TOC/furniture/table veto 保留。

同次 T3 将 continuity `_terminal`、materials 内 `source_statement_closed`/`statement_members` 的同一硬终结判断接到该原语；只迁移末尾观察，不改独立断言、否定/限定或 statement 拆分条件。结构 `relations._page_chain` 复用硬终结观察，但保留它自己既有的冒号停止条件——列表引介冒号不等于完整句，也不能因此跨页串成句子。

**不改当前在途 `operating_states/relations.py` 的业务规则。** 其中重复的 closing-wrapper 判断在语义作者冻结后再作同行为委托；只改 `closed_source_statement` 一处转调低层原语，并以原 owner 的现有行为测试保证未变。不能反过来让结构层 import 它。QA `_ends_sentence` 目前“全串含终止符 OR 软分隔符”的语义与本原语不同，T3 不偷换其语义或删除其 soft 分隔；若后续共享 closing-wrapper 集合，只能在明确回归下单独做机械复用，不把 QA 改造作为本节点额外前置大工程。

## 4. source-marked 局部备注 scope 的具体接口

### 4.1 标记与原始引介

新增窄模块 `src/company_wiki/document_understanding/structure/source_scopes.py`。第一版只识别本问题已有原文证据的**行首/块首备注格式**：简体 `备注`、对应繁体 `備註` + 明确编号 + `:`/`：`。编号只用于识别来源格式，不要求连续，不以编号/actor 文本作为 scope 身份；不能把 `见备注18`、`根据备注18：…`、没有标号的正文“备注如下”或纯数字数量当边界。

拟 `match_source_note_marker(text) -> NoteMarker | None` 仅返回原始 marker 的字符范围和编号标签；不返回 actor。字符范围只解释同一 raw unit，不改任何 locator。支持 ASCII/全角数字、中文编号的具体集合要用格式 fixture 冻结；不要用全局 NFKC 改写原文。英文 `Note 18` 与财务附注的更广歧义本轮没有真实 source oracle，列 OPEN，不能顺手宣称全市场注释都支持。

候选 unit 必须有已知 source 身份，且不是 TOC、running furniture、header/footer、table row/header/caption/cell、table_region、table_id 或显式 footnote。source_id 来自 observation/provenance，不来自 marker 文本或公司名。已知 table footnote 继续归 table/footnote owner。

引介规则按证据强度排列：

1. marker 与主体/承诺引介在一个 raw unit 内：完整保留此 unit，长度和换行均不作为否决，**不生成一份拼接新文本**；此情形没有跨unit关系，不要求bbox、font或column。
2. marker/引介被同一原生 paragraph/block 的真实 char ranges 分成多个 unit：只在物理 owner 证明顺序、同 block 身份及不重叠原始范围时，以原始 IDs 顺序保留全部 fragments。
3. marker 后是独立来源引介 unit，例如“甲方作出如下承诺：”：须source-owned成员/字符/DOM顺序或真实同页邻接证据，且有明确引介尾冒号或同原生块继续证据；在首条 numbered clause 前结束引介。不能为了找到 actor 任意扫后续正文，也不能把跨页所有段落吞成一个长标题。
4. 未能证明拆分的引介完整性：识别到的新 marker 仍关闭旧备注；受影响子项不继承旧主体，按 §6 局部 partial 处理。

所有 intro refs 都是既有 source units。长 intro 即使含可选择的业务正文，也不能因为“参与结构”而全局标成 non-selectable 或丢其原始语义成员；允许同一原始 ID 在可审计关系中作为本段 support 或后项 context，编译仍按现有去重/计费规则。不能把全文截断成 80 字 heading。

### 4.2 内部结果，不建新公共 state

拟用一个私有 frozen dataclass 表示单个已观测范围，字段与现有 `_NativeListScope` 对齐：

```python
@dataclass(frozen=True)
class _SourceMarkedScope:
    intro_ids: tuple[str, ...]
    member_ids: tuple[str, ...]
    context_by_unit: dict[str, tuple[str, ...]]
    source_by_unit: dict[str, tuple[str, ...]]
    page_proofs_by_unit: dict[str, tuple[NativePageProof, ...]]
    unresolved_unit_ids: frozenset[str]
    # same-page witness 仅本次调用内部使用，不进入旧 NativePageProof wire
```

模块入口拟为 `build_source_marked_scopes(ordering, *, native_context, limits, work_budget)`，返回 scope records 和有限 diagnostics。它不接收 grammar/fact callback，不 IO。固定只做 source-marker/原始成员组织，sections 仍负责分配 section_id/parent_id。

沿用同一调用的 WorkBudget（native_context 有预算时必须与传入 owner 一致），不 `WorkBudget()` 重置余额，不建全文新 index。一次顺序扫描，预先预留 index 和实际字符工作；每个 scope 最多沿用现有 `MAX_CONTINUATION_PAGES=2`、`MAX_CONTINUATION_UNITS=24`，intro/正文/跳过的 furniture 均计入上限，使用 limits 更低值时取较低者。扫描/refs/proof materialization 都先 charge；遇预算耗尽沿既有 WorkBudgetExceeded→partial-stage 路径返回，不在异常后补做未计费扫描。

### 4.3 sections 的新 frame 规则

在 `_display_heading_groups`/普通 heading fallback 前处理 source note marker。不要扩写一个全新文档树框架；复用 `SectionDraft`、`SectionBuild`、既有 native frame 和逐 target maps，最多增加一个私有 note frame 记录 outer stack 快照与当前 scope anchor。

顺序必须明确：

1. source 改变先清旧 stack/frame；既有 footer/TOC 排除先执行。
2. 看到新同层 note marker 时，结束旧 note 及其内部 native-list frames，恢复该 note 之前的 outer document/item stack；**不能先快照包含旧 note 的 stack，再将新 note 设为旧 note 子节点**。
3. 用新 intro 原始 IDs 建局部 section，parent 为有效外层 document/item section；depth 只用于内部局部嵌套，不声称 parser 有 native heading hint。basis 增加 `source_note_scope`，不能伪造 `heading_level_source=native`。
4. 同 actor 的第二个新承诺、甲→乙→甲、非连续/重复备注号，均按新的原始 opener unit 身份建立新 frame。不能按 actor 或 note 数字合并。
5. 只有证明在本范围内的 body 才进入此 section/依赖映射；新 ordinary heading、table/footnote/source/role/turn/列改变、真实 scope 边界均结束或暂停本地 scope。跳过 furniture 仅接受物理 owner 已正向识别的集合。
6. 缺证明时先关闭旧 note，再保留本 unit 可寻址的匿名/未证范围与诊断，不能回退继承旧 note，也不能把空 context 当已恢复主体。

新的 note intro 不是 generic navigation heading。`narrative_native_materials` 仍可保留真正外层导航，必须保留新 note 的完整 intro；前 note 的赔偿尾句既不能成为新 note ancestor，也不能从 package 的 external context/其他 owner 间接回来。若逐边 trace 发现另一条错误 producer 边，应修那条边的 owner，不允许用“所有前备注/赔偿尾句”黑名单从闭包最终集合中删除。

## 5. 来源邻接证据：先复用已有 proof，几何不是普遍门禁

完整句原语和来源标记不区分PDF/TXT/HTML。scope依据是来源真实局部关系，不是必须存在某一种几何字段。原件预览、同SHA原文复用、source export不因可选bbox缺失而受阻；这里只决定一条派生context边是否可证，不新增材料级许可或整文拒读。

优先级必须按下列证据实际存在而选用，不能先调用只接受PDF font/bbox的 `observe()`，失败后就说所有格式不可读：

1. 单raw unit内部marker与引介：直接原始成员身份，不需邻接proof。
2. `pdf-paragraph-membership/1`：现 `narrative_pdf_paragraphs` 已按源SHA、真实连续成员、文本对齐生成 group/position/count/previous/next，adapter已投影为hints。复用该已验证来源成员边，而不是新造另一个paragraph系统。
3. `native_block_character_ranges`：现continuity已有同block/hash/char range邻接检查；同源原生文本范围足以证明所需关系时，不能为了scope再要求相同bbox。实际范围不匹配、重叠或来源不同仍拒绝这条边。
4. TXT/HTML：若source parser已有同一容器中确切原始字符范围/成员顺序，或显式DOM heading-parent/order关系，投影这些真实provenance供结构消费，不虚构column/font。单有任意`ordinal`或一个相似`dom_path`字符串不够；explicit HTML/native heading本身仍按旧sections路径工作，不因缺几何退化。
5. 缺上述来源成员证据、确实需要PDF物理推断时，才用下面same-page/cross-page观察。几何字段“未知”不等于“已证矛盾”；它不能抹掉另一路已充分的原生成员proof。

候选现有paragraph/block proof位于 `narrative_continuity._Analysis.edge` 的若干geometry前置之后；实施应先写“valid source membership + no bbox”的RED，将**独立来源成员验证部分**抽成同owner窄纯helper，再让edge保持自己原有句子拼接前置、source scopes直接消费该纯成员proof。不能整段搬走edge的grammar/turn约束，不能让scope matcher复制一套group校验。若TXT/HTML所需原始char/member字段尚未投影，可仅在pipeline给借用的provenance补原始coordinates/producer member refs；先证明生产者确实提供，缺失列OPEN，不臆造新的公开DTO。

### 5.1 同页

当必须用PDF物理证据时，现 `layout.same_column` 在任一列未知时返回 True，不足以证明局部主体延伸。不可直接用它作为 T3 positive proof。只有复用现成员proof仍无法表达“两个完整条款在同一局部来源流中相邻”时，才给 `NativeSourceContext` 增加窄 `same_page_neighbour(left_id, right_id, *, furniture_unit_ids)`，复用其已有单位/ordinal/provenance 索引、`observe` 缓存和同一 budget；这不是所有格式都必须调用的接口。

返回内部 witness 或 None。witness 至少绑定 source ID、两原始 unit IDs、page、ordinal、已知 column、coordinate frame、block/paragraph 原始位置及已跳过的家具 IDs。只证明物理 flow，不做“未完成句”“同 actor”判断。成功条件：

- 两端同一真实 source、同页、同来源 role；有已知且相等的 column、有效框和 frame，实际 reading order 无反转/交叠乱序。
- ordinal 唯一、两端间每个 original 都是已确认 furniture，或确是同一原生 block 的顺序 fragments；不忽略隐藏正文、表格、footnote 或未知 block。
- 同 block fragments 要核同 block 身份/hash、真实 char ranges 非重叠且顺序与 provenance 一致；跨 block 需要连续 block/paragraph 的原生证据与已观测页覆盖。不能凭文本拼得通或 y 坐标近就补 char ranges。
- 不要求“上一句未结束”，否则完整 numbered clause 会失去 scope；同页显式引介与正文可有字体差异，不能为了省代码复用“字体完全相等”的句子拼接判断。字体差异也不能被 scope matcher 自行当作标题。
- 这个几何分支的 `observe` raw paragraph/native font/provenance 条件保持可核；无法观察时仅此物理分支返回None，不猜列、不伪造frame。上段已有充分原生成员证据的关系仍可成立，不被缺几何反向否决。

该 same-page witness **不进入**旧 `native_source_proofs_by_unit_id`，因为现 consumer 明确校验那里的 `right_page == left_page + 1`。同页关联通过真实 section 原始 heading/member refs 表达，witness 只供本次 owner 验证/测试观察。

同 block fragments 与原始 paragraph 的具体 parity 必须先用原生 fixture 写 RED；真实 H1 每条关系走哪种已充分proof是OPEN，不允许放宽 proof 迁就真实样本，也不允许一律增加font/column要求来缩小能力。

### 5.2 跨页

只调用已有 `native_context.page_neighbour(previous_body_id, current_id, furniture_unit_ids=...)`。保留既有要求：相邻物理页、源/frame/role/font/column、边缘位置/横向 lane、完整 original ordinals、positive page coverage、已证明的家具。不能仅看到 page+1 就继承，也不能让 scope opener跳过中间多页直接连接 target。

逐 target 映射必须完整：

- `required_context_by_unit_id[target]` 含本 note 全部 intro 原始 IDs；不含前 note intro/尾句。
- `required_source_unit_ids_by_unit_id[target]` 只含该 target 依赖的真实跨页 edge endpoints 和 positively identified furniture，扣除 target 自己；不是 model prose。
- `native_source_proofs_by_unit_id[target]` 保留 producer 返回的真实 page proof，不重造同字段假证明。
- 连续第二个子项依赖前页 intro 时，依赖闭包仍包含那条跨页 proof；不能只给跨页首个 target 然后让后项无证继承。
- 对确需跨页物理推断的边，页面 opaque/deferred/native_text 非 observed、缺 column、source/role/turn 冲突、无索引/缺家具证据都不可推延。若另有来源owner明确提供跨页原始成员关系，沿其所属proof合同消费，不把几何要求叠加成新门禁、不自行以文字猜跨页。已有 source page coverage 能单独证明本页原生文本时，不把全文件的其他 deferred table 页错误当作当前页完全无原生文本；仍不抬全源 completeness。

## 6. partial、失败传播与兼容

T3 成功必须同时证明“旧错误边没有了”和“新的真实引介完整保留”。无 proof/超 scope 边界时允许局部 abstain，但不能输出一个缩小 context 后的 complete 材料。

最小新增输出是既有 structure `diagnostics` 中的 source-owner code（拟 `SOURCE_SCOPE_UNPROVEN`、`SOURCE_SCOPE_LIMIT_REACHED`）及 exact affected original `unit_ids`。复用现有 `{code, unit_ids, detail}` shape；detail 只写证据原因，不写公司名单或完整长原文。每条影响列表保持 scope 的 24-unit界，未观察尾部由既有 work/deferred 计数表达，不为凑完整列表继续扫全文。

端到端传播必须逐环写测试，而不是只看 diagnostic 存在：

1. `SectionBuild` 保留未证 original IDs（内部默认空，旧调用兼容），新 scope 不把它们继承给旧 note。结构 semantic 的对应 completeness=partial；source scope owner 的确有未决范围时，structure `coverage.complete=False`。普通无备注/未知小标题不因此全文件失败。
2. `structure.__init__` 用有限诊断/内部 IDs 下调真实 scope 缺口，不只增加 code；预算异常继续用 `_partial_structure`，不发布半成品 frames/closed-stage 之外关系。
3. `narrative_native_materials.prepare_native_materials` 只按这些 owner-declared exact source IDs 加入既有 `context_blocked`，核 ID 存在/同 source；不在此重新匹配备注文本或判 actor。沿用现 `context_blocked -> continuity.complete=False`，受影响 target 不作为完整候选输出；其他独立 scope 仍可处理，不全局拒绝读文件。
4. 既有 `_candidates` 的 `graph_complete` 包含 continuity.complete，因而 `processing_base_complete/source_processing_complete=False`；当前 wire schema4沿用既有严格 bool，reading_dependencies inventory=partial，`current_reading_decision_matches` 必须 cache miss。
5. 注意 `REFERENCE_UNRESOLVED` 目前在 `_REFERENCE_DEFERRAL_REASONS`，单有这一 withheld 不阻断 processing。这里必须靠真实 context_blocked/continuity.complete链传播，不改这个全局兼容规则，不把所有旧的局部 reference defer 都升级成新门禁。

代码缺陷应 raise 而非通用 `except Exception` 吞成 complete。可预期缺证明由结构状态表达，不抛“需要人工批准”。根本无备注候选的文档沿旧结果；显式 HTML/native headings、原生 native list、PART/Item 相对层级、table/Q&A owners 保持职责与优先级。

## 7. 文件清单与实施次序

以下是同一个 T3 的文件分权，不是并行外包。先等当前源语义作者冻结其文件；不与其同时改 materials 的 statement helper 或 operating_states。

| 顺序 | 文件/责任 | 允许变更 | 禁止变更 |
| --- | --- | --- | --- |
| 1 | 新 `document_understanding/text_boundaries.py` + 新 `tests/unit/document_understanding_structure/test_text_boundaries.py` | 单一末尾原语、完整句/包装符 RED | actor/facts/POS/语言资源、IO |
| 2 | `observation_adapter.py`、`structure/layout.py` | 隐式编号共享 hard terminal veto；adapter 版本 | 普通标题全目录重写、长度扩容、虚构 hint |
| 3 | `narrative_continuity.py` | 硬终结委托、复用现paragraph/block成员proof；必要才加同页物理窄接口，现page_neighbour不放宽 | 第二套索引/预算、无几何普遍门禁或业务判定 |
| 4 | 新 `structure/source_scopes.py`、`structure/sections.py`、必要 `structure/contract.py` | 来源标记、intro/member refs、局部 frame、有限失败 IDs | 公司/页码/actor黑名单、竞争父树 |
| 5 | `structure/__init__.py`、`structure/relations.py` | 失败 completeness、原 refs 输出、结构 page-chain共享终结事实 | 新语义种类、财务/投资语义 |
| 6 | `source_catalog/narrative_native_materials.py` | source-note引介保留、exact blocked refs、硬终结委托 | 末端按赔偿词删 context、改业务准入 |
| 7 | `pipeline.py` feature、现有 recipe/cache 测试 | 更新真实算法版本/缓存反控 | 全仓hash、重签旧产物、假设版本号即通过 |
| 8 | ROOT real-acceptance runner/checks 的小扩展 | 捕获 actual section/依赖边索引及正向 scope oracle | 改 frozen原始unit/旧FAIL、固定预期绿输出 |

`source_catalog/narrative_reading.py` 预期无需新算法，只消费既有 graph/partial链。若测试证明 existing propagation 漏了一环，只补 composition-owner 的明确状态投影，不在 admission/facts 复制 notes逻辑。`operating_states/relations.py` 只在同 owner 冻结后做 §3.2 的纯机械委托；不改它的 noun/predicate/actor/qualifier。任何超出此边界的语义缺陷单独报 ROOT，不借 T3 扩大重构。

## 8. TDD 检查点：行为先于实现

### A：纯函数与结构责任

新增 `tests/unit/document_understanding_structure/test_source_note_scopes.py`；测试必须从 `du-input/1`/原生 parser units 构造 observation，经真正 `build_sections/build_structure`，不能直接塞伪造“正确 section”。

| RED组 | 最少必须锁住的断言 |
| --- | --- |
| TERM-1 | 原 R4四尾句结构变形及通用甲方句，闭包装符变化不改变正文分类；adapter/layout均不误开section |
| TERM-2 | 完整硬终结、软分隔、嵌套引号、句中标点、长文本线性工作；raw/locator/ID不变 |
| HEAD-1 | 中文/阿拉伯真业务标题、PART/Item、native/HTML explicit heading保持；table/form/TOC/furniture不得晋级 |
| NOTE-1 | R4 u0–u8去公司化 fixture 中u4只继承u3、u8继承u6，u2/u5不得成为它们任何local ancestor；不是只断言forbidden为空 |
| NOTE-2 | 甲→乙→甲、同actor新承诺、跳号/重复号以新opener unit分界，不以actor/编号复用scope |
| NOTE-3 | 86/95字符及更长、unit内部换行、同block拆分、独立来源colon引介；全部intro IDs按原文保留，不靠调大标题上限 |
| PHYS-1 | same-page/same-block真实char/provenance、有效paragraph-membership无bbox正控；几何路径column未知不得强猜，但充分原生成员proof不被缺几何否决；伪source、乱原始成员顺序、交叠/反转、table/footnote/role/turn barrier不得建边 |
| PHYS-2 | 跨页完整句子仍可属同scope，需真实page proof；缺页/缺font/frame/column/家具/coverage、第三页、24成员溢出均不能偷带intro |
| NEG-1 | 正文“见备注18”、标题中提到备注、无编号/无delimiter、table footnote、running furniture、普通年号/数量不是新note frame |
| FAIL-1 | 缺proof时旧scope已关闭；target有partial/diagnostic；预算0/临界耗尽在index/列表物化前停止，无半成品complete |
| PURE-1 | 输入deepcopy相同、重复输出相同、所有refs来自本source originals；scope内没有拼接原文或新增身份 |

物理 case 应复用 `test_native_list_physical_observer.py` 已有 `_source`/native page-view fixture模式（或抽一个仅测试用共同builder），不要从生产 import 私有 `_NativeListScope` 构造正确答案。已有完整native list proof断言不改成允许无proof。

### B：实际共享选择、编译与缓存合同

新增 `tests/unit/document_understanding_selection/test_reading_source_note_scope.py`，可复用 native ancestry 现有 `_source/_model/_spans_for` 测试builder；运行真正 `select_reading_evidence`、citation view和summary compiler，不调用模型服务。

- neutral source note 的业务子项与行政承诺两类都要测试。前者必须得到正确 intro，后者允许未入选，但结构/候选观察仍要完整，不能拿“行政全部没选”签归属正确。
- intro 是同原始 ID 的可读 context，并非所有同页句子的 package-wide 并集；physical endpoint/furniture只计 source proof，不混进 model prose。一个 endpoint 自身若另有真正 meaning dependency仍保留该meaning，不能一概剥掉。
- 紧邻两个 scope 的 support view 中，前note intro/尾句既不以context出现，也不被错误提升为support；新intro必须出现于对应view，summary实际fragments也含完整原始限定。
- 未证target即使下游comparator故意返回same，仍 `source_processing_complete=False` / inventory partial / cache miss；独立健康scope仍可得正常材料。完整同recipe正常命中一次，不能靠永久cache miss凑绿。
- 在现 `test_reading_recipe_closure.py`/`test_cf3_algorithm_identity.py` 加actual owner字节变更反控：新text_boundaries、新source_scopes、sections和physical owner变化会使真实manifest current mismatch；还原后same。使用source_catalog真实composition owner，不能patch DU薄shim后声称测到生产。
- 共用结构算法变更应同时使实际PDF与非PDF manifest失效，因为两者都使用该结构层；纯PDF frontend变化仍不影响TXT/HTML，继续保留现有负控；测试/文档/安装路径/CRLF变化不造成误失效。
- 旧无新scope字段/无note调用的wire继续可解析；保留reading-context schema1/2/3兼容、schema4 strict bool及unknown反控。不要为T3无新wire字段扩RF DTO。

新增 `tests/integration/test_source_note_scope_handler_wire.py`：至少一份小型、独立scratch内原生PDF与一份HTML，走真正 `SourceVersionReader -> NarrativeSelectHandler -> to_dict/contract validator`。PDF由测试生成可重复字体/块/页，HTML使用真实h标签及备注正文。测试可用配置隔离和非网络model-compile fixture，不能mock selector/structure/合同；这验证公开边界，不以单调私有函数代签。

### 最少正常宿主命令

均为未来实施后的命令；先准备 §11 的 owned scratch，并在候选工区运行，`T3_SCRATCH` 必须是已核绝对独占目录。每组只跑一次，失败后修首错再跑受影响小组，不反复超时整批。

```powershell
& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/document_understanding_structure/test_text_boundaries.py tests/unit/document_understanding_structure/test_source_note_scopes.py tests/unit/document_understanding_root/test_structure_shared_work_budget.py -q --tb=short --basetemp "$T3_SCRATCH/pytest-a"

& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/document_understanding_selection/test_reading_source_note_scope.py tests/unit/document_understanding_selection/test_native_list_physical_observer.py tests/unit/document_understanding_selection/test_reading_native_list_ancestry.py tests/unit/document_understanding_selection/test_reading_recipe_closure.py tests/unit/test_cf3_algorithm_identity.py -q --tb=short --basetemp "$T3_SCRATCH/pytest-b"

& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/integration/test_source_note_scope_handler_wire.py -q --tb=short --basetemp "$T3_SCRATCH/pytest-handler"
```

同组既有native-list/recipe域较多，新增case失败时只重跑具体nodeid；先前已通过且源码未再影响的组不反复跑。Ruff只检查实际改动文件；mypy按现工具对受影响src做正常check，候选最终完整现有CI只由ROOT统一推送后执行，不额外加慢的commit gate。

## 9. recipe、feature与历史兼容

- `text_boundaries.py` 从 adapter/layout/continuity显式import；`source_scopes.py` 从sections显式import，现AST recipe闭包应自动包含。需要真实cache反控证明，不能仅grep看见import或只补一个字符串hash。
- `OBSERVATION_ADAPTER_VERSION` 拟从 `/9` 升 `/10`；`NARRATIVE_CONTINUITY_FEATURE_VERSION` 在新增物理接口和终结委托后从 `/11` 升 `/12`；`PIPELINE_FEATURE_VERSION` 从 `1.15.0` 升 `1.16.0`。若当前候选已被ROOT其他已审改动递增，则基于实际版本继续递增，不覆盖成这里的旧值。
- 新内部scope feature可声明 `source-note-scope/1`，由模块实际字节进入recipe；无须新建一套手写全模块清单或全仓hash。新纯primitive同样走实际闭包，不哈希全部source/automation。
- `du-input/1`、`du-structure/1` 的公共字段形状未变，reading-context schema4和wire feature1.1不因内部basis/diagnostic自动升级。若实现确需新增公共字段，先明确该字段owner/消费者并写真实handler RED，再由ROOT决定版本，不把private observer序列化出去。
- 旧artifact/source/paid pin仍是冻结历史，不重签、不删账；旧recipe与当前不同应cache miss，并按当前已配置任务/预算处理，不制造人工审批。没有新模型结果不能说“旧正式摘要已按新scope修复”。

## 10. C：一次真实 H1 的精确检查点

在工程独审与候选必要检查完成后，ROOT冻结实际runtime，再执行**一例一次**当前H1 source选择；本细则制定阶段没有执行。输入沿用 ROOT `.planning/architecture-quality-20261101/real-acceptance/cases.json` 的 `r4-cn-h1-real` SourceRef/12单元/9对旧wrong-context oracle，原件SHA `d0dba19e…b6354a5f`/1,216,470B不变，不复制PDF、不修改旧R4/v1/v2收据。

### 10.1 先修验收观察能力，再执行一次

现 runner 已在 `_candidates` 前后旁观真实pipeline，现 v2 receipt保留公开span/member/view/package，但未完整留source-scope hierarchy与intro正向检查。新增观察只对九对oracle及其必需intro/祖先/物理proof闭包取小索引，不导出全文或重调selector：

- `original unit -> section_id -> parent chain`，每个section的heading IDs/basis；同一raw ID实际locator/text SHA与观察source身份。
- 逐target的 `required_context_by_unit_id`、`required_source_unit_ids_by_unit_id`、page proofs、scope failure诊断；同时保留package external context refs及来源owner/basis，若没有owner信息则写OPEN，不假装历史双边已完全重建。
- 原始intro片段是否属于一个scope、当前support对应哪些native carrier members；现member slice必须按原始坐标重算SHA，不按wholequote搜索替代。

**候选运行路径风险已查证**：现 `run_source_case.py.execute()` 会把 `ROOT/src`/`ROOT/scripts` 明确插到sys.path前部，不能只设置PYTHONPATH就声称运行了 `tmp/architecture-r2`。若ROOT在源码并线后运行，先核主线实际SHA与已审版本一致；若并线前运行候选，给既有runner增加明确 `--runtime-root` 参数并传递到worker，runtime_state/import也绑定该根，而证据输出/manifest仍绑定ROOT原验收目录。先用不读原件的小测试证明runtime-root选择与旧默认兼容，不复制整套源码/改product路径，不在旧v1/v2脚本压缩快照上修改。

未来候选入口示例（`--runtime-root` 当前尚不存在，必须先按上段实施并测试）：

```powershell
& C:/Miniconda/python.exe -B -X utf8 .planning/architecture-quality-20261101/real-acceptance/run_source_case.py --runtime-root C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2 --case r4-cn-h1-real --output .planning/architecture-quality-20261101/real-acceptance/h1-t3-current-v3.json
```

沿既有90秒父进程单例、16M工作及112选择等真实原配置，不抬限额。输出必须不存在，若同名已有选新唯一名，不覆盖。超时/异常保留失败收据并分析首错；不能连续重跑一批来碰绿。runtime before/after有变时该收据只记混合版本观察，不签当前通过。

### 10.2 不能省略的结果矩阵

每对R4-CONTEXT-PAIR-1…9分别记：

1. required support原始成员是否完整映射当前carrier，成员原文SHA/locator是否正确。
2. forbidden旧尾句是否从该support的context消失，且没有被其他组错误升级成support或同quote的隐含祖先。
3. **正向intro**：备注8/9/10/11各自真实原始heading/主体引介所有unit IDs是否在当前scope hierarchy和对应view上下文里；p35→p36续项是否仍属于备注11，并有真实跨页proof。
4. 若该行政support未入选，记录 `NOT_SELECTED`，结构层仍需证明它有正确原始scope；公开摘要层归属标 `NOT_EVALUATED`，不能把九个错误pair均没匹配报告成通过。
5. 只有确需该项推断却没有足够来源proof时才局部partial/defer；缺geometry/column不能否决已充分的字符/成员/DOM关系，更不影响raw预览或复用。不能借company_filing将“本公司”绑定发行人。别把partial当内容已修复，也别提高预算掩盖源能力缺口。
6. 保留原p12三经营unit、D&M和p14八成员的12目标召回；T3不得为清行政context而让已正确业务成员消失。

状态建议分开输出：`STRUCTURAL_SCOPE_VERIFIED`、`PUBLIC_VIEW_VERIFIED`、`NOT_SELECTED`、`PARTIAL_UNPROVEN`、`OPEN_LINEAGE`、`WRONG_EDGE_PRESENT`。前两种是证据检查结论，不是投资研究PASS。source选择通过不等于正式摘要/cache/RF实际采用已完成；后续仍按现主PWF在新隔离attempt真实执行并保留旧费用。

## 11. 测试隔离、空间与恢复

工程测试采用单个 ROOT 自有短目录，例如 `<CWP>/tmp/t3-<unique_nonce>`，实施者先解析绝对父路径在 `<CWP>/tmp` 内，核每层非reparse，记录该唯一目录初始不存在后才创建。所有pytest basetemp和生成PDF/HTML只放这里；不在原件根、生产公司目录或其他作者工区生成fixture。独立reviewer使用自己的nonce，互不删除。

如果 conftest relocation 改了实际basetemp，必须保存 `CW-BASETEMP-DECISION` 给出的resolved目录并核独占/初始状态；未有这份证据不得猜路径清理或宣称恢复。pytest `tmp_path` 本身不证明自动删目录。测试结束：

1. 把有限收据/命令/版本/实际source-root和新增测试资料清单写ROOT自有report，原PDF SHA/size保持。
2. 对自己明确创建的scratch再核absolute containment、非reparse、原始absent及当前清单；仅删除这个已检查的绝对目录，不扩大到其他tmp/pytest历史目录。保留需要交ROOT复核的最小证据在既有implementation-results，不复制整个运行树。
3. 记录删除前逻辑字节、exists_after=false及原件/生产config/DB前后SHA。若有必要临时文件归属无法证明，保留并写cleanup=NOT_VERIFIED，不将它冒充已恢复。
4. 真实H1沿现runner只读源catalog，记录DB/WAL/SHM及实际原件前后状态；若解析器生成暂存，按所属owner收据核实，不手工删unknown。新正式摘要的独立catalog/AUTO仍按主PWF另建，不能让该source-only试验写穿生产。

不做完整恢复备份演练，不复制模型资产，不把新module字节当作磁盘节省证明。

## 12. 大节点审查与当前 OPEN

只保留两个有实际内容的节点：**工程责任层/公开合同/缓存的合并独审**，以及**同冻结版本真实H1 source关系验收**；可由ROOT合并组织同次审查，不为每个小函数新增许可/签收。独审绑定完整源码与测试SHA，读真实RED和负控，不以作者宣称绿替代；发现小问题直接在owner修复，重跑受影响测试，不另发返工包。

必须保留的 OPEN（不得由实施者自行写绿）：

- R4冻结旧context没有完整内部graph；span102/103双context每条历史路径不能唯一重建。新source trace必须证明当前实际边，不能编造旧path。
- 真实H1备注8/9/10/11的多unit intro具体由哪种原生成员/char或物理proof充分证明，当前只读代码调查不能确认。确实无足够关系证据才partial，不放宽条件追求全绿，也不将font/column普遍追加为许可。
- 英文/其他语言Note标题、未标table footnote、TXT/HTML尚未投影的原生成员proof：具体覆盖OPEN；不能声称全覆盖。普通HTML native heading保持；纯TXT有原始字符/成员证据时接受，无layout不伪造PDF proof，也不拒绝可验证原文预览/复用。
- 当前同源语义R3工作树仍在修改；正式T3必须基于ROOT收口后的真实版本。`operating_states/relations.py`重复末尾原语只可待其owner冻结后机械迁移，不与其业务规则同时改。
- 本轮没有RED运行、源码实施、真实H1 v3、摘要POST、缓存恢复或RF采用；本文件只是完成了原T3实施准备，不能把原PWF对应项标完成。

**下一步唯一行动**：ROOT完成当前CI source-owner修复/独审收口后，按§8 A先写TERM/NOTE/PHYS红例；实现§3–6，完成B与实际handler/cache反控，再冻结做§10一次真实H1。此设计作者到此 **STOP**，不自行开始实现。
