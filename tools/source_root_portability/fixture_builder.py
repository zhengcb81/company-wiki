"""Synthetic fixture lake for the W06-CWP-PORTABILITY migration harness.

Builds at most six synthetic originals across three configured roots whose
directory names contain spaces and Chinese characters, with explicit
``[SYNTHETIC]`` metadata and fixed dates.  Registration is always precise
(``register_sources``); nothing here scans or touches production roots, and no
real Dayu/Dropbox service or directory is ever accessed — the root ids
``local_company`` / ``external_dayu`` / ``external_dropbox`` only simulate three
storage locations.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SYNTHETIC = True
NONPERIODIC_MARKER = "nonperiodic"
FIXTURE_ROOT_SPECS = (
    {"root_id": "local_company", "dir_name": "本地公司 根", "priority": 10},
    {"root_id": "external_dayu", "dir_name": "外部 Dayu 根", "priority": 20},
    {"root_id": "external_dropbox", "dir_name": "Dropbox 外部 根", "priority": 30},
)
CONFIG_ROOT_IDS = ("local_company", "external_dayu", "external_dropbox")

_PDF_TEXT = "[SYNTHETIC][W06] 年度报告 fixture original — not a real filing."
_HTML_TEXT = (
    "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
    "<title>[SYNTHETIC][W06] 募集说明书 fixture</title></head>"
    "<body><p>【合成样本】本文件为 W06 迁移回归夹具，非真实募集说明书。</p></body></html>\n"
)
_TXT_TEXT = (
    "【合成样本 / SYNTHETIC】业绩说明会纪要（W06 迁移回归夹具）\n"
    "本文件为原语言文本原件，仅用于虚拟存储根迁移与引用回放测试，"
    "不构成任何真实公司资料或投资建议。\n"
    "2026-04-10 固定日期样本。\n"
)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def minimal_pdf_bytes(text: str) -> bytes:
    """A structurally valid one-page PDF-1.4 with a correct xref table."""

    def obj(number: int, body: bytes) -> bytes:
        return f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    stream = f"BT /F1 10 Tf 20 100 Td ({text}) Tj ET".encode("ascii", "replace")
    body_stream = obj(
        4,
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
    )
    objects = [
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
               b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        body_stream,
        obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
    ]
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    position = len(header)
    for body in objects:
        offsets.append(position)
        position += len(body)
    xref_offset = position
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for offset in offsets:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
    )
    return header + b"".join(objects) + b"".join(xref) + trailer


@dataclass(frozen=True)
class FixtureDoc:
    doc_key: str
    root_id: str
    relative_path: str
    mime_type: str
    document_kind: str
    published_date: str
    fiscal_year: int | None
    period_end: str | None
    nonperiodic: bool
    body: bytes
    content_sha256: str
    byte_size: int
    sidecar_relative_path: str
    is_physical_copy_of: str | None = None

    def sidecar_payload(self) -> dict[str, Any]:
        # The sidecar_filing_v1 completeness contract (WU-701 N-02) requires
        # fiscal_year and period_end on every complete sidecar.  Nonperiodic
        # originals declare an explicit non-period marker instead of a year:
        # the marker satisfies completeness while describe_version still
        # reports fiscal_year=None (it only accepts four-digit years), so an
        # IR/prospectus original never acquires a fictitious FY.
        return {
            "schema_version": "1.0",
            "canonical_entity_id": "ent-synthetic-w06",
            "display_name": "[SYNTHETIC] W06 Fixture Co",
            "company_name": "[SYNTHETIC] W06 Fixture Co",
            "market": "CN",
            "security_id": "W06TEST",
            "document_kind": self.document_kind,
            "source_title": f"[SYNTHETIC][W06] {self.doc_key} fixture original",
            "fiscal_year": NONPERIODIC_MARKER if self.nonperiodic else self.fiscal_year,
            "period_end": NONPERIODIC_MARKER if self.nonperiodic else self.period_end,
            "filing_date": self.published_date,
            "form_type": self.document_kind,
            "language": "zh",
            "provider": "example-filing",
            "provider_document_id": f"synthetic-w06-{self.doc_key}",
            "collector_name": "w06-fixture-builder",
            "collector_version": "1.0",
            "retrieved_at": f"{self.published_date}T00:00:00Z",
            "content_sha256": self.content_sha256,
        }


@dataclass
class FixtureLake:
    """The built lake: root paths, originals, and the config-remap helpers."""

    owned_root: Path
    lake_root: Path
    catalog_dir: Path
    config_path: Path
    docs: dict[str, FixtureDoc] = field(default_factory=dict)
    root_dirs: dict[str, Path] = field(default_factory=dict)

    def original_manifest(self) -> list[dict[str, Any]]:
        entries = []
        for doc in self.docs.values():
            entries.append({
                "doc_key": doc.doc_key,
                "root_id": doc.root_id,
                "relative_path": doc.relative_path,
                "content_sha256": doc.content_sha256,
                "byte_size": doc.byte_size,
                "mime_type": doc.mime_type,
                "document_kind": doc.document_kind,
                "published_date": doc.published_date,
                "fiscal_year": doc.fiscal_year,
                "period_end": doc.period_end,
                "nonperiodic": doc.nonperiodic,
                "synthetic": SYNTHETIC,
                "is_physical_copy_of": doc.is_physical_copy_of,
            })
        return entries


def fixture_docs() -> dict[str, FixtureDoc]:
    pdf_body = minimal_pdf_bytes(_PDF_TEXT)
    html_body = _HTML_TEXT.encode("utf-8")
    txt_body = _TXT_TEXT.encode("utf-8")

    def make(doc_key: str, root_id: str, relative_path: str, mime_type: str,
             document_kind: str, published_date: str, fiscal_year: int | None,
             period_end: str | None, nonperiodic: bool, body: bytes,
             is_physical_copy_of: str | None) -> FixtureDoc:
        relative = nfc(relative_path)
        return FixtureDoc(
            doc_key=doc_key,
            root_id=root_id,
            relative_path=relative,
            mime_type=mime_type,
            document_kind=document_kind,
            published_date=published_date,
            fiscal_year=fiscal_year,
            period_end=period_end,
            nonperiodic=nonperiodic,
            body=body,
            content_sha256=sha256_bytes(body),
            byte_size=len(body),
            sidecar_relative_path=relative + ".source.json",
            is_physical_copy_of=is_physical_copy_of,
        )

    docs = {
        "pdf": make(
            "pdf", "local_company", "2025 年度报告/年报 文件.pdf",
            "application/pdf", "annual_report", "2026-03-01", 2025,
            "2025-12-31", False, pdf_body, None,
        ),
        "htm": make(
            "htm", "external_dropbox", "募集说明书 文件.html",
            "text/html", "prospectus", "2026-05-06", None, NONPERIODIC_MARKER, True,
            html_body, None,
        ),
        "txt": make(
            "txt", "external_dayu", "业绩说明会 纪要.txt",
            "text/plain", "investor_relations", "2026-04-10", None, NONPERIODIC_MARKER, True,
            txt_body, None,
        ),
    }
    docs["txt_copy"] = make(
        "txt_copy", "external_dropbox", "副本/业绩说明会 纪要.txt",
        "text/plain", "investor_relations", "2026-04-10", None, NONPERIODIC_MARKER, True,
        txt_body, "txt",
    )
    return docs


def write_config(path: Path, *, root_paths: dict[str, Path], catalog_dir: Path) -> None:
    """Write a real temporary source-catalog YAML config (schema_version 1.0)."""
    lines = [
        'schema_version: "1.0"',
        f"catalog_dir: {_yaml_path(catalog_dir)}",
        "roots:",
    ]
    for spec in FIXTURE_ROOT_SPECS:
        root_id = spec["root_id"]
        lines += [
            f"  - root_id: {root_id}",
            f"    path: {_yaml_path(root_paths[root_id])}",
            "    kind: directory",
            f"    priority: {spec['priority']}",
            "    adapter_id: sidecar_filing_v1",
            "    read_only: true",
            "    reusable_for_filing: true",
            "    routes:",
            '      - include: ["*"]',
        ]
    lines += ["reusable_root_kinds:", "  - directory"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _yaml_path(path: Path) -> str:
    text = str(path).replace("\\", "/")
    if ":" in text or " " in text or any(ord(ch) > 127 for ch in text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def build_fixture(owned_root: Path, *, lake_name: str = "lake_A") -> FixtureLake:
    """Materialize the synthetic lake under ``owned_root/lake_name``.

    The owned root must not contain prior generated content; baseline/sentinel
    bookkeeping belongs to the runner.
    """
    owned_root = Path(owned_root)
    lake_root = owned_root / lake_name
    catalog_dir = owned_root / "catalog"
    config_path = owned_root / "cfg" / f"config_{lake_name}.yaml"
    root_dirs: dict[str, Path] = {}
    for spec in FIXTURE_ROOT_SPECS:
        root_dir = lake_root / nfc(spec["dir_name"])
        root_dir.mkdir(parents=True, exist_ok=False)
        root_dirs[spec["root_id"]] = root_dir

    docs = fixture_docs()
    for doc in docs.values():
        root_dir = root_dirs[doc.root_id]
        target = root_dir / doc.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(doc.body)
        sidecar = root_dir / doc.sidecar_relative_path
        sidecar.write_text(
            json.dumps(doc.sidecar_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    write_config(
        config_path,
        root_paths=root_dirs,
        catalog_dir=catalog_dir,
    )
    return FixtureLake(
        owned_root=owned_root,
        lake_root=lake_root,
        catalog_dir=catalog_dir,
        config_path=config_path,
        docs=docs,
        root_dirs=root_dirs,
    )
