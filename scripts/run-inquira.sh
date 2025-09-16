#!/usr/bin/env bash
set -euo pipefail

# Inquira CE bootstrap via uv
# - Installs uv if missing
# - Ensures uv on PATH
# - Runs the CLI entrypoint `inquira` from package `inquira-ce`

# Install uv if missing
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

# Ensure uv on PATH (default installer location)
export PATH="$HOME/.cargo/bin:$PATH"

# Run from a released wheel (faster, reproducible)
# Pinned by default; override with INQUIRA_WHEEL_URL
WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.4a1/inquira_ce-0.4.4a1-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

# Show version being launched (best-effort from wheel filename)
WHEEL_FILE="${WHEEL_URL##*/}"
INQUIRA_VERSION="${WHEEL_FILE#inquira_ce-}"
INQUIRA_VERSION="${INQUIRA_VERSION%%-*}"
echo "Inquira: launching version ${INQUIRA_VERSION:-unknown}"

exec uvx -p 3.12 --from "$WHEEL_URL" inquira "$@"
