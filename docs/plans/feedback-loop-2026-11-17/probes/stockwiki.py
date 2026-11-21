"""Exercise StockWiki's ordinary public CLIs, then read F4 with a fresh process.

Run from company-wiki with Python 3.11+ and the StockWiki dependencies installed.
The only argument is the StockWiki checkout; no customer stores or services are used.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[4]
ENTITY = "ENT_11111111-1111-4111-8111-111111111111"


def audit(repo, scratch):
    workspace = scratch / "source"
    workspace.mkdir()
    wrong_input = scratch / "missing.json"
    root = ["--root", str(workspace)]
    commands = {
        "identity_store_offline": (["dashboard_identity_bridge_cli.py", "search", *root, "--query", "Fixture"], b""),
        "bad_identity_invocation": (["dashboard_identity_bridge_cli.py", "resolve", *root], b""),
        "assessment_identity_missing": (["dashboard_company_assessment_cli.py", "read", *root,
                                        "--entity", ENTITY, "--require-identity"], b""),
        "assessment_bounds": (["dashboard_company_assessment_cli.py", "history", *root,
                               "--entity", ENTITY, "--limit", "0"], b""),
        "register_invalid_json": (["dashboard_company_assessment_operator_cli.py", "register", *root], b"{"),
        "publish_unreadable_release": (["dashboard_company_assessment_operator_cli.py", "publish-release",
                                        *root, "--release", str(wrong_input)], b""),
        "work_decision_input_unavailable": (["-m", "stockwiki.quick_scan_refresh_owner_cli", *root,
                                            "--iqs-code-root", str(workspace),
                                            "--work-decision-request", str(wrong_input)], b""),
        "assessment_absence": (["dashboard_company_assessment_cli.py", "read", *root, "--entity", ENTITY], b""),
    }
    result = {}
    plain_env = {key: os.environ[key] for key in
                 ("PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "HOME",
                  "USERPROFILE", "LOCALAPPDATA", "APPDATA", "COMSPEC") if key in os.environ}
    for case, (command, request) in commands.items():
        out = scratch / (case + ".jsonl")
        env = dict(plain_env, RESEARCH_FEEDBACK_RUN_ID=case, RESEARCH_FEEDBACK_ATTEMPT_ID="one",
                   RESEARCH_FEEDBACK_OUT=str(out))
        done = subprocess.run([sys.executable, "-B", "-X", "utf8", *command], cwd=repo, env=env,
                              input=request, capture_output=True, timeout=30)
        try:
            body = json.loads(done.stdout or done.stderr)
        except ValueError:
            body = {"error_code": "usage" if b"usage:" in done.stderr else "unstructured_error"}
        # Each independent inspection uses the unchanged public F4 parser.
        plan = subprocess.run([sys.executable, "-B", "-m", "tools.feedback_loop", "plan", str(out)],
                              cwd=ROOT, env=plain_env, capture_output=True, timeout=30)
        parsed = json.loads(plan.stdout)
        result[case] = {
            "exit": done.returncode,
            "outcome": {k: body[k] for k in ("resolution_status", "state", "status", "reason", "error_code",
                                             "dispatch_started", "API_requests") if k in body},
            "sidecar": out.is_file(),
            "f4": [[r["check_id"], r["actual"], r["disposition"]] for r in parsed["observations"]],
        }
    result["persisted_workspace_files"] = [p.relative_to(workspace).as_posix()
                                           for p in workspace.rglob("*") if p.is_file()]
    return result


if __name__ == "__main__":
    with TemporaryDirectory(prefix="f4-stockwiki-") as tmp:
        print(json.dumps(audit(Path(sys.argv[1]).resolve(), Path(tmp)), ensure_ascii=True, indent=2))
