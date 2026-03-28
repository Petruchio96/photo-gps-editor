# Photo GPS Editor - Project Context

## Version / Snapshot
Last updated: 2026-03-27
Status: Core backend + functional GUI (thumbnails, tooltip, context menu, GPS badge, copy/paste workflow)

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
  - Adds GPS badge overlay using a PNG asset

---

## GUI Status

### Main Window

- File selection button (multi-select supported)
- Thumbnail grid (QListWidget in IconMode)
- JPG thumbnails display correctly
- RAW files use fallback icons
- Portrait images now display correctly (EXIF fix applied)
- GPS badge overlay shown on thumbnails with GPS metadata

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
- Buttons:
  - Copy Current GPS (single selection only)
  - Paste Coordinates (splits clipboard into both fields)
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
- GPS data accessed via:
  - hover tooltip
  - right-click context menu
  - right-side panel

### Implemented Enhancements

- Hover tooltip:
  - shows GPS metadata
- Right-click context menu:
  - copy GPS coordinates
- GPS badge overlay:
  - shown on thumbnails with GPS data
- Copy/Paste workflow:
  - Copy button in right panel
  - Paste button auto-splits coordinates

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

- Coordinate paste usability
  - FIXED by adding Paste button and parsing logic

---

## Known Issues (Open)

- GPS badge overlay visibility
  - Current PNG overlay works functionally
  - Appears washed out on some thumbnails
  - Needs improved contrast or redesigned asset

- Portrait orientation in file picker dialog
  - Main app thumbnails display correctly
  - File selection dialog may show portrait images sideways
  - Likely controlled by OS/Qt file dialog, needs investigation

---

## Next Steps (Priority Order)

### Immediate

1. Clean up and improve right-side panel layout
2. Improve GPS badge visual design (contrast / clarity)
3. Investigate file picker orientation behavior

### UI Enhancements

4. Improve thumbnail layout spacing and styling

### Editing Functionality

5. Wire "Apply to Selected" button
6. Implement GPS write using ExifTool
7. Add validation feedback in UI

### Advanced Features

8. Add "Clear GPS" option
9. Add detail panel enhancements
10. Add drag-and-drop support for loading photos

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
- Hover tooltip for GPS inspection
- Right-click GPS copy functionality
- GPS badge overlay support
- Copy/Paste coordinate workflow
- Correct portrait orientation in main thumbnail grid

Next phase focuses on:
- right panel cleanup
- visual improvements (badge + layout)
- writing GPS metadata