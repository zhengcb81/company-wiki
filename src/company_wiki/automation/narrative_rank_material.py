"""Compact private presentation for advisory ranking, never generated facts.

    The source task plan and canonical admission own every membership. This
    model boundary copies each used original fragment and reading hint once.
    The complete plan/strategy remain hashed outside the HTTP presentation.
"""
from company_wiki.document_understanding.source_cards import source_cards

RANK_MATERIAL_SCHEMA = "source-extractive-ranking-view/1"
RANK_STRATEGY_SCHEMA = "source-extractive-ranking-strategy/1"


def ranking_material(selected, source_plan, execution):
    admitted = {row["task"] for row in execution["tasks"]
                if row["source_disposition"] == "admitted"}
    tasks = [task for task in source_plan.tasks if task.key in admitted]
    used = {sid for task in tasks for sid in task.member_ids}
    known = {span.span_id: span for span in selected.evidence_spans}
    ordered = [sid for sid in source_plan.evidence_order if sid in used]
    positions = {sid: index for index, sid in enumerate(ordered)}
    keys = {sid: "s" + str(index + 1) for index, sid in enumerate(source_plan.evidence_order)}
    fragments = []
    for sid in ordered:
        span = known[sid]
        role = span.structured_value.get("source_role", "unknown")
        fragments.append([keys[sid], span.raw_text,
                          role if isinstance(role, str) else "unknown",
                          list(span.quality_flags)])
    cards = {card.task.key: card for card in source_cards(source_plan, known)}
    hints, rows = [], []
    for task in tasks:
        hint = cards[task.key].reading_hint()
        if hint not in hints:
            hints.append(hint)
        rows.append([task.key, [positions[sid] for sid in task.support_ids],
                     [positions[sid] for sid in task.context_ids], hints.index(hint)])
    return {"schema_version": RANK_MATERIAL_SCHEMA,
            "scope": "compiled_whole_source_cards_only",
            "fragment_columns": ["source_key", "text", "source_role", "quality_flags"],
            "fragments": fragments, "reading_hints": hints,
            "task_columns": ["key", "support", "context", "reading_hint_index"],
            "tasks": rows, "available_task_count": len(tasks)}


def ranking_strategy():
    return {"schema_version": RANK_STRATEGY_SCHEMA,
            "operation": "advisory_ranking_only",
            "source_policy": "retained in reading_hints; operational coverage stays in the program"}
