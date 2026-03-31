# Photo GPS Editor - Project Context

## Version / Snapshot
Last updated: 2026-03-30
Status: Functional GUI with GPS workflow complete (thumbnails, tooltip, context menu, GPS badge, copy/paste/apply workflow, validation, UI feedback improvements)

## Repository
GitHub repo: https://github.com/Petruchio96/photo-gps-editor

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
  - Writes GPS metadata to files

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
  - multiple selection → disables current GPS display and shows "(Multiple selection)"
- Input fields:
  - Latitude
  - Longitude
- Buttons:
  - Copy Current GPS (single selection only)
  - Paste Coordinates (splits clipboard into both fields)
  - Apply to Selected (working)

- Status messaging:
  - Single-line status field replaces previous notes area
  - Displays success, error, and guidance messages

- Validation UX:
  - Field-level validation for latitude and longitude
  - Invalid fields highlighted with red border and background
  - Tooltip shown on invalid fields with valid range guidance
  - Error styling clears automatically when user corrects input and changes focus

- Input improvements:
  - Placeholder examples for coordinate format
  - Paste workflow provides immediate feedback

- Workflow clarity:
  - Copy Current GPS remains in Selection section (acts on selected file)
  - Paste Coordinates remains in Edit section (acts on input fields)

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
- Apply workflow:
  - validates coordinates
  - writes GPS to selected files
  - refreshes UI afterward

---

## GPS Copy Design

- Right-click context menu on thumbnail
- Option: "Copy GPS Coordinates"
- Right panel copy button for single selection
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

- GPS writing workflow
  - IMPLEMENTED and working for single and multi-file selection

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

1. Continue right-side panel polish (visual styling and spacing)
2. Improve GPS badge visual design (contrast / clarity)
3. Investigate file picker orientation behavior

### UI Enhancements

4. Improve thumbnail layout spacing and styling
5. Improve status / success / error presentation in the right panel

### UI Direction (Important)

- Prioritize functionality and workflow correctness first
- Defer visual polish until core features are stable
- Future goal:
  - Make UI look and feel like a professional desktop application
  - Improve styling, spacing, and visual hierarchy

### Editing Functionality

6. Add validation feedback in UI (completed, may refine)
7. Consider adding backup option before writing metadata
8. Consider clear / remove GPS workflow

### Advanced Features

9. Add "Clear GPS" option
10. Add detail panel enhancements
11. Add drag-and-drop support for loading photos

---

## Development Notes

- Always restart Python when modifying modules (no auto-reload)
- Virtual environment must be active before running app
- GUI uses PySide6
- Image processing uses Pillow
- Metadata reading and writing use ExifTool

---

## Summary

The application now has:

- Working backend for GPS reading
- Working backend for GPS writing
- Structured data model
- Functional GUI with thumbnails and selection logic
- Clean separation between UI and backend
- Hover tooltip for GPS inspection
- Right-click GPS copy functionality
- GPS badge overlay support
- Copy/Paste coordinate workflow
- Apply-to-selected workflow
- Field-level validation with visual feedback
- Status messaging system in right panel
- Correct portrait orientation in main thumbnail grid

Next phase focuses on:
- continued right panel polish
- visual improvements (badge + layout)
- progressing toward a professional-quality UI