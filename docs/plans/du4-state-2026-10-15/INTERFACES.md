# DU4 固定交接接口 / 1

2026-10-15，ROOT 所有。以下是**内存组件接口**，不是另一套持久库、研究结论或权限合同。作者只在自己的新包内实现与导出函数，使用标准库 Mapping/Sequence 和现有只读纯工具，不建立第二套任务/费用/身份校验系统。参数和下面的必要字段固定；可加可选诊断字段，不得要求兄弟包先产出数据。

## 共同约定

`TextRef = {unit_id: str, char_start: int, char_end: int}`，按 Python Unicode 字符的左闭右开偏移；`units[unit_id].text` 是原文。每个 ref 必须精确落在原 unit 内，不能引用匹配归一化后的字符串偏移。unit 至少含 `text, parent_id, role, kind, locator`。不重复拼接全文，不改字串、ID、locator、来源角色。

原文不足时返回逐项 `ambiguous/unavailable` 或诊断；局部不足不拒绝整个文档。结构畸形（错误 schema/重复 ID/非法索引）可抛 `ValueError`。未知事实不是空字符串、零或已完成。输入不修改，输出确定；返回 JSON 可序列化字典。

三个函数均接收关键字 `work_budget`，复用现有 `document_understanding.layout_hints.contract.WorkBudget`（`charge(n)`、`used`、`WorkBudgetExceeded`）。调用方传入现有实例，不能内部重置/创建第二个生产预算。循环与索引建设计费；耗尽时保留已确定结果并返回 partial 和计数。测试可独立创建此现有预算。该计数是组件操作数，不是 API token 或费用。

测试环境必须隔离：仅自己的 tmp_path 配置/夹具；不得调用 API、读取密钥、运行真实 AUTO、写生产配置或重开原件。不得全局 `pip install -e .`，避免三个目录互相重定向 import。PowerShell 中在本工作目录执行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -c "import company_wiki; print(list(company_wiki.__path__))"
python -B -m pytest -q <本卡测试目录>
python -m ruff check <本卡源码目录> <本卡测试目录>
```

确认 import 指向本工作目录。依赖缺失应具体记录；不要改全局配置。不要运行要求生产资料库的全库真实测试。生成夹具只放本卡测试目录，测试结束恢复测试目录初始状态；pytest 本次临时目录/缓存清理，不清理别人的缓存。

## TABLE

模块：`company_wiki.document_understanding.table_measurements`。

```python
def bind_operating_table(observation: Mapping, *, work_budget: WorkBudget) -> dict: ...
```

输入 `schema_version="du4-table-observation/1"`，`scope={parent_id, table_id, page}`，`units={id: unit}`，`cells=[{cell_id,row,column,row_span,column_span,presence,text_refs,header_refs}]`。`row/column` 为零起原生索引；span 未观察到则 null；`presence=present|empty|unavailable|merged_unknown`；`text_refs`/`header_refs` 是 TextRef 列表。可选 `header_rows` 为真实表头行索引，`provenance` 只接受实际 native_slot/fine_geometry 记录。不能根据文字顺序假造原生槽。合并大格可以只保留一个大格；数值所在列未知就未知。

输出 `schema_version="du4-table-bindings/1"`，同 scope，`status=complete|partial|unavailable`，`columns`、`measurements`、`unbound_value_refs`、`diagnostics`、`work_used`。column 含 column_id/native_column/header_refs/period/status；period 含 kind=`as_of|duration|fiscal_year|unspecified`、raw_label_refs，确有披露才填 start/end/duration_months/fiscal_label。measurement 含 value_ref/row_label_refs/column_id/period/unit_refs/scope_refs/qualifier_refs/binding_status。无法确定的列/期间用 null 和具体诊断。数值字串由 value_ref 取，不做币种/数量级换算或补缺运算。

## STATE

模块：`company_wiki.document_understanding.operating_states`。

```python
def detect_operating_relations(observation: Mapping, *, work_budget: WorkBudget) -> dict: ...
```

输入 `schema_version="du4-operating-observation/1"`，`unit_id`，`units={id:unit}`，可选 `context_unit_ids`（仅同 parent 已观察上下文）、`language`。不要求来源重新签收或实体库查验。

输出 `schema_version="du4-operating-relations/1"`，`relations`、`diagnostics`、`status`、`work_used`。relation 含 `assertion_refs, actor_refs, object_refs, predicate_refs, qualifier_refs`，`activity=production|commercialization|qualification|shipment|capacity|business_scope|business_relationship|other_operating`，`polarity=positive|negative|unknown`，`stage=current|not_yet|suspended|discontinued|planned|conditional|contact_established|intended_cooperation|unknown`，`attribution=issuer|quoted_related_party|other|unknown`，`modality=actual|planned|conditional|aspirational|uncertain`。非披露关系不输出事实；unknown 允许保留，不能强行补主体。relations 不等于已被 selector 选中，更不等于投资结论。

## FORM

模块：`company_wiki.document_understanding.source_signals`。

```python
def collect_source_signals(observation: Mapping, *, work_budget: WorkBudget) -> dict: ...
```

输入 `schema_version="du4-source-signal-observation/1"`，`units={id:unit}`，`carriers=[{kind,unit_ids,value_refs,parent_id,attributes}]`。kind=`visible_inline_xbrl_document_type|visible_own_form_label|native_speaker_turn`。attributes 只承载原生已观察的 concept/visibility/speaker/turn_id/turn_role；不是声明性 provider form_type。可选 `declared_form` 仅作冲突诊断。

输出 `schema_version="du4-source-signals/1"`，`source_form_evidence=[{parent_id,value,origin,carrier_unit_ids,value_refs}]`，`turn_evidence=[{parent_id,speaker_refs,body_refs,turn_id,turn_role,origin}]`，`reserved_unit_ids`、`diagnostics`、`status`、`work_used`。reserved_unit_ids 是应由现有 router 在原 cap 中优先考虑的真实 carrier 提示，不是预算外追加。value 保留原始表单写法，可另给有限 normalization；未知值仍观察保留。不给 primary family/route/置信度，不创建第二个 router，不将 manifest/文件名制造为 observed 事实。

## 三个大节点与交付格式

A：阅读本卡和真实观察，先写可执行语义反例并保存 RED；若是新模块导入失败，随后必须补真正语义 RED，不把导入错误当作根因覆盖。B：实现通用组件，一次集中单测/契约测试；记录输入不变、原文偏移、预算耗尽、确定性和跨 parent 负控。C：集中静态检查、实际结果与提交交接。只有这些大节点；无逐函数人工批准。

各作者在自己的 PWF 写 `handoff.md` 和 `handoff.json`，必要字段：

```json
{
  "schema_version":"du4-handoff/1", "lane":"DU4-TABLE|DU4-STATE|DU4-FORM",
  "base_commit":"8206e78d4087531b1d7ed57c45a73c942cc702e3",
  "branch":"codex/du4-...", "commits":[], "changed_paths":[],
  "interface_version":"du4-interfaces/1", "entrypoint":"...",
  "tests":[{"command":"...","exit_code":0,"passed":0,"failed":0,"skipped":0,"receipt":"relative/path"}],
  "fixtures":[{"path":"...","sha256":"...","kind":"retained_real_observation|synthetic","limits":[]}],
  "red_receipt":"...", "known_limits":[], "not_run":[], "root_integration_steps":[],
  "production_writes":0,"supplier_calls":0
}
```

日志放自己的 PWF/results，保留首个语义失败和最终集中结果，不反复存全文/中间转换产物。不要将自己最终 commit SHA 写进同一 commit 造成递归，交付后可单独补交接 commit。提交后 STOP 等 ROOT 接收。
