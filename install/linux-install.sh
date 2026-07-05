#!/usr/bin/env bash
# =====================================================================
#  Slicer Profile Converter - install a desktop launcher (Linux)
#
#  HOW TO USE:
#   1. Put this script in the SAME folder as SlicerProfileConverter-linux
#   2. Run:  bash linux-install.sh
#   3. The app appears in your applications menu and on your desktop.
# =====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXE="$SCRIPT_DIR/SlicerProfileConverter-linux"

if [ ! -f "$EXE" ]; then
    echo "Could not find SlicerProfileConverter-linux next to this script."
    echo "Keep this script in the same folder as the executable and retry."
    exit 1
fi

chmod +x "$EXE"

# Install the icon (if bundled alongside).
ICON_SRC="$SCRIPT_DIR/icon.png"
ICON_DEST="$HOME/.local/share/icons/slicer-profile-converter.png"
mkdir -p "$(dirname "$ICON_DEST")"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DEST"
fi

DESKTOP_FILE_CONTENT="[Desktop Entry]
Type=Application
Name=Slicer Profile Converter
Comment=Convert 3D printing slicer profiles between Bambu Studio, OrcaSlicer and Snapmaker Orca
Exec=$EXE
Icon=$ICON_DEST
Terminal=false
Categories=Utility;Graphics;
"

# Applications menu entry.
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
echo "$DESKTOP_FILE_CONTENT" > "$APPS_DIR/slicer-profile-converter.desktop"
chmod +x "$APPS_DIR/slicer-profile-converter.desktop"

# Desktop shortcut.
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_FILE_CONTENT" > "$DESKTOP_DIR/slicer-profile-converter.desktop"
    chmod +x "$DESKTOP_DIR/slicer-profile-converter.desktop"
fi

echo "Done! 'Slicer Profile Converter' is now in your applications menu"
echo "and on your desktop."
