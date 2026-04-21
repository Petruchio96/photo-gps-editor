#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
PYINSTALLER_APP_DIR="$DIST_DIR/Photo GPS Editor"
APPDIR="$PROJECT_ROOT/build/appimage/PhotoGPSEditor.AppDir"
APPIMAGE_OUTPUT="$DIST_DIR/Photo_GPS_Editor-x86_64.AppImage"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"

if [[ ! -x "$PYINSTALLER_APP_DIR/Photo GPS Editor" ]]; then
    echo "Missing PyInstaller app at: $PYINSTALLER_APP_DIR" >&2
    echo "Build it first with: .venv/bin/python -m PyInstaller photo_gps_editor.spec --noconfirm" >&2
    exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/128x128/apps"

cp -a "$PYINSTALLER_APP_DIR" "$APPDIR/usr/bin/Photo GPS Editor"
cp "$PROJECT_ROOT/assets/app_icon_128.png" "$APPDIR/photo-gps-editor.png"
cp "$PROJECT_ROOT/assets/app_icon_128.png" "$APPDIR/usr/share/icons/hicolor/128x128/apps/photo-gps-editor.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APPDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$APPDIR/usr/bin/Photo GPS Editor/Photo GPS Editor" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/Photo GPS Editor.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Photo GPS Editor
Comment=View, copy, apply, and clear GPS metadata in photo files
Exec=Photo GPS Editor
Icon=photo-gps-editor
Categories=Graphics;Photography;
Terminal=false
EOF
cp "$APPDIR/Photo GPS Editor.desktop" "$APPDIR/usr/share/applications/photo-gps-editor.desktop"

"$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_OUTPUT"
chmod +x "$APPIMAGE_OUTPUT"

echo "Built AppImage: $APPIMAGE_OUTPUT"
