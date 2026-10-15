# DU4-FORM 交接（handoff）

LANE=DU4-FORM · PLAN_ID=du4-form-2026-10-15 · interface_version=du4-interfaces/1
基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3` · 分支 `codex/du4-form-20261015`
机器可读版本见 [handoff.json](handoff.json)。本 STOP 等 ROOT 接收。

## 入口与实现

`company_wiki.document_understanding.source_signals.collect_source_signals(observation, *, work_budget)`。

- `src/company_wiki/document_understanding/source_signals/contract.py`：输入契约校验、TextRef 精确解析、表单字面值有限归一化。
- `src/company_wiki/document_understanding/source_signals/__init__.py`：有界纯收集器（表单证据、轮次证据、reserved_unit_ids、诊断、status、work_used、observed_counts）。
- 只读依赖：`document_understanding.layout_hints.contract.WorkBudget / WorkBudgetExceeded`（复用调用方现有实例，不新建、不重置）。不 import profiles/router/pipeline/Store，不读文件、不解析 DOM、不扫描全文、不访问 provider。

## 接口实例（真实形状，合成 ID 除外）

输入 `du4-source-signal-observation/1`：

```json
{
  "schema_version": "du4-source-signal-observation/1",
  "units": {
    "u-form": {"text": "FORM 10-Q", "parent_id": "urn:…:source:sha256:5afe…", "role": "company_filing", "kind": "html_paragraph", "locator": "loc:v1/paragraph:4"}
  },
  "carriers": [
    {"kind": "visible_own_form_label", "unit_ids": ["u-form"], "value_refs": [{"unit_id": "u-form", "char_start": 0, "char_end": 9}], "parent_id": "urn:…:source:sha256:5afe…", "attributes": {}},
    {"kind": "visible_inline_xbrl_document_type", "unit_ids": ["u-form"], "value_refs": [{"unit_id": "u-form", "char_start": 5, "char_end": 9}], "parent_id": "urn:…:source:sha256:5afe…", "attributes": {"concept": "dei:DocumentType", "visibility": "visible"}}
  ],
  "declared_form": "10-K"
}
```

输出 `du4-source-signals/1`（节选）：

```json
{
  "schema_version": "du4-source-signals/1",
  "source_form_evidence": [
    {"parent_id": "urn:…:5afe…", "value": "FORM 10-Q", "origin": "visible_own_form_label", "carrier_unit_ids": ["u-form"], "value_refs": [{"unit_id": "u-form", "char_start": 0, "char_end": 9}], "normalized_value": "10-Q", "concept": null},
    {"parent_id": "urn:…:5afe…", "value": "10-Q", "origin": "visible_inline_xbrl_document_type", "carrier_unit_ids": ["u-form"], "value_refs": [{"unit_id": "u-form", "char_start": 5, "char_end": 9}], "normalized_value": "10-Q", "concept": "dei:DocumentType"}
  ],
  "turn_evidence": [],
  "reserved_unit_ids": ["u-form"],
  "diagnostics": [{"code": "DECLARED_FORM_CONFLICT", "unit_ids": ["u-form"], "detail": "declared literal '10-K' conflicts with observed ['10-Q']"}],
  "status": "partial",
  "work_used": 7,
  "observed_counts": {"units_indexed": 1, "carriers_seen": 2, "carriers_resolved": 2, "carriers_dropped": 0, "evidence_chars": 13, "reserved_unit_chars": 9}
}
```

（`work_used` = 1 unit 索引 + 2 carrier + 2×(1 carrier unit + 1 value ref)。declared 比较是字面值词法比较：`quarterly_report` 这类非字面声明不参与比较，只在无观察载体时给 `DECLARED_FORM_UNOBSERVED`。真实 VRSK 观察由 `tests/unit/du4_source_signals/test_real_observation_fixtures.py` 钉住精确 native unit ID 与字符位置。）

## 验证结果（实际命令与结果）

| 命令 | 结果 | 回执 |
| --- | --- | --- |
| `PYTHONPATH=src python -B -m pytest -q tests/unit/du4_source_signals` | 68 passed, 0 failed, 0 skipped | results/green-b-concentrated-tests.log |
| `python -m ruff check src/…/source_signals tests/unit/du4_source_signals` | clean | results/green-c-ruff.log |
| `MYPYPATH=tests/unit/du4_source_signals python -m mypy src/…/source_signals tests/unit/du4_source_signals` | no issues in 9 files | results/green-c-mypy.log |

RED 回执：results/red-a-semantic-counterexamples.log（接口骨架后 54 项语义断言失败、0 import 错误；其中 14 项为先行通过的结构/负控断言）。真实夹具 sha256 由 `test_saved_observations_match_manifest_hashes` 对照 fixtures/manifest.json 复核。

## 特别检查结论（卡 §B）

- 无隐藏全文扫描：只按 charge 计费遍历 units 索引与 carriers/refs；正则只作用于已解析的字面值字符串，不扫描 units 文本。
- 无第二家族路由：输出无 family/route/profile/confidence/subtype/regime 字段（`test_never_route_family_or_confidence_fields` 全递归断言）。
- 无「正则冒号即 speaker」退路：`Revenues:/Headcount:/Utilization:/Gross margin:/Widgets:` 等任意标签无 native carrier 即无 turn 证据，无禁止词黑名单；真实 CFO/operator/analyst 与原生 attributed table turns 均保留。
- 无 metadata 压倒父子范围：声明只出诊断；carrier units 跨 parent 即拒绝（CARRIER_PARENT_MISMATCH），8-K 容器与附件事实分列。
- 已观察 carrier 数量/字符/work 诚实报告：`observed_counts`（units_indexed/carriers_seen/resolved/dropped/evidence_chars/reserved_unit_chars）与 `work_used` 均为实测计数（`test_large_observation_work_is_honestly_metered` 等）。

## 未测范围（不冒充绿）

生产 normalize→structure→router→selector E2E、VRSK 原件新鲜限量重放、真实 transcript/8-K 附件 holdout 均属 ROOT；本卡无真实原件，均 NOT_EVALUATED。hidden-only DEI、多语种/分词封面、未见 SEC 表单变体同为 NOT_EVALUATED（未见字面值只保留事实+诊断）。

## ROOT 最小 glue（详见 handoff.json root_integration_steps）

一次 HTML walk 采集 carrier → surviving native structure → adapter → 本组件 → 现有 profile 在原 200 units/64000 chars 内优先预留 `reserved_unit_ids` 与唯一 arbitration；表单理由引用真实 carrier_unit_ids；剥离 transient reading metadata，保持旧 durable spans/ID/wire。
