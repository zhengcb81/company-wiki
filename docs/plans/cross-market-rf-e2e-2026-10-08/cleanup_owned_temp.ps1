$ErrorActionPreference = 'Stop'
$planRoot = Split-Path -Parent $PSCommandPath
$targetPathExpected = [IO.Path]::GetFullPath('C:\Users\郑曾波\AppData\Local\Temp\cwp-rf-e2e-20261008')
$archiveRootExpected = [IO.Path]::GetFullPath('C:\Users\郑曾波\Projects\revenue-forecast\output\cross-market-rf-e2e-2026-10-08')
$recordPath = Join-Path $planRoot 'cleanup_final_temp.json'
if (Test-Path -LiteralPath $recordPath) { throw 'Cleanup already recorded; do not run again.' }
$archive = Get-Content -LiteralPath (Join-Path $planRoot 'delivery_archive_index.json') -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($archive.original_temp_root) -ne $targetPathExpected) { throw 'Unexpected TEMP target.' }
if ([IO.Path]::GetFullPath($archive.durable_output_root) -ne $archiveRootExpected) { throw 'Unexpected archive root.' }
$resolvedTarget = (Resolve-Path -LiteralPath $targetPathExpected).ProviderPath
if ([IO.Path]::GetFullPath($resolvedTarget) -ne $targetPathExpected) { throw 'Resolved target differs from exact owned task directory.' }
$items = @(Get-Item -LiteralPath $resolvedTarget -Force) + @(Get-ChildItem -LiteralPath $resolvedTarget -Recurse -Force)
if (@($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'Refuse recursive cleanup with reparse points.' }
$files = @($items | Where-Object { -not $_.PSIsContainer })
if ($files.Count -ne @($archive.artifacts).Count) { throw 'TEMP changed since archive.' }
$indexed = @{}
foreach ($entry in $archive.artifacts) {
    $sourcePath = [IO.Path]::GetFullPath($entry.original_path)
    if (-not $sourcePath.StartsWith($targetPathExpected + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Indexed source outside exact task root.' }
    if ($indexed.ContainsKey($sourcePath)) { throw 'Duplicate indexed TEMP path.' }
    $indexed[$sourcePath] = $entry
}
foreach ($file in $files) {
    $entry = $indexed[[IO.Path]::GetFullPath($file.FullName)]
    if (-not $entry) { throw 'Unindexed TEMP file.' }
    if ($file.Length -ne $entry.byte_size -or (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'TEMP bytes changed since archive.' }
    switch ($entry.storage) {
        'retained_object' {
            $retainedPath = [IO.Path]::GetFullPath($entry.archive_path)
            if (-not $retainedPath.StartsWith($archiveRootExpected + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Retained object outside exact archive root.' }
            $retained = Get-Item -LiteralPath $retainedPath
            if ($retained.Length -ne $entry.byte_size -or (Get-FileHash -LiteralPath $retainedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Retained object missing or changed.' }
        }
        'company_wiki_verified_raw' {
            $proof = @($archive.current_producer_verification | Where-Object { $_.verified_sha256 -eq $entry.sha256 -and $_.verified_byte_size -eq $entry.byte_size -and $_.returncode -eq 0 })
            if (-not $proof.Count) { throw 'Missing actual producer raw verification.' }
        }
        'regenerable_intermediate_not_retained' {
            if (-not $entry.reason) { throw 'Missing explicit intermediate classification.' }
        }
        default { throw 'Unknown storage class; retain TEMP.' }
    }
}
# Target has been resolved and checked end-to-end in this PowerShell process.
Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
if (Test-Path -LiteralPath $targetPathExpected) { throw 'Task TEMP directory remains.' }
$result = [ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    exact_owned_temp_root = $targetPathExpected
    removed_temp_files = $files.Count
    removed_temp_bytes = $archive.temp_logical_bytes
    durable_retained_unique_bytes = $archive.unique_object_bytes
    original_source_bytes_preserved = $true
    production_originals_deleted = 0
    archive_index = (Join-Path $planRoot 'delivery_archive_index.json')
    task_temp_root_absent_after_cleanup = $true
    full_production_backup_restore_exercise = $false
}
$json = $result | ConvertTo-Json -Depth 5
Set-Content -LiteralPath $recordPath -Value $json -Encoding utf8
Write-Output $json
