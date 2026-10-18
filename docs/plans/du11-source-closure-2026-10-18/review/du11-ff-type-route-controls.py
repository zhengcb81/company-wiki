"""Independent schema and hook route controls, pure synthetic wires only."""
from pathlib import Path
import re
import pytest
import yaml
from test_du11_transcript_reuse_selection import excluded, result
from transcript_reuse_selection import _QUALIFICATION_FIELDS, select_local_outcome, LocalQueryContractError


def test_exact_class_info_values_remain_runtime_compatible():
    assert _QUALIFICATION_FIELDS == {'publication_status':str, 'as_of_date':(str,type(None)),
        'local_bytes_status':str, 'historical_date_eligible':(bool,type(None)),
        'historical_reuse_eligible':(bool,type(None)), 'schema_version':str}
    for value in _QUALIFICATION_FIELDS.values():
        assert isinstance(value,type) or isinstance(value,tuple) and all(isinstance(t,type) for t in value)


@pytest.mark.parametrize('field,value', [('publication_status',7), ('as_of_date',20260930),
    ('local_bytes_status',False), ('historical_date_eligible',1),
    ('historical_reuse_eligible','yes'), ('schema_version',None)])
def test_malformed_qualification_types_still_refused(field,value):
    item=excluded('unknown')
    item['qualification'][field]=value
    with pytest.raises(LocalQueryContractError):
        select_local_outcome(result({'status':'not_found','excluded_candidates':[item]}))


@pytest.mark.parametrize('date',[None,'2026-09-30'])
def test_real_unknown_qualification_not_converted_to_missing(date):
    item=excluded('unknown',as_of_date=date)
    selection=select_local_outcome(result({'status':'not_found','excluded_candidates':[item]}))
    assert selection.kind == 'unknown_publication'
    assert selection.source_ref is not None
    assert selection.qualification == item['qualification']


def test_same_mypy_entry_covers_new_runtime_and_preserves_docs_fastpath():
    data=yaml.safe_load((Path(__file__).parents[1]/'.pre-commit-config.yaml').read_text())
    hook=next(h for r in data['repos'] for h in r['hooks'] if h['id']=='mypy-contract')
    assert hook['entry']=='python -m mypy scripts/filing_contracts.py scripts/fetch_filing.py'
    assert hook['pass_filenames'] is False
    assert hook['language']=='system'
    for path in ['scripts/transcript_reuse_selection.py','scripts/transcript_tool_transport.py','scripts/new_runtime.py','scripts/nested/new.py','scripts/fetch_filing.py']:
        assert re.search(hook['files'],path)
    for path in ['docs/readme.md','tests/test_any.py','tools/ci_tests.py','.github/workflows/quality.yml','scripts/readme.md','scripts/thing.py.bak','notscripts/runtime.py']:
        assert not re.search(hook['files'],path)
