"""Frozen whole-document producer used only to construct historical test artifacts."""
from __future__ import annotations
import hashlib
import html
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable
import yaml
from company_wiki.canonical_ingest import IngestService
from company_wiki.source_catalog import normalizer as _parser
from company_wiki.source_catalog.normalizer import (
    DOCUMENT_PARSE_TIMEOUT_CODE, NormalizationCancelledError,
    NormalizationTimeoutError, UnsupportedDocumentError, _Normalized,
    _manifest_from_column, compute_text_fingerprint,
)
from company_wiki.source_catalog.admission import processing_priority_sql
from company_wiki.source_catalog.artifact_handle import ARTIFACT_HANDLE_SCHEMA_VERSION
from company_wiki.source_catalog.models import CatalogConfig, NORMALIZER_VERSION, ProcessingReport
from company_wiki.source_catalog.store import CatalogStore, canonical_json, metadata_state
_NORMALIZER_NAME = "source_catalog_normalizer"
METADATA_UNREADABLE_FLAG = "metadata_unreadable"


def _failed(path: Path, reason: str) -> _Normalized:
    body = (
        "## Extraction status\n\n"
        "This source was cataloged, but the isolated parser did not complete.\n\n"
        f"- Format: `{path.suffix.lower() or '[none]'}`\n"
        "- Quality flag: `parser_failed`\n"
        f"- Reason: {html.escape(reason)}\n"
    )
    return _Normalized(
        body,
        (),
        "isolated_parser",
        "1.0.0",
        "failed",
        ("parser_failed",),
        reason,
    )



def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)



def _frontmatter(document: Any, normalized: _Normalized) -> str:
    # ZR-502: homepage identity verification — first-page text against the
    # declared title/publisher; contradiction flags the artifact for review.
    from company_wiki.source_catalog.homepage_identity import (
        assess_homepage_identity,
        homepage_identity_quality_flag,
    )
    # ZR-503: multi-entity attribution guard — full text against the
    # declared entity; multi-entity content flags for attribution, never a
    # silent single-entity pass.
    from company_wiki.source_catalog.entity_detection import (
        detect_entities,
        multi_entity_quality_flag,
    )
    # ZR-506: section / chunk / fact assertion — structural layer over the
    # flat locator stream (ZR-504/505).
    from company_wiki.source_catalog.section_chunk_fact import (
        chunk_spans,
        content_line_count,
        detect_sections,
        extract_facts,
    )
    # ZR-510: per-chunk attribution for multi-entity documents.
    from company_wiki.source_catalog.attribution import attribute_document

    # B10-3 batch 2 + B-VR-B10R2-01/-03: the parse is the single chain's reporting half, so
    # this function can tell "no metadata" apart from "metadata that could not be read".
    # Before, the sqlite3.Row branch raised JSONDecodeError out of the whole run (this is
    # called OUTSIDE normalize_catalog's per-document try) and a dict whose value was still a
    # JSON string died with AttributeError.  Degrading silently would be worse than crashing
    # in one respect - it would record an identity verdict with no evidence - so an unreadable
    # column adds a quality flag and forces the identity verdict to "unverifiable".
    raw_metadata = (
        document.get("metadata_json") if isinstance(document, dict)
        else document["metadata_json"]
    )
    if isinstance(raw_metadata, dict):
        # A dict BRANCH value may be the ALREADY-PARSED object - ZR-502's fixtures pass one,
        # and treating it as column text made every such document look "unreadable" and
        # downgraded its identity verdict (measured: three ZR-502 cases went red).  The chain
        # parses column TEXT, so a dict is taken as-is, exactly like before batch 2.
        metadata, metadata_problem = raw_metadata, None
    else:
        metadata, metadata_problem = metadata_state(raw_metadata)
    inner = metadata.get("acquisition") or metadata.get("dayu_meta") or {}
    identity = assess_homepage_identity(
        normalized.first_page_text,
        title=document["title"],
        publisher=inner.get("publisher"),
    )
    identity_verdict = str(identity["verdict"])
    identity_flag = homepage_identity_quality_flag(identity_verdict)
    flags = list(normalized.quality_flags)
    if metadata_problem is not None:
        # B-VR-B10R2-03 (P1): with no readable metadata there is nothing to verify the
        # identity against, and the homepage check still says "consistent" because the only
        # value left to compare is the title itself.  Recording that as a pass would turn
        # MISSING EVIDENCE into a green verdict, so the degradation is made visible in both
        # places a consumer looks: a quality flag and the verdict itself (fail closed).
        if METADATA_UNREADABLE_FLAG not in flags:
            flags.append(METADATA_UNREADABLE_FLAG)
        identity = {
            **identity,
            "verdict": "unverifiable",
            "metadata_problem": metadata_problem,
        }
        identity_verdict = "unverifiable"
        identity_flag = homepage_identity_quality_flag(identity_verdict)
    if identity_flag and identity_flag not in flags:
        flags.append(identity_flag)
    entity_detection = detect_entities(
        normalized.body,
        declared_entity=inner.get("canonical_entity_id") or inner.get("display_name"),
        declared_security_ids=tuple(inner.get("security_ids") or ()),
    )
    entity_verdict = str(entity_detection["verdict"])
    entity_flag = multi_entity_quality_flag(entity_verdict)
    if entity_flag and entity_flag not in flags:
        flags.append(entity_flag)
    # ZR-506: structural assertions over the rendered body — sections
    # (chapter headings), chunks (section line ranges), facts
    # ("指标名：数字+单位").  Empty results stay honest (never fabricated).
    structure_sections = detect_sections(normalized.body)
    structure_chunks = chunk_spans(
        content_line_count(normalized.body), structure_sections
    )
    structure_facts = extract_facts(normalized.body)
    document_structure = {
        "schema_version": "1.0",
        "sections": structure_sections,
        "chunk_count": len(structure_chunks),
        "facts": structure_facts,
    }
    # ZR-510: chunk attribution for multi-entity documents — the page's own
    # company phrases are the candidate set (declared first, then any other
    # phrase found), so each chunk is attributed to what it actually names;
    # single-entity documents stay concise (no key).
    chunk_attribution = None
    if entity_verdict == "multi_entity":
        # Candidate set = declared identity + page phrases, with
        # proper-substring candidates dropped (longest-first): noisy
        # fragments like "股份有限公司" must not shadow the full name.
        raw_candidates = list(
            dict.fromkeys(
                [inner.get("canonical_entity_id"), inner.get("display_name")]
                + list(entity_detection["evidence"].get("company_phrases") or [])
            )
        )
        candidates = [
            candidate
            for candidate in raw_candidates
            if candidate
            and not any(
                candidate != other
                and candidate in (other or "")
                for other in raw_candidates
            )
        ]
        chunk_attribution = attribute_document(
            normalized.body, structure_chunks, candidates
        )
    payload = {
        "schema_version": "1.0.0",
        "artifact_role": "normalized",
        "document_id": document["document_id"],
        "source_id": document["primary_source_id"],
        "source_sha256": document["content_sha256"],
        "title": document["title"],
        "document_kind": document["document_kind"],
        "published_date": document["published_date"],
        "normalization_status": normalized.status,
        "parser_name": normalized.parser_name,
        "parser_version": normalized.parser_version,
        "quality_flags": flags,
        # ZR-501: page count from the page-aware parser (None stays honest).
        "page_count": normalized.page_count,
        # ZR-502: homepage identity verdict (consistent / contradiction /
        # unverifiable) with evidence; never a fabricated pass.
        "homepage_identity": identity,
        # ZR-503: multi-entity detection verdict (single / multi_entity /
        # unverifiable) with extracted company-name phrases; multi_entity
        # flags for attribution (fail-closed, zero hardcoded names).
        "detected_entities": entity_detection,
        # ZR-506: structural assertions — sections, chunk_count, facts.
        "document_structure": document_structure,
        # ZR-510: per-chunk attribution (multi-entity documents only).
        **({"chunk_attribution": chunk_attribution} if chunk_attribution is not None else {}),
    }
    return (
        "---\n"
        + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n\n"
    )



def _stop_requested(should_stop: Any | None) -> bool:
    """`should_stop is not None and should_stop()` as one call (the BoolOp lives here)."""
    return should_stop is not None and bool(should_stop())



def _docling_sidecar_path(source_path: Path, metadata: dict[str, Any],
                          content_sha256: str, locations: Any) -> Path | None:
    """The `processed_docling` sidecar for a PDF whose dayu metadata pins the pdf hash.

    Takes the ALREADY PARSED metadata on purpose: handing the raw column to a helper would just
    move the handoff the ratchet records at the call site.  Returns None whenever the linkage
    does not apply, which is the common case.  See the call site for why this is a function and
    not an inline block (FC-1204 / S-7).
    """
    expected_pdf_sha = (metadata.get("dayu_meta") or {}).get("pdf_sha256")
    if source_path.suffix.lower() != ".pdf":
        return None
    if expected_pdf_sha != content_sha256:
        return None
    sidecar = next(
        (item for item in locations if item["role"] == "processed_docling"), None
    )
    if sidecar is None:
        return None
    possible = Path(sidecar["absolute_path"])
    if not possible.is_file():
        return None
    return possible



def _ingest_without_raising(root_path: str, manifest: Any) -> tuple[Any | None, str | None]:
    """Ingest an EMPTY parse result for a document that already failed - never raising.

    F-B10R2-MISSINGFILE family (owner instruction 2026-09-18).  Both calls sit inside
    `except` handlers, where nothing encloses them: a manifest that no longer matches the
    bytes on disk (the file was replaced after the scan) makes `IngestService.ingest` raise
    `SourceManifestMismatchError`, which escaped the handler and aborted the WHOLE
    normalization run - every document queued behind it was starved.  A handler is the one
    place where a single bad row must stay a single bad row.

    Returns ``(bundle, problem_code)``; ``problem_code`` is None on success.  The exception
    class is part of the code (``ingest_failed:SourceManifestMismatchError``) so the report
    says WHAT went wrong instead of counting an anonymous failure.
    """
    try:
        bundle = IngestService(root=Path(root_path)).ingest(
            manifest=manifest, parser_results=()
        )
    except Exception as exc:  # noqa: BLE001 - reported as a per-document outcome
        return None, f"ingest_failed:{type(exc).__name__}"
    return bundle, None



def normalize_catalog(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int | None = None,
    force: bool = False,
    progress: Callable[..., None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    parser_timeout_seconds: float = 3600,
    parser_heartbeat_interval_seconds: float = 15,
    parser_result_max_bytes: int = 268_435_456,
    retry_limit: int = 3,
    retry_backoff_seconds: int = 900,
) -> ProcessingReport:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if retry_limit < 1:
        raise ValueError("retry_limit must be >= 1")
    if retry_backoff_seconds < 0:
        raise ValueError("retry_backoff_seconds must be >= 0")
    now_epoch = time.time()
    sql = """SELECT d.*,s.content_sha256,s.byte_size,s.mime_type,
        existing.metadata_json AS normalization_metadata_json
        FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
        LEFT JOIN artifacts existing ON existing.document_id=d.document_id
        AND existing.artifact_role='normalized' AND existing.generator_name=?
        AND existing.generator_version=?"""
    params: tuple[Any, ...] = (_NORMALIZER_NAME, NORMALIZER_VERSION)
    # FC-906-c: a document without an active original_primary location cannot
    # be parsed — it used to sit at the queue head forever and fail with no
    # artifact row and no last_failed diagnostic (production: 9506/23521 docs).
    # Exclude them from the queue (in force and non-force runs alike) so real
    # documents behind them are never starved.
    sql += """ WHERE EXISTS (
            SELECT 1 FROM locations lp JOIN roots rp ON rp.root_id=lp.root_id
            WHERE lp.document_id=d.document_id AND lp.role='original_primary'
              AND lp.location_status='active')"""
    if not force:
        sql += """ AND (existing.artifact_id IS NULL OR (
            existing.status='failed'
            AND COALESCE(json_extract(existing.metadata_json,'$.terminal'),0)=0
            AND COALESCE(json_extract(existing.metadata_json,'$.next_retry_epoch'),0)<=?)
        )"""
        params += (now_epoch,)
    sql += f" ORDER BY {processing_priority_sql('d')}, d.document_id"
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    documents = store.fetchall(sql, params)
    completed = skipped = partial = unsupported = failed = 0
    failure_reasons: dict[str, int] = {}
    last_failure_code: str | None = None
    last_failed_document_id: str | None = None
    last_failed_path: str | None = None
    for document_index, document in enumerate(documents, start=1):
        if _stop_requested(should_stop):
            partial += max(0, len(documents) - document_index + 1)
            break
        source_id = document["primary_source_id"]
        # F-B10R2-MISSINGFILE family (owner instruction 2026-09-18): this per-document read was
        # unguarded, so ONE failing statement (locked database, damaged row) aborted the whole
        # run.  It is now a per-document failure like the branches below.
        try:
            locations = store.fetchall(
                """SELECT l.*,r.path AS root_path,r.priority FROM locations l JOIN roots r ON r.root_id=l.root_id
                WHERE l.document_id=? AND l.location_status='active' ORDER BY r.priority,l.relative_path""",
                (document["document_id"],),
            )
        except sqlite3.Error as exc:
            failed += 1
            last_failure_code = f"locations_read_failed:{type(exc).__name__}"
            last_failed_document_id = document["document_id"]
            last_failed_path = ""
            failure_reasons[last_failure_code] = (
                failure_reasons.get(last_failure_code, 0) + 1
            )
            continue
        primary = next(
            (
                item
                for item in locations
                if item["role"] == "original_primary" and item["source_id"] == source_id
            ),
            None,
        )
        if primary is None:
            # FC-906-c defense in depth: a document slipping past the queue
            # filter must be VISIBLE in the report (reason + id + path), not a
            # silent failure count.
            failed += 1
            last_failure_code = "no_active_primary_location"
            last_failed_document_id = document["document_id"]
            last_failed_path = ""
            failure_reasons[last_failure_code] = (
                failure_reasons.get(last_failure_code, 0) + 1
            )
            continue
        source_path = Path(primary["absolute_path"])
        # R1 / F-B10R2-MISSINGFILE: the source file may have vanished since the scan; the
        # existing check only tests whether the document has a location row, not whether the
        # file on disk still exists.  A missing file causes manifest.verify_file() inside
        # IngestService.ingest() to raise SourceManifestMismatchError, which - inside the
        # except-Exception handler below - escapes and aborts the WHOLE run (the reviewer
        # proved this with two documents, the second healthy and queued behind, still
        # starved).  The file-not-found check is the cheapest way to make this a per-document
        # outcome instead, using the same bookkeeping as the missing-location branch above.
        if not source_path.is_file():
            failed += 1
            last_failure_code = "primary_file_missing"
            last_failed_document_id = document["document_id"]
            last_failed_path = str(source_path.resolve(strict=False))
            failure_reasons["primary_file_missing"] = (
                failure_reasons.get("primary_file_missing", 0) + 1
            )
            continue
        if progress is not None:
            progress(
                current_path=str(source_path.resolve(strict=False)),
                current=document_index,
                total=len(documents),
                detail="extracting Markdown",
            )
        # B-VR-B10R4-01 (P2): the manifest parse is in the MAIN path with no enclosing try, so a
        # damaged manifest column used to abort the WHOLE run and starve every document behind
        # it.  It is now a per-document failure, recorded and skipped, exactly like the
        # missing-primary-location branch above.
        manifest, manifest_problem = _manifest_from_column(primary["manifest_json"])
        if manifest_problem is not None:
            failed += 1
            last_failure_code = manifest_problem
            last_failed_document_id = document["document_id"]
            last_failed_path = str(source_path.resolve(strict=False))
            failure_reasons[manifest_problem] = failure_reasons.get(manifest_problem, 0) + 1
            continue
        # B-VR-B10R2-01 (P0): this parse is NOT inside the per-document try below (that try
        # starts at the parser call), so `json.loads` here used to let ONE malformed column
        # abort the WHOLE normalization run.  It goes through the chain now; an unreadable
        # column simply means "no dayu/pdf linkage" for this document and the run continues.
        # The document is not silently blessed - the frontmatter records the unreadable
        # metadata as a quality flag and downgrades the identity verdict (B-VR-B10R2-03).
        #
        # FC-1204 / S-7: the BRANCHING that consumes it moved into `_docling_sidecar_path`
        # (the frozen complexity table may only ratchet DOWN, so new decision points belong in
        # a helper).  The PARSE stays here on purpose: the handoff ratchet records this
        # function as the place the column value is handed to the chain, and moving the parse
        # would only rename that site instead of converging it.
        metadata, _metadata_problem = metadata_state(document["metadata_json"])
        docling_path = _docling_sidecar_path(
            source_path, metadata, str(document["content_sha256"] or ""), locations
        )

        def parser_progress(details: dict[str, Any]) -> None:
            if progress is not None:
                progress(
                    current_path=str(source_path.resolve(strict=False)),
                    current=document_index,
                    total=len(documents),
                    **details,
                )

        failure_metadata: dict[str, Any] | None = None
        try:
            normalized = _parser._run_parser_isolated(
                source_path,
                manifest,
                docling_path,
                timeout_seconds=parser_timeout_seconds,
                heartbeat_interval_seconds=parser_heartbeat_interval_seconds,
                result_max_bytes=parser_result_max_bytes,
                temp_dir=config.catalog_dir / "parser_tmp",
                progress=parser_progress,
                should_stop=should_stop,
            )
            bundle = IngestService(root=Path(primary["root_path"])).ingest(
                manifest=manifest,
                parser_results=normalized.parser_results,
            )
        except NormalizationCancelledError:
            partial += max(0, len(documents) - document_index + 1)
            break
        except UnsupportedDocumentError as exc:
            normalized = _parser._unsupported(source_path, str(exc)[:500])
            bundle, ingest_problem = _ingest_without_raising(
                primary["root_path"], manifest
            )
            if ingest_problem is not None:
                # The document's outcome cannot be recorded at all (its bytes no longer match
                # the manifest), so this is a FAILURE rather than an "unsupported" that would
                # pretend the artifact exists.
                failed += 1
                last_failure_code = ingest_problem
                last_failed_document_id = document["document_id"]
                last_failed_path = str(source_path.resolve(strict=False))
                failure_reasons[ingest_problem] = (
                    failure_reasons.get(ingest_problem, 0) + 1
                )
                continue
        except Exception as exc:
            # B-VR-B10R3-01 (P2, live): this parse sits INSIDE the handler but OUTSIDE every
            # try, so a document whose parse failed AND whose existing normalized-artifact row
            # carries malformed metadata used to escape here and abort the WHOLE run - the
            # same defect shape as the P0, on the sibling `normalization_metadata_json`
            # column (measured by the reviewer: two documents seeded, the second healthy and
            # queued behind, still `escaped=true` with zero normalized.md on disk).  The chain
            # parses it now; the retry bookkeeping simply starts from "no previous attempt".
            existing_metadata, _ = metadata_state(
                document["normalization_metadata_json"]
            )
            next_attempt = int(existing_metadata.get("attempt_count") or 0) + 1
            terminal = next_attempt >= retry_limit
            error_code = (
                DOCUMENT_PARSE_TIMEOUT_CODE
                if isinstance(exc, NormalizationTimeoutError)
                else type(exc).__name__
            )
            error_text = f"{error_code}: {str(exc)[:500]}"
            normalized = _failed(source_path, error_text)
            failure_metadata = {
                "attempt_count": next_attempt,
                "terminal": terminal,
                "terminal_reason": (
                    f"retry_exhausted:{error_code}" if terminal else None
                ),
                "next_retry_epoch": (
                    None if terminal else now_epoch + retry_backoff_seconds
                ),
                "error_code": error_code,
            }
            # The bookkeeping happens BEFORE the ingest, and the ingest cannot raise, so a
            # document whose failure artifact cannot be written keeps the PARSE failure as its
            # recorded reason (the real cause) while the write problem is counted beside it.
            failed += 1
            last_failure_code = error_code
            last_failed_document_id = document["document_id"]
            last_failed_path = str(source_path.resolve(strict=False))
            failure_reasons[error_code] = failure_reasons.get(error_code, 0) + 1
            bundle, ingest_problem = _ingest_without_raising(
                primary["root_path"], manifest
            )
            if ingest_problem is not None:
                failure_reasons[ingest_problem] = (
                    failure_reasons.get(ingest_problem, 0) + 1
                )
                continue
        raw_text = "\n\n".join(
            result.raw_text or "" for result in normalized.parser_results
        )
        text_fingerprint = compute_text_fingerprint(raw_text)
        output_path = (
            config.derived_dir
            / document["content_sha256"][:2]
            / document["content_sha256"]
            / "normalized.md"
        )
        content = (
            _frontmatter(document, normalized)
            + f"# {document['title']}\n\n"
            + normalized.body
        )
        # F-BAR-B10R2 family (owner instruction 2026-09-18): the derived-file write used to
        # sit outside every guard, so ONE unwritable artifact (full disk, revoked permission,
        # a directory where the file belongs) aborted the whole normalization run and starved
        # every document behind it.  It is a per-document failure now, and the byte size is
        # taken from the file we just hashed, so the artifact row and the bytes cannot drift.
        try:
            _atomic_write(output_path, content)
            artifact_hash = _sha256_file(output_path)
            artifact_byte_size = output_path.stat().st_size
        except OSError as exc:
            failed += 1
            last_failure_code = f"artifact_write_failed:{type(exc).__name__}"
            last_failed_document_id = document["document_id"]
            last_failed_path = str(output_path.resolve(strict=False))
            failure_reasons[last_failure_code] = (
                failure_reasons.get(last_failure_code, 0) + 1
            )
            continue
        artifact_id = (
            "urn:company-wiki:artifact:sha256:"
            + hashlib.sha256(
                (
                    document["document_id"] + "\0normalized\0" + NORMALIZER_VERSION
                ).encode("utf-8")
            ).hexdigest()
        )
        # F-BAR-B10R2 family: the record transaction is a per-document step too - a failing
        # statement here (locked database, damaged index, disk full) must not abort the run.
        try:
            with store.transaction() as connection:
                connection.execute(
                    "DELETE FROM evidence_spans WHERE document_id=?",
                    (document["document_id"],),
                )
                for span in bundle.evidence_spans:
                    data = span.to_dict()
                    coordinates = data["coordinates"]
                    connection.execute(
                        """INSERT INTO evidence_spans(span_id,document_id,source_id,locator,page_number,
                        paragraph_index,table_index,raw_text,span_json,parser_name,parser_version,parse_status)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            span.span_id,
                            document["document_id"],
                            span.source_id,
                            span.locator,
                            coordinates["page_number"],
                            coordinates["paragraph_index"],
                            coordinates["table_index"],
                            span.raw_text,
                            span.canonical_json(),
                            span.parser_name,
                            span.parser_version,
                            span.parse_status.value,
                        ),
                    )
                connection.execute(
                    """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,content_sha256,
                    byte_size,mime_type,generator_name,generator_version,status,error,
                    schema_version,source_sha256,metadata_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                    ON CONFLICT(document_id,artifact_role,generator_name,generator_version) DO UPDATE SET
                    path=excluded.path,content_sha256=excluded.content_sha256,byte_size=excluded.byte_size,
                    status=excluded.status,error=excluded.error,
                    schema_version=excluded.schema_version,source_sha256=excluded.source_sha256,
                    metadata_json=excluded.metadata_json,created_at=excluded.created_at""",
                    (
                        artifact_id,
                        document["document_id"],
                        source_id,
                        "normalized",
                        str(output_path.resolve()),
                        artifact_hash,
                        artifact_byte_size,
                        "text/markdown",
                        _NORMALIZER_NAME,
                        NORMALIZER_VERSION,
                        normalized.status,
                        normalized.error,
                        ARTIFACT_HANDLE_SCHEMA_VERSION,
                        str(document["content_sha256"] or ""),
                        canonical_json(
                            {
                                "schema_version": ARTIFACT_HANDLE_SCHEMA_VERSION,
                                "parser_name": normalized.parser_name,
                                "parser_version": normalized.parser_version,
                                "quality_flags": list(normalized.quality_flags),
                                "span_count": len(bundle.evidence_spans),
                                **(failure_metadata or {}),
                            }
                        ),
                    ),
                )
                connection.execute(
                    "UPDATE documents SET text_fingerprint=? WHERE document_id=?",
                    (text_fingerprint, document["document_id"]),
                )
        except sqlite3.Error as exc:
            failed += 1
            last_failure_code = f"artifact_record_failed:{type(exc).__name__}"
            last_failed_document_id = document["document_id"]
            last_failed_path = str(output_path.resolve(strict=False))
            failure_reasons[last_failure_code] = (
                failure_reasons.get(last_failure_code, 0) + 1
            )
            continue

        if normalized.status == "completed":
            completed += 1
        elif normalized.status == "partial":
            partial += 1
        elif normalized.status == "unsupported":
            unsupported += 1
    return ProcessingReport(
        "normalize",
        completed,
        skipped,
        partial,
        unsupported,
        failed,
        terminal_reasons=failure_reasons or None,
        last_failure_code=last_failure_code,
        last_failed_document_id=last_failed_document_id,
        last_failed_path=last_failed_path,
    )

