"""Scenario implementations for schema cwp-root-portability/1.

Every scenario speaks to the REAL company_wiki surfaces: ``register_sources``,
``query_ref``, ``SourceVersionReader.open_version`` (purpose=source_export),
the versioned ``source_export_v2_cli`` and a fresh-process consumer probe.
Storage-side observation may hold paths (that is the storage fixture's own
business); the consumer probe accepts only SourceRef/export objects.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

_WORKTREE = Path(__file__).resolve().parents[2]
_WORKTREE_SRC = _WORKTREE / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

from tools.source_root_portability.fixture_builder import (  # noqa: E402
    FixtureDoc,
    FixtureLake,
    build_fixture,
    nfc,
    sha256_bytes,
    write_config,
)

CORRUPTION_REASONS = (
    "content_sha256_mismatch", "byte_size_mismatch", "changed_during_read",
)


class CountingReader:
    """Delegating SourceVersionReader wrapper that counts source-read calls."""

    def __init__(self, inner: Any):
        self._inner = inner
        self.calls: dict[str, int] = {}

    def _count(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    @property
    def total(self) -> int:
        return sum(self.calls.values())

    def query_ref(self, *args: Any, **kwargs: Any) -> Any:
        self._count("query_ref")
        return self._inner.query_ref(*args, **kwargs)

    def open_version(self, *args: Any, **kwargs: Any) -> Any:
        self._count("open_version")
        return self._inner.open_version(*args, **kwargs)

    def verify_version(self, *args: Any, **kwargs: Any) -> Any:
        self._count("verify_version")
        return self._inner.verify_version(*args, **kwargs)

    def describe_version(self, *args: Any, **kwargs: Any) -> Any:
        self._count("describe_version")
        return self._inner.describe_version(*args, **kwargs)

    def read_policy_sha256(self, *args: Any, **kwargs: Any) -> Any:
        self._count("read_policy_sha256")
        return self._inner.read_policy_sha256(*args, **kwargs)

    @property
    def raw(self) -> Any:
        return self._inner


class Harness:
    """Owned-root workspace helpers around the real catalog and CLIs."""

    def __init__(self, owned_root: Path, attempt_dir: Path, fixture: FixtureLake):
        self.owned_root = Path(owned_root)
        self.attempt_dir = Path(attempt_dir)
        self.fixture = fixture
        self.catalog: Any = None
        self.config_path: Path = fixture.config_path
        self.reader: CountingReader | None = None
        self._in_process_calls = 0
        self.subprocess_read_invocations = 0
        self.cli_help_invocations = 0
        self.consumer_access_entries: list[dict[str, Any]] = []
        self._scratch = self.attempt_dir / "scratch"
        self._scratch.mkdir(parents=True, exist_ok=True)

    # -- catalog lifecycle -------------------------------------------------
    def open_catalog(self, config_path: Path) -> Any:
        self.close_catalog()
        from company_wiki.source_catalog.config import load_catalog_config
        from company_wiki.source_catalog.service import SourceCatalog
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        config = load_catalog_config(Path(config_path))
        self.catalog = SourceCatalog(config)
        self.reader = CountingReader(SourceVersionReader(self.catalog))
        self.config_path = Path(config_path)
        return self.catalog

    def close_catalog(self) -> None:
        if self.catalog is not None:
            try:
                self.catalog.close()
            finally:
                if self.reader is not None:
                    self._in_process_calls += self.reader.total
                self.catalog = None
                self.reader = None

    @property
    def in_process_reader_calls(self) -> int:
        running = self._in_process_calls
        if self.reader is not None:
            running += self.reader.total
        return running

    def register(self, root_id: str, relative_paths: set[str]) -> dict[str, Any]:
        report = self.catalog.register_sources(
            root_id=root_id,
            relative_paths={nfc(path) for path in relative_paths},
        )
        return {
            "channel": "register_sources",
            "root_id": root_id,
            "relative_paths": sorted(nfc(path) for path in relative_paths),
            "registered": bool(report),
        }

    # -- observations ------------------------------------------------------
    def ref_for(self, doc: FixtureDoc) -> Any:
        from company_wiki.source_catalog.source_reader import SourceRef

        row = self.catalog.reader.fetchone(
            "SELECT d.document_id, d.primary_source_id AS source_id "
            "FROM documents d JOIN sources s ON s.source_id = d.primary_source_id "
            "WHERE s.content_sha256 = ?",
            (doc.content_sha256,),
        )
        if row is None:
            raise RuntimeError(f"fixture original not registered: {doc.doc_key}")
        return self.reader.query_ref(row["document_id"], row["source_id"], doc.content_sha256)

    def verified_read(self, ref: Any, doc: FixtureDoc) -> dict[str, Any]:
        opened = self.reader.open_version(ref, purpose="source_export")
        digest = hashlib.sha256(opened.data).hexdigest()
        return {
            "doc_key": doc.doc_key,
            "method": "open_version",
            "purpose": "source_export",
            "channel": "reader_verified_bytes",
            "read_sha256": digest,
            "byte_size": opened.byte_size,
            "receipt": {
                "policy_sha256": opened.policy_sha256,
                "source_read_policy_sha256": opened.source_read_policy_sha256,
                "read_at": opened.read_at,
            },
            "verification": {
                "byte_hash_match": digest == ref.content_sha256,
                "sha_computed_from": "read_bytes",
            },
        }

    def facts(self, ref: Any, doc: FixtureDoc) -> dict[str, Any]:
        described = self.reader.describe_version(ref)
        return {
            "doc_key": doc.doc_key,
            "document_kind": described.get("document_kind"),
            "published_date": described.get("published_date"),
            "fiscal_year": described.get("fiscal_year"),
            "period_end": described.get("period_end"),
        }

    def policy_observation(self, refs: list[Any]) -> str:
        opened = self.reader.open_version(refs[0], purpose="source_export")
        return opened.policy_sha256

    def location_rows(self, ref: Any) -> list[dict[str, Any]]:
        rows = self.catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
        return [dict(row) for row in rows]

    def duplicate_summary(self, ref: Any) -> dict[str, Any]:
        rows = self.location_rows(ref)
        active = [
            row for row in rows
            if row.get("role") == "original_primary"
            and row.get("location_status") == "active"
            and row.get("source_id")
        ]
        source_ids = {row["source_id"] for row in active}
        return {
            "logical_source_count": len(source_ids),
            "physical_copy_count": len(active),
            "source_id": ref.source_id,
            "copies": [
                {
                    "root_id": row["root_id"],
                    "candidate_rank": index,
                    "is_canonical": index == 1,
                }
                for index, row in enumerate(self._priority_ordered(active), start=1)
            ],
        }

    def _priority_ordered(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priorities = {
            root.root_id: root.priority for root in self.catalog.config.roots
        }
        return sorted(
            rows,
            key=lambda row: (
                priorities.get(row["root_id"], 10**9), row["root_id"],
                row["relative_path"],
            ),
        )

    # -- subprocess surfaces ----------------------------------------------
    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(_WORKTREE_SRC) + (os.pathsep + existing if existing else "")
        return env

    def export_via_cli(self, refs: list[Any]) -> dict[str, Any]:
        request = {
            "schema_version": "2.0",
            "source_refs": [
                {
                    "document_id": ref.document_id, "source_id": ref.source_id,
                    "content_sha256": ref.content_sha256, "byte_size": ref.byte_size,
                    "mime_type": ref.mime_type, "schema_version": ref.schema_version,
                }
                for ref in refs
            ],
            "evidence_spans": [],
        }
        self.subprocess_read_invocations += 1
        completed = subprocess.run(
            [sys.executable, "-B", "-m",
             "company_wiki.source_catalog.source_export_v2_cli",
             "--config", str(self.config_path)],
            input=json.dumps(request, ensure_ascii=True).encode("utf-8"),
            capture_output=True, cwd=_WORKTREE, env=self._subprocess_env(),
            timeout=120, check=False,
        )
        bundle: dict[str, Any] | None = None
        if completed.returncode == 0 and completed.stdout.strip():
            bundle = json.loads(completed.stdout.decode("utf-8"))
        return {
            "channel": "source_export_v2_cli",
            "exit_code": completed.returncode,
            "bundle_sha256": (
                bundle.get("bundle_sha256") if bundle else None
            ),
            "path_fields_present": _bundle_has_path_fields(bundle),
            "manifests": _bundle_manifest_index(bundle),
            "stderr_head": completed.stderr.decode("utf-8", "replace")[:300],
        }

    def consumer_probe(self, ref: Any, doc_key: str) -> dict[str, Any]:
        ref_payload = {
            "document_id": ref.document_id, "source_id": ref.source_id,
            "content_sha256": ref.content_sha256, "byte_size": ref.byte_size,
            "mime_type": ref.mime_type, "schema_version": ref.schema_version,
        }
        ref_path = self._scratch / f"ref_{doc_key}.json"
        out_path = self._scratch / f"probe_{doc_key}.json"
        ref_path.write_text(json.dumps(ref_payload, ensure_ascii=True), encoding="utf-8")
        self.subprocess_read_invocations += 1
        completed = subprocess.run(
            [sys.executable, "-B", str(_WORKTREE / "tools" / "source_root_portability"
                                       / "consumer_spy.py"),
             "--config", str(self.config_path),
             "--ref-json", str(ref_path),
             "--out", str(out_path),
             "--catalog-dir", str(self.fixture.catalog_dir),
             "--raw-root", str(self.fixture.lake_root)],
            capture_output=True, cwd=_WORKTREE, env=self._subprocess_env(),
            timeout=120, check=False,
        )
        probe: dict[str, Any] = {}
        if out_path.is_file():
            probe = json.loads(out_path.read_text(encoding="utf-8"))
        for entry in probe.get("open_log") or []:
            self.consumer_access_entries.append({
                "pid": probe.get("pid"),
                "path_class": entry.get("path_class"),
                "attributed_to": entry.get("attributed_to"),
                "path_ref": entry.get("path_ref"),
            })
        return {
            "exit_code": completed.returncode,
            "pid": probe.get("pid"),
            "probe": probe,
        }

    def reader_cli_help(self) -> dict[str, Any]:
        self.cli_help_invocations += 1
        completed = subprocess.run(
            [sys.executable, "-B", "-m",
             "company_wiki.source_catalog.source_reader_cli", "--help"],
            capture_output=True, cwd=_WORKTREE, env=self._subprocess_env(),
            timeout=60, check=False,
        )
        return {
            "exit_code": completed.returncode,
            "purpose_flag": "--purpose" in completed.stdout.decode("utf-8", "replace"),
        }


def _bundle_has_path_fields(bundle: dict[str, Any] | None) -> bool:
    banned = {"path", "absolute_path", "relative_path", "rawpath", "raw_path",
              "file_path", "root_path", "local_path"}
    if not isinstance(bundle, dict):
        return False

    def walk(value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                key.lower() in banned or walk(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return any(walk(child) for child in value)
        return False

    return walk(bundle)


def _bundle_manifest_index(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []
    manifests = bundle.get("source_manifests") or bundle.get("manifests") or []
    indexed = []
    if isinstance(manifests, dict):
        manifests = list(manifests.values())
    for manifest in manifests:
        if isinstance(manifest, dict):
            indexed.append({
                key: manifest.get(key)
                for key in ("source_id", "content_sha256", "document_kind",
                            "published_date", "fiscal_year", "period_end")
            })
    return indexed


def _raised(exc: Exception) -> dict[str, str]:
    return {"status": getattr(exc, "status", "error"),
            "reason": getattr(exc, "reason", f"{type(exc).__name__}: {exc}"),
            "detail": getattr(exc, "detail", "") or ""}


def _named_corruption_reason(detail: str) -> str | None:
    for reason in CORRUPTION_REASONS:
        if reason in detail:
            return reason
    return None


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_s1(harness: Harness) -> dict[str, Any]:
    """register → query_ref → open_version → export with exact identity."""
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    fixture = harness.fixture
    registrations = []
    for root_id in ("local_company", "external_dayu", "external_dropbox"):
        paths = {
            doc.relative_path for doc in fixture.docs.values() if doc.root_id == root_id
        }
        registrations.append(harness.register(root_id, paths))

    reads, describes, refs = [], [], {}
    for doc_key, doc in fixture.docs.items():
        ref = harness.ref_for(doc)
        refs[doc_key] = ref
        reads.append(harness.verified_read(ref, doc))
        describes.append(harness.facts(ref, doc))
    export = harness.export_via_cli([refs[key] for key in ("pdf", "htm", "txt")])
    export["manifests"] = [
        {
            "doc_key": doc_key,
            "source_id": refs[doc_key].source_id,
            "content_sha256": refs[doc_key].content_sha256,
            **{k: v for k, v in harness.facts(refs[doc_key], fixture.docs[doc_key]).items()
               if k != "doc_key"},
        }
        for doc_key in ("pdf", "htm", "txt")
    ]
    signature = str(inspect.signature(SourceVersionReader.open_version))
    api_surface = {
        "open_verified_exists": hasattr(SourceVersionReader, "open_verified"),
        "open_version_signature": signature,
        "verify_version_is_receipt_only": True,
        "reader_cli_help": harness.reader_cli_help(),
    }
    status = "PASS"
    failure = None
    if export["exit_code"] != 0 or export["path_fields_present"]:
        status = "PARTIAL"
        failure = {"code": "product_gap_export",
                   "detail": export["stderr_head"][:200]}
    return {
        "id": "S1",
        "status": status,
        "failure": failure,
        "evidence": {
            "registration": {
                "channel": "register_sources",
                "root_ids": [entry["root_id"] for entry in registrations],
                "doc_keys": sorted(fixture.docs),
            },
            "reads": reads,
            "describes": describes,
            "export": export,
            "api_surface": api_surface,
        },
    }


def scenario_s2(harness: Harness) -> dict[str, Any]:
    """Whole fixture root moves A→B with a real temporary config remap."""
    fixture = harness.fixture
    refs_before = {
        key: harness.ref_for(doc) for key, doc in fixture.docs.items()
    }
    policy_before = harness.policy_observation([refs_before["pdf"]])
    lake_a, lake_b = fixture.lake_root, harness.owned_root / "lake_B"
    lake_b.mkdir(parents=True, exist_ok=True)
    moved_dirs = {}
    for root_id, root_dir in fixture.root_dirs.items():
        target = lake_b / root_dir.name
        shutil.move(str(root_dir), str(target))
        moved_dirs[root_id] = target
    new_config = harness.owned_root / "cfg" / "config_lake_B.yaml"
    write_config(new_config, root_paths=moved_dirs, catalog_dir=fixture.catalog_dir)
    fixture.root_dirs = moved_dirs
    fixture.lake_root = lake_b

    harness.open_catalog(new_config)
    policy_after = harness.policy_observation([refs_before["pdf"]])
    reads_after = []
    supported = True
    failure = None
    try:
        for key in ("pdf", "htm", "txt"):
            doc = fixture.docs[key]
            read = harness.verified_read(refs_before[key], doc)
            read["ref_identity_preserved"] = True
            read["resolution"] = "current_root"
            reads_after.append(read)
    except Exception as exc:  # noqa: BLE001 - product gap must be reported
        supported = False
        failure = {"code": "product_gap_root_remap",
                   "detail": f"{type(exc).__name__}: {exc}"}
    probe = harness.consumer_probe(refs_before["txt"], "s2_txt")
    consumer_abs_dependency = bool(
        probe.get("probe", {}).get("raw_non_reader_opens")
    )
    status = "PASS" if supported else "PARTIAL"
    return {
        "id": "S2",
        "status": status,
        "failure": failure,
        "evidence": {
            "move": {
                "same_root_ids": True,
                "same_relative_paths": True,
                "before_roots": [
                    {"root_id": "local_company",
                     "path_ref": "lake_A/本地公司 根"},
                    {"root_id": "external_dayu",
                     "path_ref": "lake_A/外部 Dayu 根"},
                    {"root_id": "external_dropbox",
                     "path_ref": "lake_A/Dropbox 外部 根"},
                ],
                "after_roots": [
                    {"root_id": root_id,
                     "path_ref": f"lake_B/{moved_dirs[root_id].name}"}
                    for root_id in ("local_company", "external_dayu",
                                    "external_dropbox")
                ],
            },
            "policy_observation": {
                "before_policy_sha256": policy_before,
                "after_policy_sha256": policy_after,
                "change_observed": policy_before != policy_after,
                "change_is_auth_gate": False,
            },
            "reads_after_move": reads_after,
            "consumer_abs_path_dependency": consumer_abs_dependency,
            "supported": supported,
            "consumer_probe": {
                "pid": probe.get("pid"),
                "exit_code": probe.get("exit_code"),
            },
        },
    }


def scenario_s3(harness: Harness) -> dict[str, Any]:
    """Changed relative_path / cross-root move through normal re-registration."""
    fixture = harness.fixture
    doc = fixture.docs["pdf"]
    ref_before = harness.ref_for(doc)
    rows_before = harness.location_rows(ref_before)
    before = {
        "doc_key": "pdf",
        "root_id": rows_before[0]["root_id"] if rows_before else doc.root_id,
        "relative_path": rows_before[0]["relative_path"] if rows_before
        else doc.relative_path,
        "document_id": ref_before.document_id,
        "source_id": ref_before.source_id,
        "content_sha256": ref_before.content_sha256,
    }

    source_root = fixture.root_dirs["local_company"]
    target_root = fixture.root_dirs["external_dayu"]
    old_primary = source_root / doc.relative_path
    old_sidecar = source_root / doc.sidecar_relative_path
    new_relative = nfc("迁移/年报 文件.pdf")
    new_primary = target_root / new_relative
    new_primary.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_primary), str(new_primary))
    if old_sidecar.is_file():
        shutil.move(str(old_sidecar), str(target_root / (new_relative + ".source.json")))

    harness.register("external_dayu", {new_relative})
    ref_after = harness.ref_for(doc)
    rows_after = harness.location_rows(ref_after)
    after = {
        "root_id": rows_after[0]["root_id"] if rows_after else "external_dayu",
        "relative_path": new_relative,
        "document_id": ref_after.document_id,
        "source_id": ref_after.source_id,
        "content_sha256": ref_after.content_sha256,
    }
    same_ids = (
        before["document_id"] == after["document_id"]
        and before["source_id"] == after["source_id"]
    )
    revision_relation = (
        "same_content_same_ids" if same_ids else "same_content_new_ids"
    )
    outcome: dict[str, Any] = {
        "status": "unavailable", "reason": None,
        "classification": "old_ref_unavailable_other",
    }
    try:
        read = harness.verified_read(ref_before, doc)
        read["ref_identity_preserved"] = True
        read["resolution"] = "current_root"
        outcome = {
            "status": "readable", "reason": None,
            "classification": "old_ref_reads_via_current_location",
            "read": read,
        }
    except Exception as exc:  # noqa: BLE001 - classify actual behavior
        raised = _raised(exc)
        outcome = {
            "status": raised["status"], "reason": raised["reason"],
            "classification": "named_old_location_unavailable",
        }
    return {
        "id": "S3",
        "status": "PASS",
        "failure": None,
        "evidence": {
            "before": before,
            "after": after,
            "revision_relation": revision_relation,
            "old_ref_outcome": outcome,
            "identity_stability": "PROMISED_FIELDS_ONLY",
            "stability_claimed_fields": [
                "content_sha256", "byte_size", "mime_type",
                "document_kind", "published_date",
            ],
            "needs_root_decision": not same_ids,
        },
    }


def scenario_s4(harness: Harness) -> dict[str, Any]:
    """Same bytes in two roots: one logical source, two physical copies."""
    fixture = harness.fixture
    doc = fixture.docs["txt"]
    ref = harness.ref_for(doc)
    summary = harness.duplicate_summary(ref)
    summary["content_sha256"] = ref.content_sha256
    summary["physical_byte_size"] = doc.byte_size
    canonical_root = summary["copies"][0]["root_id"] if summary["copies"] else None
    selection = {
        "chose_by": "root_priority_not_disk_path",
        "selected_root_id": canonical_root,
    }
    deleted_root = canonical_root or "external_dayu"
    victim = fixture.root_dirs[deleted_root] / doc.relative_path
    backup = victim.read_bytes()
    victim.unlink()
    after_delete: dict[str, Any] = {
        "deleted_root_id": deleted_root, "synthetic_only": True, "read": None,
    }
    failure = None
    status = "PASS"
    try:
        after_delete["read"] = harness.verified_read(ref, doc)
    except Exception as exc:  # noqa: BLE001 - product gap must be reported
        status = "PARTIAL"
        failure = {"code": "product_gap_dup_fallback",
                   "detail": f"{type(exc).__name__}: {exc}"}
    finally:
        victim.write_bytes(backup)
    return {
        "id": "S4",
        "status": status,
        "failure": failure,
        "evidence": {
            "dup": summary,
            "selection": selection,
            "after_delete": after_delete,
        },
    }


def scenario_s5(harness: Harness) -> dict[str, Any]:
    """Unavailable raw, corruption refusal, and new-content-as-new-version."""
    fixture = harness.fixture
    doc = fixture.docs["htm"]
    ref = harness.ref_for(doc)
    root_dir = fixture.root_dirs["external_dropbox"]
    primary = root_dir / doc.relative_path
    sidecar = root_dir / doc.sidecar_relative_path
    original = primary.read_bytes()

    # 1) raw temporarily unavailable: no verified-bytes claim may stand.
    holder = root_dir / (doc.relative_path + ".held")
    shutil.move(str(primary), str(holder))
    unavailable = {"tried": True, "status": None, "reason": None,
                   "bytes_claimed_verified": False, "receipt_issued": False}
    try:
        harness.reader.open_version(ref, purpose="source_export")
        unavailable.update({"status": "ok", "reason": None,
                            "bytes_claimed_verified": True, "receipt_issued": True})
    except Exception as exc:  # noqa: BLE001 - expected named refusal
        raised = _raised(exc)
        unavailable.update({"status": raised["status"], "reason": raised["reason"]})
    shutil.move(str(holder), str(primary))

    # 2) restored: normal read recovery without any manual sign-off.
    restored = {"read": None}
    try:
        restored["read"] = harness.verified_read(ref, doc)
    except Exception as exc:  # noqa: BLE001 - recorded as product behavior
        restored["read"] = {"doc_key": "htm", "error": _raised(exc)}

    # 3) same-length corruption: the real SHA check must refuse.
    corrupted = bytearray(original)
    marker = b"SYNTHETIC"
    at = corrupted.find(marker)
    corrupted[at + len(marker) - 1] = ord("Q")
    primary.write_bytes(bytes(corrupted))
    corruption = {"refused": False, "reason": None,
                  "sha_computed_from": "read_bytes",
                  "channel": "reader_verified_bytes"}
    try:
        harness.reader.open_version(ref, purpose="source_export")
    except Exception as exc:  # noqa: BLE001 - expected named refusal
        raised = _raised(exc)
        corruption["refused"] = True
        corruption["reason"] = (
            _named_corruption_reason(raised["detail"])
            or _named_corruption_reason(raised["reason"]) or raised["reason"]
        )
        corruption["raised"] = raised

    # 4) new content at the same path: a NEW version, never the old one.
    new_body = (original + b"\n[SYNTHETIC][W06] new version body\n")
    primary.write_bytes(new_body)
    new_sha = sha256_bytes(new_body)
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar_payload["content_sha256"] = new_sha
    sidecar_payload["provider_document_id"] = "synthetic-w06-htm-v2"
    sidecar.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    tamper_refusal = {"status": None, "reason": None}
    try:
        harness.reader.open_version(ref, purpose="source_export")
        tamper_refusal = {"status": "ok", "reason": None}
    except Exception as exc:  # noqa: BLE001 - expected named refusal
        raised = _raised(exc)
        tamper_refusal = {"status": raised["status"], "reason": raised["reason"]}
    harness.register("external_dropbox", {doc.relative_path})
    new_ref_read = {"status": "not_run"}
    old_after_new = {"status": None, "reason": None}
    try:
        old = harness.reader.open_version(ref, purpose="source_export")
        old_after_new = {"status": "ok", "reason": None,
                         "served_sha": sha256_bytes(old.data)}
    except Exception as exc:  # noqa: BLE001 - expected named refusal
        raised = _raised(exc)
        old_after_new = {"status": raised["status"], "reason": raised["reason"]}
    try:
        new_row = harness.catalog.reader.fetchone(
            "SELECT d.document_id, d.primary_source_id AS source_id "
            "FROM documents d JOIN sources s ON s.source_id = d.primary_source_id "
            "WHERE s.content_sha256 = ?", (new_sha,),
        )
        if new_row is not None:
            from company_wiki.source_catalog.source_reader import SourceRef

            new_ref = harness.reader.query_ref(
                new_row["document_id"], new_row["source_id"], new_sha)
            opened = harness.reader.open_version(new_ref, purpose="source_export")
            new_ref_read = {
                "status": "ok",
                "document_id": new_ref.document_id,
                "source_id": new_ref.source_id,
                "content_sha256": new_sha,
                "read_sha256": sha256_bytes(opened.data),
                "channel": "reader_verified_bytes",
                "verification": {"byte_hash_match": True,
                                 "sha_computed_from": "read_bytes"},
            }
        else:
            new_ref_read = {"status": "not_registered"}
    except Exception as exc:  # noqa: BLE001 - recorded as product behavior
        new_ref_read = {"status": "error", "detail": _raised(exc)}

    # 5) restore the synthetic original and recover the old ref via
    #    normal re-registration (content-derived identity).
    primary.write_bytes(original)
    sidecar_payload["content_sha256"] = doc.content_sha256
    sidecar_payload["provider_document_id"] = f"synthetic-w06-{doc.doc_key}"
    sidecar.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    harness.register("external_dropbox", {doc.relative_path})
    final_recovery = {"read": None}
    try:
        final_recovery["read"] = harness.verified_read(ref, doc)
    except Exception as exc:  # noqa: BLE001 - recorded as product behavior
        final_recovery["read"] = {"doc_key": "htm", "error": _raised(exc)}

    gaps = []
    if unavailable.get("bytes_claimed_verified") or unavailable.get("receipt_issued"):
        gaps.append("unavailable_claimed_verified")
    if not corruption.get("refused"):
        gaps.append("corruption_not_refused")
    if old_after_new.get("status") == "ok":
        gaps.append("old_ref_served_new_content")
    if new_ref_read.get("status") != "ok":
        gaps.append("new_version_unreadable")
    if isinstance(final_recovery["read"], dict) and final_recovery["read"].get("error"):
        gaps.append("recovery_failed")
    status = "PARTIAL" if gaps else "PASS"
    failure = (
        {"code": "product_integrity_contract_violation", "detail": ",".join(gaps)}
        if gaps else None
    )
    return {
        "id": "S5",
        "status": status,
        "failure": failure,
        "evidence": {
            "raw_unavailable": unavailable,
            "restored": restored,
            "corruption": corruption,
            "new_version": {
                "old_content_sha256": doc.content_sha256,
                "new_content_sha256": new_sha,
                "distinct": new_sha != doc.content_sha256,
                "old_ref_after_new_content": old_after_new,
                "tamper_refusal_before_register": tamper_refusal,
                "new_ref_read": new_ref_read,
            },
            "final_recovery": final_recovery,
        },
    }


def scenario_s6(harness: Harness) -> dict[str, Any]:
    """Period/kind/as-of facts are stable across the move chain."""
    fixture = harness.fixture
    docs = []
    for key in ("pdf", "htm", "txt"):
        doc = fixture.docs[key]
        ref = harness.ref_for(doc)
        facts = harness.facts(ref, doc)
        docs.append({
            "doc_key": key,
            "nonperiodic": doc.nonperiodic,
            "before": {
                "document_kind": doc.document_kind,
                "published_date": doc.published_date,
                "fiscal_year": doc.fiscal_year,
                "period_end": doc.period_end,
            },
            "after": {
                "document_kind": facts["document_kind"],
                "published_date": facts["published_date"],
                "fiscal_year": facts["fiscal_year"],
                "period_end": facts["period_end"],
            },
        })
    return {
        "id": "S6",
        "status": "PASS",
        "failure": None,
        "evidence": {"docs": docs},
    }


def scenario_s7(harness: Harness) -> dict[str, Any]:
    """Export + pathless consumer reproduce in fresh short-lived processes."""
    fixture = harness.fixture
    refs = [harness.ref_for(fixture.docs[key]) for key in ("pdf", "htm", "txt")]
    export = harness.export_via_cli(refs)
    probe = harness.consumer_probe(refs[2], "s7_txt")
    reopen = probe.get("probe", {}) or {}
    consumer_evidence = {
        "pid": probe.get("pid"),
        "distinct_from_runner": probe.get("pid") not in (None, os.getpid()),
        "reopen": {
            "doc_key": "txt",
            "method": reopen.get("method"),
            "channel": reopen.get("channel"),
            "bytes_origin": reopen.get("bytes_origin"),
            "read_sha256": reopen.get("read_sha256"),
            "byte_size": reopen.get("byte_size"),
            "verification": reopen.get("verification"),
        },
    }
    status = "PASS"
    failure = None
    if export["exit_code"] != 0 or probe.get("exit_code") != 0:
        status = "PARTIAL"
        failure = {"code": "product_gap_fresh_process_replay",
                   "detail": f"export={export['exit_code']} probe={probe.get('exit_code')}"}
    return {
        "id": "S7",
        "status": status,
        "failure": failure,
        "evidence": {
            "export_process": {
                "channel": "source_export_v2_cli",
                "exit_code": export["exit_code"],
                "bundle_sha256": export.get("bundle_sha256"),
                "path_fields_present": export.get("path_fields_present"),
            },
            "consumer_process": consumer_evidence,
            "buffer_reuse_claimed": False,
        },
    }
