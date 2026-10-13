# DU/1 冻结接口与线程所有权

本接口是纯数据技术接口，不是权限、审批或人工签收。现有source验证仍由原责任层执行。ROOT拥有此文件；worker遇到歧义在各自handoff记录并继续可独立工作，不自行改变共享字段含义。

## 1. 共同约定

Python公开函数输入/输出为JSON可序列化Mapping，内部可用dataclass；不依赖其他未合并包。schema_version为du-input/1、du-route/1、du-structure/1、du-observed/1、du-gold/1。ROOT最终负责与NarrativeUnit/DocumentStructure等现有对象适配。可选字段缺失为unknown/null，不以字段缺失触发人工审查。拒绝错误类型/重复unit ID/无法引用的unit等真实数据错误；不要求授权文件、expected Git HEAD、policy hash或新source身份复核。

所有unit只属于输入的一份source；序号ordinal从0递增且唯一，不强求连续。page为PDF物理一基页/slide一基编号或null。locator是已有opaque字符串，模块不能重新编号或解析其中公司/目录。text为本次内存原语言文本，输出结构默认只保存unit引用。无网络/磁盘写入/读取配置/当前时间依赖。相同输入相同输出，排序稳定；不读取公司名/证券代码做特判。

## 2. 输入 DocumentObservation：DU-PROFILES与DU-STRUCTURE共用

```json
{
  "schema_version": "du-input/1",
  "source_ref": {"source_id": "opaque-source-id", "source_sha256": "opaque-passed-through-digest"},
  "metadata": {
    "title": "Example filing", "declared_kind": "unknown", "regime": "unknown",
    "form_type": null, "mime_type": "application/pdf", "language": "zh",
    "published_at": null, "period_end": null, "revision": null
  },
  "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
  "units": [
    {"unit_id":"u1", "ordinal":0, "locator":"opaque-locator-1", "page":1,
     "text":"第三节 管理层讨论与分析", "kind":"heading", "language":"zh", "role":"company_filing",
     "layout":{"bbox":[40,80,530,105],"page_width":595,"page_height":842,"column":null},
     "hints":{"heading_level":1,"table_id":null,"row":null,"column":null,"speaker":null,"turn_id":null,"dom_path":null}}
  ]
}
```

source_ref作为既有绑定透传，上例digest是测试opaque示例，两个纯包不验证SHA格式；真实适配传既有验真SourceRef。metadata除title/mime_type/declared_kind外字段可缺省；layout/hints可缺省，其各值不可猜成确定值。coverage.native_scan枚举complete/partial/unavailable，不能与语义完整覆盖混为一谈。units.text每项允许上限由调用方既有NormalizationLimits约束，模块额外接受Limits，显式超限返回partial诊断。

## 3. DU-PROFILES输出与公共函数

文件入口 `src/company_wiki/document_understanding/profiles/__init__.py`：

```python
def route_document(observation: Mapping, *, limits: Mapping | None = None) -> dict: ...
def get_profile(profile_id: str) -> dict: ...
def list_profiles() -> list[dict]: ...
```

route输出必须含schema_version、profile_id、profile_version、regime、family、subtype、confidence、reasons、alternatives、child_routes、disposition_hint。confidence为high/medium/low/unknown，无校准不能输出伪精确概率。reason对象{code, unit_ids, detail}，detail短诊断不复制正文。alternatives每项{profile_id, reason}。

child_routes每项{unit_ids, profile_id, reason}，当前单原件范围，不凭空生成SourceRef；不认识的外链只reason `EXTERNAL_ATTACHMENT_NOT_READ`。disposition_hint为read/generic_read/administrative_candidate，路由阶段永不返回最终skip或删除原件。

get_profile输出：{profile_id, profile_version, family, section_priorities, semantic_units, summary_focus, negative_hints}。

- section_priorities: 数组{section_role, aliases:[str], priority:1..3}。统一角色允许business/industry/management_discussion/outlook/risk/operating_metrics/fundraising/financial_notes/questions/administrative/unknown。
- semantic_units: 从paragraph_event/qa_exchange/project/operating_table/risk/background选。
- summary_focus: 简短原语言焦点，不包含投资结论、许可或新的模型供应商设置。
- negative_hints: 目录/页眉/签章/纯财务等软提示，不是整章硬删除规则。
- 至少覆盖 cn_annual、cn_interim、cn_quarterly、hk_periodic、sec_10k、sec_10q、sec_20f、prospectus、offering、investor_qa、earnings_call、results_release、presentation、administrative、generic。profile按继承/组合去重，不做15套平行pipeline。

limits默认max_probe_units=200、max_probe_chars=64000、max_child_routes=16。优先封面/结构heading/按文档跨度分层抽样，不盲取前200；不修改input。到限标ROUTE_PROBE_LIMIT和low/unknown，仍可generic_read。ROOT以现有全局限制收敛这些上限，profile不能提高付费预算。

## 4. DU-STRUCTURE输出与公共函数

文件入口 `src/company_wiki/document_understanding/structure/__init__.py`：

```python
def build_structure(observation: Mapping, *, limits: Mapping | None = None) -> dict: ...
```

输出{schema_version, source_ref, sections, semantic_units, relations, coverage, diagnostics}。不能导入profiles包；识别generic章节结构，类型优先级由ROOT结合route结果施加。

sections每项：

```json
{"section_id":"s1", "parent_id":null, "heading_unit_ids":["u1"],
 "body_unit_ids":["u2","u3"], "section_role":"management_discussion",
 "language":"zh", "confidence":"high", "basis":["heading_level","reading_order"]}
```

sections定义逻辑章节，body_unit_ids按原顺序，允许同章跨页。语言分栏按真实layout/DOM证据建立；父section可包含子section但同层body区间不得无解释交错。未知heading为unknown。TOC/页眉通过diagnostics/relations标识，不能变成正文新章节。

semantic_units每项：

```json
{"semantic_id":"m1", "kind":"project", "section_ids":["s1"],
 "member_unit_ids":["u2","u3"], "anchor_unit_ids":["u2"],
 "required_context_unit_ids":["u2"], "completeness":"complete", "diagnostics":[]}
```

completeness为complete/partial/unknown；只表示结构关联完整，不代表经济事实正确。kind取上述六类。一个表/项目/长答复可拆多个semantic unit，但每个包保留主体/问句/表头/脚注等必要依赖。成员须存在、稳定去重排序、不能跨source；超预算返回未完成包及deferred诊断，不截掉否定/单位后宣称complete。

relations每项{from_unit_ids,to_unit_ids,kind,confidence}；kind为continuation/header_for/footnote_for/question_answer/language_parallel/section_cross_reference，均为同原件关系。不确定关联不强行输出high。双语仅结构对齐/别名，不能翻译或删原unit。依赖环若无语义必要须诊断，禁止无限展开。

coverage输出native_scan透传、structured_unit_count、unassigned_unit_ids、deferred_unit_ids、opaque_pages、complete(结构过程完成)。不把complete映射为全业务召回。limits默认max_units=50000、max_relations=100000、max_group_members=64、max_work_units=2000000；调用方更低值优先，显式partial。避免对全文units两两比较；要求按页/邻接/章节线性或n log n处理。

## 5. DU-BENCH接口

公开 `tools/document_understanding_benchmark/evaluate.py`：

```python
def evaluate(observed: Mapping, gold: Mapping) -> dict: ...
```

du-observed/1字段：sample_id/source_sha256、route（以上wire或null）、selected_locators、semantic_units（可简化到真实unit/locator映射）、claims（{text,evidence_locators,role,modality,quantities}）、coverage、metrics、execution（actual入口/版本/calls）。允许baseline没有新结构，此项NOT_EVALUATED，不能为了让baseline通过伪造新字段。

du-gold/1字段：sample_id/source_sha256、scope=development|holdout、expected_route_families、facts数组。fact={id,importance:critical|normal,any_support_sets:[[locator或literal quote anchor]],must_preserve:[短字段断言],must_not_assert:[短反例],reason}。quote anchor格式{page或line,exact_quote}；实际observed必须能回放对应原件/单元，不能靠gold给观测补答案。允许多组等价支持位置，避免唯一行号过拟合。跨页组要求一整组，至少检查主体/期间/语态/数值口径。gold中的原文摘录每文档≤8KiB，不复制全文。

结果{schema_version:du-evaluation/1,status:PASS|FAIL|PARTIAL|UNAVAILABLE,checks,metrics,not_evaluated,execution}。每check{check_id,status,expected,observed,evidence_refs}。预算到限/源缺失不计PASS；semantic entailment未审只能NOT_EVALUATED，不能regex全绿就认证语义。支持negative mutation：丢限定语、单位错、问题当事实、缺source、缺页面、双语重复、伪完整。

CLI由benchmark包实现并写README：`python -m tools.document_understanding_benchmark --mode offline|native --bindings <json> --output <独立目录>`。offline只用≤200KiB合成fixtures，不联网；native从明确bindings读取白名单原件，先确认SHA一致，再观察现有公共parser/selector，或接ROOT后续注入adapter，不自写新selector。解析责任层的验真可以复用，工具不将其变成业务重复身份链。

bindings为本机未提交{sample_id:absolute_path}，原件不复制，缺少则UNAVAILABLE。输出目录只清理本次新建的owned子目录；已有哨兵内容/mtime保持。测试结果不被当作生产授权文件。

## 6. 所有权

| owner | 允许写 | 不允许写 |
|---|---|---|
| PROFILES | profiles子包；tests/unit/document_understanding_profiles/；tests/fixtures/document_understanding_profiles/；自身PWF/交接 | structure、benchmark、现有router/selector、共享INTERFACES |
| STRUCTURE | structure子包；tests/unit/document_understanding_structure/；tests/fixtures/document_understanding_structure/；自身PWF/交接 | profiles、benchmark、现有formatparser/selector、共享INTERFACES |
| BENCH | tools/document_understanding_benchmark/及其tests/fixtures；自身PWF/交接 | src、其他tests、production配置、RF/FF/Audit等仓 |
| ROOT | 上层document_understanding/__init__.py、现有parser/selector/summary/generation适配、docs/ARCHITECTURE、母PWF和本接口 | 不覆盖worker在制文件、不改Dayu或IQS |

## 7. 交接接口（各写自己的 `.planning/du-<lane>/handoff.json` 与 handoff.md）

JSON必须包含：schema_version=du-handoff/1、lane、base_sha、implementation_commits、worktree、status、owned_paths、public_interfaces、interface_deviations、A/B/C_evidence（命令、退出码、耗时、结果路径）、tests_passed/failed/not_run、known_gaps、resource_observations、raw_preservation、scratch_restore、install_actions（应为none）、next_root_action。implementation_commits列真正实现SHA，不能仅交文档SHA；不要求手签/hash许可或逐helper收据。

handoff.md用普通话说明改了什么、边界、如何复跑、真实与合成覆盖各多少、哪些仍没证明。使用`git diff --name-only <base>...HEAD`自查范围，`git status`解释未提交文件。提交本分支即可；不得并master、安装技能、push主线、重跑生产批次。只做A/B/C三个集中节点。
