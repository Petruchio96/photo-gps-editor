# Windows Build Steps

These steps start after booting into Windows.

## 1. Install Required Tools

Install these first if they are not already installed:

- Python 3.12 from https://www.python.org/downloads/
- Git for Windows from https://git-scm.com/download/win

During Python installation, enable:

```text
Add python.exe to PATH
```

After installing, open PowerShell and verify:

```powershell
py -3.12 --version
git --version
```

## 2. Get The Project

Choose a folder where you keep programming projects. This example uses:

```powershell
mkdir "$HOME\Documents\Programming"
cd "$HOME\Documents\Programming"
```

Clone the repository:

```powershell
git clone https://github.com/Petruchio96/photo-gps-editor.git
cd photo-gps-editor
git checkout release-packaging
```

If the repository already exists on Windows, use this instead:

```powershell
cd "$HOME\Documents\Programming\photo-gps-editor"
git fetch
git checkout release-packaging
git pull
```

## 3. Create The Python Environment

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install PyInstaller
```

## 4. Add Windows ExifTool

Download Windows ExifTool from:

```text
https://exiftool.org/
```

The downloaded executable is usually named something like:

```text
exiftool(-k).exe
```

Rename it to:

```text
exiftool.exe
```

Create the tools folder if needed:

```powershell
mkdir tools\windows -Force
```

Move or copy `exiftool.exe` into:

```text
tools\windows\exiftool.exe
```

Verify it runs:

```powershell
.\tools\windows\exiftool.exe -ver
```

## 5. Run Tests

From the repository root:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests
```

The expected result is:

```text
OK
```

## 6. Build The Windows App

From the repository root:

```powershell
.\.venv\Scripts\python -m PyInstaller photo_gps_editor.spec --noconfirm
```

The expected executable is:

```text
dist\Photo GPS Editor\Photo GPS Editor.exe
```

## 7. Launch The Built App

From the repository root:

```powershell
& "dist\Photo GPS Editor\Photo GPS Editor.exe"
```

If Windows SmartScreen warns about the app, choose the option to run anyway for
local testing. The app is not code-signed yet.

## 8. Manual Smoke Test

Use copied test photos, not original photos.

Check:

- App opens.
- Choose Photos opens the file picker.
- JPG files load.
- A GPS-tagged photo shows a GPS badge.
- A no-GPS photo appears in the no-GPS group.
- Manual coordinates apply to a copied photo.
- GPS from a source photo applies to another copied photo.
- Clear GPS works on a copied GPS-tagged photo.
- Undo and redo work before closing the app.
- After closing and reopening the app, metadata changes are still present.

## 9. Test On Another Windows Machine

Copy this whole folder to another Windows machine:

```text
dist\Photo GPS Editor
```

Run:

```text
Photo GPS Editor.exe
```

Confirm it works on a machine without Python and without ExifTool installed.

## 10. Create The Windows Release Zip

After testing succeeds, create the zip:

```powershell
Compress-Archive -Path "dist\Photo GPS Editor" -DestinationPath "dist\photo-gps-editor-windows-x86_64.zip" -Force
```

The release zip will be:

```text
dist\photo-gps-editor-windows-x86_64.zip
```

## 11. Files To Upload For Release Later

The likely release files are:

```text
Photo_GPS_Editor-x86_64.AppImage
photo-gps-editor-windows-x86_64.zip
```

The Linux tarball is optional because the AppImage is more user-friendly:

```text
photo-gps-editor-linux-x86_64.tar.gz
```
