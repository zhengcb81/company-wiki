"""AUTO-5 read-only diagnostics and planning CLI.

Commands: status, doctor, plan.  All commands work without LLM keys, network
or write mode.  The ``plan`` command reads events from the store and outputs
the planned DAG without creating any jobs or side effects.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from .models import canonical_json


SCHEMA_VERSION = 1


def _status() -> dict:
    return {
        "database": None,
        "mode": "off",
        "next_work_unit": "AUTO-7",
        "schema_version": SCHEMA_VERSION,
        "status": "not_configured",
        "writes_performed": 0,
    }


def _doctor() -> dict:
    return {
        "checks": {
            "automation_store": "not_configured",
            "store_importable": True,
            "registry_importable": True,
            "policy_importable": True,
            "planner_importable": True,
            "retry_importable": True,
            "outbox_importable": True,
            "worker_importable": True,
            "event_sources_importable": True,
            "controller_importable": True,
            "gold_review_handler_importable": True,
            "human_inbox_importable": True,
            "llm_required": False,
            "models_importable": True,
            "network_required": False,
        },
        "overall": "ready_for_auto_7",
        "schema_version": SCHEMA_VERSION,
        "writes_performed": 0,
    }


def _plan(db_path: Path, event_id: str | None) -> dict:
    """Read events from the store and output the planned DAG (read-only)."""
    from .event_sources import EventSource
    from .planner import plan_jobs
    from .policy import PolicyConfig
    from .registry import create_default_registry
    from .store import AutomationStore

    store = AutomationStore(db_path)
    source = EventSource(store)
    registry = create_default_registry()
    config = PolicyConfig(allow_llm=True)

    if event_id:
        event = store.get_event(event_id)
        if event is None:
            return {"error": f"event not found: {event_id}", "exit_code": 2}
        events = (event,)
    else:
        events = source.get_all_events()

    dags = []
    for evt in events:
        try:
            dag = plan_jobs(evt, registry, config)
            dags.append({
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "jobs": [
                    {
                        "temp_id": j.temp_id,
                        "job_type": j.job_type,
                        "subject_type": j.subject_type,
                        "subject_id": j.subject_id,
                        "risk_class": j.risk_class.value,
                        "priority": j.priority,
                        "max_attempts": j.max_attempts,
                    }
                    for j in dag.jobs
                ],
                "dependencies": [
                    {"child": c, "parent": p} for c, p in dag.dependencies
                ],
            })
        except Exception as exc:
            dags.append({
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "error": str(exc),
            })

    return {"events_planned": len(dags), "dags": dags}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m company_wiki.automation.cli",
        description="Read-only automation diagnostics and planning CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    child = subparsers.add_parser("status", help="report control-plane status")
    child.add_argument("--json", action="store_true", help="emit JSON")

    # doctor
    child = subparsers.add_parser("doctor", help="verify module importability")
    child.add_argument("--json", action="store_true", help="emit JSON")

    # plan
    child = subparsers.add_parser("plan", help="plan jobs for events (read-only)")
    child.add_argument("--db", type=Path, required=True, help="path to automation.db")
    child.add_argument("--event-id", type=str, default=None, help="plan a specific event")
    child.add_argument("--json", action="store_true", help="emit JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "status":
        print(canonical_json(_status()))
        return 0
    if args.command == "doctor":
        print(canonical_json(_doctor()))
        return 0
    if args.command == "plan":
        result = _plan(args.db, args.event_id)
        exit_code = result.pop("exit_code", 0)
        print(canonical_json(result))
        return exit_code

    return 2  # unknown command


if __name__ == "__main__":
    raise SystemExit(main())
