"""Observe native outline/physical flow outputs on an immutable real source."""
from pathlib import Path
from dataclasses import asdict,is_dataclass
import hashlib,json

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.narrative_reading import _understand
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef,SourceVersionReader
from company_wiki.document_understanding.structure import sections
from company_wiki.document_understanding.narrative_continuity import NativeSourceContext

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/"pyproject.toml").exists())
SELECTION=HERE.parent/"st-a13-recognition-scope-20261025/attempt06/selection.json"
PROJECT=ROOT/".planning/shared-reading-production/r1-holdout-20261021/CN-603259/wiki"
CONFIG=PROJECT/"config/source_catalog.yaml"
OUTPUT=HERE/"real-structure-observation.json"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(u):return {"unit_id":u.unit_id,"page":u.page,"text":u.text[:180],"bbox":u.bbox,"column":u.column,"kind":u.kind,"heading_level":u.heading_level}

def main():
 if OUTPUT.exists():raise FileExistsError(OUTPUT)
 selection=json.loads(SELECTION.read_text(encoding="utf-8"));ref=SourceRef(**selection["source_ref"])
 config=load_catalog_config(CONFIG,project_root=PROJECT)
 protected={str(p):sha(p) for p in [CONFIG,config.database_path]}
 source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"src/company_wiki").rglob("*.py")}
 observed={"scopes":[],"physical_calls":[]}
 original_scopes=sections._native_list_scopes;original_page=NativeSourceContext.page_neighbour
 def scopes(ordering,native_context=None):
  result=original_scopes(ordering,native_context)
  observed["ordered_units"]=[row(u) for u in ordering.ordered if u.page in (13,14)]
  observed["scopes"]=[{"head":row(s.heads[0]),"heads":[row(u) for u in s.heads],"members":[row(u) for u in s.members],"context_by_unit":s.context_by_unit,"source_proofs":s.proofs_by_unit} for s in result.values() if s.heads[0].page in (13,14)]
  return result
 def page(self,left_id,right_id,*,furniture_unit_ids):
  before=dict(self.diagnostics)
  result=original_page(self,left_id,right_id,furniture_unit_ids=furniture_unit_ids)
  left=self.observations.get(left_id);right=self.observations.get(right_id)
  if getattr(left,"page",None)==13 and getattr(right,"page",None)==14:
   observed["physical_calls"].append({"left":asdict(left) if is_dataclass(left) else None,"right":asdict(right) if is_dataclass(right) else None,"proof":result,"diagnostics_added":{k:v-before.get(k,0) for k,v in self.diagnostics.items() if v!=before.get(k,0)}})
  return result
 catalog=SourceCatalog(config);budget=new_document_work_budget()
 try:
  verified=SourceVersionReader(catalog).open_version(ref,purpose="preview")
  if hashlib.sha256(verified.data).hexdigest()!=ref.content_sha256:raise RuntimeError("original SHA mismatch")
  sections._native_list_scopes=scopes;NativeSourceContext.page_neighbour=page
  parsed=parse_pdf_bytes(verified.data,source_id=ref.source_id,source_sha256=ref.content_sha256,language="zh",selector_version="0.9.0",work_budget=budget)
  oracle=json.loads((ROOT/".planning/r1-w08-real-20261023/oracle.json").read_text(encoding="utf-8"))
  pipeline=_understand(parsed,title=oracle["title"],kind=oracle["document_kind"],mime_type="application/pdf",work_budget=budget)
  observed["sections"]=[s for s in pipeline["structure"]["sections"] if any(u["unit_id"] in s.get("body_unit_ids",[]) or u["unit_id"] in s.get("heading_unit_ids",[]) for u in observed["ordered_units"])]
  if catalog._store is not None:raise RuntimeError("read-only probe constructed store")
 finally:
  sections._native_list_scopes=original_scopes;NativeSourceContext.page_neighbour=original_page;catalog.close()
 if protected!={str(p):sha(p) for p in [CONFIG,config.database_path]}:raise RuntimeError("protected config/catalog changed")
 if source_hashes!={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"src/company_wiki").rglob("*.py")}:raise RuntimeError("production changed during probe")
 observed.update(schema_version="st-a05-real-structure-observation/1",source_ref=selection["source_ref"],selection_sha256=sha(SELECTION),source_sha256=source_hashes,protected_unchanged=True,producer_unchanged=True,work_used=budget.used,work_limit=budget.max_work_units,work_exhausted=budget.exhausted,model_calls=0,downloads=0,raw_copies=0,summary_semantics="NOT_REVIEWED")
 body=json.dumps(observed,ensure_ascii=False,indent=2)+"\n"
 if len(body.encode())>256*1024:raise RuntimeError("bounded observation exceeded256KiB")
 with OUTPUT.open("x",encoding="utf-8") as f:f.write(body)
 print(json.dumps({"scope_heads":[s["head"]["text"] for s in observed["scopes"]],"cross_page_calls":len(observed["physical_calls"]),"physical_diagnostics":[x["diagnostics_added"] for x in observed["physical_calls"]],"work_used":budget.used,"bytes":len(body.encode())},ensure_ascii=False))

if __name__=="__main__":main()
