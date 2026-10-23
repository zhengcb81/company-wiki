"""Neutral official-index scope and coverage checks in ordinary unit CI."""

import json

import pytest

from company_wiki.source_catalog.official_discovery import discover_official_documents


def discover(body):
    return discover_official_documents(
        [{"url": "https://neutral.example/ir", "original": body.encode("utf-8"),
          "mime_type": "text/html", "capture_id": "root-neutral-index"}],
        entity="Neutral Holding", start_date="2026-01-01", as_of_date="2026-10-21",
    )


def item(content, kind):
    return f"<li>{content}</li>" if kind == "li" else f"<tr><td>{content}</td></tr>"


def nested_items(first, second, kind):
    children = item(first, kind) + item(second, kind)
    return f"<article><ul>{children}</ul></article>" if kind == "li" else (
        f"<article><table>{children}</table></article>"
    )


@pytest.mark.parametrize("kind", ["li", "tr"])
@pytest.mark.parametrize("document_url", ["/a.pdf", "/download?id=a"])
def test_nested_native_item_owns_its_date_and_download_title(kind, document_url):
    body = nested_items(
        '<time datetime="2026-09-01"></time><span>Annual Report 2025</span>'
        f'<a href="{document_url}">Download</a>',
        '<time datetime="2026-09-02"></time><a href="/b.pdf">Interim Report 2026</a>',
        kind,
    )
    result = discover(body)
    by = {row["source_url"]: row for row in result["candidates"]}
    first = by["https://neutral.example" + document_url]
    assert "Annual Report 2025" in first["title"]
    assert first["published_date"] == "2026-09-01"
    assert by["https://neutral.example/b.pdf"]["published_date"] == "2026-09-02"
    assert result["excluded"] == []


@pytest.mark.parametrize("kind", ["li", "tr"])
def test_nested_future_item_is_excluded_without_dating_an_undated_sibling(kind):
    result = discover(nested_items(
        '<time datetime="2026-10-22"></time><a href="/future.pdf">Annual Report 2025</a>',
        '<a href="/undated.pdf">Interim Report 2026</a>', kind,
    ))
    assert result["excluded"] == [{"source_url": "https://neutral.example/future.pdf",
        "published_date": "2026-10-22", "reason": "after_as_of"}]
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["source_url"] == "https://neutral.example/undated.pdf"
    assert result["candidates"][0]["published_date"] is None


def test_nearest_item_does_not_borrow_a_wider_page_update_time():
    result = discover('<article><time datetime="2026-10-22">Last updated</time>'
        '<ul><li><a href="/current.pdf">Annual Report 2025</a></li></ul></article>')
    assert result["excluded"] == []
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["published_date"] is None


def test_multilink_nearest_item_remains_ambiguous_without_borrowing_a_date():
    result = discover('<article><ul><li><time datetime="2026-09-01"></time>'
        '<a href="/a.pdf">Annual Report 2025</a>'
        '<a href="/b.pdf">Interim Report 2026</a></li></ul></article>')
    assert len(result["candidates"]) == 2
    assert all(row["published_date"] is None for row in result["candidates"])
    assert result["coverage_status"] == "partial"


def declared(payload):
    return '<script type="application/ld+json">' + json.dumps(payload) + '</script>'


@pytest.mark.parametrize("payload", [
    {"@type": "DigitalDocument", "name": "Annual Report 2025", "contentUrl": "/report.pdf"},
    {"@graph": [{"@type": "DigitalDocument", "contentUrl": "/report.pdf"}]},
])
def test_unexamined_declared_document_cannot_look_like_a_complete_checked_index(payload):
    result = discover(declared(payload))
    assert result["candidates"] == []  # Detection is not document acquisition or extraction.
    assert "embedded_document_unresolved" in result["limitations"]
    assert result["coverage_status"] == "partial"
    assert result["no_documents_claimed"] is False


@pytest.mark.parametrize("payload", [
    {"@type": "Event", "name": "Investor Day", "url": "/events"},
    {"@type": "Organization", "name": "Neutral Holding", "url": "/about"},
])
def test_non_material_declarations_do_not_create_a_blanket_partial_state(payload):
    result = discover(declared(payload))
    assert result["limitations"] == []
    assert result["coverage_status"] == "checked_index_only"


def test_bad_declared_structure_retains_unknown_instead_of_silently_finishing():
    result = discover('<script type="application/ld+json">'
        '{"@type":"DigitalDocument","contentUrl":</script>')
    assert result["coverage_status"] == "partial"
    assert result["limitations"]
    assert result["no_documents_claimed"] is False


@pytest.mark.parametrize("payload", [
    {"@type": ["Thing", "schema:DigitalDocument"], "contentUrl": "/report.pdf"},
    {"@type": "https://schema.org/TextDigitalDocument", "contentUrl": "/report.txt"},
])
def test_declared_document_type_arrays_and_schema_names_remain_unexamined(payload):
    result = discover(declared(payload))
    assert "embedded_document_unresolved" in result["limitations"]
    assert result["candidates"] == []


@pytest.mark.parametrize("body", [
    '<script type="application/ld+json">{"@type":true}</script>',
    '<script type="application/ld+json">{"@graph":"not a node"}</script>',
    '<script type="application/ld+json">{"@type":"Organization","value":NaN}</script>',
])
def test_invalid_declared_node_shapes_do_not_look_examined(body):
    result = discover(body)
    assert result["coverage_status"] == "partial"
    assert "embedded_data_unresolved" in result["limitations"]


def test_oversize_declared_payload_reports_unknown_instead_of_parsing_without_bounds():
    result = discover(declared({"@type": "Organization", "name": "X" * 100_000}))
    assert result["coverage_status"] == "partial"
    assert "embedded_data_unresolved" in result["limitations"]


def test_deep_unexamined_document_keeps_unknown_without_unbounded_walk():
    value = {"@type": "DigitalDocument", "contentUrl": "/report.pdf"}
    for _ in range(50):
        value = {"mainEntity": value}
    result = discover(declared(value))
    assert result["coverage_status"] == "partial"
    assert "embedded_data_unresolved" in result["limitations"]


@pytest.mark.parametrize("payload", [
    {"name": "Quarterly trading update", "contentUrl": "/update.pdf"},
    {"@type": "CreativeWork", "encoding": {"contentUrl": "/update.pdf"}},
    {"schema:contentUrl": "/update.pdf"},
])
def test_document_properties_do_not_need_a_known_type_to_remain_unexamined(payload):
    result = discover(declared(payload))
    assert result["candidates"] == []
    assert result["coverage_status"] == "partial"
    assert "embedded_document_unresolved" in result["limitations"]


@pytest.mark.parametrize("raw", [
    '[{"@type":"Organization"},17]',
    '{"@graph":[17]}',
    '{"@type":"DigitalDocument","@type":"Organization"}',
])
def test_invalid_graph_members_and_duplicate_fields_cannot_hide_unexamined_data(raw):
    result = discover('<script type="application/ld+json">' + raw + '</script>')
    assert result["coverage_status"] == "partial"
    assert "embedded_data_unresolved" in result["limitations"]


@pytest.mark.parametrize("suffix", [
    '<script src="/assets/metrics.js"></script>',
    '<p>Downloading this report may take a moment.</p>',
    '<script>window.ready = true;</script>',
])
def test_readable_static_material_does_not_become_an_unresolved_dynamic_shell(suffix):
    body = '<main><a data-date="2026-08-11" href="/update.pdf">Interim Report 2026</a></main>'
    result = discover(body + suffix)
    assert len(result["candidates"]) == 1
    assert result["coverage_status"] == "checked_index_only"
    assert result["limitations"] == []


@pytest.mark.parametrize("body", [
    '<main><h1>Investor materials</h1><div></div></main><script src="/ui.js"></script>',
    '<main><div>Loading…</div></main>',
])
def test_unreadable_mount_or_explicit_loading_placeholder_remains_partial(body):
    result = discover(body)
    assert result["coverage_status"] == "partial"
    assert "dynamic_content_unresolved" in result["limitations"]


def test_ordinary_jsonld_literal_arrays_are_not_invalid_document_nodes():
    result = discover(declared({"@type": "Organization", "sameAs": ["/about", "/contact"],
                                "keywords": ["business", "manufacturing"]}))
    assert result["coverage_status"] == "checked_index_only"
    assert result["limitations"] == []
