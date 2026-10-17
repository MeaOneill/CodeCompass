$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$targetDir = Join-Path $projectRoot 'tmp'
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
$secret = Read-Host 'Paste NEW DeepSeek API key (hidden; press Enter)' -AsSecureString
if ($secret.Length -lt 16) { throw 'Key is empty or too short; nothing saved.' }
# Windows DPAPI: encrypted for this Windows user, never plaintext on disk.
$secret | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $targetDir 'deepseek-key.dpapi') -Encoding ascii
Write-Output 'KEY_SAVED_ENCRYPTED. No API call was made. Return to the chat and say: saved.'
