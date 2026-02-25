#!/usr/bin/env bash
set -euo pipefail

# Install-once script: creates an `inquira` shim on PATH that runs via uv.
# No system Python required.

WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a5/inquira_ce-0.5.7a5-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

UPDATE=false
BIN_DIR_DEFAULT="$HOME/.local/bin"
BIN_DIR="${INQUIRA_INSTALL_DIR:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --update)
      UPDATE=true
      shift
      ;;
    --local)
      BIN_DIR="$PWD"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "${BIN_DIR}" ]; then
  BIN_DIR="$BIN_DIR_DEFAULT"
fi

WRAPPER="$BIN_DIR/inquira"
WRAPPER_ALREADY_PRESENT=false
if [ -f "$WRAPPER" ]; then
  WRAPPER_ALREADY_PRESENT=true
fi

if [ "$WRAPPER_ALREADY_PRESENT" = true ] && [ "$UPDATE" = false ]; then
  echo "Inquira shim already present at $WRAPPER"
  echo "Run with --update to refresh the shim."
  exit 0
fi

WHEEL_FILE="${WHEEL_URL##*/}"
INQUIRA_VERSION="${WHEEL_FILE#inquira_ce-}"
INQUIRA_VERSION="${INQUIRA_VERSION%%-*}"

if [ "$WRAPPER_ALREADY_PRESENT" = true ]; then
  echo "Updating Inquira shim for version ${INQUIRA_VERSION:-unknown}"
else
  echo "Installing Inquira shim for version ${INQUIRA_VERSION:-unknown}"
fi

echo "Installing uv (if needed)..."
if ! command -v uv >/dev/null 2>&1; then
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.cargo/bin:$PATH"

mkdir -p "$BIN_DIR"

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
WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a5/inquira_ce-0.5.7a5-py3-none-any.whl"
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
  if [ "$WRAPPER_ALREADY_PRESENT" = true ]; then
    echo "Update complete. Open a new terminal and run: inquira"
  else
    echo "Install complete. Open a new terminal and run: inquira"
  fi
else
  if [ "$WRAPPER_ALREADY_PRESENT" = true ]; then
    echo "Local update complete. Run using: ./inquira (in $BIN_DIR)"
  else
    echo "Local install complete. Run using: ./inquira (in $BIN_DIR)"
  fi
fi

echo "To override the wheel URL, set INQUIRA_WHEEL_URL before running."
