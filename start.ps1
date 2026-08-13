[CmdletBinding()]
param(
    [switch]$Install
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$BackendPython = Join-Path $BackendDir '.venv\Scripts\python.exe'

function Write-Status {
    param([string]$Message)
    Write-Host "[START] $Message" -ForegroundColor Cyan
}

function Write-Failure {
    param([string]$Message)
    Write-Host "[FAILED] $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-HttpStatus {
    param([string]$Url)

    $result = & curl.exe -s -o NUL -w '%{http_code}' --max-time 5 $Url 2>$null
    if ($LASTEXITCODE -ne 0) {
        return '000'
    }
    return $result.Trim()
}

function Wait-ForHttpStatus {
    param(
        [string]$Url,
        [string]$ExpectedStatus,
        [int]$TimeoutSeconds,
        [string]$ServiceName
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $status = Get-HttpStatus $Url
        if ($status -eq $ExpectedStatus) {
            return $true
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Write-Failure "$ServiceName did not become ready within $TimeoutSeconds seconds (last status: $status)."
    return $false
}

function Test-PortInUse {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-WorkerRunning {
    $workers = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like '*app.services.audio_worker*' }
    return [bool]$workers
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $escapedDirectory = $WorkingDirectory.Replace("'", "''")
    $childCommand = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location -LiteralPath '$escapedDirectory'; `$env:LOG_LEVEL = 'DEBUG'; $Command"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($childCommand))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encodedCommand) | Out-Null
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
    throw 'Dify is not running and no local deployment was found. Set DIFY_DIR to its root directory, which must contain docker\\docker-compose.yml or docker\\docker-compose.yaml.'
}

try {
    Write-Status "Project directory: $ProjectRoot"

    foreach ($command in @('uv', 'node', 'npm', 'docker', 'curl.exe')) {
        if (-not (Test-Command $command)) {
            throw "Required command was not found: $command. Install the dependency and try again."
        }
    }

    if ($Install) {
        Write-Status 'Installing/syncing backend dependencies...'
        Push-Location $BackendDir
        try { & uv sync } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

        Write-Status 'Installing frontend dependencies...'
        Push-Location $FrontendDir
        try { & npm install } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }

    $difyStatus = Get-HttpStatus 'http://localhost/install'
    if ($difyStatus -ne '200') {
        $DifyDir = Get-DifyDirectory
        Write-Status "Dify directory: $DifyDir"
        Write-Status 'Dify is not ready; starting Docker Compose...'
        Push-Location (Join-Path $DifyDir 'docker')
        try { & docker compose up -d } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw 'Dify Docker Compose failed to start. Confirm that Docker Desktop is running.' }
        if (-not (Wait-ForHttpStatus 'http://localhost/install' '200' 90 'Dify')) { exit 1 }
    } else {
        Write-Status 'Dify is already running; reusing it.'
    }

    $backendStatus = Get-HttpStatus 'http://localhost:8000/api/health'
    if ($backendStatus -eq '200') {
        # /api/health is intentionally stable and is not enough to distinguish an
        # older checkout of this project from the current backend.
        $artifactsStatus = Get-HttpStatus 'http://localhost:8000/api/artifacts'
        if ($artifactsStatus -eq '200') {
            Write-Status 'Backend is already running and matches the current API; reusing it.'
        } else {
            throw "An older or incompatible backend is running on port 8000: /api/health returned 200, but /api/artifacts returned $artifactsStatus. Stop the existing backend process, then run this script again."
        }
    } elseif (Test-PortInUse 8000) {
        throw 'Port 8000 is occupied but /api/health did not return 200; startup stopped to avoid affecting another service.'
    } else {
        if (-not (Test-Path -LiteralPath $BackendPython)) {
            throw 'Backend virtual environment was not found. Run .\start.ps1 -Install first.'
        }
        Write-Status 'Starting backend window...'
        Start-ServiceWindow 'Meditation Backend' $BackendDir '.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000'
        if (-not (Wait-ForHttpStatus 'http://localhost:8000/api/health' '200' 30 'Backend')) { exit 1 }
    }

    if (Test-WorkerRunning) {
        Write-Status 'Audio Worker is already running; reusing it.'
    } else {
        if (-not (Test-Path -LiteralPath $BackendPython)) {
            throw 'Backend virtual environment was not found. Run .\start.ps1 -Install first.'
        }
        Write-Status 'Starting Audio Worker window...'
        Start-ServiceWindow 'Meditation Audio Worker' $BackendDir '.\.venv\Scripts\python.exe -m app.services.audio_worker'
        Start-Sleep -Seconds 2
        if (-not (Test-WorkerRunning)) { throw 'Audio Worker did not start. Check its window output.' }
    }

    $frontendStatus = Get-HttpStatus 'http://localhost:5173/'
    if ($frontendStatus -eq '200') {
        Write-Status 'Frontend is already running; reusing it.'
    } elseif (Test-PortInUse 5173) {
        throw 'Port 5173 is occupied but the home page did not return 200; startup stopped to avoid affecting another service.'
    } else {
        Write-Status 'Starting frontend window...'
        Start-ServiceWindow 'Meditation Frontend' $FrontendDir 'npm run dev -- --port 5173 --strictPort'
        if (-not (Wait-ForHttpStatus 'http://localhost:5173/' '200' 30 'Frontend')) { exit 1 }
    }

    Write-Host ''
    Write-Host 'All services are ready:' -ForegroundColor Green
    Write-Host '  Frontend: http://localhost:5173'
    Write-Host '  Backend:  http://localhost:8000/api/health'
    Write-Host '  Dify：http://localhost/install'
} catch {
    Write-Failure $_.Exception.Message
    exit 1
}
