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
# Allow override via INQUIRA_WHEEL_URL env var if needed
WHEEL_URL="${INQUIRA_WHEEL_URL:-https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.3-alpha/inquira_ce-0.4.3-py3-none-any.whl}"
exec uvx -p 3.12 --from "$WHEEL_URL" inquira "$@"
