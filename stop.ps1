[CmdletBinding()]
param(
    [switch]$KeepDify,
    [switch]$AbortIfActiveTasks
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot 'backend'
$BackendPython = Join-Path $BackendDir '.venv\Scripts\python.exe'
$DatabasePath = Join-Path $BackendDir 'data\meditation.db'
$HadFailures = $false

function Write-Status {
    param([string]$Message)
    Write-Host "[STOP] $Message" -ForegroundColor Cyan
}

function Write-Skipped {
    param([string]$Message)
    Write-Host "[SKIP] $Message" -ForegroundColor Yellow
}

function Write-Failure {
    param([string]$Message)
    $script:HadFailures = $true
    Write-Host "[FAILED] $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-ProcessRecord {
    param([int]$ProcessId)
    return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
}

function Get-ListeningProcessIds {
    param([int]$Port)
    return @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Test-ProjectProcess {
    param(
        [int]$ProcessId,
        [string]$CommandPattern
    )

    $record = Get-ProcessRecord $ProcessId
    if (-not $record -or -not $record.CommandLine) {
        return $false
    }

    $commandLine = $record.CommandLine.Replace('/', '\\')
    return $commandLine -match $CommandPattern -and (Test-ProcessLineageMatchesProject $record)
}

function Test-ProcessLineageMatchesProject {
    param($ProcessRecord)

    $normalizedRoot = $ProjectRoot.Replace('/', '\\')
    $current = $ProcessRecord
    for ($depth = 0; $current -and $depth -lt 8; $depth++) {
        $commandLine = [string]$current.CommandLine
        if ($commandLine.Replace('/', '\\') -like "*$normalizedRoot*") {
            return $true
        }

        if ($commandLine -match '(?i)-EncodedCommand\s+([^\s]+)') {
            try {
                $decoded = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($Matches[1]))
                if ($decoded.Replace('/', '\\') -like "*$normalizedRoot*") {
                    return $true
                }
            } catch {
                # Ignore unrelated or malformed encoded commands.
            }
        }
        if (-not $current.ParentProcessId -or $current.ParentProcessId -eq $current.ProcessId) {
            break
        }
        $current = Get-ProcessRecord $current.ParentProcessId
    }
    return $false
}

function Get-ServiceWindowProcess {
    param(
        [int]$ProcessId,
        [string]$CommandPattern
    )

    $current = Get-ProcessRecord $ProcessId
    for ($depth = 0; $current -and $depth -lt 8; $depth++) {
        $commandLine = [string]$current.CommandLine
        $isPowerShell = $current.Name -match '(?i)^powershell(?:\.exe)?$'
        if ($isPowerShell -and $commandLine -match '(?i)-EncodedCommand\s+([^\s]+)') {
            try {
                $decoded = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($Matches[1]))
                if ($decoded -match $CommandPattern -and $decoded.Replace('/', '\\') -like "*$($ProjectRoot.Replace('/', '\\'))*") {
                    return $current
                }
            } catch {
                # Ignore unrelated or malformed encoded commands.
            }
        }
        if (-not $current.ParentProcessId -or $current.ParentProcessId -eq $current.ProcessId) {
            break
        }
        $current = Get-ProcessRecord $current.ParentProcessId
    }
    return $null
}

function Stop-ProcessTree {
    param(
        [int]$ProcessId,
        [string]$Description
    )

    try {
        Write-Status "Closing $Description window and its child processes (PID $ProcessId)..."
        & taskkill.exe /PID $ProcessId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "taskkill exited with code $LASTEXITCODE." }
    } catch {
        Write-Failure "Could not close $Description window (PID $ProcessId): $($_.Exception.Message)"
    }
}

function Stop-ProjectPortService {
    param(
        [int]$Port,
        [string]$ServiceName,
        [string]$CommandPattern
    )

    $processIds = Get-ListeningProcessIds $Port
    if ($processIds.Count -eq 0) {
        Write-Skipped "$ServiceName is not running on port $Port."
        return
    }

    foreach ($processId in $processIds) {
        $record = Get-ProcessRecord $processId
        if (-not (Test-ProjectProcess $processId $CommandPattern)) {
            $commandLine = if ($record) { $record.CommandLine } else { 'unavailable' }
            Write-Skipped "$ServiceName port $Port is owned by PID $processId, but its command line is not a matching project process: $commandLine"
            continue
        }

        $serviceWindow = Get-ServiceWindowProcess $processId $CommandPattern
        if ($serviceWindow) {
            Stop-ProcessTree $serviceWindow.ProcessId $ServiceName
        } else {
            try {
                Write-Status "Stopping $ServiceName process (PID $processId); no managed service window was found."
                Stop-Process -Id $processId -Force -ErrorAction Stop
            } catch {
                Write-Failure "Could not stop $ServiceName (PID $processId): $($_.Exception.Message)"
            }
        }
    }
}

function Get-ProjectWorkerProcesses {
    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match 'app\.services\.(audio|music)_worker' -and
                (Test-ProcessLineageMatchesProject $_)
            }
    )
}

function Get-ActiveTaskCounts {
    if (-not (Test-Path -LiteralPath $DatabasePath) -or -not (Test-Path -LiteralPath $BackendPython)) {
        return $null
    }

    $query = @'
import sqlite3, sys
db = sys.argv[1]
con = sqlite3.connect(db)
def count(table):
    exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        return 0
    return con.execute(f"SELECT COUNT(*) FROM {table} WHERE status IN ('pending', 'processing')").fetchone()[0]
print(f"{count('audio_tasks')},{count('music_tasks')}")
'@
    $queryFile = Join-Path ([System.IO.Path]::GetTempPath()) "meditation-guide-stop-query-$PID.py"
    try {
        [System.IO.File]::WriteAllText($queryFile, $query, [System.Text.UTF8Encoding]::new($false))
        $result = & $BackendPython $queryFile $DatabasePath 2>$null
        if ($LASTEXITCODE -ne 0 -or $result -notmatch '^\d+,\d+$') {
            return $null
        }
        $parts = $result.Split(',')
        return [pscustomobject]@{ Audio = [int]$parts[0]; Music = [int]$parts[1] }
    } catch {
        return $null
    } finally {
        Remove-Item -LiteralPath $queryFile -Force -ErrorAction SilentlyContinue
    }
}

function Get-DifyDirectory {
    if ($env:DIFY_DIR) {
        $configuredDockerDir = Join-Path $env:DIFY_DIR 'docker'
        foreach ($composeName in @('docker-compose.yml', 'docker-compose.yaml')) {
            if (Test-Path -LiteralPath (Join-Path $configuredDockerDir $composeName)) {
                return $env:DIFY_DIR
            }
        }
        throw "No docker-compose.yml or docker-compose.yaml was found under DIFY_DIR=$($env:DIFY_DIR)."
    }

    $candidates = @(
        'C:\projects\github\dify\dify-1.16.1',
        'C:\projects\github\dify',
        'D:\project\github\dify\dify-1.16.1',
        'D:\project\github\dify',
        (Join-Path $env:USERPROFILE 'github\dify\dify-1.16.1'),
        (Join-Path $env:USERPROFILE 'github\dify')
    )
    foreach ($candidate in $candidates) {
        try {
            foreach ($composeName in @('docker-compose.yml', 'docker-compose.yaml')) {
                if (Test-Path -LiteralPath (Join-Path $candidate "docker\\$composeName")) {
                    return $candidate
                }
            }
        } catch {
            # A candidate can be on a drive that does not exist on this computer.
        }
    }
    throw 'Dify local deployment was not found. Set DIFY_DIR to its root directory, which must contain docker\docker-compose.yml or docker\docker-compose.yaml.'
}

try {
    Write-Status "Project directory: $ProjectRoot"

    $activeTaskCounts = Get-ActiveTaskCounts
    if ($null -eq $activeTaskCounts) {
        Write-Skipped 'Could not determine active audio/music task counts; continuing shutdown.'
    } elseif (($activeTaskCounts.Audio + $activeTaskCounts.Music) -gt 0) {
        $message = "$($activeTaskCounts.Audio) active audio task(s) and $($activeTaskCounts.Music) active music task(s) will be interrupted; music tasks resume by stage on next startup."
        if ($AbortIfActiveTasks) {
            Write-Failure "$message Shutdown was cancelled because -AbortIfActiveTasks was specified."
            exit 1
        }
        Write-Host "[WARNING] $message Continuing shutdown." -ForegroundColor Yellow
    }

    Stop-ProjectPortService 5173 'Frontend' 'vite'

    $workers = Get-ProjectWorkerProcesses
    if ($workers.Count -eq 0) {
        Write-Skipped 'Audio/Music Workers are not running.'
    } else {
        foreach ($worker in $workers) {
            $isMusicWorker = $worker.CommandLine -match 'app\.services\.music_worker'
            $workerPattern = if ($isMusicWorker) { 'app\.services\.music_worker' } else { 'app\.services\.audio_worker' }
            $workerName = if ($isMusicWorker) { 'Music Worker' } else { 'Audio Worker' }
            if (-not (Get-ProcessRecord $worker.ProcessId)) {
                Write-Skipped "$workerName process (PID $($worker.ProcessId)) already exited with its managed process tree."
                continue
            }
            $serviceWindow = Get-ServiceWindowProcess $worker.ProcessId $workerPattern
            if ($serviceWindow) {
                Stop-ProcessTree $serviceWindow.ProcessId $workerName
            } else {
                try {
                    Write-Status "Stopping $workerName process (PID $($worker.ProcessId)); no managed service window was found."
                    Stop-Process -Id $worker.ProcessId -Force -ErrorAction Stop
                } catch {
                    Write-Failure "Could not stop $workerName (PID $($worker.ProcessId)): $($_.Exception.Message)"
                }
            }
        }
    }

    Stop-ProjectPortService 8000 'Backend' 'uvicorn'

    if ($KeepDify) {
        Write-Skipped 'Dify was kept running because -KeepDify was specified.'
    } else {
        if (-not (Test-Command 'docker')) {
            Write-Failure 'Docker command was not found; Dify was not stopped.'
        } else {
            $DifyDir = Get-DifyDirectory
            Write-Status "Stopping Dify containers in $DifyDir..."
            Push-Location (Join-Path $DifyDir 'docker')
            try {
                & docker compose down
                if ($LASTEXITCODE -ne 0) { throw "docker compose down exited with code $LASTEXITCODE." }
            } finally {
                Pop-Location
            }
        }
    }

    if ($HadFailures) {
        exit 1
    }
    Write-Host 'Shutdown completed.' -ForegroundColor Green
} catch {
    Write-Failure $_.Exception.Message
    exit 1
}
