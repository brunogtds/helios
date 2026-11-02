$ErrorActionPreference = 'Stop'
$taskContext = Join-Path ([System.IO.Path]::GetTempPath()) ('helios-eda-build-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $taskContext | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Dockerfile.eda') -Destination $taskContext
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'eda_python_worker.py') -Destination $taskContext
& docker build -f (Join-Path $taskContext 'Dockerfile.eda') -t helios-eda-python:1 $taskContext
if ($LASTEXITCODE -ne 0) { throw 'Docker image build failed. Ensure Docker Desktop is running.' }
Write-Host 'Python EDA image is ready.'
