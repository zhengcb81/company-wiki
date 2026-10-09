"""Ephemeral retrieval over selected narrative evidence packages.

This module does not scan full source documents, read or write the catalog, or
persist an inverted index. Results retain the evidence IDs and raw locators so
callers can resolve them through the existing source query contract.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import unicodedata
from typing import Any, Mapping, Sequence


NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION = "narrative-evidence-selection-bundle/0.2.0"
SUMMARY_INPUT_SCHEMA_VERSION = "narrative-summary-input/0.2.0"
NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION = "narrative-evidence-replay/0.1.0"
_VISIBLE_SELECTION_STATUSES = frozenset({"selected", "partial", "needs_review"})
_KNOWN_SELECTION_STATUSES = _VISIBLE_SELECTION_STATUSES | frozenset(
    {"skipped_no_narrative", "blocked"}
)
_CJK_RANGES = (
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0xF900, 0xFAFF),
)
_MAX_SNIPPET_CHARS = 360


class NarrativeEvidenceSearchError(ValueError):
    """Raised when a selected-evidence bundle violates its read contract."""


class NarrativeEvidenceResolveError(ValueError):
    """Raised when a selected package cannot be replayed against its raw source."""


@dataclass(frozen=True)
class NarrativeEvidenceHit:
    source_id: str
    source_sha256: str
    document_kind: str
    selection_status: str
    coverage_complete: bool
    evidence_group_id: str
    evidence_ids: tuple[str, ...]
    locators: tuple[str, ...]
    snippet: str
    score: float
    matched_terms: tuple[str, ...]
    phrase_match: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "document_kind": self.document_kind,
            "selection_status": self.selection_status,
            "coverage_complete": self.coverage_complete,
            "evidence_group_id": self.evidence_group_id,
            "evidence_ids": list(self.evidence_ids),
            "locators": list(self.locators),
            "snippet": self.snippet,
            "score": self.score,
            "matched_terms": list(self.matched_terms),
            "phrase_match": self.phrase_match,
        }


@dataclass(frozen=True)
class ResolvedNarrativeEvidence:
    """A package group re-parsed from the caller-authorized immutable raw file."""

    source_id: str
    source_sha256: str
    document_kind: str
    selection_status: str
    coverage_complete: bool
    evidence_group_id: str
    evidence_ids: tuple[str, ...]
    locators: tuple[str, ...]
    raw_text: str
    raw_text_sha256: str
    parser_name: str
    parser_version: str


@dataclass(frozen=True)
class _EvidenceGroup:
    source_id: str
    source_sha256: str
    document_kind: str
    selection_status: str
    coverage_complete: bool
    evidence_group_id: str
    evidence_ids: tuple[str, ...]
    locators: tuple[str, ...]
    text: str
    normalized_text: str
    term_frequency: Counter[str]


class NarrativeEvidenceSearch:
    """Build a query-local BM25 index from a selected-evidence bundle in memory.

    Only `summary_scope=selected_evidence_only` packages are accepted. Search
    returns selected evidence groups, never full-document text or summary
    claims. A search result is not source authorization: callers must resolve
    it against a caller-authorized raw path before presenting source text.
    """

    def __init__(self, bundle: Mapping[str, Any]):
        if not isinstance(bundle, Mapping):
            raise TypeError("bundle must be a mapping")
        if bundle.get("schema_version") != NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise NarrativeEvidenceSearchError("unsupported evidence bundle schema")
        records = bundle.get("sources")
        if not isinstance(records, list):
            raise NarrativeEvidenceSearchError("bundle sources must be a list")

        groups: list[_EvidenceGroup] = []
        for record in records:
            groups.extend(self._groups_for_record(record))
        self._groups = tuple(groups)
        self._document_frequency: Counter[str] = Counter()
        for group in self._groups:
            self._document_frequency.update(group.term_frequency.keys())
        self._average_length = (
            sum(sum(group.term_frequency.values()) for group in self._groups)
            / len(self._groups)
            if self._groups
            else 0.0
        )

    @staticmethod
    def _groups_for_record(record: Any) -> list[_EvidenceGroup]:
        if not isinstance(record, Mapping):
            raise NarrativeEvidenceSearchError("each source record must be an object")
        status = record.get("selection_status")
        if not isinstance(status, str) or status not in _KNOWN_SELECTION_STATUSES:
            raise NarrativeEvidenceSearchError("unknown selection status")
        if status not in _VISIBLE_SELECTION_STATUSES:
            return []
        coverage_complete = record.get("coverage_complete")
        if not isinstance(coverage_complete, bool):
            raise NarrativeEvidenceSearchError("coverage_complete must be boolean")
        summary_input = record.get("summary_input")
        if not isinstance(summary_input, Mapping):
            raise NarrativeEvidenceSearchError("source record lacks summary_input")
        if summary_input.get("schema_version") != SUMMARY_INPUT_SCHEMA_VERSION:
            raise NarrativeEvidenceSearchError("unsupported summary input schema")
        if summary_input.get("summary_scope") != "selected_evidence_only":
            raise NarrativeEvidenceSearchError("only selected evidence may be indexed")

        source_id = _required_string(summary_input, "source_id")
        source_sha256 = _required_string(summary_input, "source_sha256")
        document_kind = _required_string(summary_input, "document_kind")
        evidence_rows = summary_input.get("evidence")
        if not isinstance(evidence_rows, list):
            raise NarrativeEvidenceSearchError("summary evidence must be a list")

        output: list[_EvidenceGroup] = []
        for entry in evidence_rows:
            if not isinstance(entry, Mapping):
                raise NarrativeEvidenceSearchError("evidence entries must be objects")
            text = entry.get("raw_text")
            if not isinstance(text, str):
                raise NarrativeEvidenceSearchError("evidence raw_text must be a string")
            if not text.strip():
                continue
            evidence_ids = _string_tuple(entry.get("evidence_ids"), "evidence_ids")
            locators = _string_tuple(entry.get("locators"), "locators")
            if not evidence_ids or len(evidence_ids) != len(locators):
                raise NarrativeEvidenceSearchError(
                    "each selected evidence ID must have exactly one locator"
                )
            group_id = entry.get("context_group_id") or entry.get("evidence_id")
            if not isinstance(group_id, str) or not group_id:
                group_id = evidence_ids[0]
            normalized_text = _normalize_text(text)
            terms = Counter(_tokenize(normalized_text))
            if not terms:
                continue
            output.append(
                _EvidenceGroup(
                    source_id=source_id,
                    source_sha256=source_sha256,
                    document_kind=document_kind,
                    selection_status=str(status),
                    coverage_complete=coverage_complete,
                    evidence_group_id=group_id,
                    evidence_ids=evidence_ids,
                    locators=locators,
                    text=text,
                    normalized_text=normalized_text,
                    term_frequency=terms,
                )
            )
        return output

    @property
    def indexed_group_count(self) -> int:
        """Number of in-memory selected evidence groups; no disk index exists."""
        return len(self._groups)

    def search(self, query: str, *, limit: int = 10) -> tuple[NarrativeEvidenceHit, ...]:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        normalized_query = _normalize_text(query)
        query_terms = tuple(dict.fromkeys(_tokenize(normalized_query)))
        if not query_terms or not self._groups:
            return ()

        scored: list[tuple[tuple[Any, ...], NarrativeEvidenceHit]] = []
        for group in self._groups:
            matched_terms = tuple(
                term for term in query_terms if group.term_frequency.get(term, 0) > 0
            )
            if not matched_terms:
                continue
            phrase_match = normalized_query in group.normalized_text
            score = self._bm25(group, matched_terms)
            hit = NarrativeEvidenceHit(
                source_id=group.source_id,
                source_sha256=group.source_sha256,
                document_kind=group.document_kind,
                selection_status=group.selection_status,
                coverage_complete=group.coverage_complete,
                evidence_group_id=group.evidence_group_id,
                evidence_ids=group.evidence_ids,
                locators=group.locators,
                snippet=_make_snippet(group.text, query),
                score=score,
                matched_terms=matched_terms,
                phrase_match=phrase_match,
            )
            rank = (
                -int(phrase_match),
                -len(matched_terms) / len(query_terms),
                -score,
                group.source_id,
                group.evidence_group_id,
            )
            scored.append((rank, hit))
        scored.sort(key=lambda item: item[0])
        return tuple(hit for _, hit in scored[:limit])

    def _bm25(self, group: _EvidenceGroup, matched_terms: Sequence[str]) -> float:
        document_count = len(self._groups)
        document_length = sum(group.term_frequency.values())
        average_length = self._average_length or 1.0
        k1 = 1.2
        b = 0.75
        score = 0.0
        for term in matched_terms:
            frequency = group.term_frequency[term]
            document_frequency = self._document_frequency[term]
            inverse_frequency = math.log(
                1.0
                + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            denominator = frequency + k1 * (
                1.0 - b + b * document_length / average_length
            )
            score += inverse_frequency * frequency * (k1 + 1.0) / denominator
        return score


class NarrativeEvidenceResolver:
    """Replay a selected package group against an explicitly mapped raw file.

    This is an isolated pilot resolver, not a catalog lookup API. The caller
    supplies only a trusted source-ID-to-raw-path mapping; versioned parser and
    selector inputs come from the package. No path is read from the bundle,
    and only selected package groups are kept in the per-instance memory cache.

    Source records and the raw-path mapping are owned construction snapshots.
    Caller mutations are inputs for a new resolver; they cannot rebind this
    resolver's cached contract or evidence. Raw bytes are still hashed on every
    resolve, including reads that reuse parsed evidence from the cache.
    """

    def __init__(
        self,
        bundle: Mapping[str, Any],
        *,
        raw_paths_by_source_id: Mapping[str, str | Path],
    ) -> None:
        if not isinstance(bundle, Mapping):
            raise TypeError("bundle must be a mapping")
        if bundle.get("schema_version") != NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise NarrativeEvidenceResolveError("unsupported evidence bundle schema")
        records = bundle.get("sources")
        if not isinstance(records, list):
            raise NarrativeEvidenceResolveError("bundle sources must be a list")
        if not isinstance(raw_paths_by_source_id, Mapping):
            raise TypeError("raw_paths_by_source_id must be a mapping")

        self._records: dict[str, Mapping[str, Any]] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise NarrativeEvidenceResolveError("each source record must be an object")
            summary = record.get("summary_input")
            if not isinstance(summary, Mapping):
                raise NarrativeEvidenceResolveError("source record lacks summary_input")
            source_id = _required_string(summary, "source_id")
            if source_id in self._records:
                raise NarrativeEvidenceResolveError("source_id is ambiguous in bundle")
            self._records[source_id] = deepcopy(dict(record))

        self._raw_paths: dict[str, Path] = {}
        for source_id, raw_path in raw_paths_by_source_id.items():
            if not isinstance(source_id, str) or not source_id:
                raise TypeError("raw path keys must be non-empty source IDs")
            if not isinstance(raw_path, (str, Path)):
                raise TypeError("raw paths must be strings or pathlib Paths")
            self._raw_paths[source_id] = Path(raw_path)

        self._replayed: dict[
            str,
            tuple[Path, str, dict[tuple[tuple[str, ...], tuple[str, ...]], Mapping[str, Any]]],
        ] = {}

    def resolve(self, hit: NarrativeEvidenceHit) -> ResolvedNarrativeEvidence:
        """Resolve a search hit and reject IDs or locators not in the bundle."""
        if not isinstance(hit, NarrativeEvidenceHit):
            raise TypeError("hit must be a NarrativeEvidenceHit")
        record = self._source_record(hit.source_id)
        summary = record["summary_input"]
        if (
            summary.get("source_sha256") != hit.source_sha256
            or summary.get("document_kind") != hit.document_kind
            or record.get("selection_status") != hit.selection_status
            or record.get("coverage_complete") != hit.coverage_complete
        ):
            raise NarrativeEvidenceResolveError("search hit identity differs from bundle")
        row = self._find_group(
            summary,
            hit.evidence_ids,
            hit.locators,
            hit.evidence_group_id,
        )
        return self._resolve_row(record, row)

    def resolve_group(
        self, *, source_id: str, evidence_group_id: str
    ) -> ResolvedNarrativeEvidence:
        """Resolve one selected package group without running a search query."""
        record = self._source_record(source_id)
        summary = record["summary_input"]
        evidence_rows = summary.get("evidence")
        if not isinstance(evidence_rows, list):
            raise NarrativeEvidenceResolveError("summary evidence must be a list")
        matches = [
            row
            for row in evidence_rows
            if isinstance(row, Mapping)
            and (row.get("context_group_id") or row.get("evidence_id"))
            == evidence_group_id
        ]
        if len(matches) != 1:
            raise NarrativeEvidenceResolveError("evidence group is missing or ambiguous")
        row = matches[0]
        return self._resolve_row(record, row)

    def _source_record(self, source_id: str) -> Mapping[str, Any]:
        record = self._records.get(source_id)
        if record is None:
            raise NarrativeEvidenceResolveError("source_id is not present in bundle")
        if record.get("selection_status") not in _VISIBLE_SELECTION_STATUSES:
            raise NarrativeEvidenceResolveError("source selection state is not resolvable")
        summary = record.get("summary_input")
        if (
            not isinstance(summary, Mapping)
            or summary.get("schema_version") != SUMMARY_INPUT_SCHEMA_VERSION
            or summary.get("summary_scope") != "selected_evidence_only"
        ):
            raise NarrativeEvidenceResolveError(
                "source is not a supported selected-evidence package"
            )
        if not isinstance(record.get("coverage_complete"), bool):
            raise NarrativeEvidenceResolveError("coverage_complete must be boolean")
        return record

    @staticmethod
    def _find_group(
        summary: Mapping[str, Any],
        evidence_ids: Sequence[str],
        locators: Sequence[str],
        evidence_group_id: str,
    ) -> Mapping[str, Any]:
        rows = summary.get("evidence")
        if not isinstance(rows, list):
            raise NarrativeEvidenceResolveError("summary evidence must be a list")
        matches = [
            row
            for row in rows
            if isinstance(row, Mapping)
            and row.get("evidence_ids") == list(evidence_ids)
            and row.get("locators") == list(locators)
            and (row.get("context_group_id") or row.get("evidence_id"))
            == evidence_group_id
        ]
        if len(matches) != 1:
            raise NarrativeEvidenceResolveError("search hit is not an exact package group")
        return matches[0]

    def _resolve_row(
        self, record: Mapping[str, Any], row: Mapping[str, Any]
    ) -> ResolvedNarrativeEvidence:
        summary = record["summary_input"]
        source_id = _required_string(summary, "source_id")
        source_sha256 = _required_string(summary, "source_sha256")
        _required_string(record, "title")
        replay_contract = record.get("replay_contract")
        if (
            not isinstance(replay_contract, Mapping)
            or replay_contract.get("schema_version")
            != NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION
        ):
            raise NarrativeEvidenceResolveError("unsupported replay contract")

        raw_path = self._raw_paths.get(source_id)
        if raw_path is None:
            raise NarrativeEvidenceResolveError("no caller-authorized raw path for source")
        try:
            resolved_path = raw_path.resolve(strict=True)
        except OSError as exc:
            raise NarrativeEvidenceResolveError("raw source path is unavailable") from exc
        if not resolved_path.is_file():
            raise NarrativeEvidenceResolveError("raw source path is not a file")

        actual_sha256 = _sha256_file(resolved_path)
        if actual_sha256 != source_sha256:
            raise NarrativeEvidenceResolveError("raw source SHA-256 differs from bundle")
        from company_wiki.source_contract import source_id_for_sha256

        if source_id_for_sha256(actual_sha256) != source_id:
            raise NarrativeEvidenceResolveError("source ID does not match raw source hash")

        cached = self._replayed.get(source_id)
        if cached is None or cached[0] != resolved_path or cached[1] != actual_sha256:
            replayed_rows = self._replay_record(
                record,
                raw_path=resolved_path,
                source_id=source_id,
                source_sha256=actual_sha256,
            )
            if _sha256_file(resolved_path) != actual_sha256:
                raise NarrativeEvidenceResolveError("raw source changed during locator replay")
            self._replayed[source_id] = (resolved_path, actual_sha256, replayed_rows)
        else:
            replayed_rows = cached[2]

        evidence_ids = _string_tuple(row.get("evidence_ids"), "evidence_ids")
        locators = _string_tuple(row.get("locators"), "locators")
        original_text = row.get("raw_text")
        original_text_sha = row.get("raw_text_sha256")
        if not isinstance(original_text, str) or not isinstance(original_text_sha, str):
            raise NarrativeEvidenceResolveError("package evidence text and hash are required")
        if hashlib.sha256(original_text.encode("utf-8")).hexdigest() != original_text_sha:
            raise NarrativeEvidenceResolveError("package evidence text hash is invalid")
        key = (evidence_ids, locators)
        replayed = replayed_rows.get(key)
        if replayed is None:
            raise NarrativeEvidenceResolveError("selected group did not replay from raw source")
        for field in ("raw_text_sha256", "parser_name", "parser_version"):
            if replayed.get(field) != row.get(field):
                raise NarrativeEvidenceResolveError(f"replayed package {field} differs")
        return ResolvedNarrativeEvidence(
            source_id=source_id,
            source_sha256=actual_sha256,
            document_kind=str(summary.get("document_kind")),
            selection_status=str(record.get("selection_status")),
            coverage_complete=bool(record.get("coverage_complete")),
            evidence_group_id=str(row.get("context_group_id") or row.get("evidence_id")),
            evidence_ids=evidence_ids,
            locators=locators,
            raw_text=str(replayed["raw_text"]),
            raw_text_sha256=str(replayed["raw_text_sha256"]),
            parser_name=str(replayed["parser_name"]),
            parser_version=str(replayed["parser_version"]),
        )

    @staticmethod
    def _replay_record(
        record: Mapping[str, Any],
        *,
        raw_path: Path,
        source_id: str,
        source_sha256: str,
    ) -> dict[tuple[tuple[str, ...], tuple[str, ...]], Mapping[str, Any]]:
        from company_wiki.source_catalog.narrative_evidence import (
            NARRATIVE_PARSER_NAME,
            NARRATIVE_SELECTOR_NAME,
            NARRATIVE_SELECTOR_VERSION,
            parse_pdf,
            parse_transcript_text,
            select_narrative_evidence,
            transcript_parser_contract,
        )

        summary = record["summary_input"]
        contract = record.get("replay_contract")
        if (
            not isinstance(contract, Mapping)
            or contract.get("schema_version") != NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION
        ):
            raise NarrativeEvidenceResolveError("unsupported replay contract")
        if (
            contract.get("selector_name") != NARRATIVE_SELECTOR_NAME
            or contract.get("selector_version") != NARRATIVE_SELECTOR_VERSION
        ):
            raise NarrativeEvidenceResolveError("unsupported narrative selector version")
        parser_name = _required_string(contract, "parser_name")
        parser_version = _required_string(contract, "parser_version")
        if parser_name != NARRATIVE_PARSER_NAME:
            raise NarrativeEvidenceResolveError("unsupported narrative parser name")
        language = _required_string(contract, "language")
        source_format = _required_string(contract, "source_format")
        if source_format in {"transcript_txt", "transcript_html"}:
            try:
                transcript_parser_contract(parser_version)
            except ValueError as exc:
                raise NarrativeEvidenceResolveError(str(exc)) from exc
        existing_kind = _required_string(contract, "existing_kind")
        max_selected = contract.get("max_selected")
        if isinstance(max_selected, bool) or not isinstance(max_selected, int) or max_selected < 1:
            raise NarrativeEvidenceResolveError("max_selected must be a positive integer")
        parser_options = contract.get("parser_options")
        if not isinstance(parser_options, Mapping):
            raise NarrativeEvidenceResolveError("parser_options must be an object")
        source_rows = summary.get("evidence")
        if not isinstance(source_rows, list) or not source_rows:
            raise NarrativeEvidenceResolveError("selected package has no evidence groups")
        package_parser_versions = {
            _required_string(row, "parser_version")
            for row in source_rows
            if isinstance(row, Mapping)
        }
        package_parser_names = {
            _required_string(row, "parser_name")
            for row in source_rows
            if isinstance(row, Mapping)
        }
        if package_parser_versions != {parser_version} or package_parser_names != {parser_name}:
            raise NarrativeEvidenceResolveError("package parser metadata does not match replay contract")
        suffix = raw_path.suffix.casefold()
        if source_format == "pdf":
            if suffix != ".pdf":
                raise NarrativeEvidenceResolveError("raw file extension differs from replay format")
            if set(parser_options) != {"full_table_scan", "table_pages"}:
                raise NarrativeEvidenceResolveError("PDF parser options are incomplete or unknown")
            full_table_scan = parser_options.get("full_table_scan")
            if not isinstance(full_table_scan, bool):
                raise NarrativeEvidenceResolveError("full_table_scan must be boolean")
            table_pages = parser_options.get("table_pages")
            if table_pages is not None and (
                not isinstance(table_pages, list)
                or any(isinstance(page, bool) or not isinstance(page, int) or page < 1 for page in table_pages)
                or len(table_pages) != len(set(table_pages))
            ):
                raise NarrativeEvidenceResolveError("table_pages must be null or unique positive integers")
            parsed = parse_pdf(
                raw_path,
                source_id=source_id,
                source_sha256=source_sha256,
                parser_version=parser_version,
                language=language,
                full_table_scan=full_table_scan,
                table_pages=table_pages,
            )
        elif source_format in {"transcript_txt", "transcript_html"}:
            if parser_options:
                raise NarrativeEvidenceResolveError("transcript parser options must be empty")
            if source_format == "transcript_txt":
                if suffix != ".txt":
                    raise NarrativeEvidenceResolveError("raw file extension differs from replay format")
                try:
                    raw_text = raw_path.read_bytes().decode("utf-8-sig", errors="strict")
                except UnicodeError as exc:
                    raise NarrativeEvidenceResolveError("transcript TXT is not valid UTF-8") from exc
            else:
                if suffix not in {".html", ".htm"}:
                    raise NarrativeEvidenceResolveError("raw file extension differs from replay format")
                from .transcript_text_extract import (
                    TranscriptMaterialError,
                    extract_transcript_material,
                )
                try:
                    original_bytes = raw_path.read_bytes()
                    material = extract_transcript_material(original_bytes, mime_type="text/html")
                    material.verify(original_bytes)
                except TranscriptMaterialError as exc:
                    raise NarrativeEvidenceResolveError("transcript HTML byte lineage does not replay") from exc
                raw_text = material.text_utf8
            parsed = parse_transcript_text(
                raw_text,
                source_id=source_id,
                source_sha256=source_sha256,
                parser_version=parser_version,
                language=language,
            )
        else:
            raise NarrativeEvidenceResolveError("unsupported replay source format")

        selected = select_narrative_evidence(
            parsed,
            title=_required_string(record, "title"),
            existing_kind=existing_kind,
            max_selected=max_selected,
        )
        if (
            selected.document_kind != summary.get("document_kind")
            or selected.status != record.get("selection_status")
            or selected.coverage_complete != record.get("coverage_complete")
        ):
            raise NarrativeEvidenceResolveError("replayed source selection state differs")

        replay_rows: dict[
            tuple[tuple[str, ...], tuple[str, ...]], Mapping[str, Any]
        ] = {}
        for replay_row in selected.summary_input().get("evidence", []):
            key = (
                _string_tuple(replay_row.get("evidence_ids"), "evidence_ids"),
                _string_tuple(replay_row.get("locators"), "locators"),
            )
            if key in replay_rows:
                raise NarrativeEvidenceResolveError("replayed evidence group is ambiguous")
            replay_rows[key] = replay_row
        original_keys = {
            (
                _string_tuple(row.get("evidence_ids"), "evidence_ids"),
                _string_tuple(row.get("locators"), "locators"),
            )
            for row in source_rows
            if isinstance(row, Mapping)
        }
        if original_keys != set(replay_rows):
            raise NarrativeEvidenceResolveError("selected evidence set does not replay exactly")
        for key in original_keys:
            original = next(
                row
                for row in source_rows
                if isinstance(row, Mapping)
                and _string_tuple(row.get("evidence_ids"), "evidence_ids") == key[0]
                and _string_tuple(row.get("locators"), "locators") == key[1]
            )
            replayed = replay_rows[key]
            for field in ("raw_text_sha256", "parser_name", "parser_version"):
                if replayed.get(field) != original.get(field):
                    raise NarrativeEvidenceResolveError(f"replayed package {field} differs")
        return replay_rows


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise NarrativeEvidenceSearchError(f"{key} must be a non-empty string")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise NarrativeEvidenceSearchError(f"{field_name} must be a list of non-empty strings")
    return tuple(value)


def _is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in _CJK_RANGES)


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    cjk_run: list[str] = []
    word_run: list[str] = []

    def flush_cjk() -> None:
        if len(cjk_run) == 1:
            tokens.append(cjk_run[0])
        elif len(cjk_run) > 1:
            tokens.extend(cjk_run[index] + cjk_run[index + 1] for index in range(len(cjk_run) - 1))
        cjk_run.clear()

    def flush_word() -> None:
        if word_run:
            tokens.append("".join(word_run))
            word_run.clear()

    for character in text:
        if _is_cjk(character):
            flush_word()
            cjk_run.append(character)
        elif character.isalnum() or character == "_":
            flush_cjk()
            word_run.append(character)
        else:
            flush_cjk()
            flush_word()
    flush_cjk()
    flush_word()
    return tokens


def _make_snippet(text: str, query: str) -> str:
    if len(text) <= _MAX_SNIPPET_CHARS:
        return text
    position = text.casefold().find(query.casefold())
    if position < 0:
        position = 0
    start = max(0, position - _MAX_SNIPPET_CHARS // 3)
    end = min(len(text), start + _MAX_SNIPPET_CHARS)
    if end - start < _MAX_SNIPPET_CHARS:
        start = max(0, end - _MAX_SNIPPET_CHARS)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


__all__ = [
    "NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "NarrativeEvidenceHit",
    "NarrativeEvidenceSearch",
    "NarrativeEvidenceSearchError",
]
