# DU3/1 — 冻结技术接口与共同交接

Owner: ROOT。schema允许未来additive，但本卡不得单方面改字段含义。三模块互不导入；只依赖基线已有公共库。未知/缺项显式返回诊断，不猜业务事实，不创建许可、签收或canary。

## 决策依赖组件

```python
def freeze_decision_dependencies(trace: Mapping, *, limits: Mapping | None = None) -> dict: ...
def compare_decision_dependencies(frozen: Mapping, current: Mapping, *, limits: Mapping | None = None) -> dict: ...
```

`trace`：`schema_version=du-decision-trace/1`；`scopes`为`{scope_id, regime, family, form_type, purpose}`数组，child scope也是本源稳定ID，不含原文；`components`为`{component_id, version, content_digest, matcher_digest, scope_ids}`数组；`candidates`为`{candidate_id, scope_id, component_ids, eligible}`数组；`versions`为caller实际采用的算法版本Mapping。content/matcher digest是caller提供的完整SHA256；模块不读取catalog或文件来“验真”。scope限定此源决策域，当前候选包含曾参与决策但没赢者。caller提供的current inventory必须完整；用`inventory_complete: false`明确缺失，不能靠缺失条目得到same。

freeze输出`schema_version=du-decision-dependencies/1,status=complete|partial,scopes,components,candidates,versions,decision_digest,diagnostics`；排序与去重确定，重复ID/冲突或悬空组件是真输入错误，不能静默丢弃。有效字段不包含时间、路径、API密钥或run ID。`inventory_complete`须true才能complete；partial不能形成有效复用证据。

compare接两个freeze结果或冻结结果＋当前trace（类型按schema明确辨别），返回`schema_version=du-decision-comparison/1,status=same|changed|unavailable,changed_component_ids,added_candidate_ids,removed_candidate_ids,diagnostics`。匹配信号/内容、成员新增/删除/eligible变化、scope与算法版本变化均有明确因果差异；数组顺序不产生差异。无关catalog不在caller这个决策域内，不能强制塞全catalog当依赖。final-sent-policy hash是另一层，不放入这个组件代替trace。

默认资源：最多64scopes、512components、4096candidates、2MiB输入编码、200000work units；caller可降低。到限partial/unavailable、不得给same。资源限额是技术硬限，不是权限。返回汇总不复制正文，不建缓存/store。ROOT后续在router/selector instrumentation填实际inventory，并接既有AUTO两阶段CAS；本包不能认证caller漏报的外部事实。

## 版面快照组件

```python
def project_layout_snapshot(snapshot: Mapping, units: Sequence[Mapping], *, limits: Mapping | None = None) -> dict: ...
```

输入`snapshot.schema_version=du-layout-snapshot/1`，`pages`数组含`page, width, height, coordinate_frame, rotation, bindings`。每binding含`unit_id`及**实际提取所得**`bbox`、可选`font_runs/words/cells`；word/cell须含bbox及原生索引/文本范围依据，`cells`可有真实row/column/table_id。`units`是已有du-input单元，含unit_id/page/locator/text，作为绑定目标。snapshot为前端显式数据，不是PDF原文证据替代品。

输出`schema_version=du-layout-projection/1,feature_version,unit_metadata,coverage,diagnostics`。`unit_metadata`是`unit_id→{layout,hints,upstream_hints}`：保留真实bbox/page尺寸/font、granularity及可选words/cells；不改变unit_id、原text/locator/role，不新造EvidenceSpan。每细坐标仍能指出所属page/frame和真实提取来源；不能把整行/整块bbox复制成每个细格。projection无权推断column_lane、章节/续表关系、表头/脚注依赖，仍由现共享layout_hints负责。

同坐标frame才可关联。page.rect旋转尺寸与dict/text坐标不同不得混用；若有真实明确变换可转换并记录，未知frame不猜，粒度不足partial。缺unit、错页、框不合法/冲突、歧义映射给具体诊断。未对应元数据的原unit继续可读；未读页/deferred不伪complete。

默认10000units、64pages、200000cells/words合计、1000000work units；caller可降低。每循环和大容器工作有界，零预算必须停止。无文件/网络/model/OCR调用；native测试helper可对指定只读原件获取真实dict/words/table snapshot，但不进入产品模块、不启动新parser/OCR后端。ROOT后续补前端snapshot取得与旧adapter消费细metadata；本包不能宣称生产细列/细表已解决。

## 质量基准组件

沿用原`du-gold/1、du-observed/1、du-evaluation/1`及`evaluate(observed,gold)`。新增质量检查/输出字段必须additive并保留旧fixture；不用decisions/geometry新包才能运行，不导入两条在制模块。observed必须由基线实际normalize/DU公共入口及最终材料生成，并含unit→locator/text/角色、真实execution及覆盖。gold不能给observer填答案或补locator。

支持组组内AND、组间OR；主体/期间/单位/阶段/角色/否定与未读都分开。semantic entailment无法自动验证的保持NOT_EVALUATED。没有真实模型就不出summary忠实度PASS，没有生产接线就不出production PASS；工程/原文锚点/业务召回/语义审查分项报告。

新增入口放既有benchmark包公开模块，签名：

```python
def observe_final_material(material: Mapping, originals: Mapping, *, sample_id: str, execution: Mapping) -> dict: ...
def compare_runs(baseline: Mapping, candidate: Mapping, *, frozen_suite: Mapping) -> dict: ...
```

`material`为实际最终ModelRequest.data_json解码值，或标明synthetic/frozen-equivalent的同形fixture。沿既有evidence_columns/evidence行、evidence_group_columns/组alias，不自创flatten全文。`originals`为alias或canonical evidence ID→已核原unit/span与source_id/locator/text/role的绑定，观测不能从gold/模型claim补正文。输出沿du-observed/1的真实映射/execution/coverage；缺引用、实际正文与原文不符、虚报来源检查均明确失败或不可评。

`frozen_suite`含suite_id、samples（sample_id/source_sha256/read_scope/budget/gold及阈值），比较只能用同源、同范围、同预算和相同gold分母；不满足标INCOMPARABLE。输出`schema_version=du-quality-comparison/1,status=PASS|FAIL|PARTIAL|INCOMPARABLE`及各样本checks/metrics/未测，不缩分母凑改善。

## 共同交接（每worker独立ledger）

每卡写`.planning/du3-<lane>/task_plan.md、findings.md、progress.md、handoff.md、handoff.json`。JSON：`schema_version=du3-handoff/1,lane,base_sha,implementation_commits,worktree,owned_paths,interfaces,A/B/C_evidence,tests_passed,tests_failed,not_run,known_gaps,resource_observations,raw_preservation,scratch_restore,next_root_action`。evidence含命令/exit/耗时/小收据路径；不要在交接存全文或再造授权文件。

实现SHA必须真包含代码，不只提交报告；正常commit自己的分支、不操作主线或共享index。Git status解释自己未提交文件，local bindings不commit。测试用独立TemporaryDirectory和预存sentinel，原件/生产配置SHA/mtime/size不变，新增下载/截图/db在finally清理，未知目录不删。只有A/B/C集中自查，不每个小改动都手签；ROOT接收后统一跨层节点。
