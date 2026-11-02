"""Fresh-process probe; producer fixture setup stays with its own test owner."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

CWP = Path(os.environ["CWP_V2_CODE_ROOT"])
RF = Path(os.environ["RF_CODE_ROOT"])
for directory in [RF / "scripts", CWP / "src", CWP / "tests"]:
    sys.path.insert(0, str(directory))

from support.narrative_transport_fixture import published_fixture  # noqa: E402
from company_wiki_source_reader_v2 import open_source_version_v2  # noqa: E402
from company_wiki_narrative_reader import find_narrative_reference, read_narrative_context  # noqa: E402


def main():
    root = Path.cwd()
    baseline = sorted(path.name for path in root.iterdir())
    bridges = root / "relocated adapters"
    bridges.mkdir()
    commands = {}
    for operation, module in {"raw": "source_reader_cli", "narrative": "narrative_transport_cli"}.items():
        script = bridges / (operation + ".py")
        script.write_text("import subprocess,sys\nsys.exit(subprocess.call([sys.executable,'-B','-m'," +
            repr("company_wiki.source_catalog."+module) + ",*sys.argv[1:]]))\n", encoding="utf-8")
        commands[operation] = (sys.executable, "-B", str(script))
    try:
        with published_fixture(root) as fixture:
            database = fixture.catalog.store.database_path
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            source_ref = fixture.source_ref.to_dict()
            options = {"source_ref": source_ref, "catalog_config": fixture.config_path,
                "as_of_date": "2026-09-01", "expected_fiscal_year": fixture.expected_source["fiscal_year"]}
            default = open_source_version_v2(**options)
            substituted = open_source_version_v2(**options, reader_command=commands["raw"])
            assert default.body == substituted.body == fixture.raw_bytes
            ref = find_narrative_reference({"schema_version": "narrative-reference-request/1",
                "source_ref": source_ref}, catalog_config=fixture.config_path,
                reader_command=commands["narrative"])
            request = {"schema_version": "narrative-read-request/1", "narrative_ref": ref,
                "as_of_date": "2026-09-01", "expected_source": fixture.expected_source}
            normal = read_narrative_context(request, catalog_config=fixture.config_path).to_dict()
            alternate = read_narrative_context(request, catalog_config=fixture.config_path,
                reader_command=commands["narrative"]).to_dict()
            for key in ("narrative_ref", "source_ref", "summary", "evidence_spans", "quality_status"):
                assert normal[key] == alternate[key], key
            assert hashlib.sha256(database.read_bytes()).hexdigest() == before
            result = {"status": "pass", "source_sha256": source_ref["content_sha256"],
                "artifact_sha256": ref["artifact_sha256"], "same_semantics": True,
                "changed_cwd_and_command_location": True, "producer_database_unchanged": True}
    finally:
        for script in bridges.iterdir():
            script.unlink()
        bridges.rmdir()
    assert sorted(path.name for path in root.iterdir()) == baseline
    result["fixture_restored"] = True
    print(json.dumps(result))


if __name__ == "__main__":
    main()
