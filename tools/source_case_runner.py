"""Bounded real-source engineering replay. No acquisition/model/AUTO writer.

Case-specific quotations and locators live in the manifest, never in routing.
The parent starts one fresh process with a hard deadline and the full JSON
receipt is persisted. Source identities are opened through SourceVersionReader.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from tools.source_case_checks import (
    compare_storage_observations,
    compare_context_original_members,
)

ROOT = Path(__file__).resolve().parents[1]


def jsonable(value):
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise TypeError(type(value).__name__)


def file_state(path):
    path = Path(path)
    if not path.exists():
        return {"exists": False}
    digest = sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(65536), b""):
            digest.update(part)
    stat = path.stat()
    return {
        "exists": True,
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


def runtime_state():
    base = ROOT / "src/company_wiki"
    paths = sorted(base.rglob("*.py"))
    paths += sorted(
        (base / "document_understanding/statement_grammar/resources").glob("*")
    )
    digest = sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    return {
        "files": len(paths),
        "source_and_linguistic_assets_sha256": digest.hexdigest(),
    }


def encode_receipt(record):
    # Bind the observer to this checkout, not an installed tools namespace.
    from tools.source_case_receipt import encode_source_receipt

    return encode_source_receipt(jsonable(record))


def observer_state():
    return {name: file_state(ROOT / "tools" / name) for name in (
        "source_case_runner.py", "source_case_receipt.py", "source_case_checks.py",
    )}


def atomic_owned_write(path, encoded, owned, *, root_dir):
    """Atomically replace only this run's own observation files."""
    path = path.resolve()
    path.relative_to(root_dir.resolve())
    if path.exists() and owned.get(path) != sha256(path.read_bytes()).hexdigest():
        raise FileExistsError("observation path is not owned by this run")
    pending = path.with_name(path.name + ".writing-" + uuid4().hex[:12])
    try:
        with pending.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if path in owned:
            # Another writer may have changed the checkpoint while pending was
            # flushed. Only this run's current version may be replaced.
            if not path.exists() or owned[path] != sha256(path.read_bytes()).hexdigest():
                raise FileExistsError("owned observation changed before replacement")
            os.replace(pending, path)
        else:
            # First publication must be an atomic no-clobber operation. A
            # preflight existence check cannot close the create/commit race.
            if os.name == "nt":
                # Same-directory rename is atomic on Windows and refuses an
                # existing destination. Hard-link creation is not consistently
                # available to ordinary Windows workspaces/sandboxes.
                os.rename(pending, path)
            else:
                # POSIX rename replaces an existing destination, so use the
                # atomic no-clobber hard-link operation there.
                os.link(pending, path)
        owned[path] = sha256(encoded).hexdigest()
    finally:
        if pending.exists():
            pending.unlink()


def observation_checkpoint(record, phase):
    """Retain execution/integrity evidence before large result serialization."""
    fields = (
        "case_id", "started_at_utc", "status", "model_posts", "downloads",
        "raw_copies", "source_select_calls", "source_ref", "seconds",
        "database_before", "database_after", "database_unchanged",
        "original_files_before", "original_files_after", "original_files_unchanged",
        "runtime_before", "runtime_after", "runtime_unchanged", "selected_span_count",
        "observer_before", "observer_after", "observer_unchanged",
        "native_member_count", "selection_material_sha256", "decision_digest",
        "checkpoint_gaps", "session_work", "error_type",
    )
    result = {key: record[key] for key in fields if key in record}
    result.update(schema_version="source-observation-checkpoint/1", phase=phase)
    result["required_checkpoints"] = [
        {key: target[key] for key in ("unit_id", "represented", "parsed_exact_original") if key in target}
        for target in record.get("required_units", ())
    ]
    if phase == "RESULT_READY":
        sizes = {}
        for key, value in record.items():
            try:
                sizes[key] = len(json.dumps(jsonable(value), ensure_ascii=False, separators=(",", ":")).encode())
            except (TypeError, ValueError, RecursionError):
                sizes[key] = None
        result["producer_field_bytes"] = sizes
    return result


def structure_context_checkpoints(oracles, structure, originals):
    """Observe fixed targets' real producer contexts even when unselected.

    No actor is inferred and no missing relation becomes a successful check.
    The finite producer tree is walked with cycle detection, without a depth veto.
    """
    wanted = {uid for oracle in oracles for uid in oracle.get("original_support_unit_ids", ())}
    memberships = {uid: [] for uid in wanted}
    sections, duplicates = {}, set()
    for section in structure.get("sections", ()):
        sid = section.get("section_id")
        if sid in sections:
            duplicates.add(sid)
        sections[sid] = section
        for uid in (*section.get("heading_unit_ids", ()), *section.get("body_unit_ids", ())):
            if uid in memberships:
                memberships[uid].append(sid)
    meanings = {uid: set() for uid in wanted}
    proofs = {uid: set() for uid in wanted}
    for semantic in structure.get("semantic_units", ()):
        for name, target in (("required_context_by_unit_id", meanings),
                             ("required_source_unit_ids_by_unit_id", proofs)):
            for uid, references in semantic.get(name, {}).items():
                if uid in target:
                    target[uid].update(references)
    rows, context_ids = [], set()
    for oracle in oracles:
        targets = []
        forbidden = set(oracle.get("original_forbidden_context_unit_ids", ()))
        for uid in oracle.get("original_support_unit_ids", ()):
            headings = set()
            meaning = meanings[uid]
            physical = proofs[uid]
            paths = []
            for sid in memberships[uid]:
                if sid is None:
                    paths.append({"sections": [], "ancestry_path_complete": False,
                                  "reason": "NAMED_SECTION_UNAVAILABLE"})
                    continue
                path, visited, cursor = [], set(), sid
                complete = True
                while cursor is not None:
                    if cursor in visited or cursor in duplicates or cursor not in sections:
                        complete = False
                        break
                    visited.add(cursor)
                    section = sections[cursor]
                    heads = list(section.get("heading_unit_ids", ()))
                    headings.update(heads)
                    path.append({"section_id": cursor, "parent_id": section.get("parent_id"),
                                 "heading_unit_ids": heads, "basis": section.get("basis", [])})
                    cursor = section.get("parent_id")
                paths.append({"sections": path, "ancestry_path_complete": complete})
            diagnostics = [{"code": diagnostic.get("code"), "unit_ids": [uid]}
                           for diagnostic in structure.get("diagnostics", ())
                           if uid in diagnostic.get("unit_ids", ())]
            current = headings | meaning
            retained = current | physical
            context_ids.update(retained)
            targets.append({
                "unit_id": uid, "original_present": uid in originals,
                "section_occurrences": len(memberships[uid]), "section_paths": paths,
                "declared_context_unit_ids": sorted(current),
                "ancestor_heading_unit_ids": sorted(headings),
                "semantic_context_unit_ids": sorted(meaning),
                "physical_source_proof_unit_ids": sorted(physical),
                "forbidden_context_ids_observed": sorted(forbidden & current),
                "source_diagnostics": diagnostics,
                "unavailable_context_unit_ids": sorted(retained - originals.keys()),
            })
        rows.append({"oracle_id": oracle["oracle_id"], "support_units": targets,
                     "status": "STRUCTURE_OBSERVED_NO_ACTOR_INFERENCE"})
    return rows, context_ids


def excerpt_units_for_checkpoints(targets, context_checks, span_index, view_index, originals, *, additional_ids=()):
    """Keep exact source units for the fixed oracles and their current contexts."""
    by_span = {span["span_id"]: span for span in span_index}
    wanted = {target.get("current_original_unit_id") for target in targets}
    wanted.discard(None)
    wanted.update(additional_ids)
    wanted_context_spans = set()
    for check in context_checks:
        wanted.update(check.get("original_support_unit_ids", ()))
        wanted.update(check.get("original_forbidden_context_unit_ids", ()))
        support = set(check.get("mapped_support_span_ids", ()))
        for view in view_index:
            if support.intersection(view.get("support_evidence_ids", ())):
                wanted_context_spans.update(view.get("context_evidence_ids", ()))
    untraceable = []
    for span_id in sorted(wanted_context_spans):
        span = by_span.get(span_id, {})
        members = set(span.get("direct_original_unit_ids", ()))
        members.update(row["unit_id"] for row in span.get("native_members", ()) if row.get("valid_slice"))
        if not members:
            untraceable.append(span_id)
        wanted.update(members)
    rows = []
    for unit_id in sorted(wanted):
        unit = originals.get(unit_id)
        if unit is None:
            continue
        rows.append({
            "unit_id": unit.unit_id, "source_id": unit.source_id,
            "locator": unit.coordinates.locator(), "source_role": unit.source_role,
            "text_sha256": sha256(unit.raw_text.encode()).hexdigest(), "raw_text": unit.raw_text,
        })
    return rows, {
        "requested_original_ids": len(wanted), "retained_original_ids": len(rows),
        "unavailable_original_ids": sorted(wanted - originals.keys()),
        "untraceable_current_context_span_ids": untraceable,
        "scope": "Fixed source checkpoints and their current selected contexts, not the full document.",
    }


def selected_members(span):
    """Recompute native member slices using the carrier's declared coordinates."""
    native = (span.get("structured_value") or {}).get("native_range") or {}
    result = []
    origin = span["coordinates"].get("char_start") or 0
    for member in native.get("members", []):
        start = member.get("view_char_start")
        end = member.get("view_char_end")
        if not isinstance(start, int) or not isinstance(end, int):
            result.append({"unit_id": member.get("unit_id"), "valid_slice": False})
            continue
        start, end = start - origin, end - origin
        valid = 0 <= start < end <= len(span["raw_text"])
        actual = (
            sha256(span["raw_text"][start:end].encode()).hexdigest() if valid else None
        )
        result.append(
            {
                "unit_id": member.get("unit_id"),
                "locator": member.get("locator"),
                "text_sha256": member.get("text_sha256"),
                "actual_slice_sha256": actual,
                "valid_slice": valid and actual == member.get("text_sha256"),
            }
        )
    return result


def execute(case, *, checkpoint_sink=None):
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.source_catalog.narrative_pdf_reading import (
        PdfReading,
        NativePdfBackend,
    )
    from company_wiki.source_catalog import narrative_reading
    from company_wiki.source_catalog import source_reader as source_reader_module

    config = load_catalog_config(ROOT / case["catalog_config"])
    database = config.database_path
    db_paths = [database, Path(str(database) + "-wal"), Path(str(database) + "-shm")]
    before = {str(p): file_state(p) for p in db_paths}
    runtime = runtime_state()
    deadline = time.monotonic() + case.get("max_seconds", 90)

    def checkpoint():
        if time.monotonic() > deadline:
            raise TimeoutError("source acceptance checkpoint exceeded")

    def no_store(_):
        raise AssertionError("read-only acceptance must never create CatalogStore")

    SourceCatalog.store = property(no_store)
    original = narrative_reading._candidates
    original_read = source_reader_module._read_verified_bytes
    original_files_before = {}
    captured = {}

    def observe_original_read(path, **kwargs):
        # Observe only paths already resolved by the storage owner; no test-side
        # root selection and no alternate original are introduced.
        if str(path) not in original_files_before:
            original_files_before[str(path)] = file_state(path)
            record["original_files_before"] = dict(original_files_before)
            if checkpoint_sink is not None:
                checkpoint_sink(record, "ORIGINAL_BEFORE_OPEN")
        return original_read(path, **kwargs)

    def capture(parsed, pipeline, **kwargs):
        result = original(parsed, pipeline, **kwargs)
        original_units = {unit.unit_id: unit for unit in parsed.units}
        structure_checks, structure_ids = structure_context_checkpoints(
            case.get("context_oracles", ()), pipeline.get("structure", {}), original_units
        )
        captured.update(
            parsed=parsed,
            pipeline=pipeline,
            session=(kwargs.get("_session_state") or {}).get("session"),
            eligible_packages=result[2],
            original_units=original_units,
            structure_context_checks=structure_checks,
            structure_context_ids=structure_ids,
        )
        return result

    narrative_reading._candidates = capture
    source_reader_module._read_verified_bytes = observe_original_read
    catalog = SourceCatalog(config)
    record = {
        "schema_version": "architecture-real-source-case/3",
        "case_id": case["case_id"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_posts": 0,
        "downloads": 0,
        "raw_copies": 0,
        "source_select_calls": 1,
        "database_before": before,
        "runtime_before": runtime,
        "source_ref": case["request"]["source_ref"],
        "status": "RUNNING",
    }
    if checkpoint_sink is not None:
        checkpoint_sink(record, "SOURCE_READY")
    start = time.monotonic()
    try:
        payload = SourceRevisionEventPayload.from_dict(case["request"])
        handler = NarrativeSelectHandler(
            reader=SourceVersionReader(catalog),
            selector_version="0.9.0",
            pdf_reading=PdfReading(NativePdfBackend()),
        )
        raw = handler.select_source(payload, checkpoint=checkpoint).to_dict()
        spans = raw["evidence_spans"]
        by_id = {s["span_id"]: s for s in spans}
        context = raw.get("reading_context") or {}
        views = [
            v for g in context.get("groups", []) for v in g.get("citation_views", [])
        ]
        members = {s["span_id"]: selected_members(s) for s in spans}
        missing = {
            i
            for v in views
            for i in (
                *v.get("support_evidence_ids", []),
                *v.get("context_evidence_ids", []),
            )
            if i not in by_id
        }
        originals = captured.get("original_units", {})
        original_lookup = {}
        for unit in originals.values():
            key = (
                unit.coordinates.locator(),
                sha256(unit.raw_text.encode()).hexdigest(),
            )
            original_lookup.setdefault(key, []).append(unit.unit_id)
        span_index = [
            {
                "span_id": span["span_id"],
                "locator": span["locator"],
                "text_sha256": sha256(span["raw_text"].encode()).hexdigest(),
                "raw_text": span["raw_text"],
                "native_members": [
                    {
                        k: m.get(k)
                        for k in ("unit_id", "locator", "text_sha256", "valid_slice")
                    }
                    for m in members[span["span_id"]]
                ],
                "direct_original_unit_ids": original_lookup.get(
                    (span["locator"], sha256(span["raw_text"].encode()).hexdigest()), []
                ),
            }
            for span in spans
        ]
        view_index = [
            {
                "group_id": group.get("group_id"),
                "view_id": view.get("view_id") or f"group-{group_index}/view-{i}",
                "support_evidence_ids": view.get("support_evidence_ids", []),
                "context_evidence_ids": view.get("context_evidence_ids", []),
                "group_anchor_unit_ids": group.get("anchor_unit_ids"),
                "group_anchors_exposed": "anchor_unit_ids" in group,
                "reading_support_use": view.get("reading_support_use"),
                "reading_support_reason": view.get("reading_support_reason"),
            }
            for group_index, group in enumerate(context.get("groups", []))
            for i, view in enumerate(group.get("citation_views", []))
        ]
        targets = []
        for target in case.get("required_units", []):
            direct = [
                s["span_id"]
                for s in spans
                if sha256(s["raw_text"].encode()).hexdigest() == target["text_sha256"]
            ]
            carriers = [
                sid
                for sid, rows in members.items()
                if any(
                    m.get("text_sha256") == target["text_sha256"] and m["valid_slice"]
                    for m in rows
                )
            ]
            original_unit = originals.get(target.get("unit_id"))
            if original_unit is None:
                original_unit = next(
                    (
                        u
                        for u in originals.values()
                        if sha256(u.raw_text.encode()).hexdigest()
                        == target["text_sha256"]
                    ),
                    None,
                )
            cached = {}
            session = captured.get("session")
            if session is not None and original_unit is not None:
                origin = (
                    captured.get("pipeline", {})
                    .get("_carrier_origins", {})
                    .get(original_unit.unit_id, original_unit.unit_id)
                )
                owner = session.owner_for(origin)
                cached = {
                    "owner": owner,
                    "fact": jsonable(session.facts.get(owner)),
                    "passage": jsonable(session.passages.get(owner)),
                    "profile": captured["pipeline"]
                    .get("reading_plan", {})
                    .get("unit_profiles", {})
                    .get(origin),
                }
            targets.append(
                {
                    **target,
                    "parsed_exact_original": None
                    if not captured.get("parsed")
                    else original_unit is not None,
                    "current_original_unit_id": None if original_unit is None else original_unit.unit_id,
                    "represented": bool(direct or carriers),
                    "direct_span_ids": direct,
                    "native_carrier_ids": carriers,
                }
            )
            targets[-1]["prepared_cache_only_no_reanalysis"] = cached
        context_checks = [
            compare_context_original_members(oracle, span_index, view_index)
            for oracle in case.get("context_oracles", [])
        ]
        structure_checks = captured.get("structure_context_checks", [])
        structure_context_ids = captured.get("structure_context_ids", ())
        excerpts, excerpt_coverage = excerpt_units_for_checkpoints(
            targets, context_checks, span_index, view_index, originals, additional_ids=structure_context_ids
        )
        groups_by_evidence = {}
        for group in context.get("groups", []):
            groups_by_evidence.setdefault(frozenset(group.get("evidence_ids", [])), []).append(group.get("group_id"))
        session = captured.get("session")
        record.update(
            selection=raw["selection"],
            seconds=time.monotonic() - start,
            selected_span_count=len(spans),
            required_units=targets,
            context_original_member_checks=context_checks,
            source_ref=case["request"]["source_ref"],
            span_original_member_index=span_index,
            citation_view_index=view_index,
            source_excerpt_units=excerpts,
            source_excerpt_coverage=excerpt_coverage,
            source_structure_context_checks=structure_checks,
            captured_pipeline_field_names=sorted(captured.get("pipeline", {})),
            source_package_index=[
                {
                    "package_id": package.get("package_id"),
                    "kind": package.get("kind"),
                    "anchor_unit_ids": package.get("anchor_unit_ids", []),
                    "member_unit_ids": package.get("member_unit_ids", []),
                    "required_context_unit_ids": package.get("required_context_unit_ids", []),
                    "matched_group_ids": groups_by_evidence.get(frozenset(
                            captured["pipeline"]["selected_span_ids"][uid]
                            for uid in (
                                *package.get("member_unit_ids", []),
                                *package.get("required_context_unit_ids", []),
                            )
                            if uid in captured["pipeline"]["selected_span_ids"]
                        ), []),
                }
                for package in captured.get("eligible_packages", [])
                if all(
                    uid in captured["pipeline"]["selected_span_ids"]
                    for uid in (
                        *package.get("member_unit_ids", []),
                        *package.get("required_context_unit_ids", []),
                    )
                )
            ],
            reading_context_observations={
                k: v for k, v in context.items()
                if k not in {"groups", "business_facets", "reading_policies"}
            },
            parsed_units=None if not captured.get("parsed") else len(originals),
            native_member_count=sum(map(len, members.values())),
            invalid_native_members=[
                m for rows in members.values() for m in rows if not m["valid_slice"]
            ],
            closure={
                "groups": len(context.get("groups", [])),
                "views": len(views),
                "missing_selected_ids": sorted(missing),
                "all_source_ids_match": all(
                    s["source_id"] == payload.source_ref.source_id for s in spans
                ),
                "selected_material_replayed_by_handler": True,
            },
            session_work=None
            if session is None
            else {
                "used": session.work_budget.used,
                "limit": session.work_budget.max_work_units,
                "exhausted": session.work_budget.exhausted,
                "complete": session.complete,
            },
            selection_material_sha256=sha256(
                json.dumps(
                    spans, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode()
            ).hexdigest(),
            decision_digest=(raw.get("reading_dependencies") or {}).get(
                "decision_digest"
            ),
            selection_diagnostics=[
                {k: v for k, v in d.items() if k not in {"targets", "samples", "text"}}
                for d in context.get("selection_diagnostics", [])
            ],
            status="OBSERVED_NOT_COMPANY_OR_ECONOMIC_ACCEPTANCE",
        )
        controls = []
        from company_wiki.source_catalog.narrative_business_policy import (
            prepare_reading_business_assessment,
        )

        for control in case.get("synthetic_controls", []):
            observed = prepare_reading_business_assessment(
                control["text"], {"relations": []}
            )
            controls.append(
                {
                    **control,
                    "actual_readable": observed.passage.relevant,
                    "passage": jsonable(observed.passage),
                    "passed": observed.passage.relevant == control["expected_readable"],
                }
            )
        record["synthetic_controls_not_real_source_coverage"] = controls
        record["checkpoint_gaps"] = {
            "unrepresented_required_units": [
                t["unit_id"] for t in targets if not t["represented"]
            ],
            "previous_bad_context_pairs": [
                o["oracle_id"]
                for o in context_checks
                if o["previous_bad_context_observed"]
            ],
        }
        assert catalog._store is None
    except Exception as exc:
        record.update(
            status="FAILED",
            error_type=type(exc).__name__,
            error=str(exc)[:1000],
            seconds=time.monotonic() - start,
        )
    finally:
        catalog.close()
        narrative_reading._candidates = original
        source_reader_module._read_verified_bytes = original_read
        record["original_files_before"] = original_files_before
        record["original_files_after"] = {
            p: file_state(p) for p in original_files_before
        }
        record["original_files_comparison"] = compare_storage_observations(
            original_files_before, record["original_files_after"]
        )
        record["original_files_unchanged"] = record["original_files_comparison"][
            "all_supplied_files_content_unchanged"
        ]
        record["database_after"] = {str(p): file_state(p) for p in db_paths}
        record["database_comparison"] = compare_storage_observations(
            before, record["database_after"]
        )
        record["database_unchanged"] = record["database_comparison"][
            "all_supplied_files_content_unchanged"
        ]
        record["runtime_after"] = runtime_state()
        record["runtime_unchanged"] = record["runtime_after"] == runtime
    return jsonable(record)


def main(*, default_manifest=None, output_root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=default_manifest, required=default_manifest is None)
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    output_root = output.parent if output_root is None else output_root.resolve()
    output.relative_to(output_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError("receipt already exists; choose a fresh output")
    checkpoint_path = output.with_suffix(output.suffix + ".checkpoint.json")
    if checkpoint_path.exists():
        raise FileExistsError("checkpoint already exists; choose a fresh output")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    case = next(c for c in manifest["cases"] if c["case_id"] == args.case)
    case = {
        **case,
        "synthetic_controls": manifest.get(
            "synthetic_controls_are_not_real_samples", []
        ),
    }
    if args.worker:
        # Validate the observer before the source work, then persist checkpoints
        # independently of final (potentially much larger) result encoding.
        encode_receipt({"status": "RUNNING", "case_id": args.case})
        owned = {}
        observer_before = observer_state()

        def persist_checkpoint(value, phase):
            atomic_owned_write(checkpoint_path, encode_receipt(
                observation_checkpoint(value, phase)
            ), owned, root_dir=output_root)

        persist_checkpoint({"case_id": args.case, "status": "RUNNING", "source_ref": case["request"]["source_ref"],
                            "observer_before": observer_before}, "RUN_START")
        try:
            record = execute(case, checkpoint_sink=persist_checkpoint)
        except Exception as exc:
            record = {
                "case_id": args.case, "status": "FAILED", "error_type": type(exc).__name__,
                "observation_execution_failed": True, "model_posts": 0, "downloads": 0,
                "execution_checkpoint": json.loads(checkpoint_path.read_bytes()),
                "database_unchanged": None, "original_files_unchanged": None, "runtime_unchanged": None,
            }
        record["observer_before"] = observer_before
        record["observer_after"] = observer_state()
        record["observer_comparison"] = compare_storage_observations(
            observer_before, record["observer_after"]
        )
        record["observer_unchanged"] = record["observer_comparison"][
            "all_supplied_files_content_unchanged"
        ]
        persist_checkpoint(record, "RESULT_READY")
        try:
            encoded = encode_receipt(record)
        except Exception as exc:
            encoded = (json.dumps({
                "status": "OBSERVATION_INCOMPLETE", "source_status": record.get("status"),
                "encoding_error": {"code": "ENCODER_FAILED", "type": type(exc).__name__},
                "checkpoint_file": checkpoint_path.name,
            }, separators=(",", ":")) + "\n").encode()
        atomic_owned_write(output, encoded, owned, root_dir=output_root)
        saved = json.loads(encoded)
        if saved.get("status") != "OBSERVATION_INCOMPLETE":
            if owned.get(checkpoint_path) != sha256(checkpoint_path.read_bytes()).hexdigest():
                raise RuntimeError("observation checkpoint changed before cleanup")
            checkpoint_path.unlink()
        print(
            json.dumps(
                {
                    "case_id": args.case,
                    "status": saved.get("status"),
                    "source_status": record["status"],
                    "receipt_bytes": len(encoded),
                    "seconds": record.get("seconds"),
                    "represented": [
                        t["represented"] for t in record.get("required_units", [])
                    ],
                    "database_unchanged": record.get("database_unchanged"),
                    "original_files_unchanged": record.get("original_files_unchanged"),
                    "runtime_unchanged": record.get("runtime_unchanged"),
                    "observer_unchanged": record.get("observer_unchanged"),
                },
                ensure_ascii=False,
            )
        )
        if (
            record["status"] == "FAILED" or saved.get("status") == "OBSERVATION_INCOMPLETE"
            or not record.get("database_unchanged")
            or not record.get("original_files_unchanged")
            or not record.get("runtime_unchanged")
            or not record.get("observer_unchanged")
        ):
            raise SystemExit(2)
        return
    command = [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-m",
        "tools.source_case_runner",
        "--manifest",
        str(args.manifest.resolve()),
        "--case",
        args.case,
        "--output",
        str(output),
        "--worker",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=case.get("max_seconds", 90),
            check=False,
        )
        print(result.stdout[-5000:])
        print(result.stderr[-2000:], file=sys.stderr)
        raise SystemExit(result.returncode)
    except subprocess.TimeoutExpired:
        # A child may have committed its result immediately before the timeout.
        # Never overwrite that evidence. Otherwise retain the durable checkpoint.
        if not output.exists():
            try:
                atomic_owned_write(output, (json.dumps({
                "case_id": args.case, "status": "PARENT_TIMEOUT",
                "seconds_limit": case.get("max_seconds", 90),
                "model_posts": 0, "downloads": 0,
                "checkpoint_file": checkpoint_path.name if checkpoint_path.exists() else None,
                "checkpoint_sha256": sha256(checkpoint_path.read_bytes()).hexdigest() if checkpoint_path.exists() else None,
                "limitation": "No completed source/after-state proof; inspect checkpoint without repeating the batch",
                }, separators=(",", ":")) + "\n").encode(), {}, root_dir=output_root)
            except FileExistsError:
                # A child/other publisher won after the parent's existence
                # check. Keep its result; this invocation remains a timeout.
                if not output.exists():
                    raise
        print("source observer parent timeout; existing receipt/checkpoint preserved", file=sys.stderr)
        raise SystemExit(124) from None


if __name__ == "__main__":
    main()
