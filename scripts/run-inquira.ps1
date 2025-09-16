# Inquira CE bootstrap via uv (PowerShell)
# - Installs uv if missing
# - Ensures uv on PATH
# - Runs the CLI entrypoint `inquira` from package `inquira-ce`

$ErrorActionPreference = 'Stop'

# Install uv if missing (uv or uvx)
if (-not (Get-Command uv -ErrorAction SilentlyContinue) -and -not (Get-Command uvx -ErrorAction SilentlyContinue)) {
  Write-Host "Installing uv..."
  irm https://astral.sh/uv/install.ps1 | iex
}

# Ensure uv on PATH for current session (common locations)
$CargoBin = Join-Path $HOME ".cargo\bin"
$LocalBin = Join-Path $HOME ".local\bin"
foreach ($p in @($CargoBin, $LocalBin)) {
  if (Test-Path $p) {
    if (-not (($env:PATH -split ';') -contains $p)) {
      $env:PATH = "$p;$env:PATH"
    }
  }
}

# Resolve uv command (prefer uvx, fallback to 'uv x')
$useUvX = $false
if (Get-Command uvx -ErrorAction SilentlyContinue) { $useUvX = $true }
elseif (Get-Command uv -ErrorAction SilentlyContinue) { $useUvX = $false }
else {
  # Final fallback: search common bins for uv.exe
  $UvExe = $null
  foreach ($p in @($CargoBin, $LocalBin)) {
    $candidate = Join-Path $p "uv.exe"
    if (Test-Path $candidate) { $UvExe = $candidate; break }
  }
  if ($null -ne $UvExe) {
    $env:PATH = "$(Split-Path $UvExe);$env:PATH"
  } else {
    throw "uv not found after installation; open a new terminal and try again."
  }
}

# Run from a released wheel (faster, reproducible)
# Allow override via INQUIRA_WHEEL_URL env var if needed
$DefaultWheel = 'https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.4a0/inquira_ce-0.4.4a0-py3-none-any.whl'
$WheelUrl = if ($env:INQUIRA_WHEEL_URL) { $env:INQUIRA_WHEEL_URL } else { $DefaultWheel }

# Show version being launched (best-effort from wheel filename)
$m = [regex]::Match($WheelUrl, 'inquira_ce-([^-]+)-')
$ver = if ($m.Success) { $m.Groups[1].Value } else { 'unknown' }
Write-Host "Inquira: launching version $ver"
if ($useUvX) {
  uvx -p 3.12 --from $WheelUrl inquira @args
} else {
  uv -p 3.12 x --from $WheelUrl inquira @args
}
