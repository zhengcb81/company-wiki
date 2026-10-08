$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$allowedNames = @('rf_fix_stage', 'second_fix_stage', 'second_test_stage')
$rows = @()
foreach ($stageName in $allowedNames) {
    $candidate = Join-Path $taskRoot $stageName
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    if (-not $resolved.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Stage path escaped task workspace: $resolved"
    }
    $item = Get-Item -LiteralPath $resolved
    $entries = @(Get-ChildItem -LiteralPath $resolved -Force -Recurse)
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        ($entries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })) {
        throw "Do not delete a stage containing reparse points: $resolved"
    }
    $files = @($entries | Where-Object { -not $_.PSIsContainer })
    $fileRows = @($files | ForEach-Object {
        @{ path = $_.FullName; bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    Remove-Item -LiteralPath $resolved -Recurse -Force
    if (Test-Path -LiteralPath $resolved) { throw "Stage cleanup failed: $resolved" }
    $rows += @{ path = $resolved; removed_files = $fileRows; restored_absent = $true }
}
$record = @{ schema_version = '1.0'; scope = 'Only MAIN-created patch staging copies; raw/research/review files untouched'; stages = $rows }
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskRoot 'cleanup_staging.json') -Encoding utf8
$record | ConvertTo-Json -Depth 8
