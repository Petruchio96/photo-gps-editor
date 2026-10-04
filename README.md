This project was written almost entirely by AI, with human direction, testing, and design feedback throughout.

# Photo GPS Editor

Photo GPS Editor is a desktop application for viewing, copying, applying, and clearing GPS metadata in photo files. It is designed for workflows where you have photos without coordinates and want to copy GPS data from another photo or enter coordinates manually.

The app supports JPG thumbnails, selected RAW formats, grouped browsing of photos with and without GPS data, GPS badges on already-tagged photos, overwrite warnings, and single-step undo/redo for GPS edits made during the current session.

## What It Does

- Load one or many photos into a thumbnail browser.
- Show which photos already have GPS coordinates.
- Copy GPS coordinates from an existing photo.
- Use a source photo or manually entered coordinates as the GPS source.
- Apply GPS coordinates to a batch of selected photos.
- Clear GPS coordinates from photos that already have them.
- Undo or redo the most recent GPS apply/clear action while the app is open.
- Optionally keep a backup copy of each original file (Edit > Keep Backup Copies of Originals).

## Local Development Instructions

Requirements:

- Python 3
- ExifTool
- Project dependencies from `requirements.txt`

Set up and run:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Download and Use

Download the latest version from the
[Releases page](https://github.com/Petruchio96/photo-gps-editor/releases/latest).
ExifTool is included, so nothing else needs to be installed.

### Linux

`Photo_GPS_Editor-x86_64.AppImage` is a single file. Make it executable and run it:

```bash
chmod +x Photo_GPS_Editor-x86_64.AppImage
./Photo_GPS_Editor-x86_64.AppImage
```

You can also double-click it in your file manager after making it executable.
If you see a FUSE error, run it with `APPIMAGE_EXTRACT_AND_RUN=1` in front of
the command, or install your distribution's FUSE package.

`photo-gps-editor-linux-x86_64.tar.gz` contains the same app as a folder.
Extract it and run `Photo GPS Editor` inside the folder.

The Linux build uses the system Perl to run ExifTool. Perl is installed by
default on most Linux distributions.

### Windows and macOS

Packaged downloads for Windows and macOS are planned for a later release.
For now, run the project from source using the local development instructions
above, with ExifTool installed.
