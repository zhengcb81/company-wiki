"""Test-side pre-reservation observer; production code remains unchanged."""

from __future__ import annotations

import gzip
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import sys
from urllib.parse import urlsplit

INSTALLED = False
_pending: dict | None = None


def capture_selection_checkpoint(selected, directory: Path, run_id: str) -> dict:
    """Retain source decisions on refusal without rerunning PDF extraction.

    The model view intentionally excludes diagnostic execution metadata. Save
    the typed selection before its temporary lake is cleaned, never credentials,
    provider reasoning, or a second original PDF.
    """
    path = directory / (run_id + '.selection.json.gz')
    if path.parent.resolve() != directory.resolve():
        raise ValueError('OBSERVED_SELECTION_PATH_INVALID')
    body = json.dumps(selected.to_dict(), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode()
    if path.exists():
        if gzip.decompress(path.read_bytes()) != body:
            raise ValueError('OBSERVED_SELECTION_CHANGED')
    else:
        path.write_bytes(gzip.compress(body, mtime=0))
    return {'file': path.name, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


def _oracle_reading_context(context):
    """Project typed production context to the oracle's membership-only schema.

    The v3 selection contract already validates semantic group identities,
    citation partitions and source proofs. The older independent support
    oracle consumes only ordered evidence membership and group kind, so give
    it local IDs derived from membership instead of teaching the oracle a
    second copy of the production v3 identity algorithm.
    """
    if context is None:
        return None
    schema = context.get("schema_version")
    if schema in {"du-production-reading/1", "du-production-reading/2"}:
        return context
    if schema != "du-production-reading/3":
        raise ValueError("observer requires a validated production reading context")
    groups = []
    for row in context.get("groups", ()):
        evidence_ids = list(row.get("evidence_ids", ()))
        if not evidence_ids or any(not isinstance(value, str) for value in evidence_ids):
            raise ValueError("observer requires nonempty validated reading groups")
        digest = hashlib.sha256(
            json.dumps(evidence_ids, separators=(",", ":")).encode()
        ).hexdigest()
        groups.append({
            "group_id": "urn:company-wiki:reading-group:sha256:" + digest,
            "evidence_ids": evidence_ids,
            "kind": row["kind"],
            "section_role": row["section_role"],
        })
    return {"schema_version": "du-production-reading/2", "groups": groups}


def _append(path: str, value: dict) -> None:
    with Path(path).open("a", encoding="utf8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _sent_task_gold(required, selected, view, sent_keys):
    """Observe existing compiler closures; never infer new source groups."""
    from tools.document_understanding_benchmark.closed_group_support import score_facts

    spans = {span.span_id: span for span in selected.evidence_spans}
    groups = {group["group_id"]: group for group in selected.reading_context["groups"]}
    witnesses = {fact["id"]: [] for fact in required}
    for task in view.plan.tasks:
        context = None
        if task.origin_group_id is not None:
            group = groups[task.origin_group_id]
            assert tuple(group["evidence_ids"]) == task.member_ids
            context = _oracle_reading_context({
                "schema_version": selected.reading_context["schema_version"],
                "groups": [group],
            })
        scores = score_facts(required,
            evidence_spans=tuple(spans[sid] for sid in task.member_ids),
            reading_context=context, source_id=selected.source_ref.source_id)
        for fact in scores:
            if fact["supported"]:
                witnesses[fact["id"]].append(task.key)
    facts = [{"id": fact["id"],
              "supported": bool(keys := [key for key in witnesses[fact["id"]] if key in sent_keys]),
              "supported_task_keys": keys}
             for fact in required]
    return {
        "scope": "source_support_in_current_request_tasks",
        "request_scope": "full_request" if sent_keys == view.admitted_task_keys else "repair_subset",
        "sent_task_keys": [task.key for task in view.plan.tasks if task.key in sent_keys],
        "facts": facts, "required_count": len(facts),
        "supported_count": sum(fact["supported"] for fact in facts),
        "missing_ids": [fact["id"] for fact in facts if not fact["supported"]],
        "not_sent_ids": [fact["id"] for fact in facts
                         if not fact["supported"] and witnesses[fact["id"]]],
        "summary_claim_coverage": "not_evaluated",
    }


def gold_admission_missing(observation, *, attempt_no):
    """Require full source-task gold on the first request, observe repair subsets."""
    sent = observation.get("sent_tasks")
    if sent is None:
        return observation["missing_ids"]
    if sent["request_scope"] == "repair_subset":
        if attempt_no <= 1:
            raise ValueError("repair subset cannot be an initial request")
        return []  # Unsent completed tasks need not be sent again for a repair.
    return sent["missing_ids"]


def gold_observation(gold: dict, selected, envelope: dict) -> dict:
    from company_wiki.automation.narrative_model import _group_mapping

    # This is the same test oracle used by ROOT's same-source replay. The
    # observer only adapts actual model aliases; it has no support/normalizing
    # rules of its own and cannot turn a foreign mapping into source proof.
    project = str(Path(__file__).resolve().parents[2])
    if project not in sys.path:
        sys.path.insert(0, project)
    from tools.document_understanding_benchmark.closed_group_support import score_facts

    view = None
    sent_keys = frozenset()
    if envelope["schema_version"] in {"narrative-model-request/5", "narrative-model-request/6"}:
        from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view

        # Observe exactly the current compiler's material, including shared
        # references and task-local support/context. Only after byte-equivalent
        # material proof may the existing native-source oracle score selection.
        max_claims = max(1, len(selected.evidence_spans) * 2) if envelope["schema_version"] == "narrative-model-request/6" else 20
        view = compile_scoped_model_view(selected, max_claims=max_claims)
        full_material = view.to_model_dict()
        sent_keys = frozenset(row["key"] for row in envelope["material"]["tasks"])
        if envelope["material"] != full_material:
            # A coverage-repair retry sends only the still-uncovered tasks; its
            # material must equal the same compiler restricted to those keys.
            from dataclasses import replace

            full_keys = {row["key"] for row in full_material["tasks"]}
            assert sent_keys and sent_keys < full_keys
            assert envelope["material"] == replace(
                view, visible_keys=sent_keys).to_model_dict()
        assert view.plan.evidence_order == tuple(span.span_id for span in selected.evidence_spans)
        rows = [[span.span_id, span.raw_text] for span in selected.evidence_spans]
        actual_groups = _group_mapping(selected)
    else:
        rows = envelope["evidence"]
        columns = envelope["evidence_columns"]
        assert columns == ["id", "raw_text", "source_role", "quality_flags"]
        assert all(isinstance(row, list) and 2 <= len(row) <= 4 for row in rows)
        aliases = [row[0] for row in rows]
        assert len(aliases) == len(set(aliases)) == len(selected.evidence_spans)
        assert aliases == [f"e{index}" for index in range(1, len(rows) + 1)]
        assert [row[1] for row in rows] == [
            span.raw_text for span in selected.evidence_spans
        ]
        for row, span in zip(rows, selected.evidence_spans, strict=True):
            role = row[2] if len(row) > 2 else envelope["default_source_role"]
            flags = row[3] if len(row) > 3 else envelope["default_quality_flags"]
            actual_role = span.structured_value.get("source_role", "unknown")
            actual_role = actual_role if isinstance(actual_role, str) else "unknown"
            assert role == actual_role and flags == list(span.quality_flags)
        alias_by_span = {span.span_id: alias for alias, span in zip(aliases, selected.evidence_spans, strict=True)}
        actual_groups = _group_mapping(selected)
        if envelope["schema_version"] == "narrative-model-request/4":
            assert "evidence_groups" not in envelope and "evidence_group_columns" not in envelope
            assert envelope["citation_unit_columns"] == ["id", "evidence_ids", "support_evidence_ids"]
            units = envelope["citation_units"]
            assert len({row[0] for row in units}) == len(units)
            assert not {row[0] for row in units}.intersection(aliases)
            assert all(row[1] and len(row[1]) == len(set(row[1])) and set(row[1]) <= set(aliases) for row in units)
            assert all(row[2] and len(row[2]) == len(set(row[2])) and set(row[2]) <= set(row[1]) for row in units)
            assert {tuple(alias_by_span[sid] for sid in members) for _, members in actual_groups.values()} <= {
                tuple(row[1]) for row in units}
            assert {group["id"] for group in envelope["reading_strategy"]["groups"]} <= {row[0] for row in units}
        else:
            groups = envelope["evidence_groups"]
            assert envelope["evidence_group_columns"] == ["id", "evidence_ids"]
            assert len({row[0] for row in groups}) == len(groups)
            assert all(len(row[1]) == len(set(row[1])) and set(row[1]) <= set(aliases) for row in groups)
            assert groups == [[alias, [alias_by_span[sid] for sid in members]]
                for alias, (_, members) in actual_groups.items()]
    context = _oracle_reading_context(selected.reading_context)
    required = [fact for fact in gold["facts"] if fact.get("target_kind") == "required_business"]
    scored = score_facts(required, evidence_spans=selected.evidence_spans,
        reading_context=context, source_id=selected.source_ref.source_id)
    if context is None and actual_groups:
        # Legacy selection is ranked; selected_summary_input sorts each actual
        # model group by native locator order. Evaluate that exact sent closure
        # with the same oracle and its own local positions. Do not masquerade
        # legacy ordering as the new production-context contract, sort citations
        # into selection rank, or borrow new native continuity proof.
        by_id = {span.span_id: span for span in selected.evidence_spans}
        for _, members in actual_groups.values():
            ids = list(members)
            digest = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
            actual_context = {"schema_version": "du-production-reading/1", "groups": [{
                "group_id": "urn:company-wiki:reading-group:sha256:" + digest,
                "evidence_ids": ids, "kind": "legacy_model_context", "section_role": "unknown"}]}
            observed = score_facts(required, evidence_spans=tuple(by_id[sid] for sid in ids),
                reading_context=actual_context, source_id=selected.source_ref.source_id)
            scored = [{**base, "supported": base["supported"] or group["supported"]}
                for base, group in zip(scored, observed, strict=True)]
    facts = [{**result, "importance": original.get("importance")}
        for original, result in zip(required, scored, strict=True)]
    observation = {
        "scope": "full_selected_source_availability",
        "facts": facts,
        "required_count": len(facts),
        "supported_count": sum(fact["supported"] for fact in facts),
        "missing_ids": [fact["id"] for fact in facts if not fact["supported"]],
        "evidence_count": len(rows),
        "groups": len(actual_groups),
        "citation_units": len(envelope.get("citation_units", [])),
        "evidence_characters": sum(len(row[1]) for row in rows),
        "unique_aliases": True,
        "quality_oracle": "tools.document_understanding_benchmark.closed_group_support.score_facts",
    }
    observation["full_selection"] = {key: observation[key] for key in (
        "scope", "facts", "required_count", "supported_count", "missing_ids")}
    if view is not None:
        observation["sent_tasks"] = _sent_task_gold(required, selected, view, sent_keys)
    return observation


def install() -> None:
    global INSTALLED
    if INSTALLED:
        return
    config_path = os.environ.get("CWP_PHASE_C_OBSERVER")
    if not config_path:
        raise RuntimeError("PHASE_C_OBSERVER_CONFIG_MISSING")
    config = json.loads(Path(config_path).read_text(encoding="utf8"))
    if config.get("hold_activation"):
        # Test-only post-payment boundary: the normal worker has already
        # persisted its verified output and outbox before activation is called.
        from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
        from company_wiki.source_catalog.lock import CatalogOperationLockedError

        def hold_activation(*args, **kwargs):
            _append(config["events"], {
                "event": "activation_held", "run_id": config["activation_run_id"],
                "test_only": True,
            })
            print("phase_c_activation_held=1", file=sys.stderr)
            raise CatalogOperationLockedError("phase C test activation boundary")

        NarrativeArtifactStore.activate = hold_activation
    if os.environ.get("CWP_PHASE_C_NO_NETWORK") == "1":
        original_connect = socket.socket.connect

        def offline_connect(sock, address):
            if address[0] not in {"127.0.0.1", "::1"}:
                raise RuntimeError("PHASE_C_READONLY_CONSUMER_NETWORK_FORBIDDEN")
            return original_connect(sock, address)

        socket.socket.connect = offline_connect
    from company_wiki.automation.models import (
        HandlerMetrics,
        HandlerOutcome,
        canonical_json_hash,
    )
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from company_wiki.automation.narrative_model_caller import (
        BudgetedNarrativeCaller,
        NarrativeBudgetCallError,
    )
    from company_wiki.automation.narrative_selection_generation import (
        reading_material_sha256,
    )

    original_generate = BudgetedNarrativeCaller.generate

    def generate(caller, context, request):
        global _pending

        def refuse(code):
            _append(
                config["events"],
                {
                    "event": "pre_reservation_refused",
                    "run_id": caller._run_id,
                    "attempt_id": context.attempt.attempt_id,
                    "code": code,
                    "reserved": False,
                    "POST": False,
                },
            )
            raise NarrativeBudgetCallError(
                code,
                HandlerOutcome.TERMINAL_FAILURE,
                HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
            )

        selected = NarrativeSelectResult.from_dict(
            context.dependency_results["source.narrative_select"].result
        )
        assert selected.source_ref.content_sha256 == config["source_sha256"]
        body = caller._model.request_bytes(request)
        http = json.loads(body)
        envelope = json.loads(http["messages"][1]["content"])
        final = caller._store.final_generations(caller._run_id).get(
            selected.subject.item_key
        )
        expected_request = build_model_request(
            selected,
            reading_projection_version=final.get("reading_model_projection")
            if final is not None else None,
        ).with_output_budget(caller._model.max_output_tokens)
        if http["messages"][1]["content"] != expected_request.data_json:
            # A coverage-repair retry sends only the still-uncovered tasks;
            # its material must be a strict subset of the full request.
            expected_view = json.loads(expected_request.data_json)["material"]
            actual_view = envelope["material"]
            expected_tasks = {row["key"] for row in expected_view["tasks"]}
            actual_tasks = {row["key"] for row in actual_view["tasks"]}
            assert context.attempt.attempt_no > 1
            assert actual_tasks and actual_tasks < expected_tasks
            assert actual_view["schema_version"] == expected_view["schema_version"]
        expected = config["model_options"]
        token_field = expected["output_token_field"]
        assert (
            http["model"] == expected["model_id"]
            and http[token_field] == expected["max_output_tokens"]
        )
        assert http.get("temperature") == expected.get("temperature")
        assert http.get("reasoning_split") == expected.get("reasoning_split")
        assert http.get("reasoning_effort") == expected.get("reasoning_effort")
        assert http.get("thinking") == (
            {"type": expected["thinking"]}
            if expected.get("thinking") is not None
            else None
        )
        endpoint = urlsplit(expected["endpoint"])
        assert (
            caller._model._scheme,
            caller._model._host,
            caller._model._port,
            caller._model._path,
        ) == (endpoint.scheme, endpoint.hostname, endpoint.port, endpoint.path)
        run = caller._store.get_run(caller._run_id)
        assert run is not None and run.model_id == http["model"]
        version = selected.selector.version
        if version == "0.9.0":
            assert final is not None
            assert final["selection_generation"][
                "material_sha256"
            ] == reading_material_sha256(selected)
            assert final["reading_dependencies"]["status"] == "complete"
        gold_bytes = Path(config["gold"]).read_bytes()
        assert hashlib.sha256(gold_bytes).hexdigest() == config["gold_sha256"]
        gold = json.loads(gold_bytes)
        assert gold["source_sha256"] == selected.source_ref.content_sha256
        observation = gold_observation(gold, selected, envelope)
        selection_checkpoint = capture_selection_checkpoint(
            selected, Path(config['materials']), caller._run_id)
        event = {
            "event": "pre_reservation_material",
            "run_id": caller._run_id,
            "attempt_id": context.attempt.attempt_id,
            "selector_version": version,
            "input_sha256": request.input_sha256,
            "reading_model_projection": final.get("reading_model_projection")
            if final is not None else None,
            "http_body_sha256": hashlib.sha256(body).hexdigest(),
            "http_body_bytes": len(body),
            "material_sha256": reading_material_sha256(selected),
            "final_generation_sha256": canonical_json_hash(final)
            if final is not None
            else None,
            "gold": observation,
            "selection_checkpoint": selection_checkpoint,
            "mode": config["mode"],
        }
        _append(config["events"], event)
        material_file = Path(config["materials"]) / (caller._run_id + ".input.json.gz")
        if not material_file.exists():
            with gzip.open(material_file, "wb") as stream:
                stream.write(body)
        if version == "0.9.0" and gold_admission_missing(
            observation, attempt_no=context.attempt.attempt_no
        ):
            refuse("PHASE_C_GOLD_SUPPORT_MISSING")
        if config.get("forbid_post"):
            refuse("PHASE_C_CACHE_WOULD_GENERATE")
        reservations = caller._store.reservations_for_run(caller._run_id)
        if reservations and not (
            len(reservations) == 1
            and reservations[0].job_id == context.job.job_id
            and context.attempt.attempt_no > 1
        ):
            refuse("PHASE_C_PRIOR_ATTEMPT_PRESENT")
        if config["mode"] == "live":
            from tools.document_understanding_benchmark.phase_c_runner import mother_totals, mother_budget_fits

            totals = mother_totals(config["metadata"], config["usage_ledger"])
            if not mother_budget_fits(totals, tokens_bound=run.max_tokens,
                                      micro_usd_bound=run.max_micro_usd):
                refuse("PHASE_C_MOTHER_BUDGET_EXCEEDED")
        _pending = {
            "run_id": caller._run_id,
            "attempt_id": context.attempt.attempt_id,
            "http_body_sha256": event["http_body_sha256"],
            "body_bytes": len(body),
            "endpoint": expected["endpoint"],
        }
        try:
            result = original_generate(caller, context, request)
            response = result[0]
            # Preserve the final only, before semantic decoding. A transport-
            # complete reply may still fail the production summary contract.
            # No provider envelope, reasoning content or credentials are saved.
            response_path = Path(config["materials"]) / (
                caller._run_id + "." + context.attempt.attempt_id + ".response.json.gz")
            if response_path.exists():
                if gzip.decompress(response_path.read_bytes()) != response.response_bytes:
                    raise ValueError("OBSERVED_FINAL_BYTES_CHANGED")
            else:
                with gzip.open(response_path, "wb") as stream:
                    stream.write(response.response_bytes)
            _append(config["events"], {
                "event": "model_final_observed", "run_id": caller._run_id,
                "attempt_id": context.attempt.attempt_id,
                "final_bytes": len(response.response_bytes),
                "final_sha256": response.response_sha256,
                "final_only_no_reasoning": True,
            })
            return result
        finally:
            _pending = None

    def observed_generate(caller, context, request):
        try:
            return generate(caller, context, request)
        except NarrativeBudgetCallError:
            raise
        except Exception as exc:
            location = exc.__traceback__
            while location is not None and location.tb_next is not None:
                location = location.tb_next
            _append(
                config["events"],
                {
                    "event": "observation_failure",
                    "error_type": type(exc).__name__,
                    "file": Path(location.tb_frame.f_code.co_filename).name
                    if location is not None
                    else None,
                    "line": location.tb_lineno if location is not None else None,
                    "POST": any(
                        row.get("event") == "http_post_attempt"
                        and row.get("attempt_id") == context.attempt.attempt_id
                        for row in (json.loads(line) for line in
                                    Path(config["events"]).read_text(encoding="utf8").splitlines())
                    ),
                },
            )
            raise

    BudgetedNarrativeCaller.generate = observed_generate
    original_request = http.client.HTTPConnection.request

    def http_request(conn, method, url, body=None, headers=None, **kwargs):
        if method.upper() == "POST":
            if (
                _pending is None
                or not isinstance(body, bytes)
                or hashlib.sha256(body).hexdigest() != _pending["http_body_sha256"]
            ):
                raise RuntimeError("PHASE_C_HTTP_OBSERVER_MISMATCH")
            _append(config["events"], {"event": "http_post_attempt", **_pending})
        return original_request(
            conn, method, url, body=body, headers=headers or {}, **kwargs
        )

    http.client.HTTPConnection.request = http_request
    INSTALLED = True
    _append(config["events"], {"event": "observer_installed", "pid": os.getpid()})
