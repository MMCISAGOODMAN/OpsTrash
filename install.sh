#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYBIN=$(which python3 || which python)

echo "Installing Ops Trash..."

# create dirs
mkdir -p "$HOME/.ops_trash/files"

# copy package to user's home directory? We'll rely on running from repo for now.
# create default config
CONFIG_FILE="$HOME/.ops_trash/config.json"
METADATA_FILE="$HOME/.ops_trash/metadata.json"
LOG_FILE="$HOME/.ops_trash/operations.log"

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<EOF
{
  "max_retention_days": 7,
  "max_size_gb": 10,
  "web_port": 8080,
  "web_host": "0.0.0.0",
  "auto_clean": true,
  "log_enabled": true
}
EOF
  echo "Created config: $CONFIG_FILE"
fi

if [ ! -f "$METADATA_FILE" ]; then
  cat > "$METADATA_FILE" <<EOF
{"files": [], "counter": 0}
EOF
  echo "Created metadata: $METADATA_FILE"
fi

if [ ! -f "$LOG_FILE" ]; then
  touch "$LOG_FILE"
fi

# install launcher scripts
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

# copy undo launcher
cat > "$BIN_DIR/undo" <<EOF
#!/usr/bin/env bash
"$PYBIN" "$ROOT_DIR/undo" "\$@"
EOF
chmod +x "$BIN_DIR/undo"

cat > "$BIN_DIR/trash-put" <<EOF
#!/usr/bin/env bash
"$PYBIN" "$ROOT_DIR/undo" trash-put "\$@"
EOF
chmod +x "$BIN_DIR/trash-put"

echo "Installed launcher scripts to $BIN_DIR (make sure it's in your PATH)"

echo "To enable rm interception, add to your shell rc file (e.g. ~/.bashrc or ~/.zshrc):"
cat <<'ALIASES'
# Ops Trash aliases
alias rm='trash-put'
alias undo='undo'
ALIASES

echo "Installation complete."

