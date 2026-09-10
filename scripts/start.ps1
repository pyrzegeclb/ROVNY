$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run the README setup commands first.' }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'frontend\dist\index.html'))) { throw 'Build the frontend first: cd frontend; npm run build' }
Push-Location (Join-Path $repoRoot 'backend')
try { & $pythonPath -m rovny } finally { Pop-Location }
