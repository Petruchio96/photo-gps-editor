# Photo GPS Editor - Project Context

## Version / Snapshot
Last updated: 2026-04-18
Version: 1.1
Status: Version 1 desktop application with separated source/selected-photo workflow, grouped thumbnail browser, GPS badge indicators, reusable backend workflow/services layer, and expanded automated test coverage

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
  - Generates JPG thumbnails with Qt `QImageReader` scaled decode for better performance
  - Returns Qt icons for GUI display
  - Provides fallback icon for unsupported formats
  - Adds cached GPS badge overlay using a PNG asset with white background treatment

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
  - Separates source/editor actions, photo-list actions, and apply workflow actions

### Reusable Backend / Application Structure

- `services/`
  - Holds reusable workflow logic outside the PySide frontend
  - Includes source resolution, target-file rules, photo-loading/session helpers, workflow controller logic, and GPS apply orchestration
  - Intended to support future desktop, web/API, and container-based frontends

- `core/`
  - Holds lower-level domain and infrastructure logic such as models, file support, coordinate validation, ExifTool access, metadata loading, and thumbnail generation

---

## GUI Status

### Main Window

- Photo selection button (multi-select supported)
- Thumbnail grid (QListWidget in IconMode)
- Source photo selection is now separate from the selected-photo list
- JPG thumbnails display correctly
- RAW files use fallback icons
- Portrait images now display correctly
- GPS badge overlay shown on thumbnails with GPS metadata
- Browser groups files without GPS first, then shows a divider row and `Photos with GPS Coordinates` before GPS-tagged files

### Right Panel (Detail / Edit Panel)

- Shows:
  - source mode selection
  - source preview
  - active coordinates to apply
  - selected files to update
- Behavior:
  - `Use Source Photo` opens a separate source-photo workflow
  - `Enter Coordinates Manually` allows typed or pasted coordinates
- Input fields:
  - Latitude
  - Longitude
- Buttons:
  - `Choose Source Photo`
  - `Clear Source`
  - `Paste Coordinates from Clipboard`
  - `Remove Selected Photos`
  - `Clear Coordinates from Photos`
  - `Apply New GPS Coordinates to Photos`

- Source photo workflow:
  - Source photo can be chosen independently of loaded photos
  - Source preview shows thumbnail, filename, and GPS state
  - Source photo without GPS is surfaced clearly and cannot be applied

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
  - Left side is now selected-photo workflow
  - Right side is now source/editor workflow
  - `Choose Photos` is the primary left-pane action for loading files to update
  - Right-side selected-photo list acts as the batch to modify
  - `Remove Selected Photos` removes highlighted entries, or clears the whole batch when nothing in that list is highlighted
  - `Clear Coordinates from Photos` is only active when at least one photo in the batch already has GPS data

---

## UX Design Decisions (Confirmed)

### Layout

- Left: thumbnail grid
- Right: detail/edit panel

### Behavior

- Two-part workflow:
  - choose where GPS comes from
  - choose where GPS goes
- Source selection and selected-photo list are intentionally separate
- The left grid is for files that receive GPS
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
- Grouped browser list:
  - files without GPS appear first
  - files with GPS appear after a divider/header row
  - each group is sorted by filename
- Source workflow:
  - separate source photo picker
  - source preview card with thumbnail, filename, and GPS status
- Copy/Paste workflow:
  - right-click copy from thumbnails
  - Paste button auto-splits coordinates
- Apply workflow:
  - validates coordinates
  - confirms before overwriting existing file GPS
  - writes GPS to the full right-side batch list
  - clears the right-side batch list after apply completes
  - refreshes UI afterward
- Clear GPS workflow:
  - clears GPS from the full right-side batch list when eligible
  - clears the right-side batch list after completion

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
  - IMPLEMENTED for selected files that already contain coordinates

- Source selection ambiguity
  - IMPROVED by separating source-photo selection from the selected-photo list

- Thumbnail loading performance
  - IMPROVED by switching JPG thumbnail decode to Qt `QImageReader` and caching generated icons

---

## Known Issues (Open)

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
4. Explore a future API layer for web/container deployment built on the reusable `services/` backend

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
  - source/selected-photo workflow rules
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

### Advanced Features

9. Add detail panel enhancements
10. Add drag-and-drop support for loading photos
11. Add Edit file menu with cut, copy, paste and other useful options

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
- Functional GUI with separate source and selected-photo workflow
- Grouped thumbnail browser that makes GPS-tagged photos easier to identify
- Modular GUI structure with window shell, widgets, presenters, and window mixins
- Separate source photo picker with preview card
- Overwrite confirmation before replacing existing GPS
- Clear-GPS workflow and batch-list reset after apply/clear operations
- Faster JPG thumbnail loading with cached badge/fallback handling
- Reusable backend/application services separated from the desktop frontend
- Expanded automated test coverage across backend helpers, workflow services, presenters, and GUI workflow

Next phase focuses on:
- remaining visual improvements
- possible API layer for future web/container deployment
