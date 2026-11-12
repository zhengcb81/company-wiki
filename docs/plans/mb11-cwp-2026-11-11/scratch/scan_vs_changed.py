"""Scratch probe: correlate sealed Mimosa findings with this card's changed files."""
import json
from pathlib import Path

SCAN = Path(
    r"C:\Users\郑曾波\.mimosa\security-scans"
    r"\project-099bfc3848aeccb99683ccb4"
    r"\scan-2026-11-12T21-35-54.861Z-e20dc0968b7b"
)

CHANGED = {
    "src/company_wiki/source_catalog/source_stream_cli.py",
    "src/company_wiki/source_catalog/cn_primary_issuer.py",
    "src/company_wiki/source_catalog/local_reconcile.py",
    "src/company_wiki/source_catalog/narrative_selection.py",
    "src/company_wiki/source_catalog/narrative_decision_inventory.py",
    "src/company_wiki/source_catalog/narrative_normalization.py",
    "src/company_wiki/resource_budget.py",
    "src/company_wiki/document_model/narrative.py",
    "src/company_wiki/automation/narrative_transport.py",
    "src/company_wiki/automation/narrative_source_guard.py",
    "src/company_wiki/automation/narrative_transport_cli.py",
    "src/company_wiki/automation/narrative_batch.py",
    "src/company_wiki/automation/narrative_select.py",
    "src/company_wiki/automation/narrative_runtime.py",
    "src/company_wiki/automation/narrative_worker_factory.py",
    "src/company_wiki/automation/narrative_batch_cli.py",
    "scripts/config.py",
    "tests/contract/test_module_owner_isolation.py",
    "tests/contract/test_installed_public_entrypoints.py",
    "tests/contract/test_source_stream_cli.py",
    "tests/contract/test_cn_primary_issuer.py",
    "tests/unit/test_work_budget_injection.py",
    "tests/unit/test_document_model_identity.py",
    "tests/unit/test_narrative_config_scope.py",
    "tests/unit/b34_cwp_diagnostic/test_unresolved_diagnostics.py",
    "tests/unit/b34_cwp_prospectus/test_ipo_cover.py",
    "tests/integration/test_transport_normalization_injection.py",
    "pyproject.toml",
}

rows = json.loads((SCAN / "findings.json").read_text(encoding="utf-8"))
rows = rows if isinstance(rows, list) else rows.get("findings", [])


def norm(path: str) -> str:
    return path.replace("\\", "/").strip()


mine = [
    row for row in rows
    if norm(str(row.get("location", {}).get("path", ""))) in CHANGED
]
print("total findings:", len(rows))
print("findings in exactly this card's changed files:", len(mine))
for row in mine:
    print(row["severity"], row["location"], row["title"],
          str(row.get("message", ""))[:120])

# Which of the pre-commit-blocked files does the sealed scan flag?
blocked = ["test_automation_migrations.py", "test_llm_client.py",
           "identity_candidates.py"]
for name in blocked:
    hits = [row for row in rows if name in norm(str(row.get("location", {}).get("path", "")))]
    print("pre-existing blocked file", name, "->", len(hits), "findings",
          sorted({row["severity"] for row in hits}))
