"""Deterministic source-only summaries for normalized Markdown artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Any

import yaml

from .admission import processing_priority_sql
from .models import CatalogConfig, ProcessingReport, SUMMARIZER_VERSION
from .store import CatalogStore, canonical_json


_SUMMARIZER_NAME = "source_catalog_extractive_summary"
_SENTENCE_RE = re.compile(r"(?<=[。！？.!?；;])\s+")
_FORBIDDEN_RESEARCH_TERMS = re.compile(
    r"目标价|买入评级|卖出评级|增持评级|减持评级|仓位|估值|SOTP|DCF|市盈率|投资建议",
    re.IGNORECASE,
)
_INFORMATION_TERMS = re.compile(
    r"收入|营收|利润|现金流|同比|环比|增长|下降|订单|客户|产品|业务|市场|份额|"
    r"产能|产量|销量|价格|成本|毛利|费用|研发|资本开支|投资|合同|交付|库存|"
    r"应收|负债|资产|风险|计划|目标|预计|指引|revenue|profit|cash flow|customer|"
    r"capacity|order|market|cost|margin|guidance|risk",
    re.IGNORECASE,
)
_BOILERPLATE_TERMS = re.compile(
    r"股票代码|股票简称|特定对象调研|分析师会议|媒体采访|业绩说明会|新闻发布会|"
    r"路演活动|活动参与人员|接待人员|人员姓名|参与链接|电子邮箱|公司网址|"
    r"免责声明|本报告仅供|page\s+\d+|第\s*\d+\s*页",
    re.IGNORECASE,
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


def _body(markdown: str) -> str:
    if markdown.startswith("---\n"):
        _, separator, remainder = markdown[4:].partition("\n---\n")
        if separator:
            return remainder
    return markdown


def _extract_points(markdown: str, *, limit: int = 7) -> list[str]:
    body = _body(markdown)
    raw_candidates: list[str] = []
    pending: list[str] = []

    def flush_pending() -> None:
        if not pending:
            return
        value = " ".join(pending)
        raw_candidates.extend(
            item.strip() for item in _SENTENCE_RE.split(value) if item.strip()
        )
        pending.clear()

    for line in body.splitlines():
        value = line.strip()
        if not value:
            if pending and re.search(r"[。！？.!?；;]$", pending[-1]):
                flush_pending()
            continue
        if value.startswith(("#", "<!--", "```", "|", "- `loc:")) or set(value) <= {
            "-",
            ":",
            "|",
            " ",
        }:
            flush_pending()
            continue
        value = re.sub(r"^[-*+]\s+", "", value)
        pending.append(value)
        if re.search(r"[。！？.!?；;]$", value) or sum(map(len, pending)) >= 600:
            flush_pending()
    flush_pending()
    candidates: list[tuple[float, int, str]] = []
    seen: set[str] = set()
    for index, value in enumerate(raw_candidates):
        normalized = re.sub(r"\s+", " ", value).strip()
        if len(normalized) < 12 or _FORBIDDEN_RESEARCH_TERMS.search(normalized):
            continue
        normalized = normalized[:300].rstrip()
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        score = min(len(normalized), 180) / 60
        score += min(len(_INFORMATION_TERMS.findall(normalized)), 4) * 2.0
        if re.search(r"\d", normalized):
            score += 1.0
        if re.search(r"%|亿元|万元|万台|万吨|台|家|人|年|月|季度", normalized):
            score += 0.75
        if _BOILERPLATE_TERMS.search(normalized):
            score -= 5.0
        candidates.append((score, index, normalized))
    selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:limit]
    return [value for _, _, value in sorted(selected, key=lambda item: item[1])]


def _headings(markdown: str, *, limit: int = 12) -> list[str]:
    values: list[str] = []
    for line in _body(markdown).splitlines():
        if line.startswith("#"):
            value = line.lstrip("#").strip()
            if value and not _FORBIDDEN_RESEARCH_TERMS.search(value) and value not in values:
                values.append(value[:200])
                if len(values) >= limit:
                    break
    return values


def summarize_catalog(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int | None = None,
    force: bool = False,
) -> ProcessingReport:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    sql = """SELECT d.*,a.path AS normalized_path,a.status AS normalized_status,
        a.content_sha256 AS normalized_sha256,s.content_sha256 AS source_sha256
        FROM documents d JOIN artifacts a ON a.document_id=d.document_id
        JOIN sources s ON s.source_id=d.primary_source_id
        WHERE a.artifact_role='normalized'"""
    params: tuple[Any, ...] = ()
    if not force:
        sql += """ AND NOT EXISTS (
            SELECT 1 FROM artifacts existing
            WHERE existing.document_id=d.document_id
            AND existing.artifact_role='summary'
        )"""
    sql += f" ORDER BY {processing_priority_sql('d')}, d.document_id"
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    rows = store.fetchall(sql, params)
    completed = skipped = partial = failed = 0
    for row in rows:
        normalized_path = Path(row["normalized_path"])
        try:
            markdown = normalized_path.read_text(encoding="utf-8")
            points = _extract_points(markdown)
            headings = _headings(markdown)
        except (OSError, UnicodeError):
            failed += 1
            continue
        summary_status = "completed" if points else "partial"
        frontmatter = {
            "schema_version": "1.0.0",
            "artifact_role": "summary",
            "summary_method": "extractive",
            "summary_version": SUMMARIZER_VERSION,
            "document_id": row["document_id"],
            "source_id": row["primary_source_id"],
            "source_sha256": row["source_sha256"],
            "normalized_sha256": row["normalized_sha256"],
            "title": row["title"],
            "document_kind": row["document_kind"],
            "published_date": row["published_date"],
            "summary_status": summary_status,
        }
        lines = [
            "---",
            yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).rstrip(),
            "---",
            "",
            f"# {row['title']} - 资料摘要",
            "",
            "## 文档概况",
            "",
            f"- 文档类型：`{row['document_kind']}`",
            f"- 来源状态：`{row['source_status']}`",
            f"- 规范化状态：`{row['normalized_status']}`",
            f"- Source ID：`{row['primary_source_id']}`",
            "",
            "## 内容要点",
            "",
        ]
        if points:
            lines.extend(f"- {point}" for point in points)
        else:
            lines.append("- 当前规范化结果没有足够的可抽取正文；请查看原件与解析状态。")
        lines.extend(("", "## 文档结构", ""))
        if headings:
            lines.extend(f"- {heading}" for heading in headings)
        else:
            lines.append("- 未识别到稳定章节标题。")
        lines.extend(
            (
                "",
                "## 来源定位",
                "",
                f"- 规范化 Markdown：`{normalized_path}`",
                f"- Source ID：`{row['primary_source_id']}`",
                "",
                "> 本页是来源资料的抽取式整理，不包含投资评级、估值或仓位判断。",
                "",
            )
        )
        output_path = normalized_path.with_name("summary.md")
        _atomic_write(output_path, "\n".join(lines))
        content_hash = _sha256_file(output_path)
        artifact_id = "urn:company-wiki:artifact:sha256:" + hashlib.sha256(
            (row["document_id"] + "\0summary\0" + SUMMARIZER_VERSION).encode("utf-8")
        ).hexdigest()
        with store.transaction() as connection:
            connection.execute(
                """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,content_sha256,
                byte_size,mime_type,generator_name,generator_version,status,error,metadata_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(document_id,artifact_role,generator_name,generator_version) DO UPDATE SET
                path=excluded.path,content_sha256=excluded.content_sha256,byte_size=excluded.byte_size,
                status=excluded.status,error=excluded.error,metadata_json=excluded.metadata_json,created_at=excluded.created_at""",
                (
                    artifact_id,
                    row["document_id"],
                    row["primary_source_id"],
                    "summary",
                    str(output_path.resolve()),
                    content_hash,
                    output_path.stat().st_size,
                    "text/markdown",
                    _SUMMARIZER_NAME,
                    SUMMARIZER_VERSION,
                    summary_status,
                    None,
                    canonical_json(
                        {
                            "summary_method": "extractive",
                            "point_count": len(points),
                            "heading_count": len(headings),
                            "normalized_sha256": row["normalized_sha256"],
                        }
                    ),
                ),
            )
        if summary_status == "completed":
            completed += 1
        else:
            partial += 1
    return ProcessingReport("summarize", completed, skipped, partial, 0, failed)


__all__ = ["summarize_catalog"]
