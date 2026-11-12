"""Scratch probe: run installed-wheel entrypoints from a non-repo cwd."""
import subprocess
import sys
from pathlib import Path

VENV_PY = Path(r"C:/Users/Public/mb11-cwp-scratch/venv/Scripts/python.exe")
CWD = Path(r"C:/Users/Public/mb11-cwp-scratch/empty-cwd")
CWD.mkdir(exist_ok=True)

CONSOLE = [
    "company-wiki-source-export",
    "company-wiki-collect-announcement",
    "company-wiki-source-catalog",
    "company-wiki-source-read",
    "company-wiki-source-query",
    "company-wiki-company-sources",
    "company-wiki-source-export-v2",
    "company-wiki-identify",
    "company-wiki-transcript-import",
    "company-wiki-narrative-read",
    "company-wiki-narrative-batch",
]
MODULES = [
    "company_wiki.source_catalog.processed_document_cli",
    "company_wiki.source_catalog.financial_statements.cli",
]

rows = []
for name in CONSOLE:
    exe = VENV_PY.parent / (name + ".exe")
    argv = [str(exe), "--help"] if exe.is_file() else [str(VENV_PY), "-m", name, "--help"]
    done = subprocess.run(argv, cwd=str(CWD), capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120)
    where = "script" if exe.is_file() else "module"
    ok = done.returncode == 0 and "usage" in (done.stdout + done.stderr).lower()
    rows.append((name, where, done.returncode, "ok" if ok else "REFUSED",
                 (done.stderr or done.stdout).strip().splitlines()[:1]))
for module in MODULES:
    done = subprocess.run([str(VENV_PY), "-I", "-B", "-m", module, "--help"],
                          cwd=str(CWD), capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120)
    ok = done.returncode == 0 and "usage" in (done.stdout + done.stderr).lower()
    rows.append((module, "module", done.returncode, "ok" if ok else "REFUSED",
                 (done.stderr or done.stdout).strip().splitlines()[:1]))

for row in rows:
    sys.stdout.write("%-58s %-6s rc=%s %-8s %s\n" % (row[0], row[1], row[2], row[3], row[4]))

# The installed copy, not the checkout, must serve imports.
identity = subprocess.run(
    [str(VENV_PY), "-I", "-B", "-c",
     "import company_wiki; print(company_wiki.__file__)"],
    cwd=str(CWD), capture_output=True, encoding="utf-8", timeout=60,
)
sys.stdout.write("import identity: %s\n" % identity.stdout.strip())
assert "mb11-cwp" not in identity.stdout, "checkout leaked into installed import"
assert "site-packages" in identity.stdout.replace("\\", "/")
