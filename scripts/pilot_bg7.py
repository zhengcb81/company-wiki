"""BG-7 pilot: start a real worker in a temp catalog, verify process events."""

import sys
import os
import json
import time
import tempfile
import subprocess

tmp = tempfile.mkdtemp(prefix="cw_pilot_")
catalog_dir = os.path.join(tmp, ".source_catalog")
os.makedirs(catalog_dir)

# Create minimal worker state
state = {
    "last_scan_at": time.time(),
    "last_export_at": time.time(),
    "normalized_total": 0,
    "llm_summarized_total": 0,
}
with open(os.path.join(catalog_dir, "worker_state.json"), "w") as f:
    json.dump(state, f)

# Write worker control
control = {"desired_state": "enabled", "schema_version": "1.0"}
with open(os.path.join(catalog_dir, "worker_control.json"), "w") as f:
    json.dump(control, f)

# Write worker config yaml
import yaml

config_path = os.path.join(catalog_dir, "worker_config.yaml")
yaml.dump(
    {
        "schema_version": "1.2",
        "runtime_config": os.path.join(catalog_dir, "worker_runtime.json"),
        "scan_interval_minutes": 1440,
        "export_interval_minutes": 1440,
        "poll_interval_seconds": 1,
        "idle_seconds_required": 0,
        "normalize_batch_size": 1,
        "llm_summary_batch_size": 1,
        "llm_max_input_chars": 1000,
        "llm_max_output_tokens": 100,
        "llm_retry_backoff_minutes": 1440,
        "allow_processing_on_battery": True,
        "require_user_idle": False,
        "active_poll_interval_seconds": 1,
    },
    open(config_path, "w"),
)

# Run worker as subprocess
pilot_code = f'''
import sys, time, os
sys.path.insert(0, r"C:\\Users\\郑曾波\\Projects\\company-wiki\\src")
os.chdir(r"C:\\Users\\郑曾波\\Projects\\company-wiki")
from pathlib import Path
from company_wiki.source_catalog.control import WorkerController
from company_wiki.source_catalog.worker import SourceCatalogWorker, load_worker_config

catalog_dir = Path(r"{catalog_dir}")
config_path = Path(r"{config_path}")
ctl = WorkerController(catalog_dir)
worker_config = load_worker_config(config_path, project_root=Path(r"C:\\Users\\郑曾波\\Projects\\company-wiki"))
try:
    worker = SourceCatalogWorker(None, worker_config, ctl, None, None)
    worker.run_forever(control=ctl, startup_delay_seconds=0.5)
except Exception as e:
    print(f"ERROR: {{e}}")
'''

proc = subprocess.Popen(
    [sys.executable, "-c", pilot_code],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
time.sleep(4)
proc.kill()
proc.wait()

# Check process events
events_path = os.path.join(catalog_dir, "worker_process_events.jsonl")
events = []
if os.path.exists(events_path):
    for line in open(events_path, "r", encoding="utf-8"):
        if line.strip():
            events.append(json.loads(line.strip()))

event_types = [e["event"] for e in events]
result = {
    "worker_exited": proc.returncode is not None,
    "events_count": len(events),
    "events": event_types,
    "has_starting": "process_starting" in event_types,
    "has_exiting": "process_exiting" in event_types,
}
print(json.dumps(result, indent=2))

import shutil

shutil.rmtree(tmp, ignore_errors=True)
