"""Independent neutral synthetic-only CN cover checks; no real originals."""
from hashlib import sha256
from types import SimpleNamespace

import pymupdf
import pytest

from company_wiki.source_catalog.local_reconcile import _cn_cover_scope
from company_wiki.source_catalog.source_reader import SourceReadError


def observe(title, code='600999', short_name='和光科技'):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 50), '证券代码：' + code + '\n证券简称：' + short_name + '\n' + title,
                         fontname='china-s', fontsize=12)
        data = pdf.tobytes()
    original = SimpleNamespace(data=data, ref=SimpleNamespace(content_sha256=sha256(data).hexdigest()))
    identity = SimpleNamespace(canonical_name='和光科技', security_id='600999', market='CN')
    return _cn_cover_scope(original, identity, SimpleNamespace(check=lambda: None), allow_other_kinds=True)


@pytest.mark.parametrize('title', [
    '和光科技股份有限公司投资者关系活动记录表',
    '和光科技股份有限公司2026年半年度报告',
])
def test_legal_name_starting_with_display_name(title):
    facts, _ = observe(title)
    assert facts['security_id'] == '600999'


@pytest.mark.parametrize('title', [
    '请查阅海川股份有限公司2026年年度报告',
    '请查阅海川股份有限公司投资者关系活动记录表',
])
def test_reference_sentence_is_not_a_cover_title(title):
    with pytest.raises(SourceReadError):
        observe(title)


def test_conflicting_code_does_not_gain_identity():
    with pytest.raises(SourceReadError, match='primary_issuer_conflict'):
        observe('海川股份有限公司投资者关系活动记录表', code='600998')


def test_independent_legal_name_and_code_is_supported():
    facts, _ = observe('海川股份有限公司2026年第三季度报告')
    assert (facts['document_kind'], facts['fiscal_period']) == ('quarterly_report', 'Q3')


def test_wrapped_reference_does_not_donate_a_standalone_suffix_title():
    with pytest.raises(SourceReadError):
        observe('请查阅海川股份有限公司\n2026年年度报告')
