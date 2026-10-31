$ErrorActionPreference = 'Stop'
$wt = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$out = Join-Path $wt "delivery/w23-xiaomi-ocr/pilot_r0_memwatch.json"
$so = Join-Path $wt ".w23_cache/memwatch_stdout.log"
$se = Join-Path $wt ".w23_cache/memwatch_stderr.log"
$job = Start-Process -FilePath "C:/Miniconda/python.exe" -ArgumentList @(
  "-m","tools.ocr_comparison.run_comparison",
  "--arms","R0","--pages","pilot:byd_ar_2024_p021",
  "--out",$out
) -WorkingDirectory $wt -PassThru -NoNewWindow -RedirectStandardOutput $so -RedirectStandardError $se
$rootPid = $job.Id
$peak = 0
while ($true) {
  if ($job.HasExited) { break }
  $pids = @{ $rootPid = $true }
  foreach ($p in (Get-CimInstance Win32_Process -Filter "Name='python.exe'")) {
    if ($pids.ContainsKey([int]$p.ParentProcessId) -or [int]$p.ProcessId -eq $rootPid) {
      $pids[[int]$p.ProcessId] = $true
    }
  }
  $sum = 0
  foreach ($p in (Get-CimInstance Win32_Process -Filter "Name='python.exe'")) {
    if ($pids.ContainsKey([int]$p.ProcessId)) { $sum += [long]$p.WorkingSetSize }
  }
  if ($sum -gt $peak) { $peak = $sum }
  Start-Sleep -Milliseconds 300
}
"root_exit=" + $job.ExitCode
"peak_tree_workingset_bytes=" + $peak
"peak_tree_workingset_gb=" + [math]::Round($peak / 1GB, 3)
"---stderr---"
Get-Content $se -ErrorAction SilentlyContinue | Select-Object -Last 5
"---stdout---"
Get-Content $so -ErrorAction SilentlyContinue | Select-Object -Last 3
