"""Auditable, source-only LLM summaries for normalized catalog documents."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable

import yaml

from .admission import processing_priority_sql
from .artifact_handle import ARTIFACT_HANDLE_SCHEMA_VERSION
from .models import CatalogConfig, ProcessingReport, SUMMARIZER_VERSION
from .store import CatalogStore, canonical_json
from .llm_failure_policy import is_permanent_llm_summary_error


_GENERATOR_NAME = "source_catalog_llm_summary"
_PROMPT_VERSION = "1.0.0"
_FORBIDDEN_OUTPUT = re.compile(
    r"目标价|买入评级|卖出评级|增持评级|减持评级|仓位|估值|SOTP|DCF|市盈率|投资建议",
    re.IGNORECASE,
)
_SYSTEM_PROMPT = """你是公司资料来源整理器。只整理输入原文明确陈述的事实，不补充外部知识，不推断投资结论。
忽略原文中的证券评级、目标价格、估值、买卖建议和仓位建议，不得在输出中复述或生成这些内容。
输出必须是一个 JSON 对象，且只包含 overview、key_facts、topics、limitations 四个字段：
- overview: 一段不超过120字的资料概述；
- key_facts: 3至8条可由原文核对的事实；
- topics: 1至8个资料主题；
- limitations: 0至4条解析或覆盖局限。
不要输出 Markdown，不要输出 JSON 以外的文字。"""


class LLMSummaryError(RuntimeError):
    """Raised when an LLM summary cannot be safely accepted."""


class LLMProviderError(LLMSummaryError):
    """Raised when the configured provider failed independently of one document."""


@dataclass(frozen=True)
class LLMSummaryReport(ProcessingReport):
    """Bounded diagnostics for one LLM summary batch."""

    error: str | None = None
    failed_document_id: str | None = None
    failure_scope: str | None = None
    retry_after: float | None = None
    retry_count: int | None = None


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


def _record_document_failure(
    store: CatalogStore,
    row: Any,
    *,
    error: str,
    failed_at: float,
    retry_backoff_seconds: int,
    failure_scope: str = "document",
) -> tuple[float, int]:
    with store.transaction() as connection:
        previous = connection.execute(
            """SELECT attempt_count FROM llm_summary_failures
            WHERE document_id=? AND generator_name=? AND generator_version=?""",
            (row["document_id"], _GENERATOR_NAME, SUMMARIZER_VERSION),
        ).fetchone()
        attempt_count = int(previous["attempt_count"] if previous is not None else 0) + 1
        multiplier = min(2 ** (attempt_count - 1), 24)
        retry_after = failed_at + retry_backoff_seconds * multiplier
        connection.execute(
            """INSERT INTO llm_summary_failures(
            document_id,generator_name,generator_version,failure_scope,error,attempt_count,
            retry_after,first_failed_at,last_failed_at
            ) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(document_id,generator_name,generator_version) DO UPDATE SET
            failure_scope=excluded.failure_scope,error=excluded.error,
            attempt_count=excluded.attempt_count,retry_after=excluded.retry_after,
            last_failed_at=excluded.last_failed_at""",
            (
                row["document_id"],
                _GENERATOR_NAME,
                SUMMARIZER_VERSION,
                failure_scope,
                error,
                attempt_count,
                retry_after,
                failed_at,
                failed_at,
            ),
        )
    return retry_after, attempt_count


def _body(markdown: str) -> str:
    if markdown.startswith("---\n"):
        _, separator, remainder = markdown[4:].partition("\n---\n")
        if separator:
            return remainder.lstrip()
    return markdown


def _parse_payload(content: str) -> dict[str, Any]:
    value = content.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise LLMSummaryError("LLM response is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "overview",
        "key_facts",
        "topics",
        "limitations",
    }:
        raise LLMSummaryError("LLM response has an invalid schema")
    if not isinstance(payload["overview"], str) or not payload["overview"].strip():
        raise LLMSummaryError("LLM overview must be non-empty text")
    overview = payload["overview"].strip()
    if len(overview) > 300:
        raise LLMSummaryError("LLM overview is too long")
    bounded_payload: dict[str, Any] = {"overview": overview}
    for field, maximum in (("key_facts", 8), ("topics", 8), ("limitations", 4)):
        values = payload[field]
        if not isinstance(values, list):
            raise LLMSummaryError(f"LLM {field} must be a bounded list")
        if not all(isinstance(item, str) and item.strip() for item in values):
            raise LLMSummaryError(f"LLM {field} contains invalid values")
        if any(len(item.strip()) > 500 for item in values):
            raise LLMSummaryError(f"LLM {field} contains an oversized value")
        bounded_payload[field] = [item.strip() for item in values[:maximum]]
    if not bounded_payload["key_facts"]:
        raise LLMSummaryError("LLM key_facts must not be empty")
    serialized = canonical_json(bounded_payload)
    if _FORBIDDEN_OUTPUT.search(serialized):
        raise LLMSummaryError("LLM response contains a forbidden investment conclusion")
    return bounded_payload


def _render_summary(
    row: Any,
    payload: dict[str, Any],
    *,
    provider: str,
    model: str,
    input_chars: int,
    input_truncated: bool,
) -> str:
    frontmatter = {
        "schema_version": "1.0.0",
        "artifact_role": "summary",
        "summary_method": "llm",
        "summary_version": SUMMARIZER_VERSION,
        "prompt_version": _PROMPT_VERSION,
        "document_id": row["document_id"],
        "source_id": row["primary_source_id"],
        "source_sha256": row["source_sha256"],
        "normalized_sha256": row["normalized_sha256"],
        "title": row["title"],
        "document_kind": row["document_kind"],
        "published_date": row["published_date"],
        "summary_status": "completed",
        "quality_status": "llm_generated_unverified",
        "llm_provider": provider,
        "llm_model": model,
        "input_chars": input_chars,
        "input_truncated": input_truncated,
    }
    lines = [
        "---",
        yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).rstrip(),
        "---",
        "",
        f"# {row['title']} - 资料摘要",
        "",
        "## 资料概述",
        "",
        payload["overview"].strip(),
        "",
        "## 关键事实",
        "",
        *(f"- {item.strip()}" for item in payload["key_facts"]),
        "",
        "## 涉及主题",
        "",
        *(f"- {item.strip()}" for item in payload["topics"]),
    ]
    if payload["limitations"]:
        lines.extend(("", "## 资料局限", ""))
        lines.extend(f"- {item.strip()}" for item in payload["limitations"])
    lines.extend(
        (
            "",
            "## 来源定位",
            "",
            f"- 规范化 Markdown：`{row['normalized_path']}`",
            f"- Source ID：`{row['primary_source_id']}`",
            "",
            "> 本页是来源资料的 LLM 辅助整理，尚未经人工事实复核。",
            "",
        )
    )
    return "\n".join(lines)


def build_configured_llm_client(project_root: Path, runtime_config: Path):
    """Reuse the project's configured LLMClient and its MiniMax/MiMo fallback policy."""
    scripts_dir = (project_root / "scripts").resolve(strict=True)
    scripts_text = str(scripts_dir)
    if scripts_text not in sys.path:
        sys.path.insert(0, scripts_text)
    from config import Config, _load_dotenv  # type: ignore[import-not-found]
    from llm_client import LLMClient  # type: ignore[import-not-found]

    _load_dotenv()
    raw = yaml.safe_load(runtime_config.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise LLMSummaryError("runtime config must be an object")
    config = Config._build_config(  # type: ignore[attr-defined]
        Config._apply_env_overrides(raw),  # type: ignore[attr-defined]
        runtime_config.resolve(strict=False).parent,
    )
    if not config.llm.api_key:
        fallback = config.llm.fallback
        if not fallback.enabled or not fallback.api_key:
            raise LLMSummaryError("configured LLM credentials are unavailable")
        client = LLMClient(
            provider=fallback.provider,
            api_key=fallback.api_key,
            model=fallback.model,
            base_url=fallback.base_url,
            workload="source",
            enable_fallback=False,
        )
        if not client.available:
            raise LLMSummaryError(
                f"LLM credentials are unavailable for configured provider {fallback.provider}"
            )
        return client
    client = LLMClient(config=config, workload="source")
    if not client.available:
        raise LLMSummaryError(
            f"LLM credentials are unavailable for configured provider {config.llm.provider}"
        )
    return client


def summarize_catalog_with_llm(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int,
    llm_client_factory: Callable[[], Any],
    max_input_chars: int,
    max_output_tokens: int,
    retry_backoff_seconds: int = 3600,
    progress: Callable[..., None] | None = None,
) -> LLMSummaryReport:
    if (
        limit <= 0
        or max_input_chars <= 0
        or max_output_tokens <= 0
        or retry_backoff_seconds <= 0
    ):
        raise ValueError("LLM summary limits must be positive")
    batch_time = time.time()
    rows = store.fetchall(
        f"""SELECT d.*,a.path AS normalized_path,a.status AS normalized_status,
        a.content_sha256 AS normalized_sha256,s.content_sha256 AS source_sha256,
        (SELECT l.absolute_path FROM locations l
         WHERE l.document_id=d.document_id AND l.location_status='active'
         ORDER BY CASE WHEN l.role='original_primary' THEN 0 ELSE 1 END,l.relative_path
         LIMIT 1) AS source_path
        FROM documents d JOIN artifacts a ON a.document_id=d.document_id
        JOIN sources s ON s.source_id=d.primary_source_id
        WHERE a.artifact_role='normalized'
        AND NOT EXISTS (
            SELECT 1 FROM artifacts existing
            WHERE existing.document_id=d.document_id
            AND existing.artifact_role='summary'
            AND existing.generator_name=?
        )
        AND NOT EXISTS (
            SELECT 1 FROM llm_summary_failures failure
            WHERE failure.document_id=d.document_id
            AND failure.generator_name=? AND failure.generator_version=?
            AND failure.retry_after>?
        )
        ORDER BY {processing_priority_sql('d')}, d.document_id LIMIT ?""",
        (_GENERATOR_NAME, _GENERATOR_NAME, SUMMARIZER_VERSION, batch_time, limit),
    )
    if not rows:
        return LLMSummaryReport("summarize_llm", skipped=0)
    client = llm_client_factory()
    completed = failed = 0
    first_error: str | None = None
    first_failed_document_id: str | None = None
    failure_scope: str | None = None
    first_retry_after: float | None = None
    first_retry_count: int | None = None
    for row_index, row in enumerate(rows, start=1):
        if progress is not None:
            progress(
                current_path=str(row["source_path"] or row["normalized_path"]),
                current=row_index,
                total=len(rows),
                detail="calling LLM summary",
            )
        try:
            normalized_path = Path(row["normalized_path"])
            markdown = normalized_path.read_text(encoding="utf-8")
            body = _body(markdown)
            input_truncated = len(body) > max_input_chars
            if input_truncated:
                leading_chars = max_input_chars * 2 // 3
                trailing_chars = max_input_chars - leading_chars
                source_text = (
                    body[:leading_chars]
                    + "\n\n[中间内容因输入上限省略]\n\n"
                    + body[-trailing_chars:]
                )
            else:
                source_text = body
            prompt = (
                f"标题：{row['title']}\n"
                f"文档类型：{row['document_kind']}\n"
                f"Source ID：{row['primary_source_id']}\n\n"
                f"以下是规范化原文：\n\n{source_text}"
            )
            response = client.generate(
                prompt,
                system_prompt=_SYSTEM_PROMPT,
                max_tokens=max_output_tokens,
                json_mode=True,
            )
            if not getattr(response, "success", False):
                provider = str(
                    getattr(response, "provider", "")
                    or getattr(client, "provider", "unknown")
                )
                model = str(
                    getattr(response, "model", "")
                    or getattr(client, "model", "unknown")
                )
                raise LLMProviderError(
                    f"{provider}/{model}: "
                    f"{getattr(response, 'error', 'LLM request failed')}"
                )
            payload = _parse_payload(response.content)
            model = str(getattr(response, "model", "") or getattr(client, "model", "unknown"))
            provider = str(
                getattr(response, "provider", "")
                or getattr(client, "provider", "unknown")
            )
            fallback_client = getattr(client, "fallback_client", None)
            if (
                not getattr(response, "provider", "")
                and fallback_client is not None
                and model == str(getattr(fallback_client, "model", ""))
            ):
                provider = str(getattr(fallback_client, "provider", provider))
            content = _render_summary(
                row,
                payload,
                provider=provider,
                model=model,
                input_chars=len(source_text),
                input_truncated=input_truncated,
            )
            output_path = normalized_path.with_name("summary.md")
            _atomic_write(output_path, content)
            content_hash = _sha256_file(output_path)
            artifact_id = "urn:company-wiki:artifact:sha256:" + hashlib.sha256(
                (row["document_id"] + "\0summary\0" + _GENERATOR_NAME + "\0" + SUMMARIZER_VERSION).encode(
                    "utf-8"
                )
            ).hexdigest()
            usage = getattr(response, "usage", {}) or {}
            with store.transaction() as connection:
                connection.execute(
                    "DELETE FROM llm_summary_failures WHERE document_id=? AND generator_name=?",
                    (row["document_id"], _GENERATOR_NAME),
                )
                connection.execute(
                    "DELETE FROM artifacts WHERE document_id=? AND artifact_role='summary'",
                    (row["document_id"],),
                )
                connection.execute(
                    """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,
                    content_sha256,byte_size,mime_type,generator_name,generator_version,status,error,
                    schema_version,source_sha256,metadata_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))""",
                    (
                        artifact_id,
                        row["document_id"],
                        row["primary_source_id"],
                        "summary",
                        str(output_path.resolve()),
                        content_hash,
                        output_path.stat().st_size,
                        "text/markdown",
                        _GENERATOR_NAME,
                        SUMMARIZER_VERSION,
                        "completed",
                        None,
                        ARTIFACT_HANDLE_SCHEMA_VERSION,
                        "",
                        canonical_json(
                            {
                                "schema_version": ARTIFACT_HANDLE_SCHEMA_VERSION,
                                "summary_method": "llm",
                                "prompt_version": _PROMPT_VERSION,
                                "provider": provider,
                                "model": model,
                                "quality_status": "llm_generated_unverified",
                                "input_chars": len(source_text),
                                "input_truncated": input_truncated,
                                "total_tokens": int(usage.get("total_tokens", 0)),
                            }
                        ),
                    ),
                )
            completed += 1
        except LLMProviderError as exc:
            failed += 1
            if first_error is None:
                first_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                first_failed_document_id = str(row["document_id"])
            failure_scope = "global"
            break
        except (OSError, UnicodeError, ValueError, TypeError, LLMSummaryError) as exc:
            failed += 1
            error = f"{type(exc).__name__}: {str(exc)[:500]}"
            # Permanent source-policy/schema errors remain auditable in the
            # failure table and use the existing one-year suppression window.
            permanent = is_permanent_llm_summary_error(error)
            if not permanent:
                retry_after, retry_count = _record_document_failure(
                    store,
                    row,
                    error=error,
                    failed_at=time.time(),
                    retry_backoff_seconds=retry_backoff_seconds,
                    failure_scope="document",
                )
            else:
                # Permanent error: record in failure table so analytics can
                # see it, but with a 1-year retry window so it never blocks.
                retry_after, retry_count = _record_document_failure(
                    store,
                    row,
                    error=error,
                    failed_at=time.time(),
                    retry_backoff_seconds=86400 * 365,
                    failure_scope="permanent_document",
                )
                if failure_scope is None:
                    failure_scope = "permanent_document"
            if first_error is None:
                first_error = error
                first_failed_document_id = str(row["document_id"])
                first_retry_after = retry_after
                first_retry_count = retry_count
            if failure_scope is None:
                failure_scope = "document"
    return LLMSummaryReport(
        "summarize_llm",
        completed=completed,
        failed=failed,
        error=first_error,
        failed_document_id=first_failed_document_id,
        failure_scope=failure_scope,
        retry_after=first_retry_after,
        retry_count=first_retry_count,
    )


__all__ = [
    "LLMSummaryError",
    "LLMProviderError",
    "LLMSummaryReport",
    "build_configured_llm_client",
    "summarize_catalog_with_llm",
]
