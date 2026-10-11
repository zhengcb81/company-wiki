"""Cross-process pathless consumer probe (W06-CWP-PORTABILITY).

Run as a fresh short-lived process.  It accepts only a SourceRef plus a config
pointer — never a raw path — and reads the exact version through the official
``SourceVersionReader``.  A ``sys.addaudithook`` records every file open with
stack attribution, so any direct raw-file access outside the official reader is
observable evidence, not a silent violation.

stdout: one JSON line with the probe result.  Exit 0 only on a fully verified
byte read; exit 2 otherwise (result JSON still written when possible).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_WORKTREE_SRC = _ROOT / "src"
for _entry in (str(_WORKTREE_SRC), str(_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

_COMPANY_WIKI_PREFIX = (str(_WORKTREE_SRC / "company_wiki") + os.sep).lower()
_HARNESS_PREFIX = (str(Path(__file__).resolve().parent) + os.sep).lower()
_MAX_LOG_ENTRIES = 200


def _classify_attribution() -> str:
    """Walk frame objects only — no linecache/IO (an audit hook must not
    trigger the very opens it records).  Any company_wiki frame anywhere on
    the stack attributes the open to the official reader; a raw open with no
    reader frame (e.g. a sneaky consumer call) stays visible as harness/consumer.
    """
    frame = sys._getframe(1)
    saw_harness = False
    company_prefix = _COMPANY_WIKI_PREFIX.replace("\\", "/")
    harness_prefix = _HARNESS_PREFIX.replace("\\", "/")
    while frame is not None:
        filename = frame.f_code.co_filename.replace("\\", "/").lower()
        if filename.startswith(company_prefix):
            return "company_wiki"
        if filename.startswith(harness_prefix):
            saw_harness = True
        frame = frame.f_back
    return "harness" if saw_harness else "consumer"


def _normalized_prefix(path: Path) -> str:
    return os.path.normcase(str(path)) + os.sep


class OpenRecorder:
    """Audit-hook recorder: raw opens must be attributable to company_wiki."""

    def __init__(self, raw_roots: tuple[Path, ...], catalog_dir: Path | None):
        self._raw_roots = tuple(
            os.path.normcase(str(root.absolute())) + os.sep for root in raw_roots
        )
        self._catalog_dir = (
            os.path.normcase(str(catalog_dir.absolute())) + os.sep
            if catalog_dir else None
        )
        self.entries: list[dict[str, Any]] = []
        self.raw_non_reader_opens = 0
        self._active = False

    def _path_class(self, raw: Any) -> str:
        if not isinstance(raw, (str, bytes)):
            return "other"
        try:
            text = os.path.normcase(os.path.abspath(os_fsdecode(raw)))
        except (OSError, ValueError):
            return "other"
        for prefix in self._raw_roots:
            if text.startswith(prefix):
                return "raw"
        if self._catalog_dir is not None and text.startswith(self._catalog_dir):
            return "catalog"
        return "other"

    def __call__(self, event: str, args: tuple) -> None:
        if self._active:
            return
        if event == "open":
            path: Any = args[0] if args else None
        elif event == "sqlite3.connect":
            path = args[0] if args else None
        else:
            return
        self._active = True
        try:
            path_class = self._path_class(path)
            attributed_to = _classify_attribution()
            if path_class == "raw" and attributed_to != "company_wiki":
                self.raw_non_reader_opens += 1
            # Record only storage-touching classes; startup/import noise would
            # otherwise fill the bounded log before the reader runs.
            if path_class != "other" and len(self.entries) < _MAX_LOG_ENTRIES:
                self.entries.append({
                    "event": event,
                    "path_ref": _display_path(path),
                    "path_class": path_class,
                    "attributed_to": attributed_to,
                })
        finally:
            self._active = False


def os_fsdecode(value: Any) -> str:
    return os.fsdecode(value)


def _display_path(value: Any) -> str:
    try:
        text = os_fsdecode(value) if isinstance(value, (str, bytes)) else str(value)
    except Exception:  # noqa: BLE001 - display only
        return "<unrepresentable>"
    return text.replace("\\", "/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ref-json", type=Path, required=True,
                        help="file holding one SourceRef 2.0 object (no paths)")
    parser.add_argument("--raw-root", action="append", type=Path, default=[],
                        help="fixture lake root for raw-path classification")
    parser.add_argument("--catalog-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    recorder = OpenRecorder(tuple(args.raw_root), args.catalog_dir)
    sys.addaudithook(recorder)

    result: dict[str, Any] = {
        "pid": os.getpid(),
        "ref": None,
        "read_sha256": None,
        "byte_size": None,
        "status": "not_started",
        "reason": None,
        "raw_non_reader_opens": recorder.raw_non_reader_opens,
        "open_log": recorder.entries,
    }
    exit_code = 2
    try:
        raw_ref = json.loads(args.ref_json.read_text(encoding="utf-8"))
        from company_wiki.source_catalog.config import load_catalog_config
        from company_wiki.source_catalog.service import SourceCatalog
        from company_wiki.source_catalog.source_reader import (
            SourceRef,
            SourceVersionReader,
        )

        result["ref"] = {
            key: raw_ref[key]
            for key in ("document_id", "source_id", "content_sha256",
                        "byte_size", "mime_type", "schema_version")
        }
        ref = SourceRef(**raw_ref)
        catalog = SourceCatalog(load_catalog_config(args.config))
        try:
            reader = SourceVersionReader(catalog)
            opened = reader.open_version(ref, purpose="source_export")
        finally:
            catalog.close()
        digest = hashlib.sha256(opened.data).hexdigest()
        result.update({
            "status": "ok" if digest == ref.content_sha256 else "hash_mismatch",
            "read_sha256": digest,
            "byte_size": opened.byte_size,
            "bytes_origin": "fresh_read",
            "verification": {"byte_hash_match": digest == ref.content_sha256,
                             "sha_computed_from": "read_bytes"},
            "method": "open_version",
            "channel": "reader_verified_bytes",
            "receipt": {
                "policy_sha256": opened.policy_sha256,
                "source_read_policy_sha256": opened.source_read_policy_sha256,
                "read_at": opened.read_at,
            },
        })
        exit_code = 0 if digest == ref.content_sha256 else 2
    except Exception as exc:  # noqa: BLE001 - probe must report, never crash silently
        result.update({
            "status": getattr(exc, "status", None) or "error",
            "reason": getattr(exc, "reason", None) or f"{type(exc).__name__}: {exc}",
        })
    finally:
        result["raw_non_reader_opens"] = recorder.raw_non_reader_opens
        result["open_log"] = recorder.entries[:_MAX_LOG_ENTRIES]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"pid": result["pid"], "status": result["status"],
                          "read_sha256": result["read_sha256"],
                          "raw_non_reader_opens": result["raw_non_reader_opens"]},
                         ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
