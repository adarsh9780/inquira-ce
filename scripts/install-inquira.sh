#!/usr/bin/env bash
set -euo pipefail

# Install-once script: creates an `inquira` shim on PATH that runs via uv.
# No system Python required.

WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.5a1/inquira_ce-0.4.5a1-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

# Show version being installed (best-effort from wheel filename)
WHEEL_FILE="${WHEEL_URL##*/}"
INQUIRA_VERSION="${WHEEL_FILE#inquira_ce-}"
INQUIRA_VERSION="${INQUIRA_VERSION%%-*}"
echo "Installing Inquira shim for version ${INQUIRA_VERSION:-unknown}"

echo "Installing uv (if needed)..."
if ! command -v uv >/dev/null 2>&1; then
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

# Ensure uv on PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Parse flags: --local (install shim to current directory), or INQUIRA_INSTALL_DIR
BIN_DIR_DEFAULT="$HOME/.local/bin"
BIN_DIR="${INQUIRA_INSTALL_DIR:-}"
if [ -z "${BIN_DIR}" ]; then
  if [ "${1:-}" = "--local" ]; then
    BIN_DIR="$PWD"
    shift || true
  else
    BIN_DIR="$BIN_DIR_DEFAULT"
  fi
fi

mkdir -p "$BIN_DIR"

WRAPPER="$BIN_DIR/inquira"
echo "Installing shim: $WRAPPER"
cat > "$WRAPPER" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Ensure uv available
if ! command -v uv >/dev/null 2>&1; then
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.cargo/bin:$PATH"

# Allow override at runtime (no auto-latest)
WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.5a1/inquira_ce-0.4.5a1-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

# Show version being launched (best-effort from wheel filename)
WHEEL_FILE="${WHEEL_URL##*/}"
INQUIRA_VERSION="${WHEEL_FILE#inquira_ce-}"
INQUIRA_VERSION="${INQUIRA_VERSION%%-*}"
echo "Inquira: launching version ${INQUIRA_VERSION:-unknown}"

exec uvx -p 3.12 --from "$WHEEL_URL" inquira "$@"
EOF

chmod +x "$WRAPPER"

if [ "$BIN_DIR" = "$BIN_DIR_DEFAULT" ]; then
  # Add to PATH for future shells if missing
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;; # already present
    *)
      echo "Adding $BIN_DIR to your PATH in common profiles..."
      for profile in "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc"; do
        [ -f "$profile" ] || touch "$profile"
        if ! grep -qs "$BIN_DIR" "$profile"; then
          printf '\nexport PATH="$HOME/.local/bin:\$PATH"\n' >> "$profile"
        fi
      done
      ;;
  esac
  echo "Install complete. Open a new terminal and run: inquira"
else
  echo "Local install complete. Run using: ./inquira (in $BIN_DIR)"
fi

echo "To override the wheel URL, set INQUIRA_WHEEL_URL before running."
