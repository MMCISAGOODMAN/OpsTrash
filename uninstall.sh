#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"

echo "Removing launcher scripts from $BIN_DIR"
[ -f "$BIN_DIR/undo" ] && rm -f "$BIN_DIR/undo"
[ -f "$BIN_DIR/trash-put" ] && rm -f "$BIN_DIR/trash-put"

echo "Uninstall complete. Note: user data in ~/.ops_trash remains and must be removed manually if desired."

