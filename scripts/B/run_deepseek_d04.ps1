param([Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunId)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$keyPath = Join-Path $projectRoot 'tmp/deepseek-key.dpapi'
if (-not (Test-Path -LiteralPath $keyPath)) { throw 'Encrypted key missing. Run scripts/B/set_deepseek_key.ps1 in your terminal first.' }
$encrypted = (Get-Content -Raw -LiteralPath $keyPath).Trim()
$secret = ConvertTo-SecureString -String $encrypted
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
$priorKey = $env:DEEPSEEK_API_KEY
try {
    $env:DEEPSEEK_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $env:PYTHONUTF8 = '1'
    Push-Location $projectRoot
    try {
        & (Join-Path $projectRoot '.venv/Scripts/python.exe') scripts/B/run_d04.py --config configs/B/D04_deepseek_authorized.json --run-id $RunId
        $runExit = $LASTEXITCODE
    } finally { Pop-Location }
} finally {
    $env:DEEPSEEK_API_KEY = $priorKey
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
exit $runExit
