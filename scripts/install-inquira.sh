#!/usr/bin/env bash
set -euo pipefail

# Install-once script: creates an `inquira` shim on PATH that runs via uv.
# No system Python required.

WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.3-alpha/inquira_ce-0.4.3-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

echo "Installing uv (if needed)..."
if ! command -v uv >/dev/null 2>&1; then
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

# Ensure uv on PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Target bin dir for user-local shims
BIN_DIR="$HOME/.local/bin"
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

# Allow override at runtime
WHEEL_URL_DEFAULT="https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.2-alpha/inquira_ce-0.4.2-py3-none-any.whl"
WHEEL_URL="${INQUIRA_WHEEL_URL:-$WHEEL_URL_DEFAULT}"

exec uvx -p 3.12 --from "$WHEEL_URL" inquira "$@"
EOF

chmod +x "$WRAPPER"

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
echo "To override the wheel URL, set INQUIRA_WHEEL_URL before running."

