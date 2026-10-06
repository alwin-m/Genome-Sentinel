param(
    [string]$Version = "1.1.0"
)

$ErrorActionPreference = "Stop"

python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean --onedir --name "GenomeSentinel-$Version" server.py

Write-Host "Build completed. Package the dist/GenomeSentinel-$Version directory with your preferred Windows installer tool."
