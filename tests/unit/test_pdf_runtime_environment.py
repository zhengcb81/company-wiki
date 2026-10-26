"""Runtime identity follows selected metadata, never the interpreter inventory."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import _paragraph_worker as worker


def package(name, version="1", requires=(), extras=()):
    class Metadata(dict):
        def get_all(self, key, default=None):
            return list(extras) if key == "Provides-Extra" else default
    return SimpleNamespace(metadata=Metadata(Name=name, Version=version), version=version,
                           requires=list(requires))


def fingerprint(monkeypatch, packages, roots=("docling",), marker_environment=None):
    by_name = {p.metadata["Name"].lower().replace("_", "-"): p for p in packages}
    def lookup(name):
        from importlib.metadata import PackageNotFoundError
        if name not in by_name:
            raise PackageNotFoundError(name)
        return by_name[name]
    monkeypatch.setattr(worker, "distributions", lambda: packages)
    monkeypatch.setattr(worker, "distribution", lookup, raising=False)
    return worker.environment_sha256(roots=roots, marker_environment=marker_environment)


def test_duplicate_search_path_discovery_and_unrelated_distribution_do_not_change_identity(monkeypatch):
    root, dep = package("docling", requires=("backend",)), package("backend")
    expected = fingerprint(monkeypatch, [root, dep])
    assert fingerprint(monkeypatch, [root, dep, root, package("unrelated-editor", "97")]) == expected


def test_transitive_selected_version_and_metadata_dependency_changes_change_identity(monkeypatch):
    root, dep = package("docling", requires=("backend",)), package("backend", requires=("leaf",))
    leaf = package("leaf")
    expected = fingerprint(monkeypatch, [root, dep, leaf])
    assert fingerprint(monkeypatch, [root, dep, package("leaf", "2")]) != expected
    assert fingerprint(monkeypatch, [root, package("backend"), leaf]) != expected


def test_inactive_markers_and_unused_extras_do_not_require_or_bind_packages(monkeypatch):
    root = package("docling", requires=('missing; python_version < "2"', 'ocr; extra == "ocr"',
        'optional @ https://example.invalid/sdk.whl ; extra == "unused"'), extras=("ocr", "unused"))
    expected = fingerprint(monkeypatch, [root])
    assert fingerprint(monkeypatch, [root, package("ocr", "9")]) == expected


def test_marker_platform_activation_is_evaluated_and_fingerprinted(monkeypatch):
    root = package("docling", requires=('backend; sys_platform == "win32"',))
    win = fingerprint(monkeypatch, [root, package("backend")], marker_environment={"sys_platform": "win32"})
    linux = fingerprint(monkeypatch, [root], marker_environment={"sys_platform": "linux"})
    assert win != linux
    assert fingerprint(monkeypatch, [root, package("backend", "2")], marker_environment={"sys_platform": "win32"}) != win


def test_transitive_extras_revisit_earlier_nodes_and_cycles(monkeypatch):
    root = package("docling", requires=("backend", "later"))
    dep = package("backend", requires=('leaf; extra == "feature"', "docling"), extras=("feature",))
    later = package("later", requires=("backend[feature]",))
    expected = fingerprint(monkeypatch, [root, dep, later, package("leaf")])
    assert fingerprint(monkeypatch, [root, dep, later, package("leaf", "2")]) != expected
    assert fingerprint(monkeypatch, [later, dep, root, package("leaf")], roots=("docling", "docling")) == expected


def test_marker_and_extras_activation_change_even_when_package_versions_are_equal(monkeypatch):
    root = package("docling", requires=('backend; extra == "feature"',), extras=("feature",))
    expected = fingerprint(monkeypatch, [root, package("backend")])
    assert fingerprint(monkeypatch, [root, package("backend")], roots=("docling[feature]",)) != expected
    root.requires = ['backend; python_version >= "3"']
    assert fingerprint(monkeypatch, [root, package("backend")]) != expected


def test_metadata_resolution_preserves_selected_distribution_precedence(monkeypatch):
    root, first, shadow = package("docling", requires=("backend",)), package("backend"), package("backend", "2")
    monkeypatch.setattr(worker, "distribution", lambda name: {"docling": root, "backend": first}[name])
    monkeypatch.setattr(worker, "distributions", lambda: [root, first, shadow, first])
    expected = worker.environment_sha256(roots=("docling",))
    monkeypatch.setattr(worker, "distribution", lambda name: {"docling": root, "backend": shadow}[name])
    assert worker.environment_sha256(roots=("docling",)) != expected


@pytest.mark.parametrize("broken", ["missing", "name", "version", "requirement", "specifier", "extra"])
def test_missing_or_invalid_active_metadata_is_an_explicit_failure(monkeypatch, broken):
    root, dep = package("docling", requires=("backend>=2",)), package("backend", "2")
    packages = [root, dep]
    if broken == "missing":
        packages = [root]
    elif broken == "name":
        dep.metadata["Name"] = ""
    elif broken == "version":
        dep.version = ""
    elif broken == "requirement":
        root.requires = ["???"]
    elif broken == "specifier":
        dep.version = "1"
    elif broken == "extra":
        root.requires = ["backend[not-declared]"]
    with pytest.raises((ValueError, LookupError)):
        fingerprint(monkeypatch, packages)


def test_v2_config_explicit_algorithm_and_recipe_source_binding(monkeypatch):
    from company_wiki.source_catalog.narrative_pdf_enhancement import configured_paragraph_runtime
    from unit.test_pdf_paragraph_runtime import config
    raw = {**config().__dict__, "runtime_versions": dict(config().runtime_versions),
           "schema_version": "pdf-paragraph-runtime/2", "environment_algorithm": "pdf-runtime-closure/2"}
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: json.dumps(raw))
    monkeypatch.setenv("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG", "runtime.json")
    selected = configured_paragraph_runtime().config
    assert selected.environment_algorithm == "pdf-runtime-closure/2"
    assert selected.recipe()["environment_algorithm"] == "pdf-runtime-closure/2"
    assert len(selected.recipe()["environment_implementation_sha256"]) == 64
    raw.pop("environment_algorithm")
    with pytest.raises(ValueError):
        configured_paragraph_runtime()


def test_v1_recipe_is_explicit_legacy_and_never_claims_v2():
    from unit.test_pdf_paragraph_runtime import config
    assert "environment_algorithm" not in config().recipe()
    assert "environment_implementation_sha256" not in config().recipe()


@pytest.mark.parametrize("response_algorithm", ["pdf-runtime-closure/2", None, "pdf-installed-distributions/1"])
def test_v2_request_response_algorithm_binding(response_algorithm):
    from dataclasses import replace
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement
    from unit.test_pdf_paragraph_runtime import config, source
    data, parsed = source()
    selected = replace(config(), environment_algorithm="pdf-runtime-closure/2")
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        assert request["schema_version"] == "pdf-paragraph-request/2"
        assert request["environment_algorithm"] == "pdf-runtime-closure/2"
        response = {**request, "schema_version": "pdf-paragraph-response/2", "converter_instances": 1,
                    "items": [], "environment_algorithm": response_algorithm}
        return {"stdout": json.dumps(response).encode()}
    result = ParagraphEnhancement(selected, runner=runner).enhance(
        data, parsed, work_budget=WorkBudget(10000), deadline=None)
    expected = "unaligned_native_fallback" if response_algorithm == "pdf-runtime-closure/2" else "native_fallback"
    assert result.layout_diagnostics[-1]["status"] == expected
