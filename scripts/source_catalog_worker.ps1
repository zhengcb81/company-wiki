param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [string]$ConfigPath = '',
    [string]$WorkerConfigPath = '',
    [string]$CatalogDir = '',
    [int]$StartupDelaySeconds = 0,
    [double]$RestartBaseSeconds = 5,
    [double]$RestartMaxSeconds = 300,
    [double]$RestartResetSeconds = 900,
    [double]$WorkerHangTimeoutSeconds = 900,
    [int]$ChildPollMilliseconds = 5000
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $ProjectRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

if ($RestartBaseSeconds -lt 0) {
    throw 'RestartBaseSeconds must be non-negative'
}
if ($RestartMaxSeconds -lt $RestartBaseSeconds) {
    throw 'RestartMaxSeconds must be greater than or equal to RestartBaseSeconds'
}
if ($RestartResetSeconds -lt 0) {
    throw 'RestartResetSeconds must be non-negative'
}
if ($WorkerHangTimeoutSeconds -le 0) {
    throw 'WorkerHangTimeoutSeconds must be greater than zero'
}
if ($ChildPollMilliseconds -le 0) {
    throw 'ChildPollMilliseconds must be greater than zero'
}

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $ProjectRoot 'config/source_catalog.yaml'
}
if ([string]::IsNullOrWhiteSpace($WorkerConfigPath)) {
    $WorkerConfigPath = Join-Path $ProjectRoot 'config/source_catalog_worker.yaml'
}
if ([string]::IsNullOrWhiteSpace($CatalogDir)) {
    $CatalogDir = Join-Path $ProjectRoot '.source_catalog'
}

if (-not ('CompanyWiki.KillOnCloseJob' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace CompanyWiki {
    [StructLayout(LayoutKind.Sequential)]
    internal struct JobObjectBasicLimitInformation {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct IoCounters {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct JobObjectExtendedLimitInformation {
        public JobObjectBasicLimitInformation BasicLimitInformation;
        public IoCounters IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    public static class KillOnCloseJob {
        private const int JobObjectExtendedLimitInformationClass = 9;
        private const uint JobObjectLimitKillOnJobClose = 0x00002000;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObject(
            IntPtr jobAttributes,
            string name
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(
            IntPtr job,
            int informationClass,
            ref JobObjectExtendedLimitInformation information,
            uint informationLength
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(
            IntPtr job,
            IntPtr process
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        public static IntPtr Create() {
            IntPtr handle = CreateJobObject(IntPtr.Zero, null);
            if (handle == IntPtr.Zero) {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
            JobObjectExtendedLimitInformation information =
                new JobObjectExtendedLimitInformation();
            information.BasicLimitInformation.LimitFlags =
                JobObjectLimitKillOnJobClose;
            uint size = (uint)Marshal.SizeOf(information);
            if (!SetInformationJobObject(
                    handle,
                    JobObjectExtendedLimitInformationClass,
                    ref information,
                    size)) {
                int error = Marshal.GetLastWin32Error();
                CloseHandle(handle);
                throw new Win32Exception(error);
            }
            return handle;
        }

        public static void Assign(IntPtr job, IntPtr process) {
            if (!AssignProcessToJobObject(job, process)) {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
        }

        public static void Close(IntPtr handle) {
            if (handle != IntPtr.Zero) {
                CloseHandle(handle);
            }
        }
    }
}
'@
}

$LauncherEventsPath = Join-Path $CatalogDir 'worker_launcher_events.jsonl'
$LauncherLockPath = Join-Path $CatalogDir 'worker_launcher.lock'
$SessionId = [guid]::NewGuid().ToString('N')
$LauncherLockStream = $null
$ChildJobHandle = [IntPtr]::Zero
$ActiveChild = $null

function Get-SourceHashOrUnknown {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    } catch {
        return $null
    }
}

$LoadedLauncherSourceHashes = [ordered]@{
    supervisor_ps1 = Get-SourceHashOrUnknown -Path $PSCommandPath
    logon_ps1 = Get-SourceHashOrUnknown -Path (Join-Path $PSScriptRoot 'source_catalog_worker_at_logon.ps1')
    logon_vbs = Get-SourceHashOrUnknown -Path (Join-Path $PSScriptRoot 'source_catalog_worker_at_logon.vbs')
}

function Write-LauncherEvent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [Nullable[int]]$ExitCode = $null,
        [string]$Message = '',
        [string]$Reason = '',
        [Nullable[int]]$Attempt = $null,
        [Nullable[int]]$ChildPid = $null,
        [Nullable[double]]$UptimeSeconds = $null,
        [Nullable[double]]$RestartDelaySeconds = $null,
        [string]$StdoutLog = '',
        [string]$StderrLog = '',
        [string]$WorkerStage = '',
        [string]$CurrentPath = '',
        [Nullable[double]]$CurrentPathElapsedSeconds = $null,
        [string]$ProgressDetail = '',
        [Nullable[int]]$ParserPid = $null
    )

    try {
        New-Item -ItemType Directory -Path $CatalogDir -Force | Out-Null
        $Payload = [ordered]@{
            schema_version = '1.1'
            recorded_at = (Get-Date).ToUniversalTime().ToString('o')
            status = $Status
            message = $Message
            reason = $Reason
            python_exe = $PythonExe
            project_root = $ProjectRoot
            startup_delay_seconds = $StartupDelaySeconds
            worker_hang_timeout_seconds = $WorkerHangTimeoutSeconds
            child_poll_milliseconds = $ChildPollMilliseconds
            launcher_pid = $PID
            session_id = $SessionId
            stdout_log = $StdoutLog
            stderr_log = $StderrLog
            launcher_source_hashes = $LoadedLauncherSourceHashes
        }
        if ($null -ne $ExitCode) {
            $Payload['exit_code'] = [int]$ExitCode
        }
        if ($null -ne $Attempt) {
            $Payload['attempt'] = [int]$Attempt
        }
        if ($null -ne $ChildPid) {
            $Payload['child_pid'] = [int]$ChildPid
        }
        if ($null -ne $UptimeSeconds) {
            $Payload['uptime_seconds'] = [math]::Round([double]$UptimeSeconds, 3)
        }
        if ($null -ne $RestartDelaySeconds) {
            $Payload['restart_delay_seconds'] = [math]::Round(
                [double]$RestartDelaySeconds,
                3
            )
        }
        if ($WorkerStage) { $Payload['worker_stage'] = $WorkerStage }
        if ($CurrentPath) { $Payload['current_path'] = $CurrentPath }
        if ($null -ne $CurrentPathElapsedSeconds) {
            $Payload['current_path_elapsed_seconds'] = [math]::Round(
                [double]$CurrentPathElapsedSeconds,
                3
            )
        }
        if ($ProgressDetail) { $Payload['progress_detail'] = $ProgressDetail }
        if ($null -ne $ParserPid) { $Payload['parser_pid'] = [int]$ParserPid }
        Add-Content -LiteralPath $LauncherEventsPath -Encoding UTF8 -Value (
            $Payload | ConvertTo-Json -Compress
        )
    } catch {
    }
}

function Read-ControlSnapshot {
    $ControlPath = Join-Path $CatalogDir 'worker_control.json'
    try {
        if (-not (Test-Path -LiteralPath $ControlPath -PathType Leaf)) {
            return [pscustomobject]@{
                desired_state = 'enabled'
                stop_requested_for = $null
            }
        }
        $Control = Get-Content -LiteralPath $ControlPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $Desired = if ($Control.desired_state -eq 'paused') {
            'paused'
        } else {
            'enabled'
        }
        return [pscustomobject]@{
            desired_state = $Desired
            stop_requested_for = $Control.stop_requested_for
        }
    } catch {
        return [pscustomobject]@{
            desired_state = 'enabled'
            stop_requested_for = $null
        }
    }
}

function Read-RuntimeSnapshot {
    $RuntimePath = Join-Path $CatalogDir 'worker_runtime.json'
    try {
        if (-not (Test-Path -LiteralPath $RuntimePath -PathType Leaf)) {
            return $null
        }
        return Get-Content -LiteralPath $RuntimePath -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        return $null
    }
}

$WorkerArguments = @(
    '-m', 'company_wiki.source_catalog.cli',
    '--config', $ConfigPath,
    'worker',
    '--worker-config', $WorkerConfigPath
)
if ($StartupDelaySeconds -gt 0) {
    $WorkerArguments += @('--startup-delay-seconds', [string]$StartupDelaySeconds)
}

New-Item -ItemType Directory -Path $CatalogDir -Force | Out-Null
try {
    try {
        $LauncherLockStream = [System.IO.File]::Open(
            $LauncherLockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    } catch [System.IO.IOException] {
        Write-LauncherEvent -Status 'already_running' -Reason 'launcher_lock_held'
        exit 0
    }

    $ChildJobHandle = [CompanyWiki.KillOnCloseJob]::Create()
    Write-LauncherEvent -Status 'starting' -Reason 'launcher_session_started'
    $Attempt = 0
    $ConsecutiveFailures = 0

    while ($true) {
        $Attempt += 1
        $BaselineControl = Read-ControlSnapshot
        $AttemptTag = '{0}-attempt-{1:D4}' -f $SessionId, $Attempt
        $StdoutLogPath = Join-Path $CatalogDir "worker_stdout-$AttemptTag.log"
        $StderrLogPath = Join-Path $CatalogDir "worker_stderr-$AttemptTag.log"
        $StartedAt = Get-Date

        $Child = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList $WorkerArguments `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $StdoutLogPath `
            -RedirectStandardError $StderrLogPath `
            -PassThru
        $ActiveChild = $Child
        # PowerShell 5.1 can report a fast child's ExitCode as zero if its
        # Process handle was never materialized before the process exits.
        $ChildHandle = $Child.Handle
        [CompanyWiki.KillOnCloseJob]::Assign($ChildJobHandle, $ChildHandle)
        Write-LauncherEvent `
            -Status 'child_started' `
            -Reason 'worker_process_started' `
            -Attempt $Attempt `
            -ChildPid $Child.Id `
            -StdoutLog $StdoutLogPath `
            -StderrLog $StderrLogPath

        $ForcedRestartReason = ''
        while (-not $Child.WaitForExit($ChildPollMilliseconds)) {
            $UptimeSeconds = ((Get-Date) - $StartedAt).TotalSeconds
            $Runtime = Read-RuntimeSnapshot
            $HeartbeatAgeSeconds = $null
            if (
                $null -ne $Runtime -and
                $null -ne $Runtime.pid -and
                [int]$Runtime.pid -eq $Child.Id -and
                $null -ne $Runtime.heartbeat_at
            ) {
                $NowEpochSeconds = (
                    [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0
                )
                $HeartbeatAgeSeconds = [math]::Max(
                    0,
                    $NowEpochSeconds - [double]$Runtime.heartbeat_at
                )
                if ($HeartbeatAgeSeconds -gt $WorkerHangTimeoutSeconds) {
                    $ForcedRestartReason = 'heartbeat_timeout'
                }
            } elseif ($UptimeSeconds -gt $WorkerHangTimeoutSeconds) {
                $ForcedRestartReason = 'session_start_timeout'
            }

            if ($ForcedRestartReason) {
                $TimeoutMessage = if ($null -ne $HeartbeatAgeSeconds) {
                    'heartbeat age {0:N1}s exceeded {1:N1}s' -f `
                        $HeartbeatAgeSeconds, $WorkerHangTimeoutSeconds
                } else {
                    'no matching runtime session after {0:N1}s' -f $UptimeSeconds
                }
                Write-LauncherEvent `
                    -Status 'child_unresponsive' `
                    -Message $TimeoutMessage `
                    -Reason $ForcedRestartReason `
                    -Attempt $Attempt `
                    -ChildPid $Child.Id `
                    -UptimeSeconds $UptimeSeconds `
                    -StdoutLog $StdoutLogPath `
                    -StderrLog $StderrLogPath `
                    -WorkerStage "$($Runtime.worker_status)" `
                    -CurrentPath "$($Runtime.current_path)" `
                    -CurrentPathElapsedSeconds $Runtime.current_path_elapsed_seconds `
                    -ProgressDetail "$($Runtime.progress_detail)" `
                    -ParserPid $Runtime.parser_pid
                try {
                    $Child.Kill()
                } catch [System.InvalidOperationException] {
                    # The exact child exited between the timeout check and Kill().
                }
                if (-not $Child.WaitForExit(10000)) {
                    throw "worker child PID $($Child.Id) did not stop after watchdog timeout"
                }
                break
            }
        }
        $Child.Refresh()
        $ExitCode = [int]$Child.ExitCode
        $ActiveChild = $null
        $UptimeSeconds = ((Get-Date) - $StartedAt).TotalSeconds
        $CurrentControl = Read-ControlSnapshot

        if ($ExitCode -eq 0 -and -not $ForcedRestartReason) {
            Write-LauncherEvent `
                -Status 'exited' `
                -ExitCode $ExitCode `
                -Reason 'clean_exit' `
                -Attempt $Attempt `
                -ChildPid $Child.Id `
                -UptimeSeconds $UptimeSeconds `
                -StdoutLog $StdoutLogPath `
                -StderrLog $StderrLogPath
            exit 0
        }

        if ($CurrentControl.desired_state -eq 'paused') {
            Write-LauncherEvent `
                -Status 'exited' `
                -ExitCode $ExitCode `
                -Reason 'persistent_pause' `
                -Attempt $Attempt `
                -ChildPid $Child.Id `
                -UptimeSeconds $UptimeSeconds `
                -StdoutLog $StdoutLogPath `
                -StderrLog $StderrLogPath
            exit 0
        }

        $NewStopRequest = (
            $null -ne $CurrentControl.stop_requested_for -and
            $CurrentControl.stop_requested_for -ne
                $BaselineControl.stop_requested_for
        )
        if ($NewStopRequest) {
            Write-LauncherEvent `
                -Status 'exited' `
                -ExitCode $ExitCode `
                -Reason 'control_stop' `
                -Attempt $Attempt `
                -ChildPid $Child.Id `
                -UptimeSeconds $UptimeSeconds `
                -StdoutLog $StdoutLogPath `
                -StderrLog $StderrLogPath
            exit 0
        }

        if ($UptimeSeconds -ge $RestartResetSeconds) {
            $ConsecutiveFailures = 0
        }
        $ConsecutiveFailures += 1
        $RestartReason = if ($ForcedRestartReason) {
            $ForcedRestartReason
        } else {
            'unexpected_nonzero_exit'
        }
        $RestartDelay = [math]::Min(
            $RestartMaxSeconds,
            $RestartBaseSeconds * [math]::Pow(2, $ConsecutiveFailures - 1)
        )
        Write-LauncherEvent `
            -Status 'restarting' `
            -ExitCode $ExitCode `
            -Reason $RestartReason `
            -Attempt $Attempt `
            -ChildPid $Child.Id `
            -UptimeSeconds $UptimeSeconds `
            -RestartDelaySeconds $RestartDelay `
            -StdoutLog $StdoutLogPath `
            -StderrLog $StderrLogPath
        if ($RestartDelay -gt 0) {
            Start-Sleep -Milliseconds ([int][math]::Ceiling($RestartDelay * 1000))
        }
    }
} catch {
    $Message = $_.Exception.Message
    if ($null -ne $ActiveChild) {
        try {
            if (-not $ActiveChild.HasExited) {
                $ActiveChild.Kill()
                $null = $ActiveChild.WaitForExit(10000)
            }
        } catch {
        }
    }
    Write-LauncherEvent `
        -Status 'launcher_exception' `
        -ExitCode 1 `
        -Reason 'launcher_infrastructure_error' `
        -Message $Message
    exit 1
} finally {
    [CompanyWiki.KillOnCloseJob]::Close($ChildJobHandle)
    if ($null -ne $LauncherLockStream) {
        $LauncherLockStream.Dispose()
    }
}
