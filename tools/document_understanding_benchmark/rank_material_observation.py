"""Test-side observation of compact ranking bytes and typed source closures.

The existing card-admission owner says what can be published. Serialization is
checked here field by field against original spans/tasks, not by calling the
production ranking-presentation builder to obtain an expected payload.
"""
from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
from company_wiki.automation.models import canonical_json
from company_wiki.document_understanding.source_cards import source_cards


def _require(condition):
    if not condition:
        raise ValueError("PHASE_C_COMPACT_RANK_SCOPE_INVALID")


def observed_rank_keys(selected, envelope, view):
    material = envelope["material"]
    _require(isinstance(material, dict) and set(material) == {
        "schema_version", "scope", "fragment_columns", "fragments", "reading_hints",
        "task_columns", "tasks", "available_task_count"})
    _require(material["schema_version"] == "source-extractive-ranking-view/1"
             and material["scope"] == "compiled_whole_source_cards_only")
    _require(material["fragment_columns"] == ["source_key", "text", "source_role", "quality_flags"]
             and material["task_columns"] == ["key", "support", "context", "reading_hint_index"])
    plan = compile_extractive_plan(selected)
    expected_keys = [row["task"] for row in plan.execution["tasks"]
                     if row["source_disposition"] == "admitted"]
    output = envelope["output_plan"]
    _require(output["source_plan_sha256"] == plan.execution["plan_sha256"]
             and output["admitted_task_keys"] == expected_keys
             and type(output["source_task_count"]) is int
             and output["source_task_count"] == len(plan.execution["tasks"]))
    _require(type(output["available_task_count"]) is int
             and output["available_task_count"] == len(expected_keys)
             and type(material["available_task_count"]) is int
             and material["available_task_count"] == len(expected_keys))
    tasks = {task.key: task for task in view.plan.tasks}
    wanted = {sid for key in expected_keys for sid in tasks[key].member_ids}
    spans = {span.span_id: span for span in selected.evidence_spans}
    ordered = [sid for sid in view.plan.evidence_order if sid in wanted]
    fragments = material["fragments"]
    _require(isinstance(fragments, list) and len(fragments) == len(ordered))
    for row, sid in zip(fragments, ordered):
        span = spans[sid]
        role = span.structured_value.get("source_role", "unknown")
        _require(row == [view._source_keys[sid], span.raw_text,
                         role if isinstance(role, str) else "unknown", list(span.quality_flags)])
    hints = material["reading_hints"]
    _require(isinstance(hints, list) and all(isinstance(hint, dict) for hint in hints))
    cards = {card.task.key: card for card in source_cards(view.plan, spans)}
    rows = material["tasks"]
    _require(isinstance(rows, list) and len(rows) == len(expected_keys))
    used_indices, used_hints = set(), set()
    for row, key in zip(rows, expected_keys):
        _require(isinstance(row, list) and len(row) == 4 and row[0] == key)
        support, context, hint_index = row[1:]
        _require(isinstance(support, list) and bool(support) and isinstance(context, list))
        for indices in [support, context]:
            _require(all(type(index) is int and 0 <= index < len(ordered) for index in indices))
            _require(len(set(indices)) == len(indices))
        _require(not set(support).intersection(context))
        task = tasks[key]
        _require(tuple(ordered[index] for index in support) == task.support_ids
                 and tuple(ordered[index] for index in context) == task.context_ids)
        _require(type(hint_index) is int and 0 <= hint_index < len(hints)
                 and canonical_json(hints[hint_index]) == canonical_json(cards[key].reading_hint()))
        used_indices.update(support + context)
        used_hints.add(hint_index)
    _require(used_indices == set(range(len(ordered))) and used_hints == set(range(len(hints))))
    return frozenset(expected_keys)
