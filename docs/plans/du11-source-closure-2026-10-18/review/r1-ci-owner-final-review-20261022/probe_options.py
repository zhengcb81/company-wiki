from pathlib import Path
import json
import os
import subprocess
import time
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXTURE = OUT / "hook-fixture"
config_path = FIXTURE / ".pre-commit-config.yaml"
original_config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
owner = "src/company_wiki/automation/narrative_run_store.py"
original = subprocess.run(["git", "show", "2f632193:" + owner], cwd=ROOT,
                           check=True, stdout=subprocess.PIPE).stdout
current = (ROOT / owner).read_bytes()
probe = FIXTURE / "src/company_wiki/review_type_probe.py"
assert probe.is_file()
subprocess.run(["git", "-C", str(FIXTURE), "rm", "-f", "--", probe.relative_to(FIXTURE).as_posix()],
               check=True, stdout=subprocess.PIPE)
env = os.environ.copy()
env["PATH"] = str(ROOT / ".venv/Scripts") + os.pathsep + env["PATH"]
env["PRE_COMMIT_HOME"] = str(FIXTURE / "pre-commit-home")
observations = []
for case, entry, pass_filenames, body, cache in (
    ("silent-original-cold", "python -m mypy --follow-imports=silent", True, original, "silent-cache"),
    ("full-original-cold", "python -m mypy src", False, original, "full-cache"),
    ("full-fixed-warm", "python -m mypy src", False, current, "full-cache"),
):
    config = json.loads(json.dumps(original_config))
    hook = next(h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "mypy-contract")
    hook["entry"] = entry
    hook["pass_filenames"] = pass_filenames
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (FIXTURE / owner).write_bytes(body)
    env["MYPY_CACHE_DIR"] = str(FIXTURE / cache)
    command = [r"C:\Miniconda\python.exe", "-m", "pre_commit", "run", "mypy-contract",
               "--config", ".pre-commit-config.yaml", "--files", owner]
    started = time.monotonic()
    result = subprocess.run(command, cwd=FIXTURE, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (OUT / (case + ".log")).write_text(result.stdout, encoding="utf-8")
    observations.append({"case": case, "entry": entry, "pass_filenames": pass_filenames,
                         "returncode": result.returncode,
                         "seconds": round(time.monotonic() - started, 3), "output": result.stdout})
(OUT / "hook-options.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
print(json.dumps(observations, indent=2))
