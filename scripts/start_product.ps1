param([ValidateRange(1024,65535)][int]$Port=8789, [switch]$Offline)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')
$runtimePython=Join-Path (Get-Location).Path '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $runtimePython)) {
    $check = 'import sys; sys.exit(0 if sys.version_info[:2]==(3,12) and sys.maxsize > 2**32 else 1)'
    $created = $false
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c $check
        if ($LASTEXITCODE -eq 0) {
            & python -m venv .venv
            $created = $LASTEXITCODE -eq 0
        }
    }
    if (-not $created -and (Get-Command py -ErrorAction SilentlyContinue)) {
        & py -3.12 -c $check
        if ($LASTEXITCODE -eq 0) {
            & py -3.12 -m venv .venv
            $created = $LASTEXITCODE -eq 0
        }
    }
    if (-not $created) { throw 'Install 64-bit Python 3.12 and reopen the launcher' }
}
if (-not (Test-Path -LiteralPath '.venv/package-deps.ok')) {
    & $runtimePython -m pip --disable-pip-version-check install --no-index --find-links dependencies --require-hashes -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the included dependencies' }
    New-Item -ItemType File -Path '.venv/package-deps.ok' -Force | Out-Null
}
$env:PYTHONUTF8='1'
if ($Offline) { $env:DEEPSEEK_API_KEY=$null }
& $runtimePython scripts/serve_product.py --port $Port
exit $LASTEXITCODE
