import pytest
from company_wiki.document_understanding.operating_states.relations import independent_statement_start
from company_wiki.source_catalog import narrative_reading as reading
from unit.du11_source_closure.test_cross_page_reference_plan import page_case

@pytest.mark.parametrize('text,expected',[("本企業另一款設備已經投入運作。",True),("Our new systems are awaiting customer approval.",True),("our customers next year.",False),("our customers, but rollout remains restricted.",False),("these products still require approval before production.",False)])
def test_shared_boundary_role_is_not_event_truth(text,expected):
    assert independent_statement_start(text) is expected

@pytest.mark.parametrize('right',["本企業另一款設備尚未獲准量產。","Our new systems are not yet approved for production."])
def test_new_product_uncertainty_is_not_glued_to_prior_product(right):
    parsed,pipeline=page_case(["公司的第一种设备尚在开展生产验",right]); raw=[u.raw_text for u in parsed.units]; ids=[u.unit_id for u in parsed.units]
    packages,_,_,blocked=reading._prose_reading_packages(parsed,pipeline)
    assert not any(len(p['member_unit_ids'])>1 for p in packages)
    assert any(p['member_unit_ids']==[ids[1]] for p in packages)
    assert ids[1] not in blocked and [u.raw_text for u in parsed.units]==raw

from importlib import import_module
from pathlib import Path
from company_wiki.document_understanding import decision_inventory

@pytest.mark.parametrize('name',["company_wiki.document_understanding.operating_states.relations","company_wiki.document_understanding.operating_states.patterns","company_wiki.document_understanding.operating_states.text_view","company_wiki.document_normalization.text_matching","company_wiki.source_catalog.n6_candidate_operating_facts"])
def test_each_shared_owner_eol_equivalence_is_stable(name,tmp_path,monkeypatch):
    module=import_module(name); original=Path(module.__file__).read_bytes().replace(b"\r\n",b"\n")
    assert ".codex" in str(Path(module.__file__).resolve())
    before=decision_inventory._versions(); equivalent=tmp_path/'equivalent_crlf.py';equivalent.write_bytes(original.replace(b"\n",b"\r\n"))
    monkeypatch.setattr(module,'__file__',str(equivalent)); assert decision_inventory._versions()==before
