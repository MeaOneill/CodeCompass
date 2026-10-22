param(
    [ValidateSet('human_manual','test_fixture')][string]$Actor = 'human_manual',
    [ValidateRange(1024,65535)][int]$Port = 8781
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install the official Python runtime before starting.' }
        & $pythonPath -m pip install --require-hashes -r scripts/B/requirements-d01-win-py312.hashes.txt
        if ($LASTEXITCODE -ne 0) { throw 'Locked dependency installation failed; existing files are preserved.' }
    }
    $env:PYTHONUTF8 = '1'
    $env:PYTHONPATH = 'src'
    $databasePath = if ($Actor -eq 'human_manual') { 'experiments/B/B-D07-human-guided-v4/state.sqlite3' } else { 'tmp/B-D07-user-guided-v4.sqlite3' }
    & $pythonPath scripts/B/serve_d07.py --port $Port --actor $Actor --database $databasePath
    exit $LASTEXITCODE
} finally { Pop-Location }
