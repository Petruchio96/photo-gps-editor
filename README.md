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

Packaged executable downloads will be added here after release builds are tested.

Planned first release formats:

- Windows: a zipped one-folder app containing `Photo GPS Editor.exe`
- Linux: a PyInstaller one-folder app first, then an AppImage once the folder
  build is proven

For now, run the project from source using the local development instructions above.
