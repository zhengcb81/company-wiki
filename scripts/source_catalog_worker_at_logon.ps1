param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$LauncherPath = Join-Path $ProjectRoot 'scripts/source_catalog_worker.ps1'
# Keep the logon delay inside the worker so pause/stop remains interruptible:
# -StartupDelaySeconds 120
$Arguments = @(
    '-NoProfile',
    '-NonInteractive',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    ('"{0}"' -f $LauncherPath),
    '-PythonExe',
    ('"{0}"' -f $PythonExe),
    '-ProjectRoot',
    ('"{0}"' -f $ProjectRoot),
    '-StartupDelaySeconds',
    '120'
)
$Supervisor = Start-Process `
    -FilePath 'powershell.exe' `
    -ArgumentList $Arguments `
    -WindowStyle Hidden `
    -PassThru
if ($null -eq $Supervisor) {
    throw 'Unable to start Source Catalog supervisor'
}
exit 0
