"""Major-node local HTTP/public-byte check; no supplier or real forecast claim.

RF_NARRATIVE_CODE_ROOT and STOCKWIKI_NARRATIVE_CODE_ROOT select isolated consumer
checkouts. Ordinary CI need not contain sibling repositories. The source and
artifact are created by current CWP handlers, not handwritten exported JSON.
"""

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation import narrative_batch as batch
from integration.test_narrative_legacy_effort_history import _request
from support import narrative_batch_fixtures as fixtures
from support.narrative_batch_fixtures import (
    isolated_batch_directory,
    prepare_source_catalog,
)

loopback_model_server = fixtures.loopback_model_server
ROOT = Path(__file__).resolve().parents[2]
RF = os.environ.get("RF_NARRATIVE_CODE_ROOT")
SW = os.environ.get("STOCKWIKI_NARRATIVE_CODE_ROOT")
pytestmark = pytest.mark.skipif(
    not RF or not SW, reason="Explicit isolated RF and StockWiki checkouts required"
)


CONSUMER = r"""
from pathlib import Path
import json,sys
root,rf,sw,cwp=map(Path,sys.argv[1:])
sys.path[:0]=[str(rf/'scripts'),str(sw)]
from company_wiki_narrative_contracts import validate_narrative_response
from stockwiki.narrative_source import NarrativeSourceTransport
request=json.loads((root/'read-request.json').read_text(encoding='utf-8'))
body=(root/'bundle.json').read_bytes()
receipt=(root/'receipt.json').read_bytes()
value=validate_narrative_response(request,body,receipt).to_dict()
assert value['reading_context']['schema_version']=='du-production-reading/4'
views=[v for g in value['reading_context']['groups'] for v in g['citation_views']]
assert views and all(v['reading_support_use'] in ('support','context_only','unresolved') for v in views)
argv=[sys.executable,'-B','-X','utf8','-m','company_wiki.source_catalog.narrative_transport_cli',
      '--config',str(root/'config'/'source_catalog.json')]
reader=NarrativeSourceTransport(argv_prefix=argv,timeout_s=30,max_stdout_bytes=1310720)
stock=reader.read(request)
assert stock.to_dict()['reading_context']==value['reading_context']
print(json.dumps({'rf_public_wire':'PASS','stockwiki_public_reader':'PASS','source_use_views':len(views)}))
"""


def test_current_source_use_survives_actual_public_reader_bytes_and_recovery(
    tmp_path_factory,
    loopback_model_server,
    monkeypatch,
    record_property,
):
    def reply(envelope):
        material = envelope["material"]
        task = material["tasks"][0]
        support = task.get("support_parts", material["task_defaults"]["support_parts"])
        key = task["parts"][0]["key"] if support == "all_parts" else support[0]
        part = next(part for part in task["parts"] if part["key"] == key)
        if "shared_ref" in part:
            part = next(
                row
                for row in material["shared_fragments"]
                if row["source_key"] == part["shared_ref"]
            )
        return {
            "drafts_by_task": {
                task["key"]: [
                    {
                        "text": part["text"][:200],
                        "basis_parts": [key],
                        "modality": "uncertain",
                    }
                ]
            }
        }

    monkeypatch.setattr(fixtures, "response_draft", reply)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        before = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in state.raw_paths.items()
        }
        try:
            request, _ = _request(state, loopback_model_server.endpoint, "1")
            request = replace(request, selector_version="0.9.0", max_seconds=90)
            result = batch.run_batch(
                request,
                project_root=root,
                catalog_config_path=state.config_path,
                db_path=root / "automation.db",
                work_dir=root / "work",
            )
            assert result["status"] == "completed", result
            assert (
                len(loopback_model_server.requests) == 1
                and not loopback_model_server.errors
            )
            assert result["documents"][0]["artifact_ref"]
            again = batch.run_batch(
                request,
                project_root=root,
                catalog_config_path=state.config_path,
                db_path=root / "automation.db",
                work_dir=root / "work",
            )
            assert (
                again["documents"] == result["documents"]
                and again["budget"] == result["budget"]
            )
            assert len(loopback_model_server.requests) == 1
            ref = next(iter(state.indexed.values()))[0]
            # The fixture's batch API passes project_root explicitly. The
            # public CLI resolves relative paths from canonical root/config/.
            public_config = root / "config" / "source_catalog.json"
            public_config.parent.mkdir()
            public_config.write_bytes(state.config_path.read_bytes())
            env = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONPATH=str(ROOT / "src"),
                COMPANY_WIKI_DISABLE_DOTENV="1",
                COMPANY_WIKI_NETWORK="blocked",
            )
            argv = [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                "-m",
                "company_wiki.source_catalog.narrative_transport_cli",
                "--config",
                str(public_config),
            ]
            reference = subprocess.run(
                [*argv, "--operation", "reference"],
                input=json.dumps(
                    {
                        "schema_version": "narrative-reference-request/1",
                        "source_ref": asdict(ref),
                    }
                ).encode(),
                env=env,
                capture_output=True,
                timeout=30,
                check=False,
            )
            assert reference.returncode == 0, reference.stderr.decode(
                "utf-8", errors="replace"
            )
            meta = state.reader.describe_version(ref)
            read = {
                "schema_version": "narrative-read-request/1",
                "narrative_ref": json.loads(reference.stdout),
                "as_of_date": "2026-10-28",
                "expected_source": {
                    key: meta.get(key)
                    for key in (
                        "canonical_entity_id",
                        "market",
                        "security_id",
                        "document_kind",
                        "fiscal_year",
                        "fiscal_period",
                    )
                },
            }
            public = subprocess.run(
                [*argv, "--operation", "read"],
                input=json.dumps(read).encode(),
                env=env,
                capture_output=True,
                timeout=30,
                check=False,
            )
            assert public.returncode == 0, public.stderr.decode(
                "utf-8", errors="replace"
            )
            (root / "bundle.json").write_bytes(public.stdout)
            (root / "receipt.json").write_bytes(public.stderr)
            (root / "read-request.json").write_text(json.dumps(read), encoding="utf-8")
            consumer = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    "-c",
                    CONSUMER,
                    str(root),
                    str(RF),
                    str(SW),
                    str(ROOT),
                ],
                env=env,
                capture_output=True,
                timeout=45,
            )
            assert consumer.returncode == 0, consumer.stderr.decode(
                "utf-8", errors="replace"
            )
            report = json.loads(consumer.stdout)
            assert (
                report["rf_public_wire"] == report["stockwiki_public_reader"] == "PASS"
            )
            assert {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in state.raw_paths.items()
            } == before
            # Small public response/receipt evidence stays in JUnit, outside
            # the temporary lake. It permits a fresh installed-reader check
            # without another worker run, source copy or HTTP request.
            record_property("public_bundle", public.stdout.decode("utf-8"))
            record_property("public_receipt", public.stderr.decode("utf-8"))
            record_property("public_request", json.dumps(read))
        finally:
            state.catalog.close()
