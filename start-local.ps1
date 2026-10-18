$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython local_api.py
} elseif ($pythonCommand) {
    & $pythonCommand.Source local_api.py
} else {
    throw 'Python 3 and openpyxl are required. Then run python local_api.py.'
}
