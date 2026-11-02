param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'helios_backup\helios\venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create a virtual environment and install requirements.txt first.' }
Write-Host "HELIOS EDA First: http://127.0.0.1:$Port"
& $taskPython -B -m uvicorn main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port
