#Requires -Version 5.1
<#
.SYNOPSIS
    Hidden Opportunities Agent -- one-command launcher.

.DESCRIPTION
    Starts the full React + FastAPI stack:
      1. Validates Python venv; installs requirements.txt if needed.
      2. Validates Node / npm; runs npm install if needed.
      3. Loads .env (copies .env.example if missing).
      4. Seeds the SQLite database if it is absent or empty.
      5. Opens two named console windows:
           [HOA] FastAPI :8000  - uvicorn backend (hot-reload)
           [HOA] Vite UI :5173  - React dev server (HMR, /api -> :8000)
      6. Waits for both services, then opens http://localhost:5173.

    No Docker, PostgreSQL, Redis, or Celery required.
    All data lives in data/db/opportunities.db (SQLite).

.PARAMETER NoSeed
    Skip the database seed check.
    Use when the DB already has data and you just want to restart services.

.PARAMETER SkipInstall
    Skip pip-install and npm-install checks.
    Fastest restart when no new packages have been added.

.PARAMETER ForceSeed
    Re-run seed_db.py even if the database already has data.
    Useful to reset to a clean synthetic dataset.

.EXAMPLE
    .\demo.ps1                              # full start
    .\demo.ps1 -NoSeed                      # restart, keep existing data
    .\demo.ps1 -NoSeed -SkipInstall         # fastest restart
    .\demo.ps1 -ForceSeed                   # wipe and re-seed DB, then start
#>

param(
    [switch]$NoSeed      = $false,
    [switch]$SkipInstall = $false,
    [switch]$ForceSeed   = $false
)

$RepoRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $RepoRoot

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step { param([string]$Msg)
    Write-Host ""
    Write-Host "  >>  $Msg" -ForegroundColor Cyan
}
function Write-Ok   { param([string]$Msg) Write-Host "  OK  $Msg" -ForegroundColor Green  }
function Write-Warn { param([string]$Msg) Write-Host "  !!  $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "  XX  $Msg" -ForegroundColor Red    }

function Exit-Script {
    param([string]$Reason)
    Write-Fail $Reason
    Read-Host "`n  Press Enter to exit"
    exit 1
}

function Wait-Http {
    param([string]$Url, [string]$Label, [int]$MaxAttempts = 40)
    Write-Host "      waiting for $Label ..." -ForegroundColor DarkGray
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -lt 500) { return $true }
        } catch { }
        Write-Host "      attempt $i / $MaxAttempts ..." -ForegroundColor DarkGray
        Start-Sleep 3
    }
    return $false
}

function Open-Window {
    param([string]$Title, [string]$WorkDir, [string]$Cmd)
    # Write command to a temp .ps1 file -- avoids PowerShell quoting edge cases
    $tmp = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.ps1'
    $lines = @(
        "`$host.UI.RawUI.WindowTitle = '$Title'",
        $Cmd
    )
    [System.IO.File]::WriteAllLines($tmp, $lines, [System.Text.Encoding]::UTF8)
    Start-Process powershell -WorkingDirectory $WorkDir `
        -ArgumentList @('-NoProfile', '-NoExit', '-File', $tmp)
}

# ── Banner ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host "     Hidden Opportunities Agent  --  Demo Launcher            " -ForegroundColor Cyan
Write-Host "     FastAPI . SQLite . React . Vite                          " -ForegroundColor DarkCyan
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host ""

# ── 1. Python virtual environment ─────────────────────────────────────────────

Write-Step "Checking Python virtual environment"

$VenvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPy)) {
    Write-Warn ".venv not found -- creating virtual environment..."

    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Exit-Script "Failed to create .venv. Is Python 3.11+ available on PATH?"
    }

    Write-Host "      Installing requirements.txt (first run -- may take 2-3 min)..." -ForegroundColor DarkGray
    & $VenvPy -m pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Exit-Script "pip install failed. Check requirements.txt and network access." }
    Write-Ok ".venv created and dependencies installed"

} elseif ($SkipInstall) {
    $pyVer = (& $VenvPy --version).ToString().Trim()
    Write-Ok "$pyVer (.venv) -- install check skipped (-SkipInstall)"

} else {
    $pyVer = (& $VenvPy --version).ToString().Trim()

    # Quick probe -- only run pip if a key package (fastapi) is missing.
    # Assign to $null so any ErrorRecord (stderr wrapped by PS) is silently discarded.
    $null = & $VenvPy -c "import fastapi" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "fastapi not found in .venv -- running pip install..."
        & $VenvPy -m pip install --quiet -r requirements.txt
        if ($LASTEXITCODE -ne 0) { Exit-Script "pip install failed." }
        Write-Ok "Dependencies installed"
    } else {
        Write-Ok "$pyVer (.venv)"
    }
}

# ── 2. Node / npm + frontend packages ─────────────────────────────────────────

Write-Step "Checking Node / npm"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Exit-Script "Node.js not found. Install the LTS release from https://nodejs.org and retry."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Exit-Script "npm not found. Reinstall Node.js and retry."
}

$nodeVer = (node --version).ToString().Trim()
$npmVer  = (npm  --version).ToString().Trim()
Write-Ok "Node $nodeVer  /  npm $npmVer"

$FrontendDir = Join-Path $RepoRoot "frontend"
$NodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $FrontendDir)) {
    Exit-Script "frontend/ directory not found. Run the React migration steps first."
}

if (-not (Test-Path $NodeModules)) {
    Write-Warn "node_modules missing -- running npm install in frontend/..."
    Push-Location $FrontendDir
    npm install --silent
    $ec = $LASTEXITCODE
    Pop-Location
    if ($ec -ne 0) { Exit-Script "npm install failed. Check frontend/package.json and network access." }
    Write-Ok "npm install complete"
} elseif ($SkipInstall) {
    Write-Ok "node_modules present -- install check skipped (-SkipInstall)"
} else {
    Write-Ok "node_modules present"
}

# ── 3. .env ───────────────────────────────────────────────────────────────────

Write-Step "Preparing .env"

$EnvFile     = Join-Path $RepoRoot ".env"
$ExampleFile = Join-Path $RepoRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $ExampleFile) {
        Copy-Item $ExampleFile $EnvFile
        Write-Warn ".env missing -- copied from .env.example (review API keys before use)"
    } else {
        @"
DEMO_MODE=true
LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
"@ | Set-Content $EnvFile -Encoding UTF8
        Write-Warn ".env.example not found -- created minimal .env with DEMO_MODE=true"
    }
}

# Parse .env into a hashtable and export every key into this process
$rawLines = Get-Content $EnvFile
$envMap   = @{}
foreach ($line in $rawLines) {
    $t = $line.Trim()
    if ((-not $t) -or $t.StartsWith('#')) { continue }
    if ($t -match '^([^=]+)=(.*)$') {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim()
        # Strip surrounding quotes if present
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or
            ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        $envMap[$k] = $v
    }
}
foreach ($kv in $envMap.GetEnumerator()) {
    [System.Environment]::SetEnvironmentVariable($kv.Key, $kv.Value, 'Process')
}
Write-Ok ".env loaded ($($envMap.Count) variables)"

# LLM API key status
$hasAnthropic = $envMap.ContainsKey('ANTHROPIC_API_KEY') -and
                -not [string]::IsNullOrWhiteSpace($envMap['ANTHROPIC_API_KEY']) -and
                $envMap['ANTHROPIC_API_KEY'] -notmatch '^sk-ant-\.\.\.'
$hasOpenAI    = $envMap.ContainsKey('OPENAI_API_KEY') -and
                -not [string]::IsNullOrWhiteSpace($envMap['OPENAI_API_KEY']) -and
                $envMap['OPENAI_API_KEY'] -notmatch '^sk-\.\.\.'

if ($hasAnthropic) {
    Write-Ok "ANTHROPIC_API_KEY configured -- LLM proposals active"
} elseif ($hasOpenAI) {
    Write-Ok "OPENAI_API_KEY configured -- LLM proposals active"
} else {
    Write-Warn "No LLM API key set -- proposals will use deterministic template fallback"
    Write-Host "      Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env for AI-generated proposals." -ForegroundColor DarkGray
}

# ── 4. SQLite database seed ───────────────────────────────────────────────────

$DbPath = Join-Path $RepoRoot "data\db\opportunities.db"

if ($ForceSeed -or (-not $NoSeed)) {
    Write-Step "Checking SQLite database"

    # Write a temp probe script -- avoids PowerShell/Python quoting issues
    $probePy = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.py'
    @"
import sys, os
sys.path.insert(0, os.path.normpath(r'REPO_ROOT'))
try:
    from src.db.schema import get_connection
    conn = get_connection()
    n = conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
    conn.close()
    print(n)
except Exception:
    print(0)
"@.Replace('REPO_ROOT', $RepoRoot) | Set-Content $probePy -Encoding UTF8

    $clientCount = 0
    try {
        # No 2>&1 -- the probe catches all exceptions and prints a number to stdout only
        $raw = & $VenvPy $probePy
        $clientCount = [int](($raw | Select-Object -Last 1).ToString().Trim())
    } catch { $clientCount = 0 }
    Remove-Item $probePy -Force -ErrorAction SilentlyContinue

    $needSeed = $ForceSeed -or (-not (Test-Path $DbPath)) -or ($clientCount -eq 0)

    if (-not $needSeed) {
        Write-Ok "Database has $clientCount client(s) -- skipping seed"
    } else {
        if ($ForceSeed) {
            Write-Warn "Force-seeding: re-creating synthetic dataset..."
        } elseif (-not (Test-Path $DbPath)) {
            Write-Warn "Database not found -- seeding with synthetic data..."
        } else {
            Write-Warn "Database is empty -- seeding with synthetic data..."
        }

        Write-Host "      Running scripts/seed_db.py (~75 synthetic clients)..." -ForegroundColor DarkGray
        & $VenvPy scripts\seed_db.py
        $seedEc = $LASTEXITCODE

        if ($seedEc -ne 0) {
            Write-Warn "seed_db.py returned non-zero -- database may be partially seeded."
            Write-Host "      Run manually: python scripts/seed_db.py" -ForegroundColor DarkGray
        } else {
            Write-Ok "Database seeded"
        }
    }
} else {
    Write-Warn "Database seed check skipped (-NoSeed)"
}

# ── 5. FastAPI backend on :8000 ───────────────────────────────────────────────

Write-Step "Starting FastAPI backend on :8000"

# Run uvicorn as a Python module so the venv interpreter is used explicitly.
# --reload-dir limits file-watching to backend/ and src/ only.
$apiCmd = "& '$VenvPy' -m uvicorn backend.main:app " +
          "--host 0.0.0.0 --port 8000 --reload " +
          "--reload-dir backend --reload-dir src"

Open-Window "[HOA] FastAPI :8000" $RepoRoot $apiCmd

$apiUp = Wait-Http "http://localhost:8000/api/health" "FastAPI :8000" 40
if ($apiUp) {
    Write-Ok "FastAPI is up  ->  http://localhost:8000"
    Write-Host "      Swagger docs  ->  http://localhost:8000/docs" -ForegroundColor DarkGray
} else {
    Write-Warn "FastAPI health check timed out. Check the [HOA] FastAPI window for errors."
    Write-Host "      Common cause: a missing Python package. Run: pip install -r requirements.txt" -ForegroundColor DarkGray
}

# ── 6. Vite dev server on :5173 ───────────────────────────────────────────────

Write-Step "Starting Vite dev server on :5173"

Open-Window "[HOA] Vite UI :5173" $FrontendDir "npm run dev"

$uiUp = Wait-Http "http://localhost:5173" "Vite :5173" 30
if ($uiUp) {
    Write-Ok "Frontend is up  ->  http://localhost:5173"
} else {
    Write-Warn "Vite health check timed out. Check the [HOA] Vite UI window for errors."
}

# ── 7. Open browser + summary ─────────────────────────────────────────────────

if ($apiUp -or $uiUp) {
    Start-Process "http://localhost:5173"
}

$llmStatus = if ($hasAnthropic) { "Anthropic (active)" }
             elseif ($hasOpenAI) { "OpenAI (active)" }
             else                { "Template fallback -- add API key to .env" }
$llmColor  = if ($hasAnthropic -or $hasOpenAI) { "Green" } else { "Yellow" }

$div = "  " + ("=" * 62)
Write-Host ""
Write-Host $div -ForegroundColor DarkCyan
Write-Host "  Service              URL / Location                         " -ForegroundColor White
Write-Host $div -ForegroundColor DarkCyan
Write-Host "  React frontend       http://localhost:5173                  " -ForegroundColor Green
Write-Host "  FastAPI backend      http://localhost:8000                  " -ForegroundColor Green
Write-Host "  API docs (Swagger)   http://localhost:8000/docs             " -ForegroundColor Cyan
Write-Host "  API docs (Redoc)     http://localhost:8000/redoc            " -ForegroundColor Cyan
Write-Host "  SQLite database      data/db/opportunities.db               " -ForegroundColor DarkGray
Write-Host $div -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  LLM provider         $llmStatus" -ForegroundColor $llmColor
Write-Host ""
Write-Host "  Console windows" -ForegroundColor White
Write-Host "  [HOA] FastAPI :8000  uvicorn backend.main:app --reload     " -ForegroundColor Gray
Write-Host "  [HOA] Vite UI :5173  Vite dev server with HMR              " -ForegroundColor Gray
Write-Host ""
Write-Host "  Useful commands" -ForegroundColor White
Write-Host "  Re-seed database     python scripts/seed_db.py             " -ForegroundColor Gray
Write-Host "  Run daily job        python scripts/daily_job.py           " -ForegroundColor Gray
Write-Host "  Train ML model       python scripts/train_model.py         " -ForegroundColor Gray
Write-Host "  Process NLP signals  python scripts/process_text.py        " -ForegroundColor Gray
Write-Host "  Fast restart         .\demo.ps1 -NoSeed -SkipInstall       " -ForegroundColor Gray
Write-Host "  Reset data           .\demo.ps1 -ForceSeed                 " -ForegroundColor Gray
Write-Host $div -ForegroundColor DarkCyan
Write-Host ""
