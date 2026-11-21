[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][string]$SettingsPath,
    [Parameter(Mandatory)][string]$PythonPath,
    [string]$HostsPath,
    [string]$TaskName,
    [string[]]$Owners = @()
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$settings = (Resolve-Path -LiteralPath $SettingsPath).Path
if (-not $HostsPath) { $HostsPath = Join-Path (Split-Path $settings) 'hosts.json' }
$hostsFile = (Resolve-Path -LiteralPath $HostsPath).Path
$interpreter = (Resolve-Path -LiteralPath $PythonPath).Path
$launcher = (Resolve-Path -LiteralPath (Join-Path (Split-Path $interpreter) 'pythonw.exe')).Path
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if (-not $TaskName) { $TaskName = "CompanyWiki-F4-Recover-$sid" }
$description = 'Company-wiki F4 original observation recovery'
$arguments = '-B -X utf8 -m tools.feedback_loop.local_host --config "{0}" recover --hosts "{1}" --save-result' -f $settings, $hostsFile
foreach ($owner in ($Owners | Sort-Object -Unique)) {
    if ($owner -notmatch '^[\w.-]+$') { throw "Invalid owner argument: $owner" }
    $arguments += ' --owner "{0}"' -f $owner
}
$action = New-ScheduledTaskAction -Execute $launcher -Argument $arguments -WorkingDirectory $repo
$logon = New-ScheduledTaskTrigger -AtLogOn -User $sid
$periodic = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$policy = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$user = New-ScheduledTaskPrincipal -UserId $sid -LogonType Interactive -RunLevel Limited
$existing = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Description -ne $description) {
        throw "Another application owns scheduled task $TaskName"
    }
    $actions = @($existing.Actions)
    $triggers = @($existing.Triggers)
    $matches = $actions.Count -eq 1 -and $actions[0].Execute -eq $launcher -and
        $actions[0].Arguments -eq $arguments -and $actions[0].WorkingDirectory -eq $repo -and
        $triggers.Count -eq 2 -and
        @($triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' -and $_.Enabled }).Count -eq 1 -and
        @($triggers | Where-Object { $_.Repetition.Interval -eq 'PT10M' -and $_.Enabled }).Count -eq 1 -and
        $existing.Settings.StartWhenAvailable -and $existing.Settings.MultipleInstances -eq 'IgnoreNew' -and
        $existing.Settings.Enabled -and $existing.Principal.RunLevel -eq 'Limited' -and
        $existing.Principal.LogonType -eq 'Interactive'
    if ($matches) {
        [pscustomobject]@{ TaskName = $TaskName; Status = 'already_installed'; Action = $arguments }
        return
    }
}
if ($PSCmdlet.ShouldProcess($TaskName, 'Register the current user recovery command')) {
    Register-ScheduledTask -TaskName $TaskName -TaskPath '\' -Action $action -Trigger @($logon, $periodic) -Settings $policy -Principal $user -Description $description -Force | Out-Null
    [pscustomobject]@{ TaskName = $TaskName; Status = 'installed'; Action = $arguments }
}
