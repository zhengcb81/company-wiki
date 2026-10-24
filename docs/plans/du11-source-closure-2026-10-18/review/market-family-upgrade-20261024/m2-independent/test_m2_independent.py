"""Independent M2 counterexamples and real public carrier/model compilation."""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import io,json,zipfile
from xml.sax.saxutils import escape
import pytest
from company_wiki.document_normalization import normalize_document,replay_units,NormalizationLimits
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.source_catalog.narrative_evidence import parse_transcript_text
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.transcript_layout import AnonymousTurnObserver

MIME='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
TITLE='某公司财报交流会'
PLAN='Speaker 2 00:20 We plan to launch new products.'
LIMIT='But this launch plan has not been finalized and may change.'

def package(lines,heading=None):
    rows=[]
    for i,t in enumerate(lines):
        props='<w:pPr><w:outlineLvl w:val="0"/></w:pPr>' if i==heading else ''
        rows.append('<w:p>'+props+'<w:r><w:t>'+escape(t)+'</w:t></w:r></w:p>')
    xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join(rows)+'</w:body></w:document>'
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:z.writestr('word/document.xml',xml.encode())
    return out.getvalue()

def doc(lines,heading=None,version=None):
    raw=package(lines,heading);h=sha256(raw).hexdigest()
    return raw,normalize_document(raw,source_id='urn:company-wiki:source:sha256:'+h,source_sha256=h,mime_type=MIME,parser_version=version)

def txt(text,version='0.4.0'):
    h=sha256(text.encode()).hexdigest()
    return parse_transcript_text(text,source_id='urn:company-wiki:source:sha256:'+h,source_sha256=h,parser_version=version)

def route(units,title=TITLE):
    return understand_units(units,source_id='projection:independent',source_sha256='a'*64,mime_type=MIME,title=title)['route']['family']

@pytest.mark.parametrize('end',('End of transcript','Speaker 1 00:40 This concludes the call.'))
def test_docx_end_control_stops_native_turn_before_editorial_footer(end):
    _,d=doc(['Speaker 1 00:00 Initial business remarks.',end,'Website Editor: independent footer.'])
    assert 'native_speaker_turn' not in d.units[-1].metadata


def test_empty_physical_heading_clears_native_turn_before_suppressing_empty_text():
    _,d=doc(['Speaker 1 00:00 Business.','','Unattributed body after native heading.'],heading=1)
    assert 'native_speaker_turn' not in d.units[-1].metadata


def test_docx_structural_boundary_after_end_never_reopens_closed_transcript():
    _,d=doc(['Speaker 1 00:00 An actual business response.',
             'End of transcript','Editorial Appendix',
             'Speaker 7 01:20 A navigation placeholder after the transcript.'],heading=2)
    assert 'native_speaker_turn' not in d.units[-1].metadata


def test_shared_turn_clear_is_a_boundary_not_a_new_source_session():
    observer=AnonymousTurnObserver()
    assert observer.observe('Speaker 1 00:00 An actual response.',source_id='s',locator='p:0')
    assert observer.observe('End of transcript',source_id='s',locator='p:1') is None
    observer.clear()
    assert observer.observe('Speaker 7 01:20 A footer placeholder.',source_id='s',locator='p:3') is None


def test_txt_natural_body_heading_owns_roster_exclusion():
    text=('Speaker 8 00:00 Editorial roster.\nSpeaker 9 00:10 Editorial reply.\n'
          'Earnings Call Transcript\nSpeaker 1 01:00 Product discussion.\n'
          'Speaker 2 01:10 Delivery remains conditional.\nEnd of transcript')
    p=txt(text)
    assert p.units
    assert all('Editorial' not in u.raw_text and u.raw_text!='Earnings Call Transcript' for u in p.units)


def test_named_speaker_after_anonymous_turn_is_a_real_boundary():
    p=txt('Speaker 1 00:00 What are the operating plans for the coming quarter?\nSpeaker 2 00:10 We plan to launch a new product after the review.\n'
          'John Doe, Chief Executive Officer: The named response.\nEnd of transcript')
    named=next(u for u in p.units if 'named response' in u.raw_text)
    assert named.metadata.get('native_speaker_turn',{}).get('speaker')!='Speaker 2'

@pytest.mark.parametrize('clock',('65:12','123:45','01:05:12'))
def test_elapsed_clock_not_limited_to_subhour_minutes(clock):
    value=AnonymousTurnObserver().observe('Speaker 3 '+clock+' New late speaker.',source_id='s',locator='p:1')
    assert value and value['speaker']=='Speaker 3' and value['timestamp']==clock

@pytest.mark.parametrize('clock',('99:99','00:000','01:60:20','00:10:20:30'))
def test_invalid_clocks_do_not_create_a_native_actor(clock):
    assert AnonymousTurnObserver().observe('Speaker 3 '+clock+' Text.',source_id='s',locator='p:1') is None


def test_native_speakers_from_different_originals_cannot_route_combined_projection_as_call():
    _,a=doc(['Speaker 1 00:00 We discuss earnings.'])
    _,b=doc(['Speaker 2 00:12 We discuss the quarter.'])
    assert a.source_id!=b.source_id
    assert route([*a.units,*b.units])!='earnings_call'


def test_same_native_actor_with_whitespace_variants_cannot_count_as_two():
    _,d=doc(['Speaker 1 00:00 We discuss earnings.','Speaker  1 00:12 We discuss the quarter.'])
    assert route(d.units)!='earnings_call'

@pytest.mark.parametrize('text',(
    'The company plans to update business expense records.',
    'We plan to update customer acquisition training records.',
    'We plan to launch product training manuals for employees.',
    '公司计划推出产品培训手册供内部员工使用。',
))
def test_intent_object_head_is_not_a_business_word_modifying_admin_material(text):
    assert 'operating_plan' not in detect_reading_business_fact(text).reasons

@pytest.mark.parametrize('text',('公司计划更新产品。','We plan to continue customer support.','We hope to continue our service platform.'))
def test_link_tokenization_must_not_swallow_the_actual_intent_action(text):
    assert 'operating_plan' in detect_reading_business_fact(text).reasons


def test_txt_observes_each_native_line_once(monkeypatch):
    seen=[];old=AnonymousTurnObserver.observe
    def observe(self,text,**kwargs):
        seen.append(kwargs['locator']);return old(self,text,**kwargs)
    monkeypatch.setattr(AnonymousTurnObserver,'observe',observe)
    lines=['Full Conference Call Transcript','Speaker 1 00:00 What are the new product launch plans?','Speaker 2 00:20 We plan to launch new products next year.',*[f'Continuation line {i}.' for i in range(128)],'End of transcript']
    result=txt('\n'.join(lines))
    assert result.units
    assert len(seen)==len(set(seen))
    assert len(seen)<=len(lines)

@pytest.mark.parametrize('version',('1.0.0','1.1.0'))
def test_saved_docx_pins_remain_distinct_and_replayable(version):
    lines=['Speaker 1 00:00 Business.','Speaker 2 00:10 Product plans.']
    raw,new=doc(lines)
    old=normalize_document(raw,source_id=new.source_id,source_sha256=new.source_sha256,mime_type=MIME,parser_version=version)
    assert old.parser_version==version and new.parser_version=='1.2.0'
    assert all('native_speaker_turn' not in u.metadata for u in old.units)
    assert set(u.unit_id for u in new.units).isdisjoint(u.unit_id for u in old.units)
    assert replay_units(raw,source_sha256=old.source_sha256,units=old.units,limits=NormalizationLimits())==tuple(lines)


def selected(lines,mime=MIME):
    from unit.test_narrative_select_handler import _payload,_context,FakeReader
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.models import HandlerOutcome
    data=package(lines) if mime==MIME else ('\n'.join([TITLE,*lines,'End of transcript'])).encode()
    p=_payload(data,title=TITLE,document_kind='investor_relations' if mime==MIME else 'earnings_call_transcript',language='en',mime_type=mime)
    output=NarrativeSelectHandler(reader=FakeReader(p,data),selector_version='0.9.0')(_context(p,lambda:None))
    assert output.outcome is HandlerOutcome.SUCCEEDED,output.error
    return data,NarrativeSelectResult.from_dict(output.result)

@pytest.mark.parametrize('mime',(MIME,'text/plain'))
def test_actual_selected_roundtrip_model_material_and_unknown_role_remain_source_bound(mime):
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_replay import replay_narrative_evidence
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
    data,s=selected(['Speaker 1 00:00 Will production begin?',PLAN,LIMIT,'Speaker 1 01:00 Is this already final?'],mime)
    assert s.evidence_spans
    restored=NarrativeSelectResult.from_dict(json.loads(json.dumps(s.to_dict())))
    assert restored.to_dict()==s.to_dict()
    assert replay_narrative_evidence(data,restored)==len(s.evidence_spans)
    request=build_model_request(restored,reading_projection_version='reading-model-input/5')
    value=json.loads(request.data_json)
    assert value['schema_version']=='narrative-model-request/6'
    assert PLAN in request.data_json
    assert LIMIT in request.data_json,'Same-turn adjacent limitation must reach the source task, not remain hidden raw'
    claims=compile_extractive_plan(s).draft['claims']
    assert claims and all(c['modality']!='actual' for c in claims)
    assert all(span.structured_value['source_role']=='unknown' for span in s.evidence_spans)


def test_current_docx_parser_pin_from_actual_worker_option_assembler_is_accepted_and_replayed():
    from types import SimpleNamespace
    from unit.test_narrative_select_handler import _payload
    from company_wiki.automation.narrative_batch import _normalization_parsers
    from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
    raw,document=doc(['Speaker 1 00:00 Business.','Speaker 2 00:10 Product plans.'])
    payload=_payload(raw,title=TITLE,document_kind='investor_relations',language='en',mime_type=MIME)
    event=SimpleNamespace(payload_json=json.dumps(payload),subject_id='doc-select')
    binding=SimpleNamespace(events=(event,),generation_manifests={'doc-select':{'parser_component':{'version':document.parser_version}}})
    parsers=_normalization_parsers(binding,{})
    assert parsers=={'doc-select':'1.2.0'}
    # This is the real serialized option consumed by worker_factory.create_runtime.
    restored=json.loads(json.dumps(parsers))
    normalization=NarrativeNormalization(parser_versions=restored)
    again=normalization.normalize(raw,source_id=document.source_id,source_sha256=document.source_sha256,mime_type=MIME,document_id='doc-select')
    assert again.parser_version=='1.2.0'
    spans=tuple(unit.to_evidence_span(topics=[],selection_reasons=[]) for unit in again.units)
    assert normalization.replay(raw,source_id=document.source_id,source_sha256=document.source_sha256,mime_type=MIME,evidence_spans=spans)==len(spans)


@pytest.mark.parametrize('heading',('',TITLE+'\n'))
@pytest.mark.parametrize('body',('', ' A中xx'))
def test_empty_labels_and_one_cjk_letter_are_not_actual_transcript_body(heading,body):
    p=txt(heading+'Speaker 1 00:00'+body+'\nSpeaker 2 00:10'+body)
    assert not p.units
    assert 'transcript_start_missing' in p.errors


def card_texts(s):
    from company_wiki.document_understanding.source_cards import source_cards
    from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
    p=build_summary_task_plan(s.evidence_spans,reading_context=s.reading_context,max_claims=40)
    return [c.text or '' for c in source_cards(p,{span.span_id:span for span in s.evidence_spans})]


@pytest.mark.parametrize('mime',(MIME,'text/plain'))
@pytest.mark.parametrize('gap',('We discussed an unrelated topic before returning to the launch plan.',
    'Speaker 1 00:30 This is a different question, with its own separate answer.'))
def test_plan_qualification_never_jumps_an_intervening_original_or_actor(mime,gap):
    _,s=selected(['Speaker 1 00:00 When will production begin?',PLAN,gap,LIMIT],mime)
    assert not any(PLAN in t and LIMIT in t for t in card_texts(s))


@pytest.mark.parametrize('mime',(MIME,'text/plain'))
def test_unbounded_intrinsic_limitation_defers_whole_plan_instead_of_naked_card(mime):
    from unit.test_narrative_select_handler import _payload,_context,FakeReader
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.automation.models import HandlerOutcome
    caveat=LIMIT+' '+('Detailed conditions remain subject to financing and regulatory approval. '*45)
    lines=['Speaker 1 00:00 When will production begin?',PLAN,caveat]
    data=package(lines) if mime==MIME else ('\n'.join([TITLE,*lines,'End of transcript'])).encode()
    p=_payload(data,title=TITLE,document_kind='investor_relations' if mime==MIME else 'earnings_call_transcript',language='en',mime_type=mime)
    output=NarrativeSelectHandler(reader=FakeReader(p,data),selector_version='0.9.0')(_context(p,lambda:None))
    # No eligible complete material is a legitimate bounded result. It must not
    # manufacture a successful smaller card by cutting away its own caveat.
    assert output.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert output.error.code=='PARSER_INCOMPLETE'


@pytest.mark.parametrize('mime',(MIME,'text/plain'))
def test_ordinary_question_does_not_become_plan_factual_support(mime):
    question='Speaker 1 00:00 Does the company have enough funding to launch products?'
    _,s=selected([question,PLAN,LIMIT],mime)
    assert any(PLAN in t and LIMIT in t for t in card_texts(s))
    assert not any(PLAN in t and question in t for t in card_texts(s))


@pytest.mark.parametrize('dimension',('source_id','parser_version','source_role','native_turn'))
def test_local_turn_dependency_never_borrows_other_source_parser_role_or_turn(dimension):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import WorkBudget
    _,d=doc([PLAN,LIMIT])
    a,b=d.units
    if dimension=='native_turn':
        b=replace(b,metadata={**b.metadata,'native_speaker_turn':{
            **b.metadata['native_speaker_turn'],'turn_id':'different-original-turn'}})
    else:
        b=replace(b,**{dimension:{'source_id':'other-source','parser_version':'1.1.0','source_role':'management'}[dimension]})
    s=SourceOperatingSession({u.unit_id:u for u in (a,b)},work_budget=WorkBudget(100000))
    assert not s.local_qualification_dependencies(())
    assert s.complete


def test_local_turn_dependency_charges_existing_budget_without_fallback_on_exhaustion():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import WorkBudget
    _,d=doc([PLAN,LIMIT])
    normal=SourceOperatingSession({u.unit_id:u for u in d.units},work_budget=WorkBudget(100000))
    assert normal.local_qualification_dependencies(())=={d.units[0].unit_id:(d.units[1].unit_id,)}
    assert normal.work_budget.used>len(PLAN)+len(LIMIT)
    budget=WorkBudget(1)
    small=SourceOperatingSession({u.unit_id:u for u in d.units},work_budget=budget)
    assert small.local_qualification_dependencies(())=={}
    assert not small.complete and budget.exhausted and budget.used<=1


def test_short_chinese_native_turns_need_real_body_but_keep_unknown_identity():
    p=txt(TITLE+'\n说话人1 00:00 产品何时发布？\n说话人2 00:10 公司计划更新产品。\n但具体计划尚未确定。\nEnd of transcript')
    assert p.units and not p.errors
    assert all(u.source_role=='unknown' for u in p.units)
