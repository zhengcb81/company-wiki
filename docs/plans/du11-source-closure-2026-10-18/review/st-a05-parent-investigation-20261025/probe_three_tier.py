"""Neutral native hierarchy observation; no product edits or financial facts."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0,str(ROOT / "tests"))
from unit.document_understanding_selection.test_reading_native_list_ancestry import _source, _run_public, _own_context

rows=[
 (1,"一、经营情况",0,(90,100,550,112)),
 (1,"(1) 仪器业务实现收入12亿元。",1,(90,640,550,672)),
 (1,"报告期内：",1,(90,640,550,672)),
 (1,"- 维护服务保持增长。",2,(110,690,550,702)),
 (1,"i. 服务客户数量增长15%。",3,(125,720,550,732)),
 (2,"- 制造服务保持增长。",0,(110,70,550,82)),
 (2,"i. 服务收入达到8亿元，同比增长18%。",1,(125,105,550,117)),
 (2,"- 软件服务保持增长。",2,(110,160,550,172)),
 (2,"i. 客户订单增长20%。",3,(125,195,550,207)),
 (2,"(2) 消费业务实现收入9亿元。",4,(90,250,550,282)),
 (2,"报告期内：",4,(90,250,550,282)),
 (2,"- 订阅用户数量增长12%。",5,(110,300,550,312)),
]
parsed=_source(rows)
pipeline,selected,work=_run_public(parsed)
unit={u.raw_text:u for u in parsed.units}
parent=unit[rows[1][1]];intro=unit[rows[2][1]];sibling=unit[rows[9][1]]
checks=[_own_context(parsed,pipeline,selected,unit[rows[i][1]],(parent,intro,unit[rows[j][1]]),sibling)
        for i,j in [(4,3),(6,5),(8,7)]]
result={"schema_version":"st-a05-neutral-three-tier-observation/1","kind":"NEUTRAL_FIXTURE_NOT_REAL_SOURCE_ACCEPTANCE",
 "expected":"Each roman business fact keeps numbered business parent, intro and its own bullet; never the numbered sibling",
 "work_used":work,"checks":checks,"failed_checks":sum(bool(c["failures"]) for c in checks),
 "source_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
 ROOT/"src/company_wiki/document_understanding/structure/sections.py",ROOT/"src/company_wiki/source_catalog/narrative_native_dependencies.py"]},
 "model_calls":0,"downloads":0,"raw_copies":0}
out=Path(__file__).with_name("neutral-observation.json")
with out.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
print(json.dumps({"failed_checks":result["failed_checks"],"failures":[x["failures"] for x in checks],"work_used":work},ensure_ascii=False))
