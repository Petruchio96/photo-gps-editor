# Photo GPS Editor - Project Context

## Snapshot

Last updated: 2026-04-18
Version: 1.1
Status: Version 1 desktop app with GPS read/write workflows, grouped thumbnails, GPS badges, undo/redo for GPS edits, and expanded automated tests.

Repository: https://github.com/Petruchio96/photo-gps-editor

## Goal

Desktop application for viewing and editing GPS metadata in photo files.

Key objectives:
- Select one or many photos using a standard file dialog
- Display thumbnails in a grid
- View and copy GPS metadata
- Apply GPS metadata from a source photo or manual coordinates
- Clear GPS metadata from selected photos
- Support JPG and selected RAW formats: CR2, CR3, DNG
- Run on Linux Mint and Windows 11

## Architecture

### Core

- `core/models.py`: shared data models such as `PhotoInfo` and `GpsCoordinates`
- `core/coordinates.py`: latitude/longitude validation
- `core/file_types.py`: supported extension checks
- `core/exiftool_wrapper.py`: ExifTool read/write/clear integration
- `core/photo_loader.py`: converts paths into `PhotoInfo`
- `core/thumbnail_loader.py`: thumbnail generation, fallback icons, GPS badge overlay, and icon caching

### Services

- Reusable workflow logic outside the PySide frontend
- Handles source resolution, target-file rules, session refresh, overwrite detection, coordinate parsing, and GPS apply orchestration
- Intended to remain reusable for possible future desktop, API, web, or container workflows

### Desktop GUI

- `gui/main_window.py`: shell window, menus, shared UI state, undo/redo memory
- `gui/widgets/`: layout construction for browser/editor panels
- `gui/presenters/`: UI-facing view-state builders
- `gui/window_mixins/`: focused behavior for photo list, source/editor actions, and apply workflow

## Current UI

### Left Browser Pane

- Loads photos with `Choose Photos`
- Shows thumbnails in a responsive grid
- Groups photos without GPS first, then photos with GPS under `Photos with GPS Coordinates`
- Sorts by filename within each GPS group
- Shows GPS badges on thumbnails that already have GPS
- Supports select all, clear selection, and removing loaded photos
- `Remove All Photos` changes to `Remove Selected Photos` only for partial selections
- Right-click can copy GPS coordinates from a GPS-tagged thumbnail

### Right GPS Editor Pane

- Source modes:
- `Use Source Photo`
- `Enter Coordinates Manually`

- Source photo workflow:
- Source photo is independent from the destination photo list
- Preview card shows thumbnail, filename, and GPS status
- Source photos without GPS cannot be applied
- `Clear Source` is enabled only when a source photo is selected

- Manual coordinate workflow:
- Latitude/longitude fields support decimal degrees, DMS, and DDM
- Paste button accepts valid clipboard coordinates and auto-splits latitude/longitude
- Field-level validation shows invalid state and tooltips
- Placeholder examples use generic coordinates

- Destination batch workflow:
- Right-side list is the batch to modify
- `Remove All Photos` changes to `Remove Selected Photos` only for partial selections
- `Clear Coordinates from Photos` is enabled only when at least one batch photo has GPS
- `Apply New GPS Coordinates to Photos` writes to the full right-side batch list
- Apply and clear actions reset the right-side batch list after completion

### Menus

- File:
- `Choose Photos...`
- `Remove Photos`
- `Exit` with standard OS shortcut

- Edit:
- `Undo` with standard OS shortcut
- `Redo` with standard OS shortcut
- `Copy`
- `Paste`

- Help:
- `About` includes the GitHub repository link

## GPS Edit Undo / Redo

- Single-step in-memory undo/redo for GPS write actions
- Applies to:
- `Apply New GPS Coordinates to Photos`
- `Clear Coordinates from Photos`
- Stores prior GPS state for each successfully changed photo
- Restores prior coordinates or blank/no-GPS state on undo
- Redo reapplies the undone GPS action
- Undo/redo memory is replaced by the next apply/clear action
- Undo/redo memory is cleared when new photos are loaded with `Choose Photos`
- Memory is not written to disk and is cleared on program exit

## Known Issue

- Portrait orientation in the OS/Qt file picker may still appear sideways.
- Main app thumbnails already display portrait orientation correctly.
- This is likely controlled by the native file dialog and is not currently urgent.

## Future Ideas

- Add drag-and-drop support for loading photos
- Add optional backup behavior before writing metadata
- Explore a future API/web/container layer on top of the reusable `services/` backend

## Development Notes

- Use the project virtual environment when running the app or tests
- Run the app with `.venv/bin/python app.py`
- Run tests with `.venv/bin/python -m unittest discover -s tests`
- GUI uses PySide6
- Metadata reading/writing uses ExifTool
- Thumbnail/icon processing uses Qt and Pillow
- Current coverage includes backend helpers, GUI presenters, workflow services, and main-window smoke tests
