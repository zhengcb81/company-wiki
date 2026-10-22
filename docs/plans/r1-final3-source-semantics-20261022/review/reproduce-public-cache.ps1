Set-Location -LiteralPath 'C:/Users/郑曾波/Projects/company-wiki-r1-local-observation'
$env:PYTHONPATH='C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/src;C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/tests'
$env:PYTHONIOENCODING='utf-8'
@'
import sys,json
from pathlib import Path
import company_wiki.source_catalog.narrative_reading as reading
import company_wiki.source_catalog.narrative_business_policy as policy
import company_wiki.source_catalog.narrative_source_purpose as purpose
root=Path.cwd()
modules=(reading,policy,purpose)
assert all(Path(m.__file__).resolve().is_relative_to(root/'src') for m in modules)
print(json.dumps({'phase':'before_pytest','module_files':[m.__file__ for m in modules]},ensure_ascii=True))
import pytest
code=pytest.main(['docs/plans/r1-final3-source-semantics-20261022/review/test_w08_public_cache.py','-q','-p','no:cacheprovider','--basetemp',str(root/'docs/plans/r1-final3-source-semantics-20261022/review/public-cache-reproduce-temp'),'--junitxml',str(root/'docs/plans/r1-final3-source-semantics-20261022/review/public-cache-reproduce.xml')])
assert all(Path(m.__file__).resolve().is_relative_to(root/'src') for m in modules)
print(json.dumps({'phase':'after_pytest','module_files':[m.__file__ for m in modules],'pytest_exit':code},ensure_ascii=True))
raise SystemExit(code)
'@ | & 'C:\Users\郑曾波\Projects\company-wiki\.venv\Scripts\python.exe' -B - 2>&1 | Tee-Object -FilePath 'C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/docs/plans/r1-final3-source-semantics-20261022/review/public-cache-reproduce.stdout.txt'
exit $LASTEXITCODE
