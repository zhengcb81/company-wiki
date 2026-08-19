"""ZR-509 acceptance tests: official HTML capture identity gate.

  C1  parse_html_identity extracts title (<title>/<h1>, tags stripped),
      entity candidates (suffix-anchored phrases, first-seen order) and
      period (CN date / ISO date / bare year).
  C2  validate_html_capture gates: ok / missing_title / no_entity /
      entity_mismatch; period validity.
  C3  entity-less page (wrong-strategy HTML shape) is fail-closed.
  C4  structured, deterministic output (JSON-serializable).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.html_capture import (  # noqa: E402
    parse_html_identity,
    validate_html_capture,
)

ANNOUNCEMENT_HTML = """<!DOCTYPE html>
<html><head><title>紫金矿业集团股份有限公司关于2026年年度报告的公告</title></head>
<body><h1>紫金矿业集团股份有限公司关于2026年年度报告的公告</h1>
<p>本公司董事会及全体董事保证本公告内容不存在任何虚假记载。</p>
<p>公告日期：2026年4月30日</p></body></html>
"""

WRONG_STRATEGY_HTML = """<!DOCTYPE html>
<html><head><title>2026年投资策略报告</title></head>
<body><h1>2026年投资策略报告</h1>
<p>本报告仅供内部参考，不构成投资建议。</p></body></html>
"""


# ---------------------------------------------------------------------------
# C1 — identity parsing
# ---------------------------------------------------------------------------


def test_c1_extracts_title_entities_period():
    identity = parse_html_identity(ANNOUNCEMENT_HTML)
    assert identity["title"] == "紫金矿业集团股份有限公司关于2026年年度报告的公告"
    assert any("紫金矿业" in phrase for phrase in identity["entities"])
    assert identity["period"] == "2026-04-30"


def test_c1_h1_fallback_and_iso_date():
    html = "<html><body><h1>某公司 2025-03-01 公告</h1><p>正文</p></body></html>"
    identity = parse_html_identity(html)
    assert identity["title"] == "某公司 2025-03-01 公告"
    assert identity["period"] == "2025-03-01"


def test_c1_bare_year_period():
    identity = parse_html_identity("<title>某公司 2026年 年报</title><p>2026年</p>")
    assert identity["period"] == "2026"


def test_c1_empty_input():
    identity = parse_html_identity(None)
    assert identity["title"] is None
    assert identity["entities"] == []
    assert identity["period"] is None


# ---------------------------------------------------------------------------
# C2 — identity gate
# ---------------------------------------------------------------------------


def test_c2_official_announcement_passes():
    identity = parse_html_identity(ANNOUNCEMENT_HTML)
    result = validate_html_capture(
        identity, declared_entity="紫金矿业集团股份有限公司"
    )
    assert result["verdict"] == "ok"
    assert result["reason"] is None


def test_c2_missing_title():
    identity = parse_html_identity("<html><body><p>没有标题的页面</p></body></html>")
    result = validate_html_capture(identity)
    assert result["verdict"] == "missing_title"


def test_c2_no_entity():
    identity = parse_html_identity("<title>标题</title><p>无公司名的正文</p>")
    result = validate_html_capture(identity)
    assert result["verdict"] == "no_entity"


def test_c2_entity_mismatch():
    identity = parse_html_identity(
        "<title>陕西煤业股份有限公司公告</title><p>陕西煤业股份有限公司2026年公告</p>"
    )
    result = validate_html_capture(identity, declared_entity="紫金矿业集团股份有限公司")
    assert result["verdict"] == "entity_mismatch"


def test_c2_no_declared_entity_any_entity_passes():
    identity = parse_html_identity(ANNOUNCEMENT_HTML)
    result = validate_html_capture(identity)
    assert result["verdict"] == "ok"


# ---------------------------------------------------------------------------
# C3 — entity-less page fail-closed
# ---------------------------------------------------------------------------


def test_c3_wrong_strategy_shape_is_fail_closed():
    identity = parse_html_identity(WRONG_STRATEGY_HTML)
    assert identity["entities"] == []
    result = validate_html_capture(
        identity, declared_entity="紫金矿业集团股份有限公司"
    )
    assert result["verdict"] == "no_entity"


# ---------------------------------------------------------------------------
# C4 — structured deterministic output
# ---------------------------------------------------------------------------


def test_c4_outputs_are_json_serializable():
    for html in (ANNOUNCEMENT_HTML, WRONG_STRATEGY_HTML, "<html></html>"):
        identity = parse_html_identity(html)
        json.dumps(identity)
        json.dumps(validate_html_capture(identity, declared_entity="x"))


def test_c4_deterministic():
    first = parse_html_identity(ANNOUNCEMENT_HTML)
    second = parse_html_identity(ANNOUNCEMENT_HTML)
    assert first == second
    assert (
        validate_html_capture(first, declared_entity="紫金矿业集团股份有限公司")
        == validate_html_capture(second, declared_entity="紫金矿业集团股份有限公司")
    )


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
