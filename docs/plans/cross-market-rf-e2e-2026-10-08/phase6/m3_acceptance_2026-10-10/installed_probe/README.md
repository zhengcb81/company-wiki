# M3 installed runtime: independent offline acceptance

**Final verdict: accepted for the installed engineering node.** On 2026-10-10, all 18 fresh subprocess checks returned their expected exit codes. This uses synthetic fixtures; it does not sign off any real company forecast, source acquisition, or AUTO JSON routing.

## Re-run

Prerequisites: the accepted RF repository test fixtures under `~/Projects/revenue-forecast`, Python with the project's runtime dependencies, and synchronized `filing-fetch` / `revenue-forecast` skills in both `~/.agents/skills` and `~/.codex/skills`. No provider or model credential is used.

Run in PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\郑曾波\Projects\company-wiki\docs\plans\cross-market-rf-e2e-2026-10-08\phase6\m3_acceptance_2026-10-10\installed_probe'
python -X utf8 -B .\run_probe.py
```

The coordinator creates synthetic JSON fixtures. Each product subprocess starts with `-I -B -X utf8`, explicitly imports from only the selected installed skill, and checks its actual module paths. Its working directory, output files and publication registry are under a newly owned TEMP directory. The harness removes that directory and compares the complete installed file manifests before and after execution.

The final stdout must report `status: pass`, `tests: 18`, `installation_mutations: []`, and `owned_temp_removed: true`. An individual rejected half-year input must exit 2 with `requires annual flow coverage`; the other commands must exit 0. Every run automatically writes to a new unique `attempts/<UTC>-<UUID>/` directory and prints its receipt path. Historical root receipts and logs are not overwritten, and no manual backup step is needed. The supplementary 36 Git-blob SHA comparisons in the original root receipt describe the accepted installation campaign; the harness itself checks installation restoration on every run.

Optional explicit output: add `--report-dir attempts/my-new-attempt`. Relative paths resolve under this probe package. The directory must be new or empty and inside the package; files, links, directories containing evidence, and reuse of an already claimed attempt fail before fixture creation or product execution. An exclusive claim and exclusive evidence writes prevent accidental concurrent replacement. Failed attempts are retained for diagnosis and a retry uses a new directory.

## Scope: nine checks per physical installation

| Checks | Expected result |
|---|---|
| FF envelope and diagnostic siblings | `acquisition-observation/1` stays at the top level in success and typed-error payloads; the independent legacy acquisition-failure object remains intact. |
| RF public CLI version | Installed engine `4.2.0` loads its actual installed modules. |
| Three direct half-year annual consumers | Half-year annual driver, segment base and reported total are each rejected; no implicit annualization. |
| Complete FY public CLI | Schema `3.9` complete-year flows produce JSON and Markdown in TEMP. |
| Complete FY compute → strong validation → render | Fresh installed computation and CLI result both validate and agree; the rendered period dates are present. |
| Explicit derived FY public CLI | H1 60 + H2 50 explicitly derives a complete-year input of 110 and runs successfully. |
| Derived FY compute → strong validation → render | Original halves stay 60 and 50; derived input stays 110; the CLI and independent computation agree. |

The FF check includes null fees, known lower bounds with incomplete usage, and malformed diagnostics. Malformed outcome lists, null exchange counts and nonfinite fees cannot mask the primary typed provider error. The fresh RF consumer also preserves FF's observation and legacy failure sibling.

## Evidence and restoration

- [ACCEPTANCE.md](ACCEPTANCE.md): final engineering findings and limits.
- [verification.json](verification.json): original sealed campaign commands, expected/actual exits, timestamps, module-origin logs, log hashes and restoration proof; repeat campaigns have their own `attempts/*/verification.json`.
- [run_probe.py](run_probe.py): repeatable offline harness.
- `*.stdout.log` / `*.stderr.log`: original subprocess output; `ruff-final.*.log`: final harness style result.

Current campaign: 36 selected installed files match the accepted main Git blobs; all 590 installed files remain unchanged; TEMP was deleted. No original document or production configuration was opened or modified. External provider calls, external model calls and paid usage are zero.

The original sealed campaign records its own execution-time harness hash and subsequent formatting-only edit. The later harness adds automatic independent output directories; its fresh verification is kept under `attempts/` with its own harness hash. Child product checks are unchanged. No product source, installation or shared planning changes were made by this reviewer.

### Automatic preservation verified

The upgraded runner was exercised in [attempt 20261010T203521373000Z](attempts/20261010T203521373000Z-5517ba96006c41b9be5a9581419e1525/verification.json): all 18 fresh installed checks passed, all 590 installed files stayed unchanged, and test TEMP was removed. [Output allocation checks](attempts/20261010T203521373000Z-5517ba96006c41b9be5a9581419e1525/output_directory_checks.json) record 11 passing checks: unique defaults; explicit new and empty directories; rejection of nonempty, previously claimed, file, package-root and outside-package targets; exclusive evidence writes; actual CLI refusal before product execution; preserved historic evidence; allocator TEMP restoration. SHA-256 checks prove all 40 sealed root files remained unchanged. These checks required no external calls or paid usage.
