"""Actual CLI import -> finite Worker -> summary -> public read; owned TEMP only."""

from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from support import narrative_batch_fixtures as fixtures
from support.native_document_fixtures import (
    DOCX_MIME,
    docx_business_qa,
    natural_html_call,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_source_flow import (
    prepare_official_narrative_request,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader

loopback_model_server = fixtures.loopback_model_server
REPO = Path(__file__).resolve().parents[2]


def environment():
    env = {
        key: os.environ[key]
        for key in (
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATH",
            "TEMP",
            "TMP",
            "USERPROFILE",
        )
        if key in os.environ
    }
    env.update(
        PYTHONPATH=os.pathsep.join([str(REPO / "src"), str(REPO / "scripts")]),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        DEEPSEEK_API_KEY=fixtures.KEY,
    )
    env[fixtures.KEY_ENV] = fixtures.KEY
    return env


def invoke(root, args, stdin=None, timeout=60):
    call = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", *args],
        cwd=root,
        env=environment(),
        input=None if stdin is None else json.dumps(stdin).encode("utf-8"),
        capture_output=True,
        timeout=timeout,
    )
    assert fixtures.KEY.encode() not in call.stdout + call.stderr, (
        "synthetic credential exposure"
    )
    assert call.returncode == 0, (
        "native CLI failed; output retained only by local pytest capture"
    )
    return call, json.loads(call.stdout)


def test_two_native_formats_full_cli_worker_reuse_restores_test_directory(
    loopback_model_server,
):
    with tempfile.TemporaryDirectory(prefix="cwW05-") as folder:
        test_dir = Path(folder)
        sentinel = test_dir / "keep.txt"
        sentinel.write_bytes(b"pre-existing independent fixture")
        baseline = {p.name: p.read_bytes() for p in test_dir.iterdir()}
        root = test_dir / "run"
        root.mkdir()
        companies = root / "companies"
        companies.mkdir()
        config = root / "config" / "catalog.json"
        config.parent.mkdir()
        config.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "catalog_dir": "catalog",
                    "roots": [
                        {
                            "root_id": "company_raw",
                            "path": "companies",
                            "kind": "company_raw",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        sources = [
            (docx_business_qa(), DOCX_MIME, "investor_relations", "unknown"),
            (natural_html_call(), "text/html", "investor_call_transcript", "en"),
        ]
        results = []
        for index, (body, mime, kind, language) in enumerate(sources):
            sha = hashlib.sha256(body).hexdigest()
            incoming = root / f"incoming{index}"
            incoming.write_bytes(body)
            request = {
                "schema_version": "official-source-import-request/1",
                "request_id": f"native-{index}",
                "source": {
                    "entity": "Acme",
                    "market": "US",
                    "security_id": "ACME",
                    "document_kind": kind,
                    "title": "Acme native business communication",
                    "publisher": "Acme",
                    "source_url": "https://issuer.example/native" + str(index),
                    "published_date": "2026-09-30",
                    "language": language,
                },
                "content_sha256": sha,
                "mime_type": mime,
                "max_bytes": 1048576,
                "capture_receipt": {
                    "capture_method": "local_document",
                    "tool_name": "w05-fixture",
                    "tool_call_id": f"original-{index}",
                    "captured_at": "2026-10-09T00:00:00Z",
                    "response_bytes": len(body),
                    "content_sha256": sha,
                },
            }
            req = root / f"import{index}.json"
            req.write_text(json.dumps(request), encoding="utf-8")
            call, result = invoke(
                root,
                [
                    "-m",
                    "company_wiki.source_catalog.official_source_cli",
                    "--config",
                    str(config),
                    "--project-root",
                    str(root),
                    "--input-file",
                    str(incoming),
                    "--request",
                    str(req),
                ],
            )
            assert str(root).encode() not in call.stdout
            assert result["source_ref"]["content_sha256"] == sha
            results.append(result)
        template = {
            "schema_version": "narrative-batch-request/1",
            "run_id": "w05-native",
            "profile": "P2",
            "max_seconds": 40,
            "max_tokens": 100000,
            "max_cost_usd": "1",
            "model": {
                "model_id": "stub-model",
                "endpoint": loopback_model_server.endpoint,
                "api_key_env": fixtures.KEY_ENV,
                "max_output_tokens": 8192,
                "timeout_seconds": 5,
                "allow_local_http": True,
            },
            "pricing": {
                "version": "fixture-price/1",
                "input_micro_usd_per_million_tokens": 1000000,
                "output_micro_usd_per_million_tokens": 2000000,
            },
        }
        batch = prepare_official_narrative_request(results, batch_template=template)
        req = root / "batch.json"
        req.write_text(json.dumps(batch.to_dict()), encoding="utf-8")
        llm = root / "llm.yaml"
        llm.write_text(
            json.dumps(
                {
                    "llm": {
                        "provider": "deepseek",
                        "model": "stub-model",
                        "base_url": loopback_model_server.endpoint.removesuffix(
                            "/chat/completions"
                        ),
                        "max_tokens": 8192,
                        "temperature": 0.7,
                    },
                    "search": {"api_key": "synthetic-unused-search"},
                    "paths": {"wiki_root": str(root)},
                }
            ),
            encoding="utf-8",
        )
        raw_before = {
            str(p.relative_to(companies)): p.read_bytes()
            for p in companies.rglob("*")
            if p.is_file()
        }
        command = [
            str(REPO / "scripts/narrative_batch_configured.py"),
            "--llm-config",
            str(llm),
            "--allow-local-model-http",
            "--project-root",
            str(root),
            "--catalog-config",
            str(config),
            "--automation-db",
            str(root / "AUTO.sqlite"),
            "--work-dir",
            str(root / "work"),
            "--request",
            str(req),
        ]
        _, output = invoke(root, command)
        assert (
            output["status"] == "completed"
            and len(loopback_model_server.requests) == 2
            and not loopback_model_server.errors
        )
        assert output["budget"]["unknown_reservations"] == 0
        for imported, (body, mime, kind, language) in zip(
            results, sources, strict=True
        ):
            _, reference = invoke(
                root,
                [
                    "-m",
                    "company_wiki.source_catalog.narrative_transport_cli",
                    "--config",
                    str(config),
                    "--operation",
                    "reference",
                ],
                {
                    "schema_version": "narrative-reference-request/1",
                    "source_ref": imported["source_ref"],
                },
            )
            call, bundle = invoke(
                root,
                [
                    "-m",
                    "company_wiki.source_catalog.narrative_transport_cli",
                    "--config",
                    str(config),
                    "--operation",
                    "read",
                ],
                {
                    "schema_version": "narrative-read-request/1",
                    "narrative_ref": reference,
                    "as_of_date": "2026-10-09",
                    "expected_source": {
                        "canonical_entity_id": None,
                        "market": "US",
                        "security_id": "ACME",
                        "document_kind": kind,
                        "fiscal_year": None,
                        "fiscal_period": None,
                    },
                },
            )
            receipt = json.loads(call.stderr)
            assert (
                receipt["replay_status"] == "verified"
                and hashlib.sha256(call.stdout).hexdigest()
                == reference["artifact_sha256"]
            )
            assert bundle["summary"]["translate"] is False and bundle["summary"][
                "draft"
            ]["language"] == ("zh" if language == "unknown" else language)
            assert bundle["evidence_spans"] and any(
                s["structured_value"]["source_role"] == "analyst"
                for s in bundle["evidence_spans"]
            )
            assert all(
                claim["evidence_ids"] for claim in bundle["summary"]["draft"]["claims"]
            )
            assert bundle["versions"]["parser"] == (
                "1.0.0" if mime == DOCX_MIME else "0.2.0"
            )
        _, repeat = invoke(root, command)
        assert (
            repeat["budget"] == output["budget"]
            and len(loopback_model_server.requests) == 2
        )
        assert raw_before == {
            str(p.relative_to(companies)): p.read_bytes()
            for p in companies.rglob("*")
            if p.is_file()
        }
        catalog = SourceCatalog(
            CatalogConfig(
                project_root=root,
                catalog_dir=root / "catalog",
                roots=(RootSpec("company_raw", companies, "company_raw"),),
            )
        )
        try:
            reader = SourceVersionReader(catalog)
            for result, (body, mime, kind, language) in zip(
                results, sources, strict=True
            ):
                ref = result["source_ref"]
                actual = reader.query_ref(
                    ref["document_id"], ref["source_id"], ref["content_sha256"]
                )
                assert reader.open_version(actual, purpose="source_export").data == body
            paths = [
                Path(row["absolute_path"])
                for row in catalog.store.fetchall(
                    "SELECT absolute_path FROM locations WHERE role='original_primary'"
                )
            ]
            assert any(p.suffix == ".docx" for p in paths) and any(
                p.suffix == ".html" for p in paths
            )
        finally:
            catalog.close()
        import shutil

        assert root.resolve().parent == test_dir.resolve()
        shutil.rmtree(root)
        assert baseline == {p.name: p.read_bytes() for p in test_dir.iterdir()}
    assert not test_dir.exists()
