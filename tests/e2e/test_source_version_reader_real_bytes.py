"""Real-byte gate for the first path-independent source reader slice.

Only allowlisted existing originals are read. All scans, mutations, catalog
files and fallback copies live under a unique pytest tmp_path child.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.scanner import R4_PROVENANCE_KEY
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
    SourceVersionReader,
)
from company_wiki.source_contract import SourceExportBundleV2


P06_SHA = "cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b"
STAR_SHA = "0d40d94aef8d2fa08c4c75760198be426a0b579be3d7200ec9450a7e04522b4f"
P06_SIZE = 5_595_592
STAR_SIZE = 1_794_755

P06_RELATIVE = Path(
    "三角防务/raw/research/"
    "三角防务：西安三角防务股份有限公司向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF"
)
STAR_RELATIVE = Path(
    "工业与信息化/软件与自动化控制/星环科技/"
    "星环科技：2025年年度报告.pdf"
)
P06_ORIGINAL = Path.home() / "Projects" / "company-wiki" / "companies" / P06_RELATIVE
STAR_ORIGINAL = Path.home() / "Dropbox" / "Stock" / STAR_RELATIVE
DAYU_STAR_RELATIVE = Path(
    "688031/filings/fil_cn_cd044bc0b6d88ca025885f43ed445e0b4c209822/"
    "fil_cn_cd044bc0b6d88ca025885f43ed445e0b4c209822.pdf"
)
DAYU_STAR_ORIGINAL = (
    Path.home() / "Projects" / "dayu-agent" / "workspace" / "portfolio"
    / DAYU_STAR_RELATIVE
)
DAYU_STAR_META = DAYU_STAR_ORIGINAL.parent / "meta.json"
DAYU_STAR_ENTITY_META = DAYU_STAR_ORIGINAL.parents[2] / "meta.json"


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".source.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _file_state(path: Path) -> tuple[str, int, int, int | None, str]:
    info = path.stat()
    return (
        str(path.resolve(strict=True)),
        info.st_size,
        info.st_mtime_ns,
        getattr(info, "st_file_attributes", None),
        _sha256(path),
    )


def _tree_state(root: Path) -> dict[str, tuple]:
    result: dict[str, tuple] = {}
    for path in (root, *sorted(root.rglob("*"))):
        info = path.lstat()
        assert not path.is_symlink(), f"unexpected link in test tree: {path}"
        assert not (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ), f"unexpected reparse point in test tree: {path}"
        key = "." if path == root else path.relative_to(root).as_posix()
        identity = (info.st_mtime_ns, getattr(info, "st_file_attributes", None))
        if path.is_dir():
            result[key] = ("directory", *identity)
        else:
            result[key] = ("file", info.st_size, *identity, _sha256(path))
    return result


def _available_originals(raw: Path, expected_sha: str, expected_size: int) -> dict[Path, tuple]:
    companion = _sidecar(raw)
    for path in (raw, companion):
        if not path.is_file():
            pytest.skip(f"real source input unavailable: {path}")
        info = path.stat()
        cloud_flags = sum(
            getattr(stat, name, 0)
            for name in (
                "FILE_ATTRIBUTE_OFFLINE",
                "FILE_ATTRIBUTE_RECALL_ON_OPEN",
                "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS",
                "FILE_ATTRIBUTE_REPARSE_POINT",
            )
        )
        if getattr(info, "st_file_attributes", 0) & cloud_flags:
            pytest.skip(f"real source input may require hydration: {path}")
    states = {path: _file_state(path) for path in (raw, companion)}
    assert states[raw][1] == expected_size
    assert states[raw][4] == expected_sha
    return states


def _available_files(paths: tuple[Path, ...]) -> dict[Path, tuple]:
    for path in paths:
        if not path.is_file():
            pytest.skip(f"real source input unavailable: {path}")
        info = path.stat()
        cloud_flags = sum(
            getattr(stat, name, 0)
            for name in (
                "FILE_ATTRIBUTE_OFFLINE",
                "FILE_ATTRIBUTE_RECALL_ON_OPEN",
                "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS",
                "FILE_ATTRIBUTE_REPARSE_POINT",
            )
        )
        if getattr(info, "st_file_attributes", 0) & cloud_flags:
            pytest.skip(f"real source input may require hydration: {path}")
    return {path: _file_state(path) for path in paths}


def _copy_checked(source: Path, target: Path, expected_sha: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    shutil.copyfile(source, target)
    assert _sha256(target) == expected_sha
    return target


def _forbid_external_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(*_args, **_kwargs):
        raise AssertionError("real-byte reader test attempted network or subprocess access")

    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket.socket, "connect_ex", refused)
    monkeypatch.setattr(socket, "create_connection", refused)
    monkeypatch.setattr(subprocess, "Popen", refused)


def _new_run(tmp_path: Path) -> tuple[Path, dict[str, tuple], os.stat_result, dict[str, tuple]]:
    baseline = _tree_state(tmp_path)
    parent_state = tmp_path.stat()
    fixed_tests = _tree_state(Path(__file__).parent)
    run_root = tmp_path / f"real-reader-{uuid.uuid4().hex}"
    assert not run_root.exists()
    run_root.mkdir()
    return run_root, baseline, parent_state, fixed_tests


def _finish_run(
    tmp_path: Path,
    run_root: Path,
    baseline: dict[str, tuple],
    parent_state: os.stat_result,
    fixed_tests: dict[str, tuple],
    original_states: dict[Path, tuple],
    catalog: SourceCatalog | None,
) -> None:
    if catalog is not None:
        catalog.close()
    if run_root.exists():
        intended_parent = tmp_path.resolve(strict=True)
        resolved = run_root.resolve(strict=True)
        assert resolved.parent == intended_parent
        assert run_root.name.startswith("real-reader-")
        _tree_state(run_root)
        shutil.rmtree(run_root)
    os.utime(tmp_path, ns=(parent_state.st_atime_ns, parent_state.st_mtime_ns))
    assert _tree_state(tmp_path) == baseline
    assert _tree_state(Path(__file__).parent) == fixed_tests
    assert {path: _file_state(path) for path in original_states} == original_states


def _catalog(run_root: Path, roots: tuple[RootSpec, ...]) -> SourceCatalog:
    assert all(root.path.is_relative_to(run_root) for root in roots)
    config = CatalogConfig(
        project_root=run_root,
        catalog_dir=run_root / "state" / "catalog",
        reusable_root_kinds=("company_raw", "directory"),
        roots=roots,
    )
    catalog = SourceCatalog(config)
    catalog.scan()
    return catalog


def _exact_row(catalog: SourceCatalog, digest: str) -> dict:
    row = catalog.reader.fetchone(
        """SELECT d.document_id, d.primary_source_id AS source_id,
                  s.content_sha256
           FROM documents d JOIN sources s
             ON s.source_id=d.primary_source_id
           WHERE d.source_status='active' AND s.content_sha256=?""",
        (digest,),
    )
    assert row is not None
    return dict(row)


def test_real_star_native_metadata_conflict_is_priority_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_states = _available_originals(STAR_ORIGINAL, STAR_SHA, STAR_SIZE)
    sidecar = _sidecar(STAR_ORIGINAL)
    original_states.update(_available_files((
        DAYU_STAR_ORIGINAL, DAYU_STAR_META, DAYU_STAR_ENTITY_META,
    )))
    assert original_states[DAYU_STAR_ORIGINAL][1] == STAR_SIZE
    assert original_states[DAYU_STAR_ORIGINAL][4] == STAR_SHA
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["content_sha256"] == STAR_SHA
    assert payload["document_kind"] == "annual_report"
    assert payload["fiscal_year"] == 2025
    assert payload["source_url"].startswith("https://")

    run_root, baseline, parent_state, fixed_tests = _new_run(tmp_path)
    catalogs: list[SourceCatalog] = []
    try:
        _forbid_external_actions(monkeypatch)
        dayu_root = run_root / "sandbox" / "dayu_portfolio"
        dropbox_root = run_root / "sandbox" / "dropbox_stock"
        dayu_file = _copy_checked(
            DAYU_STAR_ORIGINAL, dayu_root / DAYU_STAR_RELATIVE, STAR_SHA
        )
        _copy_checked(
            DAYU_STAR_META, dayu_file.parent / "meta.json",
            original_states[DAYU_STAR_META][4],
        )
        _copy_checked(
            DAYU_STAR_ENTITY_META,
            dayu_root / "688031" / "meta.json",
            original_states[DAYU_STAR_ENTITY_META][4],
        )
        dropbox_file = _copy_checked(
            STAR_ORIGINAL, dropbox_root / STAR_RELATIVE, STAR_SHA
        )
        sidecar_sha = original_states[sidecar][4]
        _copy_checked(sidecar, _sidecar(dropbox_file), sidecar_sha)

        request = SourceRequest(
            entity="星环科技", market="CN", security_id="688031",
            document_kind="annual_report", fiscal_year=2025,
            as_of_date="2026-09-27", mode="exact",
        )
        outcomes = []
        for name, dayu_priority, dropbox_priority in (
            ("dayu-first", 10, 20), ("dropbox-first", 20, 10),
        ):
            roots = (
                RootSpec(
                    "dayu_portfolio", dayu_root, "dayu_portfolio",
                    priority=dayu_priority, adapter_id="dayu_filing_v1",
                    read_only=True, reusable_for_filing=True,
                ),
                RootSpec(
                    "dropbox_stock", dropbox_root, "directory",
                    priority=dropbox_priority,
                    adapter_id="sidecar_filing_v1", read_only=True,
                    reusable_for_filing=True,
                ),
            )
            config = CatalogConfig(
                project_root=run_root,
                catalog_dir=run_root / "state" / name,
                reusable_root_kinds=("company_raw", "directory"),
                roots=roots,
            )
            catalog = SourceCatalog(config)
            catalog.scan()
            catalogs.append(catalog)
            locations = catalog.reader.fetchall(
                """SELECT l.root_id FROM locations l JOIN sources s
                     ON s.source_id=l.source_id
                   WHERE s.content_sha256=? AND l.role='original_primary'
                     AND l.location_status='active'""",
                (STAR_SHA,),
            )
            assert {row["root_id"] for row in locations} == {
                "dayu_portfolio", "dropbox_stock",
            }

            reader = SourceVersionReader(catalog)
            result = reader.query_local(request)
            assert result.status == "not_found", result
            assert result.reason == "no_local_match"
            row = _exact_row(catalog, STAR_SHA)
            ref = reader.query_ref(
                row["document_id"], row["source_id"], STAR_SHA
            )
            assert all(
                "path" not in key and "root" not in key and "location" not in key
                for key in asdict(ref)
            )
            with pytest.raises(SourceReadError) as error:
                reader.describe_version(ref)
            assert error.value.status == "blocked"
            assert error.value.reason == "metadata_conflict"

            version = catalog.reader.exact_source_version(ref.document_id)
            assert version is not None
            metadata = json.loads(version["metadata_json"])
            provenance = metadata.get(R4_PROVENANCE_KEY)
            assert isinstance(provenance, dict)
            field_records = provenance.get("fields")
            assert isinstance(field_records, dict)
            conflict_fields = tuple(sorted(
                key for key, record in field_records.items()
                if isinstance(record, dict) and record.get("conflicts")
            ))
            assert conflict_fields
            outcomes.append((ref.document_id, ref.source_id, conflict_fields))

        assert outcomes[0] == outcomes[1]
    finally:
        for catalog in reversed(catalogs):
            catalog.close()
        _finish_run(
            tmp_path, run_root, baseline, parent_state, fixed_tests,
            original_states, None,
        )


def test_real_p06_sparse_sidecar_preview_is_not_formal_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_states = _available_originals(P06_ORIGINAL, P06_SHA, P06_SIZE)
    sidecar = _sidecar(P06_ORIGINAL)
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert "fiscal_year" not in sidecar_payload
    assert "period_end" not in sidecar_payload
    assert "source_url" not in sidecar_payload

    run_root, baseline, parent_state, fixed_tests = _new_run(tmp_path)
    catalog = None
    try:
        _forbid_external_actions(monkeypatch)
        company_root = run_root / "sandbox" / "companies"
        staged = _copy_checked(P06_ORIGINAL, company_root / P06_RELATIVE, P06_SHA)
        _copy_checked(sidecar, _sidecar(staged), original_states[sidecar][4])
        root = RootSpec(
            "company_raw", company_root, "company_raw", priority=10,
            adapter_id="company_raw_v1", read_only=False,
            reusable_for_filing=True, canonical_write_target="companies",
        )
        catalog = _catalog(run_root, (root,))
        ids = _exact_row(catalog, P06_SHA)
        reader = SourceVersionReader(catalog)

        request = SourceRequest(
            entity="三角防务", market="CN", security_id="300775",
            document_kind="other", as_of_date="2026-09-27", mode="exact",
        )
        assert reader.query_local(request).status == "not_found"

        ref = reader.query_ref(ids["document_id"], ids["source_id"], P06_SHA)
        assert all(
            "path" not in key and "root" not in key and "location" not in key
            for key in asdict(ref)
        )
        preview = reader.open_version(ref, purpose="preview")
        assert preview.byte_size == P06_SIZE
        assert hashlib.sha256(preview.data).hexdigest() == P06_SHA
        with pytest.raises(SourceReadError) as error:
            reader.open_version(ref, purpose="filing_reuse")
        assert error.value.status == "blocked"
        assert error.value.reason == "capture_incomplete"
    finally:
        _finish_run(
            tmp_path, run_root, baseline, parent_state, fixed_tests,
            original_states, catalog,
        )


def test_real_p06_four_root_export_is_independent_of_root_names_and_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real PDF source keeps its exported identity across isolated roots."""
    original_states = _available_originals(P06_ORIGINAL, P06_SHA, P06_SIZE)
    run_root, baseline, parent_state, fixed_tests = _new_run(tmp_path)
    catalogs: list[SourceCatalog] = []
    try:
        _forbid_external_actions(monkeypatch)

        def make_roots(
            layout: str, labels: tuple[str, ...], priorities: tuple[int, ...]
        ) -> tuple[RootSpec, ...]:
            roots = []
            for label, priority in zip(labels, priorities, strict=True):
                root_path = run_root / "sandbox" / layout / label
                staged = _copy_checked(
                    P06_ORIGINAL, root_path / P06_RELATIVE, P06_SHA
                )
                _copy_checked(
                    _sidecar(P06_ORIGINAL),
                    _sidecar(staged),
                    original_states[_sidecar(P06_ORIGINAL)][4],
                )
                roots.append(RootSpec(
                    label, root_path, "company_raw", priority=priority,
                    adapter_id="company_raw_v1", read_only=True,
                    reusable_for_filing=True,
                    canonical_write_target="companies",
                ))
            return tuple(roots)

        def open_catalog(
            name: str, roots: tuple[RootSpec, ...]
        ) -> SourceCatalog:
            assert all(root.path.is_relative_to(run_root) for root in roots)
            config = CatalogConfig(
                project_root=run_root,
                catalog_dir=run_root / "state" / name,
                reusable_root_kinds=("company_raw", "directory"),
                roots=roots,
            )
            catalog = SourceCatalog(config)
            catalog.scan()
            catalogs.append(catalog)
            return catalog

        first = open_catalog(
            "catalog-first",
            make_roots("layout-first", ("root-a", "root-b", "root-c", "root-d"),
                       (10, 20, 30, 40)),
        )
        second = open_catalog(
            "catalog-relocated",
            make_roots("layout-relocated", ("vault-1", "vault-2", "vault-3", "vault-4"),
                       (40, 30, 20, 10)),
        )

        def export(catalog: SourceCatalog) -> dict:
            row = _exact_row(catalog, P06_SHA)
            reader = SourceVersionReader(catalog)
            ref = reader.query_ref(
                row["document_id"], row["source_id"], P06_SHA
            )
            bundle = SourceExportBundleV2.build(
                source_reader=reader, refs=(ref,), evidence_spans=(),
            )
            return bundle.to_dict()

        first_export = export(first)
        second_export = export(second)
        assert first_export == second_export
        assert first_export["counts"] == {
            "source_manifests": 1, "evidence_spans": 0,
        }
        manifest = first_export["manifests"][0]
        assert manifest["content_sha256"] == P06_SHA
        assert manifest["byte_size"] == P06_SIZE
        assert "path" not in first_export
        assert all(
            "path" not in field and "root" not in field
            for field in manifest
        )
        _forbid_external_actions(monkeypatch)
    finally:
        for catalog in reversed(catalogs):
            catalog.close()
        _finish_run(
            tmp_path, run_root, baseline, parent_state, fixed_tests,
            original_states, None,
        )
