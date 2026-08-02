param(
    [ValidateSet('menu', 'status', 'start', 'pause', 'resume', 'stop', 'duplicates')]
    [string]$Action = 'menu',
    [string]$PythonExe = 'python',
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateRange(1, 300)]
    [int]$StatusTimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
try { [Console]::InputEncoding = $Utf8NoBom } catch { }
try { [Console]::OutputEncoding = $Utf8NoBom } catch { }
$OutputEncoding = $Utf8NoBom
$ConfigPath = Join-Path $ProjectRoot 'config/source_catalog.yaml'
$WorkerConfigPath = Join-Path $ProjectRoot 'config/source_catalog_worker.yaml'
$ControlLogPath = Join-Path $ProjectRoot '.source_catalog/control_center.log'
$RuntimePath = Join-Path $ProjectRoot '.source_catalog/worker_runtime.json'
$RuntimeStaleAfterSeconds = 60

function Write-ControlDiagnostic {
    param([Parameter(Mandatory = $true)][string]$Message)

    try {
        $LogDirectory = Split-Path -Parent $ControlLogPath
        if (-not (Test-Path -LiteralPath $LogDirectory)) {
            New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
        }
        Add-Content -LiteralPath $ControlLogPath -Encoding UTF8 -Value (
            "{0:o} {1}" -f (Get-Date), $Message
        )
    } catch {
        # Diagnostics must never prevent the control center from opening.
    }
}

function ConvertTo-WindowsCommandLineArgument {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Value
    )

    if ($Value.IndexOf([char]0) -ge 0) {
        throw 'Command arguments cannot contain a NUL character'
    }
    $Builder = [System.Text.StringBuilder]::new()
    $null = $Builder.Append([char]34)
    $BackslashCount = 0
    foreach ($Character in $Value.ToCharArray()) {
        if ($Character -eq [char]92) {
            $BackslashCount += 1
            continue
        }
        if ($Character -eq [char]34) {
            if ($BackslashCount -gt 0) {
                $null = $Builder.Append([char]92, $BackslashCount * 2)
            }
            $null = $Builder.Append([char]92)
            $null = $Builder.Append([char]34)
            $BackslashCount = 0
            continue
        }
        if ($BackslashCount -gt 0) {
            $null = $Builder.Append([char]92, $BackslashCount)
            $BackslashCount = 0
        }
        $null = $Builder.Append($Character)
    }
    if ($BackslashCount -gt 0) {
        $null = $Builder.Append([char]92, $BackslashCount * 2)
    }
    $null = $Builder.Append([char]34)
    return $Builder.ToString()
}

function Invoke-CatalogCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$ExtraArguments = @(),
        [ValidateRange(1, 600)][int]$TimeoutSeconds = 120
    )

    $Arguments = @(
        '-m', 'company_wiki.source_catalog.cli',
        '--config', $ConfigPath,
        $Command
    ) + $ExtraArguments
    $ArgumentLine = @($Arguments | ForEach-Object {
        ConvertTo-WindowsCommandLineArgument -Value "$_"
    }) -join ' '
    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $PythonExe
    $StartInfo.Arguments = $ArgumentLine
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    try {
        $StartInfo.StandardOutputEncoding = $Utf8NoBom
        $StartInfo.StandardErrorEncoding = $Utf8NoBom
    } catch {
        # PYTHONUTF8 still guarantees the child side on older .NET hosts.
    }
    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    try {
        if (-not $Process.Start()) {
            throw "Unable to start catalog command: $Command"
        }
        $StandardOutput = $Process.StandardOutput.ReadToEndAsync()
        $StandardError = $Process.StandardError.ReadToEndAsync()
        if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
            try { $Process.Kill() } catch { }
            try { $Process.WaitForExit() } catch { }
            throw "Command '$Command' timed out after $TimeoutSeconds seconds"
        }
        $Process.WaitForExit()
        $Output = "$($StandardOutput.Result)".Trim()
        $ErrorOutput = "$($StandardError.Result)".Trim()
        if ($Process.ExitCode -ne 0) {
            $Detail = if ($ErrorOutput) { $ErrorOutput } else { $Output }
            throw "Command '$Command' failed with exit code $($Process.ExitCode): $Detail"
        }
        try {
            return ($Output | ConvertFrom-Json)
        } catch {
            throw "Command '$Command' returned invalid JSON: $($_.Exception.Message)"
        }
    } finally {
        $Process.Dispose()
    }
}

function Invoke-WorkerCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [ValidateRange(1, 600)][int]$TimeoutSeconds = 120
    )

    return Invoke-CatalogCommand -Command $Command -ExtraArguments @(
        '--worker-config', $WorkerConfigPath
    ) -TimeoutSeconds $TimeoutSeconds
}

function Format-ByteSize {
    param([long]$Bytes)

    if ($Bytes -ge 1GB) { return ('{0:N2} GB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N2} MB' -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ('{0:N1} KB' -f ($Bytes / 1KB)) }
    return "$Bytes bytes"
}

function Format-StatusTime {
    param($Value)

    if ($null -eq $Value -or "$Value" -eq '') { return '-' }
    try {
        if ($Value -is [double] -or $Value -is [float] -or $Value -is [decimal] -or $Value -is [long] -or $Value -is [int]) {
            return [DateTimeOffset]::FromUnixTimeSeconds([long][Math]::Floor([double]$Value)).ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')
        }
        return [DateTimeOffset]::Parse("$Value").ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')
    } catch {
        return "$Value"
    }
}

function Read-LiveWorkerRuntime {
    if (-not (Test-Path -LiteralPath $RuntimePath)) { return $null }
    try {
        return (Get-Content -LiteralPath $RuntimePath -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        # The worker replaces this tiny file atomically; a transient read race is harmless.
        return $null
    }
}

function Show-LiveWorkerProgress {
    param($Runtime)

    if ($null -eq $Runtime) {
        Write-Progress -Id 14 -Activity 'Live worker: stopped or starting' -Status 'No live runtime file' -PercentComplete 0
        return
    }
    $HeartbeatAgeSeconds = $null
    try {
        if ($null -ne $Runtime.heartbeat_at -and "$($Runtime.heartbeat_at)" -ne '') {
            $HeartbeatAgeSeconds = [DateTimeOffset]::Now.ToUnixTimeSeconds() - [long][Math]::Floor([double]$Runtime.heartbeat_at)
        }
    } catch {
        $HeartbeatAgeSeconds = $null
    }
    if ($null -ne $HeartbeatAgeSeconds -and $HeartbeatAgeSeconds -gt $RuntimeStaleAfterSeconds) {
        Write-Progress -Id 14 -Activity 'Live worker: stopped' -Status "Stale heartbeat; last beat $(Format-StatusTime -Value $Runtime.heartbeat_at)" -PercentComplete 0
        return
    }
    $StageText = "$($Runtime.worker_status)"
    $Stage = if (-not [string]::IsNullOrWhiteSpace($StageText)) { $StageText } else { 'unknown' }
    if ($Stage -eq 'idle') { $Stage = 'waiting' }
    $Current = [int]($Runtime.progress_current)
    $Total = [int]($Runtime.progress_total)
    $Percent = if ($null -ne $Runtime.progress_percent) {
        [Math]::Max(0, [Math]::Min(100, [int][Math]::Round([double]$Runtime.progress_percent)))
    } else {
        0
    }
    $Position = if ($Total -gt 0) { "$Current / $Total ($($Runtime.progress_percent)%)" } else { 'waiting' }
    $Detail = if ($Runtime.progress_detail) { "$($Runtime.progress_detail)" } else { 'waiting for next cycle' }
    $CurrentPath = if ($Runtime.current_path) { "$($Runtime.current_path)" } else { '(no active file)' }
    Write-Progress -Id 14 -Activity "Live worker: $Stage" -Status "$Position | $Detail" -CurrentOperation $CurrentPath -PercentComplete $Percent
}

function Read-ControlChoiceWithLiveProgress {
    if ([Console]::IsInputRedirected) {
        return (Read-Host 'Choose')
    }
    try {
        Write-Host 'Choose (press 0-6; no Enter needed): ' -NoNewline
        while ($true) {
            if ([Console]::KeyAvailable) {
                $Key = [Console]::ReadKey($true)
                $Choice = "$($Key.KeyChar)"
                if ($Choice -match '^[0-6]$') {
                    Write-Progress -Id 14 -Completed
                    Write-Host $Choice
                    return $Choice
                }
            }
            Show-LiveWorkerProgress -Runtime (Read-LiveWorkerRuntime)
            Start-Sleep -Milliseconds 500
        }
    } catch {
        Write-Progress -Id 14 -Completed
        return (Read-Host 'Choose')
    }
}

function Show-WorkerStatus {
    $Status = Invoke-WorkerCommand -Command 'worker-status' -TimeoutSeconds $StatusTimeoutSeconds
    $Startup = if ($Status.startup.installed) {
        "ON ($($Status.startup.method))"
    } else {
        'OFF'
    }
    $Intent = if ($Status.desired_state -eq 'paused') { 'PAUSED' } else { 'ENABLED' }
    $Runtime = if ($Status.runtime_state) {
        $Status.runtime_state.ToUpperInvariant()
    } else {
        'UNKNOWN'
    }
    $SnapshotTime = if ($Status.status_generated_at) {
        Format-StatusTime -Value $Status.status_generated_at
    } else { '-' }
    $HeartbeatAge = if ($null -ne $Status.heartbeat_age_seconds) {
        "$($Status.heartbeat_age_seconds)s"
    } else { '-' }
    $Inventory = $Status.process_inventory
    $ProdCount = if ($Inventory.production_workers) { @($Inventory.production_workers).Count } else { 0 }
    $PytestCount = if ($Inventory.pytest_temp_workers) { @($Inventory.pytest_temp_workers).Count } else { 0 }
    $ForeignCount = if ($Inventory.foreign_workers) { @($Inventory.foreign_workers).Count } else { 0 }
    $SupervisorCount = if ($Inventory.production_supervisors) { @($Inventory.production_supervisors).Count } else { 0 }
    $PytestSupervisorCount = if ($Inventory.pytest_temp_supervisors) { @($Inventory.pytest_temp_supervisors).Count } else { 0 }
    $ForeignSupervisorCount = if ($Inventory.foreign_supervisors) { @($Inventory.foreign_supervisors).Count } else { 0 }
    Write-Host ''
    Write-Host 'Company Wiki Source Catalog'
    Write-Host ''
    Write-Host 'Process health'
    Write-Host "  Snapshot   : $SnapshotTime"
    Write-Host "  Auto-start : $Startup"
    Write-Host "  User mode  : $Intent"
    Write-Host "  Process    : $Runtime"
    if ($Status.runtime_state -eq 'running' -and $Status.pid) {
        Write-Host "  PID        : $($Status.pid)"
        Write-Host "  Worker     : $($Status.worker_status)"
        Write-Host "  Heartbeat  : $(Format-StatusTime -Value $Status.heartbeat_at) (age $HeartbeatAge)"
    }
    if ($ProdCount -gt 1) {
        Write-Host "  WARNING    : $ProdCount production workers detected (expected 0-1)" -ForegroundColor Red
    }
    if ($SupervisorCount -eq 1) {
        Write-Host "  Supervisor : RUNNING (PID $($Inventory.production_supervisors[0].pid))" -ForegroundColor Green
    } elseif ($SupervisorCount -eq 0) {
        if ($Status.desired_state -eq 'enabled') {
            Write-Host '  Supervisor : NOT RUNNING (automatic recovery unavailable)' -ForegroundColor Red
        } else {
            Write-Host '  Supervisor : NOT RUNNING' -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Supervisor : DUPLICATE ($SupervisorCount supervisors)" -ForegroundColor Red
    }
    $LoadedCode = if ($Status.loaded_code_fingerprint) {
        "$($Status.loaded_code_fingerprint)".Substring(
            0, [math]::Min(12, "$($Status.loaded_code_fingerprint)".Length)
        )
    } else { 'unknown' }
    $CurrentCode = if ($Status.current_code_fingerprint) {
        "$($Status.current_code_fingerprint)".Substring(
            0, [math]::Min(12, "$($Status.current_code_fingerprint)".Length)
        )
    } else { 'unknown' }
    if ($null -ne $Status.code_match -and $Status.code_match -eq $true) {
        Write-Host "  Code       : MATCH | loaded $LoadedCode | current $CurrentCode" -ForegroundColor Green
    } elseif ($null -ne $Status.code_match -and $Status.code_match -eq $false) {
        Write-Host "  Code       : MISMATCH | loaded $LoadedCode | current $CurrentCode" -ForegroundColor Yellow
        Write-Host "    Worker is running older code; controlled reload is pending." -ForegroundColor Yellow
    } else {
        Write-Host "  Code       : UNKNOWN | loaded $LoadedCode | current $CurrentCode" -ForegroundColor Yellow
    }
    if ($Status.code_fingerprint_error) {
        Write-Host "    Code error: $($Status.code_fingerprint_error)" -ForegroundColor Yellow
    }
    if ($PytestCount -gt 0) {
        Write-Host "  Test workers: $PytestCount (pytest temp dirs, not production)" -ForegroundColor Yellow
        foreach ($w in @($Inventory.pytest_temp_workers)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
    }
    if ($ForeignCount -gt 0) {
        Write-Host "  Foreign     : $ForeignCount other source_catalog processes" -ForegroundColor Yellow
        foreach ($w in @($Inventory.foreign_workers)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
    }
    if ($PytestSupervisorCount -gt 0) {
        Write-Host "  Test launchers: $PytestSupervisorCount (pytest temp dirs, not production)" -ForegroundColor Yellow
        foreach ($w in @($Inventory.pytest_temp_supervisors)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
    }
    if ($ForeignSupervisorCount -gt 0) {
        Write-Host "  Foreign launchers: $ForeignSupervisorCount other source_catalog supervisors" -ForegroundColor Yellow
        foreach ($w in @($Inventory.foreign_supervisors)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
    }
    if ($Status.stale_runtime -and $Status.pid) {
        Write-Host "  Last PID   : $($Status.pid) (historical; process is not running)" -ForegroundColor Yellow
        Write-Host "  Last beat  : $(Format-StatusTime -Value $Status.heartbeat_at)"
        if ($Status.last_worker_status) {
            Write-Host "  Last stage : $($Status.last_worker_status)" -ForegroundColor Yellow
        }
        if ($Status.last_current_path) {
            Write-Host "  Last file  : $($Status.last_current_path)" -ForegroundColor Yellow
        }
    }
    if ($Status.scheduler.last_cycle_at) {
        Write-Host "  Last cycle : $(Format-StatusTime -Value $Status.scheduler.last_cycle_at)"
        if ($Status.scheduler.last_error) {
            $ErrorLabel = switch ($Status.scheduler.last_error_scope) {
                'llm_global' { 'Active LLM error' }
                'llm_document' { 'Last LLM document error' }
                'llm_permanent_document' { 'Last permanent LLM error' }
                'cycle' { 'Last cycle error' }
                default { 'Last error' }
            }
            Write-Host "  $ErrorLabel : $($Status.scheduler.last_error)"
        }
        if ($Status.scheduler.llm_retry_after) {
            Write-Host "  LLM retry  : $(Format-StatusTime -Value $Status.scheduler.llm_retry_after)"
        }
    }
    if ($null -ne $Status.scheduler.parse_timeout_total) {
        Write-Host "  Parse timeouts: total $($Status.scheduler.parse_timeout_total)"
        if ($Status.scheduler.last_parse_timeout_path) {
            Write-Host "    Last path: $($Status.scheduler.last_parse_timeout_path)" -ForegroundColor Yellow
        }
    }
    if ($Status.worker_status -eq 'waiting' -and $null -ne $Status.next_wait_seconds) {
        Write-Host "  Next wake  : $($Status.next_wait_seconds)s [$($Status.next_wake_reason)] at $(Format-StatusTime -Value $Status.next_wake_at)"
    }
    $Pipeline = $Status.pipeline
    if ($Pipeline -and $Pipeline.available) {
        $Scan = $Pipeline.last_scan
        $Index = $Pipeline.index
        $Markdown = $Pipeline.markdown
        $Summary = $Pipeline.llm_summary
        $Current = $Pipeline.current
        Write-Host ''
        Write-Host 'Pipeline inventory'
        Write-Host "  Current    : $($Current.stage) ($($Current.active_documents) document active)"
        if ($Current.path) {
            Write-Host "    File     : $($Current.path)"
            Write-Host "    Progress : $($Current.current) / $($Current.total) ($($Current.percent)%)"
            Write-Host "    Detail   : $($Current.detail)"
        }
        if ($Status.current_path_elapsed_seconds) {
            $Elapsed = [math]::Round($Status.current_path_elapsed_seconds, 0)
            $ElapsedMin = [math]::Floor($Elapsed / 60)
            $ElapsedSec = [math]::Round($Elapsed % 60, 0)
            Write-Host "    Elapsed  : ${ElapsedMin}m ${ElapsedSec}s on $($Status.current_path)" -ForegroundColor $(if ($Status.long_running_document_warning) {'Yellow'} else {'DarkGray'})
        }
        if ($Status.parser_pid) {
            $ParserElapsed = if ($null -ne $Status.parser_elapsed_seconds) { "$($Status.parser_elapsed_seconds)s" } else { 'unknown' }
            $ParserTimeout = if ($null -ne $Status.parser_timeout_seconds) { "$($Status.parser_timeout_seconds)s" } else { 'unknown' }
            $ParserOwnership = if ($Status.parser_ownership) { "$($Status.parser_ownership)" } else { 'unknown' }
            Write-Host "    Parser   : PID $($Status.parser_pid) | elapsed $ParserElapsed / timeout $ParserTimeout | owner $ParserOwnership"
        }
        if ($Status.long_running_document_warning) {
            Write-Host "    WARNING  : single document processing for $(if ($Status.current_path_elapsed_seconds) {[math]::Round($Status.current_path_elapsed_seconds, 0)} else {'?'})s; not failed" -ForegroundColor Yellow
        }
        Write-Host ''
        Write-Host 'Scan health'
        if ($Scan) {
            Write-Host "  Last scan  : $(Format-StatusTime -Value $Scan.completed_at) [$($Scan.status)]"
            Write-Host "    Files    : seen $($Scan.files_seen) | reused $($Scan.files_reused) | rehashed $($Scan.files_hashed) | excluded $($Scan.files_excluded) | policy $($Scan.policy_excluded) | errors $($Scan.errors)"
            Write-Host "    New      : documents $($Scan.new_documents) | unique contents $($Scan.new_sources)"
            if (
                $null -ne $Scan.new_errors -or
                $null -ne $Scan.known_quarantined
            ) {
                Write-Host "    Errors   : total $($Scan.errors) | new $($Scan.new_errors) | known quarantine $($Scan.known_quarantined)"
            }
            foreach ($Detail in @($Scan.error_details)) {
                $ErrorKind = if ($null -eq $Detail.unchanged) {
                    'current; legacy classification unknown'
                } elseif ($Detail.unchanged) { 'known quarantine' } else { 'new/current' }
                $ErrorPath = if ($Detail.relative_path) {
                    "$($Detail.root_id)/$($Detail.relative_path)"
                } else { "$($Detail.root_id)" }
                Write-Host "      [$ErrorKind] $ErrorPath" -ForegroundColor Yellow
                Write-Host "        $($Detail.error)" -ForegroundColor DarkGray
            }
        }
        Write-Host ''
        Write-Host 'Export health'
        if ($Status.scheduler.last_export_at) {
            $ExportDuration = if ($null -ne $Status.scheduler.last_export_duration_seconds) {
                "$($Status.scheduler.last_export_duration_seconds)s"
            } else { 'unknown' }
            $ExportSteps = if ($null -ne $Status.scheduler.last_export_progress_total) {
                "$($Status.scheduler.last_export_progress_total)"
            } else { 'unknown' }
            Write-Host "  Last export: $(Format-StatusTime -Value $Status.scheduler.last_export_at) | duration $ExportDuration | steps $ExportSteps"
            if ($Status.scheduler.last_export_progress_detail) {
                Write-Host "    Last step: $($Status.scheduler.last_export_progress_detail)"
            }
        } else {
            Write-Host '  Last export: none recorded'
        }
        Write-Host ''
        Write-Host "  Indexed    : documents $($Index.documents) | physical files $($Index.physical_locations) | unique contents $($Index.unique_sources)"
        Write-Host "    Doc state: active $($Index.active_documents) | incomplete $($Index.incomplete_documents) | upstream rejected $($Index.upstream_rejected_documents) | quarantined $($Index.quarantined_documents)"
        Write-Host "    Copies   : duplicates $($Index.duplicate_copies) | active $($Index.active_locations) | missing $($Index.missing_locations) | quarantined $($Index.quarantined_locations)"
        Write-Host "  Markdown   : eligible $($Markdown.eligible) | pending $($Markdown.pending) | converting $($Markdown.in_progress) | blocked $($Markdown.blocked)"
        if (
            $null -ne $Markdown.blocked_quarantined -or
            $null -ne $Markdown.blocked_incomplete -or
            $null -ne $Markdown.blocked_other
        ) {
            Write-Host "    Blocked  : quarantined $($Markdown.blocked_quarantined) | incomplete $($Markdown.blocked_incomplete) | other $($Markdown.blocked_other)"
        }
        Write-Host "    MD result: completed $($Markdown.completed) | partial $($Markdown.partial) | unsupported $($Markdown.unsupported) | failed $($Markdown.failed)"
        if ($null -ne $Markdown.retryable_failed -or $null -ne $Markdown.terminal_failed) {
            Write-Host "    MD retry : retryable $($Markdown.retryable_failed) | terminal $($Markdown.terminal_failed)"
        }
        if ($Status.scheduler.normalized_total) {
            Write-Host "    MD total  : $($Status.scheduler.normalized_total) processed since start"
        }
        $RetryableFailed = if ($null -ne $Summary.retryable_failed) { $Summary.retryable_failed } else { $Summary.failed }
        $PermanentFailed = if ($null -ne $Summary.permanent) { $Summary.permanent } else { 0 }
        Write-Host "  LLM summary: pending $($Summary.pending) | summarizing $($Summary.in_progress) | completed $($Summary.completed) | retryable $RetryableFailed | permanent $PermanentFailed | deferred $($Summary.deferred)"
        if ($Summary.global_deferred) {
            Write-Host "    Global retry: $(Format-StatusTime -Value $Summary.global_retry_after)" -ForegroundColor Yellow
            if ($Summary.global_error) {
                Write-Host "    Global error: $($Summary.global_error)" -ForegroundColor Yellow
            }
        }
        if ($Summary.next_document_retry_after) {
            Write-Host "    Doc retry : $(Format-StatusTime -Value $Summary.next_document_retry_after) | last failed $($Summary.last_failed_document_id)"
        }
        if ($PermanentFailed -gt 0) {
            Write-Host "    Permanent : last document $($Summary.last_permanent_document_id)"
        }
        if ($Summary.legacy_scope_mismatch) {
            Write-Host "    Legacy scope mismatch: $($Summary.legacy_scope_mismatch)" -ForegroundColor Yellow
        }
        Write-Host ''
        Write-Host 'Lock health'
        $LockHealth = $Pipeline.health.locks
        $LockDetail = if ($LockHealth.operation_lock_pid) {
            " (pid $($LockHealth.operation_lock_pid), operation $($LockHealth.operation_lock_operation))"
        } else { '' }
        $LockColor = if ($LockHealth.operation_lock -in @('stale', 'invalid')) { 'Yellow' } else { 'Gray' }
        Write-Host "  operation_lock  : $($LockHealth.operation_lock)$LockDetail" -ForegroundColor $LockColor
        if ($LockHealth.operation_lock_identity_verification) {
            Write-Host "    Identity  : $($LockHealth.operation_lock_identity_verification) | recorded $($LockHealth.operation_lock_process_creation_time) | observed $($LockHealth.operation_lock_observed_process_creation_time)"
        }
        Write-Host ''
        Write-Host 'Artifact health'
        $Health = $Pipeline.health
        if ($Health.artifacts) {
            $Art = $Health.artifacts
            Write-Host "  Artifacts  : DB rows $($Art.artifact_rows) | reconciled $(if($Art.derived_detached_count){$Art.derived_detached_count}else{'0'})"
            if ($Art.reconciliation_needed) {
                Write-Host "    WARNING  : artifact index empty / derived detached" -ForegroundColor Yellow
            }
        }
        $Explanations = $Pipeline.explanations
        if ($Explanations -and $Explanations.markdown_pending_reason) {
            Write-Host "  Why pending: $($Explanations.markdown_pending_reason)" -ForegroundColor DarkGray
        }
        Write-Host ''
        Write-Host 'Process events'
            if ($Status.recent_process_event) {
                Write-Host "    Last event  : $($Status.recent_process_event.event) (pid $($Status.recent_process_event.pid))"
            }
            if ($Status.recent_process_event_error) {
                Write-Host "    Event error : $($Status.recent_process_event_error)" -ForegroundColor Red
            }
            if ($Status.recent_launcher_event) {
                $Launcher = $Status.recent_launcher_event
                $LauncherDetail = "$($Launcher.status)"
                if ($Launcher.reason) {
                    $LauncherDetail += " | reason=$($Launcher.reason)"
                }
                if ($null -ne $Launcher.child_pid) {
                    $LauncherDetail += " | child_pid=$($Launcher.child_pid)"
                }
                if ($null -ne $Launcher.attempt) {
                    $LauncherDetail += " | attempt=$($Launcher.attempt)"
                }
                if ($null -ne $Launcher.worker_hang_timeout_seconds) {
                    $LauncherDetail += " | watchdog=$($Launcher.worker_hang_timeout_seconds)s"
                }
                if (
                    $Launcher.status -in @('exited', 'restarting', 'launcher_exception') -and
                    $null -ne $Launcher.exit_code
                ) {
                    $LauncherDetail += " | exit=$($Launcher.exit_code)"
                }
                if (
                    $Launcher.status -eq 'restarting' -and
                    $null -ne $Launcher.restart_delay_seconds
                ) {
                    $LauncherDetail += " | restart_in=$($Launcher.restart_delay_seconds)s"
                }
                Write-Host "    Launcher    : $LauncherDetail"
                if ($Launcher.stdout_log) {
                    Write-Host "    Worker stdout: $($Launcher.stdout_log)"
                }
                if ($Launcher.stderr_log) {
                    Write-Host "    Worker stderr: $($Launcher.stderr_log)"
                }
            }
        $Recent = $Pipeline.recent_batches
        if ($Recent.markdown) {
            Write-Host "    Last MD  : completed $($Recent.markdown.completed) | partial $($Recent.markdown.partial) | unsupported $($Recent.markdown.unsupported) | failed $($Recent.markdown.failed)"
        }
        if ($Recent.llm_summary) {
            Write-Host "    Last LLM : completed $($Recent.llm_summary.completed) | failed $($Recent.llm_summary.failed)"
            if ($Recent.llm_summary.failure_scope) {
                Write-Host "      Scope   : $($Recent.llm_summary.failure_scope) | document $($Recent.llm_summary.failed_document_id)"
            }
        }
    } elseif ($Pipeline -and $Pipeline.error) {
        Write-Host "  Pipeline   : unavailable ($($Pipeline.error))" -ForegroundColor Yellow
    }
    Write-Host ''
}

function Show-WorkerStatusSafely {
    Write-Host ''
    Write-Host 'Company Wiki Source Catalog'
    Write-Host "  Reading worker status (timeout $($StatusTimeoutSeconds)s)..." -ForegroundColor Cyan
    try {
        Show-WorkerStatus
        return $true
    } catch {
        $Message = "Unable to read worker status: $($_.Exception.Message)"
        Write-ControlDiagnostic -Message $Message
        Write-Host ''
        Write-Host 'Company Wiki Source Catalog'
        Write-Host "  Snapshot   : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (local, possibly stale)"
        Write-Host "  $Message" -ForegroundColor Red
        Write-Host '  The menu remains available. Try Refresh status after a few seconds.' -ForegroundColor Yellow
        Write-Host ''
        return $false
    }
}

function Invoke-ControlAction {
    param([Parameter(Mandatory = $true)][string]$SelectedAction)

    switch ($SelectedAction) {
        'status' { $null = Show-WorkerStatusSafely; return }
        'start'  { $null = Invoke-WorkerCommand -Command 'worker-start' }
        'pause'  { $null = Invoke-WorkerCommand -Command 'worker-pause' }
        'resume' { $null = Invoke-WorkerCommand -Command 'worker-resume' }
        'stop'   { $null = Invoke-WorkerCommand -Command 'worker-stop' }
    }
    $null = Show-WorkerStatusSafely
}

function Show-DuplicateCenter {
    $Search = Read-Host 'Filter by company, title, date, kind, or path (Enter for all)'
    $Offset = 0
    $PageSize = 10
    while ($true) {
        $Arguments = @('--limit', "$PageSize", '--offset', "$Offset")
        if ($Search) {
            $Arguments += @('--text', $Search)
        }
        $Inventory = Invoke-CatalogCommand -Command 'duplicates' -ExtraArguments $Arguments
        $Groups = @($Inventory.groups)
        Write-Host ''
        Write-Host 'Exact-copy duplicate center'
        Write-Host "  Matching groups : $($Inventory.total_groups)"
        Write-Host "  Recyclable copies: $($Inventory.total_reclaimable_copies)"
        Write-Host "  Reclaimable size : $(Format-ByteSize -Bytes $Inventory.total_reclaimable_bytes)"
        Write-Host '  Canonical copies are protected. No file is removed automatically.'
        Write-Host ''
        if ($Groups.Count -eq 0) {
            Read-Host 'No matching duplicate groups. Press Enter to return' | Out-Null
            return
        }

        $Choices = @()
        $Number = 1
        foreach ($Group in $Groups) {
            $Entity = @($Group.entities) -join ', '
            Write-Host "[$Entity] $($Group.title)  $($Group.published_date)"
            Write-Host "  KEEP  $($Group.canonical.absolute_path)" -ForegroundColor Green
            foreach ($Copy in @($Group.duplicates)) {
                Write-Host "  $Number. $(Format-ByteSize -Bytes $Copy.size_bytes)  $($Copy.absolute_path)"
                $Choices += [PSCustomObject]@{
                    Number = $Number
                    LocationId = $Copy.location_id
                }
                $Number += 1
            }
            Write-Host ''
        }

        Write-Host 'N = next page, P = previous page, S = new search, 0 = return'
        $Choice = Read-Host 'Choose one duplicate copy to inspect'
        if ($Choice -eq '0') { return }
        if ($Choice -match '^[Nn]$') {
            if (($Offset + $PageSize) -lt [int]$Inventory.total_groups) {
                $Offset += $PageSize
            }
            continue
        }
        if ($Choice -match '^[Pp]$') {
            $Offset = [Math]::Max(0, $Offset - $PageSize)
            continue
        }
        if ($Choice -match '^[Ss]$') {
            $Search = Read-Host 'New filter (Enter for all)'
            $Offset = 0
            continue
        }
        if ($Choice -notmatch '^\d+$') {
            Write-Host 'Unknown choice.' -ForegroundColor Yellow
            continue
        }
        $Selected = @($Choices | Where-Object { $_.Number -eq [int]$Choice })
        if ($Selected.Count -ne 1) {
            Write-Host 'The selected copy is not on this page.' -ForegroundColor Yellow
            continue
        }

        $Preview = Invoke-CatalogCommand -Command 'duplicate-preview' -ExtraArguments @(
            '--location-id', $Selected[0].LocationId
        )
        Write-Host ''
        Write-Host 'Selected duplicate (will move to Windows Recycle Bin):'
        Write-Host "  COPY : $($Preview.absolute_path)" -ForegroundColor Yellow
        Write-Host "  KEEP : $($Preview.canonical_path)" -ForegroundColor Green
        Write-Host "  SIZE : $(Format-ByteSize -Bytes $Preview.size_bytes)"
        Write-Host "  SHA  : $($Preview.content_sha256)"
        Write-Host 'The catalog will re-check both hashes immediately before recycling.'
        if ($Preview.root_id -eq 'dropbox_stock') {
            Write-Host 'WARNING: Dropbox may sync this removal to your other devices.' -ForegroundColor Red
        }
        $Confirmation = Read-Host "Type '$($Preview.confirmation_phrase)' to continue, or Enter to cancel"
        if ($Confirmation -cne $Preview.confirmation_phrase) {
            Write-Host 'Cancelled. Nothing was changed.'
            continue
        }
        $Result = Invoke-CatalogCommand -Command 'duplicate-recycle' -ExtraArguments @(
            '--location-id', $Preview.location_id,
            '--confirmation-token', $Preview.confirmation_token
        )
        Write-Host ''
        Write-Host 'Moved one duplicate copy to Windows Recycle Bin.' -ForegroundColor Green
        Write-Host "  Recycled: $($Result.absolute_path)"
        Write-Host "  Kept    : $($Result.canonical_path)"
        Write-Host "  Audit ID: $($Result.action_id)"
        Read-Host 'Press Enter to refresh the duplicate list' | Out-Null
    }
}

Set-Location -LiteralPath $ProjectRoot
Write-ControlDiagnostic -Message "Control center launched (action=$Action, host=$($Host.Name), pid=$PID)."
if ($Action -eq 'duplicates') {
    Show-DuplicateCenter
    exit 0
}
if ($Action -ne 'menu') {
    Invoke-ControlAction -SelectedAction $Action
    exit 0
}

try {
    $Host.UI.RawUI.WindowTitle = 'Company Wiki Source Catalog Control'
} catch {
    $Message = "Window title could not be set: $($_.Exception.Message)"
    Write-ControlDiagnostic -Message $Message
    Write-Host $Message -ForegroundColor Yellow
}
while ($true) {
    $null = Show-WorkerStatusSafely
    Write-Host '  1. Refresh status'
    Write-Host '  2. Pause now and keep paused after restart'
    Write-Host '  3. Resume and start now'
    Write-Host '  4. Stop this run (auto-start remains enabled)'
    Write-Host '  5. Start now (only when enabled)'
    Write-Host '  6. Browse exact duplicates / recycle selected copies'
    Write-Host '  0. Exit'
    try {
        $Choice = Read-ControlChoiceWithLiveProgress
    } catch {
        $Message = "Control center cannot read keyboard input: $($_.Exception.Message)"
        Write-ControlDiagnostic -Message $Message
        Write-Host $Message -ForegroundColor Red
        Write-Host "Diagnostic log: $ControlLogPath" -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        exit 1
    }
    try {
        switch ($Choice) {
            '1' { }
            '2' { Invoke-ControlAction -SelectedAction 'pause' }
            '3' { Invoke-ControlAction -SelectedAction 'resume' }
            '4' { Invoke-ControlAction -SelectedAction 'stop' }
            '5' { Invoke-ControlAction -SelectedAction 'start' }
            '6' { Show-DuplicateCenter }
            '0' {
                Write-ControlDiagnostic -Message 'Control center exited by user.'
                exit 0
            }
            default { Write-Host 'Unknown choice.' -ForegroundColor Yellow }
        }
    } catch {
        Write-ControlDiagnostic -Message "Menu action failed: $($_.Exception.Message)"
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host 'Press Enter to continue' | Out-Null
    }
}
