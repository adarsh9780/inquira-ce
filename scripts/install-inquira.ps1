param(
  [switch]$Local,
  [string]$InstallDir
)

# Install-once script: creates an `inquira` shim that runs via uv.
# Default: adds to user PATH; with -Local or -InstallDir, writes shim to the chosen folder only.

$ErrorActionPreference = 'Stop'

$DefaultWheel = 'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a3/inquira_ce-0.5.7a3-py3-none-any.whl'
$WheelUrl = if ($env:INQUIRA_WHEEL_URL) { $env:INQUIRA_WHEEL_URL } else { $DefaultWheel }

Write-Host 'Installing uv (if needed)...'
if (-not (Get-Command uv -ErrorAction SilentlyContinue) -and -not (Get-Command uvx -ErrorAction SilentlyContinue)) {
  irm https://astral.sh/uv/install.ps1 | iex
}

# Ensure uv on PATH for current session (common locations)
$CargoBin = Join-Path $HOME '.cargo\bin'
$LocalBin = Join-Path $HOME '.local\bin'
foreach ($p in @($CargoBin, $LocalBin)) {
  if (Test-Path $p) {
    if (-not (($env:PATH -split ';') -contains $p)) {
      $env:PATH = "$p;$env:PATH"
}
}

# Show version being installed (best-effort from wheel filename)
$m = [regex]::Match($WheelUrl, 'inquira_ce-([^-]+)-')
$ver = if ($m.Success) { $m.Groups[1].Value } else { 'unknown' }
Write-Host "Installing Inquira shim for version $ver"
}

# Target bin dir for shims
if ($Local -or $InstallDir) {
  if ($InstallDir) { $BinDir = $InstallDir } else { $BinDir = (Get-Location).Path }
} else {
  $BinDir = Join-Path $HOME '.local\bin'
}
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# Create a .cmd shim so it runs from cmd.exe, PowerShell, or Run dialog
$CmdPath = Join-Path $BinDir 'inquira.cmd'
$CmdContent = @'
@echo off
setlocal
REM Ensure uv available (PowerShell installer)
where uv >nul 2>nul || powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
if "%INQUIRA_WHEEL_URL%"=="" set "INQUIRA_WHEEL_URL=https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a3/inquira_ce-0.5.7a3-py3-none-any.whl"
for %%f in ("%INQUIRA_WHEEL_URL%") do set "_WHEEL_FILE=%%~nxf"
for /f "tokens=2 delims=-" %%v in ("%_WHEEL_FILE%") do set "_INQ_VER=%%v"
echo Inquira: launching version %_INQ_VER%
uv -p 3.12 x --from "%INQUIRA_WHEEL_URL%" inquira %*
'@
$CmdContent = $CmdContent -replace 'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a3/inquira_ce-0.5.7a3-py3-none-any.whl', [Regex]::Escape($WheelUrl)
Set-Content -Path $CmdPath -Value $CmdContent -Encoding ASCII

if (-not $Local -and -not $InstallDir) {
  # Persist user PATH entries: shim dir and common uv bins
  $UserPath = [Environment]::GetEnvironmentVariable('Path','User')
  foreach ($p in @($BinDir, $LocalBin, $CargoBin)) {
    if (-not ($UserPath -split ';' | Where-Object { $_ -eq $p })) {
      $UserPath = ($UserPath + ';' + $p).Trim(';')
    }
  }
  [Environment]::SetEnvironmentVariable('Path', $UserPath, 'User')
  # Update current session PATH too
  foreach ($p in @($BinDir, $LocalBin, $CargoBin)) {
    if (-not (($env:PATH -split ';') -contains $p)) { $env:PATH = "$p;$env:PATH" }
  }
  Write-Host "Ensured $BinDir, $LocalBin and $CargoBin on your user PATH."
  Write-Host 'Install complete. Open a new terminal and run: inquira'
} else {
  Write-Host "Local install complete. Run using: .\\inquira.cmd (in $BinDir)"
}
Write-Host 'To override the wheel URL, set INQUIRA_WHEEL_URL before running.'
