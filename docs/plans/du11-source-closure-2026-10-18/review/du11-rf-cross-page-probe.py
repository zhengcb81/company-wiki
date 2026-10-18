from copy import deepcopy
from test_du11_narrative_citation_wire import draft, finalize, _span
from test_du11_narrative_citation_consumption import consume, binding, entry_two
from company_wiki_narrative_contracts import validate_narrative_response

def test_cross_page_original_support_context_and_uncertainty_remain_source_owned():
    parts=draft(); spans=parts['bundle']['evidence_spans']; mapping={}
    for index,page in ((4,1),(5,2)):
        old=spans[index]; coord={**old['coordinates'],'page_number':page}
        new=_span(old['source_id'],old['raw_text'],coord,deepcopy(old['structured_value']))
        new['quality_flags']=['source_uncertainty'] if page==2 else []
        mapping[old['span_id']]=new['span_id'];mapping[old['locator']]=new['locator'];spans[index]=new
    def remap(v):
        if isinstance(v,str):return mapping.get(v,v)
        if isinstance(v,list):return [remap(x) for x in v]
        if isinstance(v,dict):return {k:remap(x) for k,x in v.items()}
        return v
    parts=remap(parts);spans=parts['bundle']['evidence_spans'];support=[spans[4]['span_id'],spans[5]['span_id']];context=[spans[3]['span_id'],spans[6]['span_id']]
    parts['bundle']['reading_context']['groups']=[{'group_id':'cross-page-source-owned','kind':'native_continuity','section_role':'business','evidence_ids':support+context,'citation_views':[{'support_evidence_ids':support,'context_evidence_ids':context}]}]
    request,body,receipt=finalize(parts);validated=validate_narrative_response(request,body,receipt);value=validated.to_dict(); original=deepcopy(value)
    updated,report=consume(validated,[binding(value,'table_row',citation_view=0)])
    dep=report['citation_trace']['dependencies'][0]
    assert dep['support_evidence_ids']==support and dep['context_evidence_ids']==context
    assert updated['evidence_claims'][-1]['excerpt']==spans[4]['raw_text']=='Overseas | 1,240'
    assert value['evidence_spans'][6]['raw_text']=='Amounts are in USD million unless stated.'
    assert value['evidence_spans'][5]['quality_flags']==['source_uncertainty']
    assert value==original
    result=entry_two(validated,'table_row',citation_view=0);dep2=result['citation_trace']['dependencies'][0]
    assert dep2['support_evidence_ids']==support and dep2['context_evidence_ids']==context
    assert result['claims'][0]['excerpt']==spans[4]['raw_text']
