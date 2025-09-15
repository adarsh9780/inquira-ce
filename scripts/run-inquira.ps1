# Inquira CE bootstrap via uv (PowerShell)
# - Installs uv if missing
# - Ensures uv on PATH
# - Runs the CLI entrypoint `inquira` from package `inquira-ce`

$ErrorActionPreference = 'Stop'

# Install uv if missing
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "Installing uv..."
  irm https://astral.sh/uv/install.ps1 | iex
}

# Ensure uv on PATH for current session if needed
$CargoBin = Join-Path $HOME ".cargo\bin"
if (-not (($env:PATH -split ';') -contains $CargoBin)) {
  $env:PATH = "$CargoBin;$env:PATH"
}

# Run from a released wheel (faster, reproducible)
# Allow override via INQUIRA_WHEEL_URL env var if needed
$WheelUrl = if ($env:INQUIRA_WHEEL_URL) { $env:INQUIRA_WHEEL_URL } else { 'https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.3-alpha/inquira_ce-0.4.2-py3-none-any.whl' }
uvx -p 3.12 --from $WheelUrl inquira @args
