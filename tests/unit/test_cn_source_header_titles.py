"""Real PDF headers: issuer code binds titles independently of display aliases."""
from hashlib import sha256
from types import SimpleNamespace

import pymupdf
import pytest

from company_wiki.source_catalog.local_reconcile import _cn_cover_scope
from company_wiki.source_catalog.source_reader import SourceReadError


def observe(title, *, code='600999', allow_other=True):
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,50),'证券代码：'+code+'\n证券简称：和光科技\n'+title,
                         fontname='china-s',fontsize=12)
        data=pdf.tobytes()
    original=SimpleNamespace(data=data,ref=SimpleNamespace(content_sha256=sha256(data).hexdigest()))
    identity=SimpleNamespace(canonical_name='和光科技',security_id='600999',market='CN')
    return _cn_cover_scope(original,identity,SimpleNamespace(check=lambda:None),allow_other_kinds=allow_other)


@pytest.mark.parametrize(('title','kind','period'), (
    ('投资者关系活动记录表','investor_relations',None),
    ('投资者关系\n活动记录表','investor_relations',None),
    ('2026年年度报告','annual_report','FY'),
    ('2026年半年度报告','semi_annual_report','H1'),
    ('2026年第三季度报告','quarterly_report','Q3'),
))
@pytest.mark.parametrize('prefix', ('','海川先进材料股份有限公司','和光科技股份有限公司'))
def test_code_bound_standalone_title_is_independent_of_the_short_name(prefix,title,kind,period):
    facts,proof=observe(prefix+title)
    assert facts['security_id']=='600999' and facts['entity']=='和光科技'
    assert facts['document_kind']==kind and facts['fiscal_period']==period
    assert all(row['content_sha256'] for row in proof.values())


def test_legal_name_cannot_override_a_conflicting_security_code():
    with pytest.raises(SourceReadError,match='primary_issuer_conflict'):
        observe('海川先进材料股份有限公司投资者关系活动记录表',code='600998')


@pytest.mark.parametrize('title', ('公司说明：投资者关系活动记录表',
    '请查阅海川股份有限公司2026年年度报告','请查阅海川股份有限公司投资者关系活动记录表',
    '请查阅海川股份有限公司\n2026年年度报告',
    '参见海川股份有限公司\n投资者关系活动记录表',
    '详见海川股份有限公司2026年半年度报告'))
def test_a_procedure_sentence_does_not_become_a_document_title(title):
    with pytest.raises(SourceReadError):
        observe(title)
