"""Owned synthetic independent exact-Ref composition probe. No model/network."""
from pathlib import Path
from dataclasses import replace
import json,sys
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests'))
from integration import test_narrative_generation_reuse as reuse
from test_phase_c_readonly_source import _fixture_source, _fingerprint
from company_wiki.source_catalog.source_reader import SourceRef
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source, ReadonlySourceGap
from tools.document_understanding_benchmark import phase_c_runner as runner


def test_exact_ref_six_field_rejection_and_actual_runner_wiring(tmp_path, monkeypatch):
    result_records=[]
    def no_network(*_args, **_kwargs):
        raise AssertionError('independent offline probe forbids sockets')
    monkeypatch.setattr('socket.socket.connect',no_network)
    monkeypatch.setattr('socket.create_connection',no_network)
    with reuse.setup_source('http://127.0.0.1:1/chat/completions') as (_root,catalog,config,_,imported,_kind):
        original,descriptor=_fixture_source(catalog,imported)
        original_ref=SourceRef(**imported['source_ref'])
        protected={p:_fingerprint(p) for p in [original,config,catalog.config.database_path]}
        changes={'document_id':'urn:company-wiki:document:sha256:'+'b'*64,
                 'source_id':'urn:company-wiki:source:sha256:'+'c'*64,
                 'content_sha256':'0'*64,'byte_size':original_ref.byte_size+1,
                 'mime_type':'application/pdf','schema_version':'source-ref/future'}
        for key,value in changes.items():
            with pytest.raises(ReadonlySourceGap) as caught:
                prepare_registered_source(source_config=config,owned_root=tmp_path/('wrong-'+key),
                    original=original,expected_sha256=original_ref.content_sha256,descriptor=descriptor,
                    as_of_date='1900-01-01',expected_ref=replace(original_ref,**{key:value}))
            result_records.append({'mutation':key,'rejected_reason':caught.value.reason})
        descriptor['published_date']=None
        gold=tmp_path/'synthetic-gold.json';gold.write_text('{"facts": []}',encoding='utf-8')
        facts={'content_sha256':original_ref.content_sha256,'facts':{'published_date':None},
               'evidence':{'published_date':{'value':None,'locator':'independent:unknown-publication'}}}
        sample={'sample_id':'neutral-explicit-ref','original':str(original),'fingerprint':runner.fingerprint(original),
                'gold':str(gold),'mime_type':original_ref.mime_type,'source_metadata_observation':descriptor,
                'source_ref':imported['source_ref'],'registered_source_facts':facts}
        metadata=runner.loopback_preparation();provider=metadata['providers'][0]
        provider['options']['endpoint']='https://model.fixture.invalid/chat/completions'
        calls=[]
        def held(owned,output,label,command,env,*args,**kwargs):
            request=json.loads(Path(command[command.index('--request')+1]).read_text(encoding='utf-8'))
            assert request['sources']==[imported['source_ref']]
            calls.append(command)
            raise RuntimeError('INDEPENDENT_EXPLICIT_REF_HELD_BEFORE_MODEL')
        monkeypatch.setattr(runner,'_cli',held)
        destination=tmp_path/'receipt';destination.mkdir()
        outcome=runner.run_pair(sample,provider,metadata,mode='live',output=destination,
            selected_versions='0.9.0',source_mode='registered_readonly',source_catalog_config=config)
        assert len(calls)==1 and outcome['model_post_attempts']==0
        assert outcome['temporary_lake_removed'] and outcome['protected_unchanged'] and outcome['sentinel_unchanged']
        assert outcome['source_registration']['selection']=={'mode':'exact_source_version','filing_identity_period_asof_qualification':'NOT_EVALUATED'}
        assert outcome['source_registration']['manifest']['published_date'] is None
        assert outcome['source_ref']==imported['source_ref']
        assert all(_fingerprint(p)==old for p,old in protected.items())
        result_records.append({'actual_runner_expected_ref_wiring':'PASS','held_cli_calls':len(calls),'model_posts':0,
            'selection':outcome['source_registration']['selection'],'temporary_lake_removed':True,'protected_unchanged':True})
    (Path(__file__).parent/'independent-exact-ref.json').write_text(json.dumps(result_records,indent=2),encoding='utf-8')
