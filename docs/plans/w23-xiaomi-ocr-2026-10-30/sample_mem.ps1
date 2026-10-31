$ErrorActionPreference = 'SilentlyContinue'
$peak = 0
$deadline = (Get-Date).AddSeconds(240)
while ((Get-Date) -lt $deadline) {
  $roots = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*tools.ocr_comparison.run_comparison*' }
  if (-not $roots) {
    if ($peak -gt 0) { break }
    Start-Sleep -Milliseconds 300
    continue
  }
  $pids = @{}
  foreach ($r in $roots) { $pids[[int]$r.ProcessId] = $true }
  foreach ($p in (Get-CimInstance Win32_Process -Filter "Name='python.exe'")) {
    if ($pids.ContainsKey([int]$p.ParentProcessId)) { $pids[[int]$p.ProcessId] = $true }
  }
  $sum = 0
  foreach ($p in (Get-CimInstance Win32_Process -Filter "Name='python.exe'")) {
    if ($pids.ContainsKey([int]$p.ProcessId)) { $sum += [long]$p.WorkingSetSize }
  }
  if ($sum -gt $peak) { $peak = $sum }
  Start-Sleep -Milliseconds 300
}
"peak_tree_workingset_bytes=" + $peak
"peak_tree_workingset_gb=" + [math]::Round($peak / 1GB, 3)
