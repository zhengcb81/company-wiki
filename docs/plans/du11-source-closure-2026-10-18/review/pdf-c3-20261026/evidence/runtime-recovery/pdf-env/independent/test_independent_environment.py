"""Independent metadata-only counterexamples; never imports the PDF SDK."""
from email.message import Message
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.narrative_pdf_environment import describe_environment


def dist(name, requires=(), extras=(), version="1.0"):
    message = Message()
    message["Name"] = name
    message["Version"] = version
    for extra in extras:
        message["Provides-Extra"] = extra
    return SimpleNamespace(metadata=message, requires=list(requires), version=version)


def describe(packages, roots=("docling",)):
    return describe_environment(roots, distribution_lookup=packages.__getitem__)


def test_dependency_and_root_order_are_semantically_irrelevant():
    packages = {
        "docling": dist("docling", ("worker>=1", "render")),
        "worker": dist("worker", ("leaf",)),
        "render": dist("render", ("leaf",)),
        "leaf": dist("leaf"),
    }
    first = describe(packages, ("docling", "render"))
    packages["docling"].requires.reverse()
    assert describe(packages, ("render", "docling", "render")) == first


def test_second_incoming_specifier_is_checked_even_when_node_was_selected():
    packages = {
        "docling": dist("docling", ("worker>=1", "render")),
        "worker": dist("worker", version="1.5"),
        "render": dist("render", ("worker>=2",)),
    }
    with pytest.raises(ValueError, match="does not satisfy"):
        describe(packages)


def test_extras_fixed_point_revisits_multiple_earlier_nodes():
    packages = {
        "docling": dist("docling", ("a", "z")),
        "a": dist("a", ('b[edge]; extra == "late"',), extras=("late",)),
        "z": dist("z", ("a[late]",)),
        "b": dist("b", ('a[late]; extra == "edge"', 'leaf; extra == "edge"'), extras=("edge",)),
        "leaf": dist("leaf"),
    }
    result = describe(packages)
    by_name = {row["name"]: row for row in result["distributions"]}
    assert set(by_name) == set(packages)
    assert by_name["a"]["extras"] == ["late"]
    assert by_name["b"]["extras"] == ["edge"]
    packages["leaf"].version = "1.1"
    assert describe(packages)["environment_sha256"] != result["environment_sha256"]


def test_direct_url_only_fails_when_its_extra_is_active():
    packages = {"docling": dist("docling", ('extension @ https://example.invalid/never-fetch.whl ; extra == "remote"',), ("remote",))}
    assert len(describe(packages)["distributions"]) == 1
    with pytest.raises(ValueError, match="direct URL"):
        describe(packages, ("docling[remote]",))


def test_canonical_names_select_one_distribution_and_reject_foreign_name():
    calls = []
    package = dist("Mixed.Name")
    def lookup(name):
        calls.append(name)
        return package
    result = describe_environment(("Mixed_Name",), distribution_lookup=lookup)
    assert calls == ["mixed-name"]
    assert result["distributions"][0]["name"] == "mixed-name"
    package.metadata.replace_header("Name", "different")
    with pytest.raises(ValueError, match="incomplete"):
        describe_environment(("Mixed_Name",), distribution_lookup=lookup)


def test_output_hash_binds_all_declared_payload_fields():
    result = describe({"docling": dist("docling")})
    payload = {key: result[key] for key in ("algorithm", "roots", "marker_environment", "distributions")}
    expected = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["environment_sha256"] == expected
    payload["distributions"][0]["requires"].append("new-dependency")
    assert sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != expected


def test_no_environment_inventory_enumeration(monkeypatch):
    from importlib import metadata
    def forbidden():
        raise AssertionError("all-environment enumeration forbidden")
    monkeypatch.setattr(metadata, "distributions", forbidden)
    assert describe({"docling": dist("docling")})["environment_sha256"]
