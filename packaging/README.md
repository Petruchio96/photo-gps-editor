# Packaging Notes

The first release packaging target is a PyInstaller one-folder build. This is
easier to debug than a single-file executable and is the safest starting point
for a PySide6 desktop app.

## Linux

Build from the repository root:

```bash
.venv/bin/python -m pip install PyInstaller
.venv/bin/python -m PyInstaller photo_gps_editor.spec --noconfirm
tar -C dist -czf dist/photo-gps-editor-linux-x86_64.tar.gz 'Photo GPS Editor'
```

The Linux output is:

```text
dist/Photo GPS Editor/
  Photo GPS Editor
  _internal/
dist/photo-gps-editor-linux-x86_64.tar.gz
```

The PyInstaller spec bundles:

- `assets/`
- `/usr/bin/exiftool`
- ExifTool's Linux Perl support modules from `/usr/share/perl5/Image`
- ExifTool's `File::RandomAccess` module from `/usr/share/perl5/File`

This gives the app its own ExifTool copy while still relying on the system Perl
runtime, which is present by default on many Linux desktop installs.

## Windows

Build on Windows rather than cross-compiling from Linux.

1. Install Python 3.12.
2. Create and activate a virtual environment.
3. Install runtime dependencies and PyInstaller.
4. Put the Windows ExifTool executable at `tools/windows/exiftool.exe`.
5. Run:

```powershell
python -m PyInstaller photo_gps_editor.spec --noconfirm
```

The Windows output will be a one-folder app containing `Photo GPS Editor.exe`.
Zip that folder for the first Windows release.

## AppImage

An AppImage is the closest Linux equivalent to a downloadable Windows app. Build
it after the PyInstaller folder build launches and passes a manual smoke test:

```bash
packaging/build_appimage.sh
```

If `appimagetool` is not installed, download it and pass it explicitly:

```bash
APPIMAGETOOL=/tmp/appimagetool-x86_64.AppImage packaging/build_appimage.sh
```

The AppImage output is:

```text
dist/Photo_GPS_Editor-x86_64.AppImage
```

If a Linux system reports a FUSE error when running the AppImage, install or
enable FUSE for normal AppImage launching. For testing, this fallback avoids
FUSE by extracting first:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 dist/Photo_GPS_Editor-x86_64.AppImage
```
