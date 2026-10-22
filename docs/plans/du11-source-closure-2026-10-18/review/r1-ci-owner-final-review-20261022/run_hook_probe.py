"""Independent, finite actual pre-commit probe in an owned synthetic Git repo."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXTURE = OUT / "hook-fixture"
assert not FIXTURE.exists(), "Do not overwrite a pre-existing probe fixture"
FIXTURE.mkdir()
for original in (ROOT / "src").rglob("*.py"):
    dest = FIXTURE / original.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, dest)
for name in ("pyproject.toml", ".pre-commit-config.yaml"):
    shutil.copyfile(ROOT / name, FIXTURE / name)
subprocess.run(["git", "init", "-q", str(FIXTURE)], check=True)
subprocess.run(["git", "-C", str(FIXTURE), "add", "src", "pyproject.toml", ".pre-commit-config.yaml"],
               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

env = os.environ.copy()
env["PATH"] = str(ROOT / ".venv" / "Scripts") + os.pathsep + env["PATH"]
env["PRE_COMMIT_HOME"] = str(FIXTURE / "pre-commit-home")
env["MYPY_CACHE_DIR"] = str(FIXTURE / "mypy-cache")
env["PYTHON_DOTENV_DISABLED"] = "1"
owner = "src/company_wiki/automation/narrative_run_store.py"
paid = "src/company_wiki/automation/narrative_paid_response.py"
current = (ROOT / owner).read_bytes()
prior = subprocess.run(["git", "show", "HEAD:" + owner], cwd=ROOT,
                       check=True, stdout=subprocess.PIPE).stdout
observations = []


def probe(case, files):
    command = [r"C:\Miniconda\python.exe", "-m", "pre_commit", "run", "mypy-contract",
               "--config", ".pre-commit-config.yaml", "--files", *files]
    started = time.monotonic()
    result = subprocess.run(command, cwd=FIXTURE, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (OUT / (case + ".log")).write_text(result.stdout, encoding="utf-8")
    observations.append({"case": case, "command": command, "returncode": result.returncode,
                         "duration_seconds": round(time.monotonic() - started, 3),
                         "output": result.stdout})


probe("current-single-body", [owner])
(FIXTURE / owner).write_bytes(prior)
probe("original-error-single-body", [owner])
probe("original-error-paired-bodies", [owner, paid])
(FIXTURE / owner).write_bytes(current)
synthetic = FIXTURE / "src/company_wiki/review_type_probe.py"
synthetic.write_text("def needs_str(value: str) -> int:\n    return len(value)\n\n"
                     "def probe(value: str | None) -> int:\n    return needs_str(value)\n", encoding="utf-8")
subprocess.run(["git", "-C", str(FIXTURE), "add", str(synthetic)], check=True)
probe("new-module-local-optional-error", [synthetic.relative_to(FIXTURE).as_posix()])
payload = {"schema_version": "r1-ci-actual-hook-probe/1", "fixture": str(FIXTURE),
           "source_current_sha256": hashlib.sha256(current).hexdigest(),
           "source_original_git_sha256": hashlib.sha256(prior).hexdigest(),
           "hook_config_sha256": hashlib.sha256((ROOT / ".pre-commit-config.yaml").read_bytes()).hexdigest(),
           "observations": observations}
(OUT / "actual-hook.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"cases": [{k:v for k,v in item.items() if k != "output"} for item in observations]},
                 ensure_ascii=False, indent=2))
