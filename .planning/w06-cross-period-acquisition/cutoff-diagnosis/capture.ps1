$ErrorActionPreference = 'Stop'
$taskEvidence = $PSScriptRoot
$canonicalRoot = 'C:/Users/郑曾波/Projects/company-wiki'
$etRoot = 'C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts'
$ffRoot = 'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root'
$attemptRoot = Join-Path $canonicalRoot '.tmp/w06-root-matrix-evidence/attempt-1f64f745d3a94506ae4bc35c8997b562'
$freezePath = Join-Path $canonicalRoot 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/producer-scope-fix/product-freeze.json'
$report = Get-Content -LiteralPath (Join-Path $attemptRoot 'report.json') -Raw | ConvertFrom-Json
$case = @($report.cases | Where-Object { $_.id -eq 'call_past_cutoff' })
if ($case.Count -ne 1) { throw 'Expected exactly one unchanged cutoff case' }
$paths = @((Join-Path $attemptRoot 'report.json'), $freezePath)
$paths += @('fixture', 'request', 'response') | ForEach-Object { Join-Path $attemptRoot "artifacts/call_past_cutoff.run1.$_.json" }
$paths += @('result', 'usage') | ForEach-Object { Join-Path $attemptRoot "artifacts/call_past_cutoff.$_.json" }
$paths += @('transcript_api.py', 'retrieval_worker.py', 'retrieval_runtime.py', 'transcript_tool.py', 'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py', 'tests/request_budget_cli_proxy.py') | ForEach-Object { Join-Path $etRoot $_ }
$paths += @('scripts/transcript_tool_transport.py', 'scripts/transcript_companion.py', 'scripts/et_v2_contract.py', 'scripts/ff_v2_envelope.py', 'tools/offline_contract_matrix/matrix_outcome.py', '.planning/w06-ff-matrix/task_plan.md', '.planning/m3-acquisition-usage-20261010/task_plan.md') | ForEach-Object { Join-Path $ffRoot $_ }
$freeze = Get-Content -LiteralPath $freezePath -Raw | ConvertFrom-Json
$files = foreach ($path in $paths) {
    $item = Get-Item -LiteralPath $path
    [ordered]@{ path = $item.FullName; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant(); bytes = $item.Length }
}
$producer = foreach ($entry in $freeze.product_files.PSObject.Properties) {
    $path = Join-Path $freeze.worktree $entry.Name
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    [ordered]@{ path = $path; sha256 = $hash; expected_sha256 = $entry.Value.sha256; matches_freeze = $hash -eq $entry.Value.sha256 }
}
if (@($producer | Where-Object { -not $_.matches_freeze }).Count) { throw 'CWP producer freeze drift' }
$bindings = foreach ($repository in $report.dependencies) {
    foreach ($module in $repository.modules) {
        $hash = (Get-FileHash -LiteralPath $module.file -Algorithm SHA256).Hash.ToLowerInvariant()
        [ordered]@{ repository = $repository.repository; path = $module.file; sha256 = $hash; expected_sha256 = $module.sha256; matches_matrix = $hash -eq $module.sha256 }
    }
}
if (@($bindings | Where-Object { -not $_.matches_matrix }).Count) { throw 'Matrix dependency drift' }
$snapshot = [ordered]@{
    schema_version = 'cutoff-readonly-inputs/1'
    captured_utc = [DateTime]::UtcNow.ToString('o')
    matrix = [ordered]@{ total = @($report.cases).Count; pass = @($report.cases | Where-Object { $_.result -eq 'PASS' }).Count; fail = @($report.cases | Where-Object { $_.result -eq 'FAIL' }).Count; cutoff = $case[0] }
    input_files = $files
    cwp_product_freeze = $producer
    matrix_dependency_bindings = $bindings
    keys_read = 0
    product_writes = 0
    tests_run = 0
    real_requests = 0
}
$baselinePath = Join-Path $taskEvidence 'inputs-before.json'
if (-not (Test-Path -LiteralPath $baselinePath)) {
    [System.IO.File]::WriteAllText($baselinePath, ($snapshot | ConvertTo-Json -Depth 22), [System.Text.UTF8Encoding]::new($false))
} else {
    $baseline = Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json
    $before = @{}
    foreach ($file in $baseline.input_files) { $before[$file.path] = $file.sha256 }
    foreach ($file in $files) { if ($before[$file.path] -ne $file.sha256) { throw "Read-only input changed: $($file.path)" } }
    $snapshot['pre_post_unchanged'] = $true
    [System.IO.File]::WriteAllText((Join-Path $taskEvidence 'inputs-after.json'), ($snapshot | ConvertTo-Json -Depth 22), [System.Text.UTF8Encoding]::new($false))
}
[ordered]@{ cwp_frozen = @($producer).Count; matrix_bindings = @($bindings).Count; inputs = @($files).Count; pass = $snapshot.matrix.pass; fail = $snapshot.matrix.fail; keys_read = 0; product_writes = 0 } | ConvertTo-Json -Compress
