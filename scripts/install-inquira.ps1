# Install-once script: creates an `inquira` shim on PATH that runs via uv.
# No system Python required.

$ErrorActionPreference = 'Stop'

$DefaultWheel = 'https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.2-alpha/inquira_ce-0.4.2-py3-none-any.whl'
$WheelUrl = if ($env:INQUIRA_WHEEL_URL) { $env:INQUIRA_WHEEL_URL } else { $DefaultWheel }

Write-Host 'Installing uv (if needed)...'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  irm https://astral.sh/uv/install.ps1 | iex
}

# Ensure uv on PATH for current session
$CargoBin = Join-Path $HOME '.cargo\bin'
if (-not (($env:PATH -split ';') -contains $CargoBin)) {
  $env:PATH = "$CargoBin;$env:PATH"
}

# Target bin dir for user-local shims
$BinDir = Join-Path $HOME '.local\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# Create a .cmd shim so it runs from cmd.exe, PowerShell, or Run dialog
$CmdPath = Join-Path $BinDir 'inquira.cmd'
$CmdContent = @'
@echo off
setlocal
REM Ensure uv available (PowerShell installer)
where uv >nul 2>nul || powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
if "%INQUIRA_WHEEL_URL%"=="" set "INQUIRA_WHEEL_URL=__DEFAULT_WHEEL__"
uvx -p 3.12 --from "%INQUIRA_WHEEL_URL%" inquira %*
'@
$CmdContent = $CmdContent -replace '__DEFAULT_WHEEL__', [Regex]::Escape($WheelUrl)
Set-Content -Path $CmdPath -Value $CmdContent -Encoding ASCII

# Persist the bin dir on the user PATH
$UserPath = [Environment]::GetEnvironmentVariable('Path','User')
if (-not ($UserPath -split ';' | Where-Object { $_ -eq $BinDir })) {
  [Environment]::SetEnvironmentVariable('Path', ($UserPath + ';' + $BinDir).Trim(';'), 'User')
  # Update current session PATH too
  $env:PATH = "$env:PATH;$BinDir"
  Write-Host "Added $BinDir to your user PATH."
}

Write-Host 'Install complete. Open a new terminal and run: inquira'
Write-Host 'To override the wheel URL, set INQUIRA_WHEEL_URL before running.'

