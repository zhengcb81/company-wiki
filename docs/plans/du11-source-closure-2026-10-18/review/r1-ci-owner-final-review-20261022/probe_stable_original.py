from pathlib import Path
import json
import os
import subprocess
import time
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXTURE = OUT / "hook-fixture"
owner = "src/company_wiki/automation/narrative_run_store.py"
old = subprocess.run(["git", "show", "2f632193:" + owner], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout
(FIXTURE / owner).write_bytes(old)
config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
hook = next(h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "mypy-contract")
hook["entry"] = "python -m mypy"
hook["pass_filenames"] = True
(FIXTURE / ".pre-commit-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
env = os.environ.copy()
env["PATH"] = str(ROOT / ".venv/Scripts") + os.pathsep + env["PATH"]
env["PRE_COMMIT_HOME"] = str(FIXTURE / "pre-commit-home")
env["MYPY_CACHE_DIR"] = str(FIXTURE / "mypy-cache")
command = [r"C:\Miniconda\python.exe", "-m", "pre_commit", "run", "mypy-contract",
           "--config", ".pre-commit-config.yaml", "--files", owner]
started = time.monotonic()
result = subprocess.run(command, cwd=FIXTURE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace")
payload = {"case": "changed-original-explicit-2f", "command": command,
           "returncode": result.returncode, "seconds": round(time.monotonic() - started, 3),
           "source_commit": "2f632193014a1bbdd223dd578d6a3a697555b1b8", "output": result.stdout}
(OUT / "changed-original-explicit-2f.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
(OUT / "changed-original-explicit-2f.log").write_text(result.stdout, encoding="utf-8")
print(json.dumps(payload, indent=2))
