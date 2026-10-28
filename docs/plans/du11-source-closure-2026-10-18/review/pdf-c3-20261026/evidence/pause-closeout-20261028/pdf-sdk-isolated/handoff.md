# Selected SDK deployment handoff

Deployment-only milestone passed; SDK startup remains **unproven** because the single no-document probe met a false positive in its own no-persistent-write audit guard. Nothing was adopted into production. No code/PWF/Git/global installation/ACL changes, PDF reads, network/downloads or paid calls were made.

## What exists

`env/` is a standard Python3.13.9 venv created with `--without-pip --copies`, `include-system-site-packages=false`. Its own standard `.gitignore` contains `*`; repository ignore files are unchanged. Only the existing resolver's104 distributions were projected from426 globally visible distributions. All36,121 selected files are hardlinks (1,233,549,343 logical shared bytes); no SDK/model file bytes were copied. Standard venv launchers/scaffold copied517,241 bytes. NTFS directory/link bookkeeping consumes additional storage but was not measured; do not describe the logical1.233GB as a new1.233GB allocation or claim exact total disk allocation.

`runtime-isolated.json` differs from the original runtime profile only in Python path. It retains the same original model/config artifacts and SHA, metadata environment SHA `c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`,120s,3pages,4GiB,CPU4,64MiB input and2MiB output. No canonical profile was edited. The light new-interpreter proof observed104 third-party distributions (+separate first-party company-wiki metadata), no base/user site or pip, identical resolver output/SHA and zero SDK imports.

Historical wheel RECORD mismatch is **diagnostic**, not a new permission gate: exactly six INSTALLER provenance files declare the pip-era4-byte marker but contain current5-byte `conda`. There is no detected runtime code mismatch, required missing file, target escape or true selected-target conflict. All9 conflicting claims from unselected pypptx-with-oxml match the selected python-pptx actual bytes. Existing pywin32/setuptools `.pth` hooks were inspected and retained byte-exact, not replaced with a loader. The deployment froze actual source bytes and rehashed before each link; `samefile` was proved for every link. Environment SHA remains the existing metadata-closure identity, not a claim of immutable whole-code identity.

## The one cold probe

`single-cold-attempt.json`, `cold-probe.json`, `cold.stdout.jsonl` and `cold.stderr.log` preserve the exact attempt. Deadline30s,4GiB/CPU4,zero document bytes,offline flags,owned process tree. It ended ChildFailed in18.805505s. The10s stack was still in Transformers' metadata inference; by17.78s it had advanced to `transformers.generation -> torch -> dill`. Dill determines file types with `open(os.devnull, 'r+b')`; the probe guard rejected that standard Windows NUL discard device as if it were a persistent write. That device does not create or modify a persistent file. This is the probe's false positive, **not evidence of a missing package/DLL or a deployment runtime success**. Peak sampled/observed Job commit313,511,936 bytes. Scratch `.c3iso28` was restored absent. No retry and no120s batch followed.

ROOT acknowledged this classification and owns the later narrowly corrected device-aware guard test and, if needed, next bounded probe under unchanged resource caps. Do not rerun `run_cold_probe.py`: its one-use marker deliberately rejects repetition. Do not delete the marker or rewrite the failed receipt to green. No PDF recall/summary correctness or SDK constructor readiness is claimed. Fresh interpreter does not imply machine-cold filesystem caches: source hashing/linking warmed the OS cache. Python audit hooks do not prove exhaustive native syscall interception.

## Reproduction / deployment boundaries

The scripts are evidence-backed tools for this exact owned deployment, not a new product loader. Starting from a **new empty owned destination** (the current `env/` must not be overwritten), `preflight.py` freezes the authorized source snapshot; `deploy.py` makes the normal venv and selected hardlinks and runs `light_check.py`. The local compressed plan is necessary execution material for those scripts but should be regenerated, not committed. Current deployment already exists and is retained for ROOT independent review; no repeat full scan or SDK attempt is needed to inspect receipts.

The exact already-executed commands were:

```powershell
C:/Miniconda/python.exe -B -I .planning/c3-20261028/pdf-sdk-isolated/preflight.py
C:/Miniconda/python.exe -B -I .planning/c3-20261028/pdf-sdk-isolated/deploy.py
C:/Miniconda/python.exe -B -I .planning/c3-20261028/pdf-sdk-isolated/run_cold_probe.py
C:/Miniconda/python.exe -B -I .planning/c3-20261028/pdf-sdk-isolated/finalize.py
```

The first preserved strict preflight status is `SOURCE_RECORD_CONFLICT` because it conservatively grouped provenance diagnostics and active standard hooks. `revised-deployment-plan.md` records ROOT's actual-source contract **before** hardlinking; `deployment.json` is the distinct actual-source deployment receipt. Do not edit that old status into false wheel parity.

Hardlinks share in-place mutation risk: never edit/chmod/change ACL on projected package files. Global source bytes/metadata files and ACL were not changed; NTFS hardlink counts necessarily increased. Safe future retirement removes only owned link names after verifying the exact absolute `env/` target; never follows sources for deletion. Console launchers may retain original base interpreter shebangs; this profile uses the explicit venv Python plus the existing worker module, not these console scripts.

Light/probe launch sanitized Python environment variables. Existing product launch inherits parent environment, so an injected `PYTHONPATH`/`PYTHONHOME` can defeat discovery isolation; this is a limited launch condition for ROOT to consider, not an implemented product fix or new gate. Product launch/environment code was not changed and no scope expansion is proposed in this handoff.

## Review / small artifact list

`handoff.json` binds exact local scripts/receipts by SHA; `selected-manifest.json` lists104 distributions, RECORD SHA, original protected owner hashes and original artifact SHA. `finalize.py` verified after the failed probe that original owners/profile/design, all104 RECORDs, and actual model/config hashes still match their frozen originals, with no second SDK import.

ROOT may retain/commit only this small directory's top-level scripts, plans, compact manifests/profile and receipts after review. **Exclude `env/`, `projection-plan.local.json.gz` (1.996MB per-file working inventory), and all SDK/model files.** Do not `git add` the directory indiscriminately. No Git/index/commit/push action was performed by this child.
