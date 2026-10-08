"""Test the five repaired files on HEAD, excluding every pre-existing owner edit."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

repo = Path("C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite")
scope = ["src/cninfo_api.py", "tests/unit/test_cninfo_api.py",
         "tests/unit/test_cninfo_api_fixture_contract.py",
         "tests/unit/test_company_wiki_adapter.py", "tests/unit/test_g4_latest_discovery.py"]
base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
archive = subprocess.check_output(["git", "archive", "--format=zip", "HEAD"], cwd=repo)
record = {"base_commit": base, "owner_edits_included": False, "overlay": []}
with tempfile.TemporaryDirectory(prefix="cwp-rf-sid-clean-scope-") as tmp:
    root = Path(tmp).resolve()
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        for item in zipped.infolist():
            target = (root / item.filename).resolve()
            assert target.is_relative_to(root), item.filename
        zipped.extractall(root)
    for relative in scope:
        data = (repo / relative).read_bytes()
        shutil.copyfile(repo / relative, root / relative)
        record["overlay"].append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *scope[1:]]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=False, timeout=90)
    print(completed.stdout)
    print(completed.stderr, file=sys.stderr)
    record.update(returncode=completed.returncode, isolated_root=str(root))
record["temporary_root_restored"] = not root.exists()
print(json.dumps(record, ensure_ascii=False))
sys.exit(completed.returncode)
