# Photo GPS Editor - Project Context

## Version / Snapshot
Last updated: 2026-04-11
Version: 1.0
Status: Version 1 desktop application with separated source/destination workflow, reusable backend workflow/services layer, desktop presentation layer, overwrite confirmation, and expanded automated test coverage

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

### Desktop Frontend Structure

- `gui/main_window.py`
  - Acts as the desktop shell window
  - Focuses on Qt setup, shared window concerns, and wiring frontend pieces together

- `gui/widgets/`
  - Builds the left browser panel and right editor panel
  - Keeps layout construction separate from window workflow logic

- `gui/presenters/`
  - Holds desktop-only presentation helpers and view-state builders
  - Includes source preview, editor panel state, thumbnail presentation, and desktop-facing helper modules

- `gui/window_mixins/`
  - Splits large window behavior into focused desktop UI concerns
  - Separates source/editor actions, destination list actions, and apply workflow actions

### Reusable Backend / Application Structure

- `services/`
  - Holds reusable workflow logic outside the PySide frontend
  - Includes source resolution, destination rules, photo-loading/session helpers, workflow controller logic, and GPS apply orchestration
  - Intended to support future desktop, web/API, and container-based frontends

- `core/`
  - Holds lower-level domain and infrastructure logic such as models, file support, coordinate validation, ExifTool access, metadata loading, and thumbnail generation

---

## GUI Status

### Main Window

- Destination file selection button (multi-select supported)
- Thumbnail grid (QListWidget in IconMode)
- Source photo selection is now separate from destination photo selection
- JPG thumbnails display correctly
- RAW files use fallback icons
- Portrait images now display correctly (EXIF fix applied)
- GPS badge overlay shown on thumbnails with GPS metadata

### Right Panel (Detail / Edit Panel)

- Shows:
  - source mode selection
  - source preview
  - active coordinates to apply
  - selected destination files
- Behavior:
  - `Use Source Photo` opens a separate source-photo workflow
  - `Enter Coordinates Manually` allows typed or pasted coordinates
- Input fields:
  - Latitude
  - Longitude
- Buttons:
  - `Choose Source Photo...`
  - `Clear Source`
  - `Paste Coordinates`
  - `Apply GPS to Destination Files`

- Source photo workflow:
  - Source photo can be chosen independently of loaded destination files
  - Source preview shows thumbnail, filename, and GPS state
  - Source photo without GPS is surfaced clearly and cannot be applied

- Status messaging:
  - Single-line status card replaces previous notes area
  - Displays success, error, and guidance messages
  - Used for clipboard errors, source loading feedback, cancel flow, and apply results

- Validation UX:
  - Field-level validation for latitude and longitude
  - Invalid fields highlighted with red border and background
  - Tooltip shown on invalid fields with valid range guidance
  - Error styling clears automatically when user corrects input and changes focus

- Input improvements:
  - Placeholder examples for coordinate format
  - Paste workflow provides immediate feedback
  - Manual coordinate entry now accepts decimal degrees, Degrees Minutes Seconds, and Degrees Decimal Minutes

- Workflow clarity:
  - Left side is now destination-only workflow
  - Right side is now source/editor workflow
  - `Select Photos` button and loaded/selected badges now live above the left pane because they belong to the destination workspace

---

## UX Design Decisions (Confirmed)

### Layout

- Left: thumbnail grid
- Right: detail/edit panel

### Behavior

- Two-part workflow:
  - choose where GPS comes from
  - choose where GPS goes
- Source and destination selection are intentionally separate
- Destination grid is for files that receive GPS
- Right panel is for source selection, coordinate entry, and apply actions

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
- Source workflow:
  - separate source photo picker
  - source preview card with thumbnail, filename, and GPS status
- Copy/Paste workflow:
  - right-click copy from thumbnails
  - Paste button auto-splits coordinates
- Apply workflow:
  - validates coordinates
  - confirms before overwriting existing destination GPS
  - writes GPS to selected files
  - refreshes UI afterward

---

## Known Issues (Resolved)

- Portrait thumbnails displaying incorrectly
  - FIXED using EXIF orientation handling

- Coordinate paste usability
  - FIXED by adding Paste button and parsing logic

- DMS/DDM coordinate paste support
  - FIXED by accepting Degrees Minutes Seconds and Degrees Decimal Minutes in manual input and paste workflow

- GPS writing workflow
  - IMPLEMENTED and working for single and multi-file selection

- Overwrite confirmation before replacing existing GPS
  - IMPLEMENTED for destination files that already contain coordinates

- Invalid clipboard paste flow
  - FIXED with status-card error messaging instead of crashing

- Source and destination selection ambiguity
  - IMPROVED by separating source-photo selection from destination-photo selection

---

## Known Issues (Open)

- GPS badge overlay visibility
  - Current PNG overlay works functionally
  - Appears washed out and low-quality on some thumbnails
  - Next planned work item
  - Needs improved contrast or redesigned asset

- Portrait orientation in file picker dialog
  - Main app thumbnails display correctly
  - File selection dialog may show portrait images sideways
  - Likely controlled by OS/Qt file dialog, needs investigation

---

## Next Steps (Priority Order)

### Immediate

1. Redesign the thumbnail GPS indicator/badge so existing GPS data is clearly visible and looks polished
2. Investigate file picker orientation behavior
3. Continue UI polish and spacing refinements now that the workflow model is stable
4. Consider performance improvements for file loading and thumbnail generation
5. Explore a future API layer for web/container deployment built on the reusable `services/` backend

### UI Enhancements

### UI Direction (Important)

- Prioritize functionality and workflow correctness first
- Defer visual polish until core features are stable
- Future goal:
  - Make UI look and feel like a professional desktop application
  - Improve styling, spacing, and visual hierarchy

### Architecture Direction (Important)

- Version 1 now has a reusable backend-oriented services layer and a separate desktop presentation layer
- Keep workflow rules out of frontend-specific UI code whenever possible
- Treat the current PySide6 application as the desktop frontend
- Backend services can support:
  - desktop GUI
  - future web frontend
  - containerized / Docker deployment
- Backend currently owns or strongly centers:
  - photo loading
  - coordinate parsing and validation
  - source/destination workflow rules
  - overwrite detection
  - GPS write operations
  - workflow/session models
- Frontend currently owns:
  - file pickers
  - thumbnail presentation
  - forms, buttons, and dialogs
  - visual status display
  - layout and interaction flow

### Editing Functionality

8. Add backup option before writing metadata
9. Consider clear / remove GPS workflow

### Advanced Features

10. Add "Clear GPS" option
11. Add detail panel enhancements
12. Add drag-and-drop support for loading photos
13. Add Edit file menu with cut, copy, paste and other useful options

---

## Development Notes

- Always restart Python when modifying modules (no auto-reload)
- Virtual environment must be active before running app
- GUI uses PySide6
- Image processing uses Pillow
- Metadata reading and writing use ExifTool
- Run the app with the project virtual environment, not system Python, so PySide6 is available
- Current automated coverage now includes backend helpers, GUI presenters, workflow services, and main workflow smoke tests

---

## Summary

The application now has:

- Working backend for GPS reading
- Working backend for GPS writing
- Structured data model
- Functional GUI with separate source and destination workflow
- Modular GUI structure with window shell, widgets, presenters, and window mixins
- Separate source photo picker with preview card
- Overwrite confirmation before replacing existing GPS
- Reusable backend/application services separated from the desktop frontend
- Expanded automated test coverage across backend helpers, workflow services, presenters, and GUI workflow

Next phase focuses on:
- visual improvements (badge + layout)
- performance improvements for loading and thumbnail generation
- possible API layer for future web/container deployment
