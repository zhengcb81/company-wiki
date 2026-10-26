"""Finite W08 migration check; historical sections owner only, then current public pipeline.

The first subprocess uses the exact baseline sections source in this owned
review directory. Other modules are current. This is not a byte-exact full
historical release or a real-company content acceptance.
"""
import hashlib
import json
from pathlib import Path

from integration import test_narrative_generation_reuse as reuse
from integration import test_shared_reading_production_e2e as shared

loopback_model_server = reuse.loopback_model_server
LEGACY = Path(__file__).resolve().parents[2] / "docs/plans/r1-final3-source-semantics-20261022/review/legacy-sections-908ec2c4.py.txt"


def deploy_legacy_reading_sources(root):
    """Deploy the actual old component beside its physical identity owner.

    Other reading modules fall through to their unchanged current sources. The
    structure inventory hashes its own sibling package, so an in-memory exec
    or a changed module label cannot represent an old installed deployment.
    """
    current = Path(__file__).resolve().parents[2] / "src/company_wiki/document_understanding"
    deployed = root / "legacy-deployment/document_understanding"
    deployed.mkdir(parents=True)
    for name in ("__init__.py", "decision_inventory.py"):
        (deployed / name).write_bytes((current / name).read_bytes())
    for source in sorted((current / "structure").rglob("*.py")):
        target = deployed / source.relative_to(current)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    (deployed / "structure/sections.py").write_bytes(LEGACY.read_bytes())
    return current, deployed


def observe_structure(root):
    """Observe the actual producer; never replace its output or cache decision."""
    bootstrap = root / "reading-bootstrap/sitecustomize.py"
    with bootstrap.open("a", encoding="utf-8") as stream:
        stream.write("\nfrom pathlib import Path\nfrom types import SimpleNamespace\nimport json\nimport inspect\n"
            "from company_wiki.document_understanding import structure\n"
            "from company_wiki.document_understanding.structure import sections\n"
            "_observed_build_sections = sections.build_sections\n"
            "_observed_build_parameters = inspect.signature(_observed_build_sections).parameters\n"
            "_observed_build_accepts_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD "
            "for p in _observed_build_parameters.values())\n"
            "def _observe_sections(*args, **kwargs):\n"
            "    for optional in ('native_context', 'work_budget'):\n"
            "        if (optional in kwargs and optional not in _observed_build_parameters "
            "and not _observed_build_accepts_kwargs):\n"
            "            kwargs = dict(kwargs)\n"
            "            kwargs.pop(optional)\n"
            "    result = _observed_build_sections(*args, **kwargs)\n"
            "    if not hasattr(result, 'required_context_by_unit_id'):\n"
            "        result = SimpleNamespace(sections=result.sections, diagnostics=result.diagnostics, "
            "unit_section=result.unit_section, required_context_by_unit_id={}, "
            "required_source_by_unit_id={}, source_proofs_by_unit_id={})\n"
            "    texts = {unit.unit_id: unit.text for unit in args[0]}\n"
            "    record = {'producer': sections.__file__, 'sections': ["
            "{'headings': [texts[uid] for uid in section.heading_ids], "
            "'body': [texts[uid] for uid in section.body_ids], 'basis': section.basis} "
            "for section in result.sections]}\n"
            "    with (Path(__file__).parent.parent / 'observed-structures.jsonl').open('a', encoding='utf-8') as out:\n"
            "        out.write(json.dumps(record, ensure_ascii=True) + '\\n')\n"
            "    return result\n"
            "sections.build_sections = _observe_sections\n"
            "structure.build_sections = _observe_sections\n")


def observed_structures(root):
    return [json.loads(line) for line in (root / "observed-structures.jsonl").read_text(encoding="utf-8").splitlines()]


def own_context(bundle):
    texts = {span["span_id"]: span["raw_text"] for span in bundle["evidence_spans"]}
    targets = [span for span in bundle["evidence_spans"] if "New product revenue exceeds 30%" in span["raw_text"]]
    result = []
    for span in targets:
        contexts = []
        for group in bundle["reading_context"]["groups"]:
            for view in group["citation_views"]:
                if span["span_id"] in view["support_evidence_ids"]:
                    contexts.extend(texts[sid] for sid in view["context_evidence_ids"])
        result.append({"locator": span["locator"], "context": list(dict.fromkeys(contexts))})
    return result


def test_old_sections_cache_misses_then_new_public_parent_and_cache_restore(loopback_model_server, monkeypatch, tmp_path):
    import pymupdf as fitz
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((90, 80), "I. Management discussion", fontsize=12)
    page.insert_text((90, 120), "(1) Diagnostics services generated USD 12 million.\nDuring the period:", fontsize=11)
    page.insert_text((110, 165), "- New product revenue exceeds 30%.", fontsize=11)
    page.insert_text((90, 210), "(2) Technical services generated USD 9 million.\nDuring the period:", fontsize=11)
    page.insert_text((110, 255), "- New product revenue exceeds 30%.", fontsize=11)
    page.insert_text((90, 300), "The company plans remain subject to market conditions.", fontsize=11)
    original = doc.tobytes()
    doc.close()
    record = {"baseline_component": str(LEGACY), "baseline_sections_sha256": hashlib.sha256(LEGACY.read_bytes()).hexdigest(),
              "scope": "one actual historical sections component; current remaining code; synthetic generated PDF",
              "external_provider_calls": 0}
    with reuse.setup_source(loopback_model_server.endpoint, "text/html") as (root, catalog, config, llm, _, _):
        imported = reuse.official._public_official_import(root, config, original,
            mime="application/pdf", kind="annual_report", language="en")
        kind = "annual_report"
        protected = shared._protected(root, config, llm)
        try:
            current_sources, legacy_sources = deploy_legacy_reading_sources(root)
            launcher = shared._launcher(root)
            bootstrap = root / "reading-bootstrap/sitecustomize.py"
            with bootstrap.open("a", encoding="utf-8") as stream:
                stream.write("\nfrom pathlib import Path\n"
                    "import importlib.util\nimport sys\nimport company_wiki\n"
                    "deployed = Path(" + ascii(str(legacy_sources)) + ")\n"
                    "current = Path(" + ascii(str(current_sources)) + ")\n"
                    "name = 'company_wiki.document_understanding'\n"
                    "loaded = sys.modules.get(name)\n"
                    "if loaded is not None and Path(loaded.__file__).resolve() != (deployed / '__init__.py').resolve():\n"
                    "    raise RuntimeError('legacy fixture must load before the current reading package')\n"
                    "if loaded is None:\n"
                    "    spec = importlib.util.spec_from_file_location(name, deployed / '__init__.py',\n"
                    "        submodule_search_locations=[str(deployed), str(current)])\n"
                    "    if spec is None or spec.loader is None:\n"
                    "        raise RuntimeError('legacy fixture package deployment unavailable')\n"
                    "    package = importlib.util.module_from_spec(spec)\n"
                    "    sys.modules[name] = package\n"
                    "    company_wiki.document_understanding = package\n"
                    "    spec.loader.exec_module(package)\n")
            observe_structure(root)
            old_request = reuse.request_path(root, imported, loopback_model_server.endpoint, "old-a", selector_version="0.9.0")
            process, old_result = reuse.invoke(root, config, old_request, llm, "old-a", launcher=launcher)
            assert process.returncode == 0 and old_result["status"] == "completed", (old_result, process.stderr)
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            old_ref, old_bundle, _ = reuse.public_read(root, config, imported, kind)
            old_final = shared._assert_formal_generation(root, catalog, imported, "old-a", old_ref, old_bundle, loopback_model_server.requests[0][0])
            old_context = own_context(old_bundle)
            old_structures = observed_structures(root)
            assert old_structures
            assert all("native_numbered_list" not in section["basis"]
                       for row in old_structures for section in row["sections"])
            old_reuse_request = reuse.request_path(root, imported, loopback_model_server.endpoint, "old-b", selector_version="0.9.0")
            process, old_cached = reuse.invoke(root, config, old_reuse_request, llm, "old-b", launcher=launcher)
            assert process.returncode == 0 and old_cached["status"] == "completed", (old_cached, process.stderr)
            assert len(loopback_model_server.requests) == 1
            assert old_cached["budget"]["tokens"] == 0
            assert observed_structures(root) == old_structures
            launcher = shared._launcher(root)
            observe_structure(root)
            new_request = reuse.request_path(root, imported, loopback_model_server.endpoint, "new-c", selector_version="0.9.0")
            process, new_result = reuse.invoke(root, config, new_request, llm, "new-c", launcher=launcher)
            assert process.returncode == 0 and new_result["status"] == "completed", (new_result, process.stderr)
            assert len(loopback_model_server.requests) == 2 and not loopback_model_server.errors
            new_ref, new_bundle, _ = reuse.public_read(root, config, imported, kind)
            new_final = shared._assert_formal_generation(root, catalog, imported, "new-c", new_ref, new_bundle, loopback_model_server.requests[1][0])
            assert new_ref != old_ref
            assert new_final["reading_dependencies"]["versions"]["business_algorithms"] != old_final["reading_dependencies"]["versions"]["business_algorithms"]
            new_context = own_context(new_bundle)
            new_structures = observed_structures(root)
            assert len(new_structures) > len(old_structures)
            actual_new = new_structures[len(old_structures):]
            assert all(Path(row["producer"]).resolve().is_relative_to(Path(__file__).resolve().parents[2] / "src")
                       for row in actual_new)
            scopes = [section for row in actual_new for section in row["sections"]
                      if "native_numbered_list" in section["basis"]]
            for own, sibling in (("Diagnostics services", "Technical services"), ("Technical services", "Diagnostics services")):
                assert any(own in "\n".join(section["headings"])
                           and sibling not in "\n".join(section["headings"])
                           and any("New product revenue exceeds 30%" in body for body in section["body"])
                           for section in scopes)
            print(json.dumps({"phase": "new_public_context", "selected_texts": [s["raw_text"] for s in new_bundle["evidence_spans"]], "old_context": old_context, "new_context": new_context}, ensure_ascii=True))
            assert len(new_context) == 2 and len({row["locator"] for row in new_context}) == 2
            for row, own, sibling in zip(new_context, ("Diagnostics services", "Technical services"),
                                         ("Technical services", "Diagnostics services"), strict=True):
                joined = "\n".join(row["context"])
                assert own in joined and sibling not in joined, row
                assert "During the period:" in joined, row
            assert old_context != new_context
            again_request = reuse.request_path(root, imported, loopback_model_server.endpoint, "new-d", selector_version="0.9.0")
            process, new_cached = reuse.invoke(root, config, again_request, llm, "new-d", launcher=launcher)
            assert process.returncode == 0 and new_cached["status"] == "completed", (new_cached, process.stderr)
            assert len(loopback_model_server.requests) == 2
            assert new_cached["budget"]["tokens"] == 0
            assert observed_structures(root) == new_structures
            assert reuse.public_read(root, config, imported, kind)[0] == new_ref
            old_exact, old_again, _ = reuse.public_read(root, config, imported, kind, exact=old_ref)
            assert old_exact == old_ref and old_again == old_bundle
            record.update(old_result=old_result, old_cache=old_cached, new_result=new_result, new_cache=new_cached,
                          old_context=old_context, new_context=new_context, old_ref=old_ref, new_ref=new_ref,
                          old_structures=old_structures, new_structures=new_structures,
                          old_final=old_final, new_final=new_final, loopback_fixture_posts=len(loopback_model_server.requests),
                          old_bundle_unchanged=True)
        finally:
            shared._assert_protected(root, protected)
    record["owned_lake_removed"] = not root.exists()
    (tmp_path / "public-cache-result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
