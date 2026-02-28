#!/bin/bash
# Builds installer_app.py into a macOS .app and wraps it in a .dmg.
# Requirements: uv (for pyinstaller), create-dmg (optional, for .dmg)
#
# Usage: ./build_installer.sh

set -e

APP_NAME="ChatGPT History for Claude"
SCRIPT="installer_app.py"
DIST_DIR="dist"

echo "→ Installing PyInstaller…"
uv tool install pyinstaller

echo "→ Building .app…"
uvx pyinstaller \
  --windowed \
  --onefile \
  --name "$APP_NAME" \
  --distpath "$DIST_DIR" \
  "$SCRIPT"

echo "→ App built at: $DIST_DIR/$APP_NAME.app"

# Optional: wrap in a .dmg (requires: brew install create-dmg)
if command -v create-dmg &>/dev/null; then
  echo "→ Creating .dmg…"
  create-dmg \
    --volname "$APP_NAME" \
    --window-size 540 380 \
    --icon-size 128 \
    --app-drop-link 380 200 \
    --icon "$APP_NAME.app" 160 200 \
    "$DIST_DIR/$APP_NAME.dmg" \
    "$DIST_DIR/$APP_NAME.app"
  echo "→ DMG built at: $DIST_DIR/$APP_NAME.dmg"
else
  echo "ℹ  Skipping .dmg (install create-dmg with: brew install create-dmg)"
fi

echo "✅ Done."
