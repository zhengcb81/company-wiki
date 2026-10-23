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


def observe_structure(root):
    """Observe the actual producer; never replace its output or cache decision."""
    bootstrap = root / "reading-bootstrap/sitecustomize.py"
    with bootstrap.open("a", encoding="utf-8") as stream:
        stream.write("\nfrom pathlib import Path\nimport json\n"
            "from company_wiki.document_understanding import structure\n"
            "from company_wiki.document_understanding.structure import sections\n"
            "_observed_build_sections = sections.build_sections\n"
            "def _observe_sections(*args, **kwargs):\n"
            "    result = _observed_build_sections(*args, **kwargs)\n"
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
            launcher = shared._launcher(root)
            bootstrap = root / "reading-bootstrap/sitecustomize.py"
            with bootstrap.open("a", encoding="utf-8") as stream:
                stream.write("\nfrom pathlib import Path\n"
                    "from company_wiki.document_understanding import structure\n"
                    "from company_wiki.document_understanding.structure import sections\n"
                    "legacy_path = Path(" + ascii(str(LEGACY)) + ")\n"
                    "exec(compile(legacy_path.read_bytes(), str(legacy_path), 'exec'), sections.__dict__)\n"
                    "sections.__file__ = str(legacy_path)\n"
                    "structure.build_sections = sections.build_sections\n")
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
