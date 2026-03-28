# Photo GPS Editor - Project Context

## Version / Snapshot
Last updated: 2026-03-27
Status: Core backend + initial GUI complete

---

## Project Goal

Desktop application for viewing and editing GPS metadata in photo files.

Key objectives:
- Select one or many photos using a standard file dialog
- Display thumbnails in a grid
- View GPS metadata
- Edit GPS metadata for single or multiple files
- Support JPG and selected RAW formats (CR2, CR3, DNG)
- Run on Linux Mint and Windows 11

---

## Current Architecture

### Core Modules

- `models.py`
  - Defines `PhotoInfo`, `GpsCoordinates`, `WriteResult`

- `coordinates.py`
  - Validates latitude and longitude ranges

- `file_types.py`
  - Determines supported file extensions (case-insensitive)

- `exiftool_wrapper.py`
  - Handles interaction with ExifTool
  - Reads GPS metadata using JSON output
  - Uses `-n` for numeric coordinate output

- `photo_loader.py`
  - Converts file paths into `PhotoInfo` objects
  - Handles missing GPS and errors cleanly

- `thumbnail_loader.py`
  - Generates thumbnails using Pillow
  - Applies EXIF orientation fix (`ImageOps.exif_transpose`)
  - Returns Qt icons for GUI display
  - Provides fallback icon for unsupported formats

---

## GUI Status

### Main Window

- File selection button (multi-select supported)
- Thumbnail grid (QListWidget in IconMode)
- JPG thumbnails display correctly
- RAW files use fallback icons
- Portrait images now display correctly (EXIF fix applied)

### Right Panel (Detail / Edit Panel)

- Shows:
  - number of selected files
  - current GPS for single selection
- Behavior:
  - single selection → shows GPS
  - multiple selection → disables GPS display and shows "(Multiple selection)"
- Input fields:
  - Latitude
  - Longitude
- Apply button (UI only, not yet wired)

---

## UX Design Decisions (Confirmed)

### Layout

- Left: thumbnail grid
- Right: detail/edit panel

### Behavior

- Selection-driven UI (no separate modes)
- Single selection:
  - shows current GPS
- Multi-selection:
  - disables current GPS display
  - allows batch editing

### Thumbnail Area

- Clean display:
  - thumbnail
  - filename
- No GPS text shown in grid (planned removal)

### Planned Enhancements

- Hover tooltip:
  - show GPS metadata
- Satellite icon:
  - shown on thumbnails with GPS data

---

## GPS Copy Design

- Right-click context menu on thumbnail
- Option: "Copy GPS Coordinates"
- Format:
  latitude, longitude (decimal format)

Example:
40.486325, -111.813415

---

## Known Issues (Resolved)

- Portrait thumbnails displaying incorrectly
  - FIXED using EXIF orientation handling

---

## Next Steps (Priority Order)

### Immediate

1. Remove GPS text from thumbnail labels
2. Add hover tooltip showing GPS metadata
3. Add right-click context menu:
   - Copy GPS Coordinates

### UI Enhancements

4. Add satellite icon overlay for photos with GPS
5. Improve thumbnail layout spacing and styling

### Editing Functionality

6. Wire "Apply to Selected" button
7. Implement GPS write using ExifTool
8. Add validation feedback in UI

### Advanced Features

9. Add paste handling for coordinate input
10. Add "Clear GPS" option
11. Add detail panel enhancements

---

## Development Notes

- Always restart Python when modifying modules (no auto-reload)
- Virtual environment must be active before running app
- GUI uses PySide6
- Image processing uses Pillow

---

## Summary

The application now has:

- Working backend for GPS reading
- Structured data model
- Functional GUI with thumbnails and selection logic
- Clean separation between UI and backend
- Initial UX design validated and implemented

Next phase focuses on:
- interaction (hover, right-click)
- visual indicators (icons)
- writing GPS metadata