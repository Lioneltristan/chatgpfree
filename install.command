#!/bin/bash
# ChatGPT History for Claude — Installer
# Double-click to run. No typing required.

set -e

REPO="git+https://github.com/Lioneltristan/chatgpfree"
PACKAGE="chatgpt-history-mcp"
SERVER_NAME="ChatGPT history"
CLAUDE_DIR="$HOME/Library/Application Support/Claude"
HISTORY_DIR="$CLAUDE_DIR/chatgpt-history"
CONFIG_PATH="$CLAUDE_DIR/claude_desktop_config.json"

# ── Helper: native macOS dialog ───────────────────────────────────────────────
dialog() {
  osascript -e "display dialog \"$1\" buttons {\"$2\"} default button \"$2\" with title \"ChatGPT History for Claude\""
}

pick_file() {
  osascript -e "set f to choose file with prompt \"Select your ChatGPT export file (.zip or .json):\" of type {\"zip\", \"json\", \"public.zip-archive\", \"public.json\"}" \
            -e "POSIX path of f"
}

# ── Step 1: welcome ───────────────────────────────────────────────────────────
osascript -e 'display dialog "This will set up ChatGPT History for Claude.\n\nYou will be asked to select your ChatGPT export file, then everything is handled automatically." buttons {"Get Started"} default button "Get Started" with title "ChatGPT History for Claude"'

# ── Step 2: pick export file ──────────────────────────────────────────────────
echo "Waiting for file selection…"
EXPORT_PATH=$(pick_file 2>/dev/null) || {
  osascript -e 'display dialog "No file selected. Setup cancelled." buttons {"OK"} default button "OK" with title "ChatGPT History for Claude"'
  exit 0
}
echo "Selected: $EXPORT_PATH"

# ── Step 3: install uv if needed ─────────────────────────────────────────────
echo "Checking for uv…"
UVX=""
for candidate in \
  "$HOME/.local/bin/uvx" \
  "$HOME/.cargo/bin/uvx" \
  "/usr/local/bin/uvx" \
  "/opt/homebrew/bin/uvx"
do
  if [ -x "$candidate" ]; then
    UVX="$candidate"
    break
  fi
done

if [ -z "$UVX" ]; then
  UVX=$(which uvx 2>/dev/null || true)
fi

if [ -z "$UVX" ]; then
  echo "Installing uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Reload PATH
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  UVX=$(which uvx 2>/dev/null || true)
  if [ -z "$UVX" ]; then
    dialog "Installation failed: could not install uv.\n\nPlease restart your Mac and try again." "OK"
    exit 1
  fi
fi
echo "Found uvx: $UVX"

# ── Step 4: copy export to stable location ───────────────────────────────────
echo "Copying export file…"
mkdir -p "$HISTORY_DIR"
cp "$EXPORT_PATH" "$HISTORY_DIR/conversations.json"
STORED_PATH="$HISTORY_DIR/conversations.json"
echo "Saved to: $STORED_PATH"

# ── Step 5: write Claude Desktop config ──────────────────────────────────────
echo "Updating Claude Desktop config…"
mkdir -p "$CLAUDE_DIR"

# Merge into existing config with Python (ships with macOS)
# Pass values via environment variables so no bash interpolation happens inside Python source.
export _CGH_CONFIG_PATH="$CONFIG_PATH"
export _CGH_SERVER_NAME="$SERVER_NAME"
export _CGH_UVX="$UVX"
export _CGH_REPO="$REPO"
export _CGH_PACKAGE="$PACKAGE"
export _CGH_STORED_PATH="$STORED_PATH"
python3 - <<'PYEOF'
import json, os, pathlib

config_path = pathlib.Path(os.environ["_CGH_CONFIG_PATH"])
config = {}
if config_path.exists():
    try:
        config = json.loads(config_path.read_text())
    except Exception:
        pass

config.setdefault("mcpServers", {})[os.environ["_CGH_SERVER_NAME"]] = {
    "command": os.environ["_CGH_UVX"],
    "args": ["--from", os.environ["_CGH_REPO"], os.environ["_CGH_PACKAGE"], "--export-path", os.environ["_CGH_STORED_PATH"]],
}

config_path.write_text(json.dumps(config, indent=2))
print("Config written.")
PYEOF

# ── Step 6: relaunch Claude Desktop ──────────────────────────────────────────
echo "Relaunching Claude Desktop…"
osascript -e 'tell application "Claude" to quit' 2>/dev/null || true
sleep 2
open -a "Claude" 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────────────────────
osascript -e 'display dialog "All set! Claude Desktop is restarting.\n\nYou can now search your ChatGPT history directly from Claude." buttons {"Done"} default button "Done" with title "ChatGPT History for Claude"'

echo "Done."
