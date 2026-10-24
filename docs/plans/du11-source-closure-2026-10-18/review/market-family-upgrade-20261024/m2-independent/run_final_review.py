"""Independent final M2 review, source-byte binding and no-model real-source seam."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,importlib,shutil
from datetime import datetime,timezone
ROOT=Path.cwd().resolve()
OUT=ROOT/'docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/m2-independent'
SCRATCH=ROOT/'.m2-independent-bt'
MODULES=['company_wiki.document_normalization','company_wiki.document_normalization.docx_parser','company_wiki.document_normalization.units','company_wiki.document_understanding.native_signal_bridge','company_wiki.document_understanding.observation_adapter','company_wiki.document_understanding.pipeline','company_wiki.document_understanding.profiles.signals','company_wiki.source_catalog.narrative_business_disclosures','company_wiki.source_catalog.narrative_business_policy','company_wiki.source_catalog.narrative_evidence','company_wiki.source_catalog.narrative_normalization','company_wiki.source_catalog.narrative_operating_relations','company_wiki.source_catalog.narrative_reading','company_wiki.source_catalog.transcript_layout','company_wiki.source_catalog.transcript_versions']
TESTS=[str(OUT/'test_m2_independent.py'),'tests/unit/document_understanding_root/test_native_anonymous_turns.py','tests/unit/document_understanding_root/test_qualitative_operating_intent.py','tests/unit/document_understanding_root/test_turn_plan_qualification.py','tests/unit/document_understanding_root/test_normalization_version_capability.py','tests/unit/test_docx_heading_normalization.py','tests/unit/test_native_document_pipeline.py','tests/unit/test_transcript_boundary_versions.py','tests/unit/test_transcript_parser_compatibility.py','tests/unit/document_understanding_selection/test_reading_native_dependency_closure.py','tests/unit/document_understanding_selection/test_reading_native_continuity.py','tests/unit/document_understanding_selection/test_reading_native_carriers.py','tests/unit/test_narrative_reading_model_projection.py','tests/unit/test_narrative_reading_transport.py','tests/unit/du11_source_quality','tests/unit/test_p2_office_table/test_docx_structure.py','tests/unit/test_p2_office_table/test_docx_footnotes.py']
def digest(path):return sha256(path.read_bytes()).hexdigest()
def tree():
 rows={p.relative_to(ROOT).as_posix():digest(p) for p in sorted((ROOT/'src').rglob('*.py'))}
 return {'files':rows,'tree_sha256':sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
def imports():
 r={}
 for name in MODULES:
  p=Path(importlib.import_module(name).__file__).resolve();assert p.is_relative_to(ROOT/'src');r[name]={'path':str(p),'sha256':digest(p)}
 return r
def cleanup():
 assert SCRATCH.resolve().parent==ROOT and SCRATCH.name=='.m2-independent-bt'
 if SCRATCH.exists():shutil.rmtree(SCRATCH)
 assert not SCRATCH.exists()
if __name__=='__main__':
 # This exact exclusive scratch was absent before its first review use; no user
 # fixture data is put here, and each test leaves it absent after the review.
 cleanup()
 before=tree();loaded=imports()
 command=[sys.executable,'-X','utf8','-m','pytest',*TESTS,'-q','--basetemp='+str(SCRATCH),'--junitxml='+str(OUT/'final-semantic.xml')]
 env={**os.environ,'PYTHONPATH':str(ROOT/'src')+';'+str(ROOT/'tests'),'PYTHONDONTWRITEBYTECODE':'1'}
 proc=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
 (OUT/'final-semantic.log').write_text(proc.stdout,encoding='utf-8')
 after=tree();cleanup()
 receipt={'at':datetime.now(timezone.utc).isoformat(),'command':command,'returncode':proc.returncode,'imports':loaded,'before':before,'after':after,'source_unchanged':before==after,'test_files':{str(Path(p).relative_to(ROOT)) if Path(p).is_absolute() else p:digest(Path(p)) for p in TESTS if Path(p).is_file()},'scratch_absent':not SCRATCH.exists(),'limits':'No model, network, credentials or production configuration writes. This semantic suite does not claim whole RF or source content completeness.'}
 (OUT/'final-semantic-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
 print(proc.stdout[-3500:]);print('SOURCE_UNCHANGED',before==after,'SCRATCH_ABSENT',not SCRATCH.exists())
 if proc.returncode or before!=after:raise SystemExit(1)
