param(
    [ValidateSet('menu', 'status', 'start', 'pause', 'resume', 'stop', 'duplicates')]
    [string]$Action = 'menu',
    [string]$PythonExe = 'python',
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
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

function Invoke-CatalogCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$ExtraArguments = @()
    )

    $Arguments = @(
        '-m', 'company_wiki.source_catalog.cli',
        '--config', $ConfigPath,
        $Command
    ) + $ExtraArguments
    $Output = @(& $PythonExe @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($Output -join ' ')"
    }
    return (($Output -join [Environment]::NewLine) | ConvertFrom-Json)
}

function Invoke-WorkerCommand {
    param([Parameter(Mandatory = $true)][string]$Command)

    return Invoke-CatalogCommand -Command $Command -ExtraArguments @(
        '--worker-config', $WorkerConfigPath
    )
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
    $Status = Invoke-WorkerCommand -Command 'worker-status'
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
    Write-Host ''
    Write-Host 'Company Wiki Source Catalog'
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
    if ($PytestCount -gt 0) {
        Write-Host "  Test workers: $PytestCount (pytest temp dirs, not production)" -ForegroundColor Yellow
        foreach ($w in @($Inventory.pytest_temp_workers)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
    }
    if ($ForeignCount -gt 0) {
        Write-Host "  Foreign     : $ForeignCount other source_catalog processes" -ForegroundColor Yellow
        foreach ($w in @($Inventory.foreign_workers)) { Write-Host "    PID $($w.pid)" -ForegroundColor DarkGray }
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
        Write-Host "  Last error : $($Status.scheduler.last_error)"
        if ($Status.scheduler.llm_retry_after) {
            Write-Host "  LLM retry  : $(Format-StatusTime -Value $Status.scheduler.llm_retry_after)"
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
        if ($Status.long_running_document_warning) {
            Write-Host "    WARNING  : single document processing for $(if ($Status.current_path_elapsed_seconds) {[math]::Round($Status.current_path_elapsed_seconds, 0)} else {'?'})s; not failed" -ForegroundColor Yellow
        }
        if ($Scan) {
            Write-Host "  Last scan  : $(Format-StatusTime -Value $Scan.completed_at) [$($Scan.status)]"
            Write-Host "    Files    : seen $($Scan.files_seen) | reused $($Scan.files_reused) | rehashed $($Scan.files_hashed) | excluded $($Scan.files_excluded) | errors $($Scan.errors)"
            Write-Host "    New      : documents $($Scan.new_documents) | unique contents $($Scan.new_sources)"
        }
        Write-Host "  Indexed    : documents $($Index.documents) | physical files $($Index.physical_locations) | unique contents $($Index.unique_sources)"
        Write-Host "    Doc state: active $($Index.active_documents) | incomplete $($Index.incomplete_documents) | upstream rejected $($Index.upstream_rejected_documents) | quarantined $($Index.quarantined_documents)"
        Write-Host "    Copies   : duplicates $($Index.duplicate_copies) | active $($Index.active_locations) | missing $($Index.missing_locations) | quarantined $($Index.quarantined_locations)"
        Write-Host "  Markdown   : eligible $($Markdown.eligible) | pending $($Markdown.pending) | converting $($Markdown.in_progress) | blocked $($Markdown.blocked)"
        Write-Host "    MD result: completed $($Markdown.completed) | partial $($Markdown.partial) | unsupported $($Markdown.unsupported) | failed $($Markdown.failed)"
        if ($Status.scheduler.normalized_total) {
            Write-Host "    MD total  : $($Status.scheduler.normalized_total) processed since start"
        }
        Write-Host "  LLM summary: pending $($Summary.pending) | summarizing $($Summary.in_progress) | completed $($Summary.completed) | failed $($Summary.failed) | deferred $($Summary.deferred)"
        if ($Summary.next_document_retry_after) {
            Write-Host "    Doc retry : $(Format-StatusTime -Value $Summary.next_document_retry_after) | last failed $($Summary.last_failed_document_id)"
        }
Write-Host '  Lock health'
            Write-Host "    operation_lock  : $($Pipeline.health.locks.operation_lock)"
        Write-Host ''
        Write-Host '  Artifact health'
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
        if ($Summary.next_document_retry_after) {
            Write-Host "    Doc retry : $(Format-StatusTime -Value $Summary.next_document_retry_after) | last failed $($Summary.last_failed_document_id)"
        }
Write-Host ''
        Write-Host '  Process events'
            if ($Status.recent_process_event) {
                Write-Host "    Last event  : $($Status.recent_process_event.event) (pid $($Status.recent_process_event.pid))"
            }
            if ($Status.recent_process_event_error) {
                Write-Host "    Event error : $($Status.recent_process_event_error)" -ForegroundColor Red
            }
            if ($Status.recent_launcher_event) {
                Write-Host "    Launcher    : $($Status.recent_launcher_event.status)"
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
        'status' { Show-WorkerStatus; return }
        'start'  { $null = Invoke-WorkerCommand -Command 'worker-start' }
        'pause'  { $null = Invoke-WorkerCommand -Command 'worker-pause' }
        'resume' { $null = Invoke-WorkerCommand -Command 'worker-resume' }
        'stop'   { $null = Invoke-WorkerCommand -Command 'worker-stop' }
    }
    Show-WorkerStatus
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
