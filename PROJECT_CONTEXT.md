# Photo GPS Editor - Project Context

## Snapshot

Last updated: 2026-10-04
Version: 1.1 released (Linux); 1.2 in progress on `main`
Status: Desktop app redesigned around the grid selection (inspector panel, Show filter, Copy from Photo on Left), with background loading, real RAW thumbnails, failure-tolerant writes, undo/redo, optional backups, and CI builds for Linux, Windows, and macOS.

Repository: https://github.com/Petruchio96/photo-gps-editor

## Goal

Desktop application for viewing and editing GPS metadata in photo files.

Key objectives:
- Select one or many photos using a standard file dialog
- Display thumbnails in a grid, including real thumbnails for RAW files
- View and copy GPS metadata
- Apply GPS metadata to the photos selected in the grid, from typed, pasted, or photo-sourced coordinates
- Clear GPS metadata from selected photos
- Support JPG and selected RAW formats: CR2, CR3, DNG
- Run on Linux Mint, Windows 11, and macOS (Apple Silicon)

## Architecture

### Core

- `core/models.py`: shared data models such as `PhotoInfo` and `GpsCoordinates`
- `core/coordinates.py`: latitude/longitude validation
- `core/file_types.py`: supported extension checks
- `core/exiftool_wrapper.py`: ExifTool read/write/clear integration through one long-running `-stay_open` process; reads embedded RAW previews (small thumbnails are captured during the bulk GPS read to avoid reopening files); optional `keep_backups`
- `core/process_guard.py`: starts helper processes (ExifTool) so they cannot outlive the app after a crash (shell watchdog on Linux/macOS, job object on Windows)
- `core/photo_loader.py`: converts paths into `PhotoInfo` using single-file and bulk metadata reads

### Services

- Reusable workflow logic outside the PySide frontend
- Handles source resolution, target-file rules, session refresh, overwrite detection, coordinate parsing, and GPS apply orchestration
- `services/workflow_facade.py`: single backend workflow entry point used by the desktop frontend
- `services/photo_metadata_cache.py`: backend-owned in-memory metadata cache for unchanged selected photos
- `services/gps_edit_history.py`: single-step undo/redo memory
- Apply, clear, and undo/redo attempt every file and report failures instead of stopping at the first one
- Intended to remain reusable for possible future desktop, API, web, or container workflows

### Desktop GUI

- `gui/main_window.py`: shell window, header bar, menus, status row messages, undo/redo actions
- `gui/background.py`: one background thread for loading GPS data and thumbnails; waits for the running job before the app exits
- `gui/thumbnail_loader.py`: thumbnail generation (JPEG and embedded RAW previews, cropped and rotated upright), fallback icons, GPS badge overlay, and icon caching
- `gui/widgets/`: browser panel (grid with click-to-add selection), inspector panel, loading indicator, thumbnail delegate (shimmer placeholders, SOURCE marker, "No GPS" dimming)
- `gui/presenters/`: UI-facing view-state builders; `inspector_state.py` holds the inspector logic with no Qt code
- `gui/window_mixins/`: focused behavior for the photo list, inspector, New Location / pick mode, and apply/remove workflows

## Current UI

The photos selected in the grid are the photos being edited. Color has one
meaning each: navy header, orange = selection and the Apply action, blue =
location source, green/amber = has/needs GPS.

### Left Photos Pane

- Loads photos with `Choose Photos` (GPS data and thumbnails load in the background; a progress row and shimmer placeholders appear only for slow loads)
- Newly loaded photos open on the `Needs GPS` filter (or `All` if none need GPS)
- `Show:` filter: `All`, `Needs GPS`, `Has GPS`, with counts
- Groups photos without GPS first, then photos with GPS, with colored headings
- Shows GPS badges on thumbnails that already have GPS
- Selection: click or Ctrl+click adds/removes a photo; Shift+click adds a range; dragging a box from empty space adds photos; empty clicks do nothing; Ctrl+A and `Select All` select the photos shown; arrow keys move focus without changing the selection; Space toggles
- `Remove All from List` changes to `Remove Selected from List` for partial selections (files are never deleted)
- Right-click: `Copy GPS Coordinates`, `Use This Location` (does not change the selection)
- Status row under the grid shows photo counts, action results with an `Undo` link, and errors

### Right Inspector Pane

- `Photos to Change`: selection title, preview (one large thumbnail or a row of small ones), current GPS summary, `Copy` for a single photo
- `New Location`: latitude/longitude fields (decimal, DMS, DDM; a pasted pair auto-splits), `Paste`, `Browse Photos`, `Clear`
- `Copy from Photo on Left` enters pick mode: the button becomes `Cancel`, a blue banner explains the mode, only photos with GPS can be picked (filter rules show them), and everything except the All/Has GPS filters, `Choose Photos`, and `Remove from List` is disabled; the selection is kept
- The location source shows on a blue card and as a blue `SOURCE` outline in the grid; editing the fields by hand drops it
- `Apply to N Photos` (orange); an amber note warns when existing GPS will be replaced; the confirmation offers `Skip Photos with GPS`, `Replace`, or `Cancel`
- `Remove GPS from N Photos` (red outline), with confirmation
- Pop-ups for a browsed photo with no GPS and for an unreadable photo

### Menus

- File:
- `Choose Photos...`
- `Remove Photos`
- `Exit` with standard OS shortcut

- Edit:
- `Undo` with standard OS shortcut
- `Redo` with standard OS shortcut
- `Select All Photos`
- `Copy GPS Coordinates`
- `Paste Coordinates`
- `Keep Backup Copies of Originals` (saved between sessions)

- Help:
- `About` includes the GitHub repository link

## GPS Edit Undo / Redo

- Single-step in-memory undo/redo for GPS write actions
- Applies to:
- `Apply to N Photos`
- `Remove GPS from N Photos`
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
- In the Linux (GTK) file picker, selecting folders together with files makes `Open` do nothing; this is the picker's behavior. A safety-net pop-up for pickers that return folders is planned.

## Future Ideas

- Add drag-and-drop support for loading photos
- Design a new GPS badge icon to replace the satellite icon
- Add a map view for seeing photo locations and picking a new one
- Explore a future API/web/container layer (Docker on a Synology NAS) on top of the reusable `services/` backend

## Development Notes

- Use the project virtual environment when running the app or tests
- Run the app with `.venv/bin/python app.py`
- Run tests with `.venv/bin/python -m unittest discover -s tests` (add `QT_QPA_PLATFORM=offscreen` to run without a display)
- GitHub Actions (`.github/workflows/build.yml`) runs the tests and builds Linux, Windows, and macOS apps on every push; pushing a `v*` tag attaches the builds to that release
- Pull requests are merged with GitHub's merge button (merge commit)
- GUI uses PySide6
- Metadata reading/writing uses ExifTool
- Thumbnail/icon processing uses Qt and Pillow
- Current coverage includes backend helpers, GUI presenters, workflow services, main-window behavior (real mouse/keyboard events), background loading, and process cleanup


## Completed Refactor Summary

Status: Completed on the `refactor-backend-split-and-performance` branch.

Purpose:
- Separate reusable backend logic from the PySide desktop frontend.
- Improve large photo selection performance, especially metadata loading for the left browser pane.
- Keep behavior stable while simplifying ownership and avoiding unnecessary framework or threading complexity.

Outcome:
- Desktop-specific rendering now lives in `gui/`.
- Shared backend code in `core/` and `services/` has no PySide6, Pillow, or GUI imports.
- The desktop GUI uses `PhotoWorkflowFacade` as its main backend workflow entry point.
- Metadata loading is faster through backend caching and bulk ExifTool reads.
- Manual testing showed large photo batches load at about half the previous time.
- Automated coverage increased to include backend boundary, cache, bulk read, facade, and restore workflow behavior.

Phase outcomes:
1. Moved thumbnail/icon rendering from `core` to `gui/thumbnail_loader.py`, preserving JPEG thumbnails, fallback icons, GPS badges, and icon caching.
2. Added `services/workflow_facade.py` and routed desktop load/source/apply/refresh workflows through `PhotoWorkflowFacade`.
3. Added `services/photo_metadata_cache.py` for backend-owned in-memory metadata caching keyed by path, modified time, and file size.
4. Added bulk GPS metadata reads with `ExifToolWrapper.read_gps_many()` and `PhotoLoader.load_photo_infos()`, while preserving unsupported-file handling and single-file fallback paths.
5. Moved undo/redo GPS restore execution behind `PhotoWorkflowFacade.restore_gps_states_workflow()`.
6. Reduced browser refresh overhead by separating session refresh, thumbnail item creation, and list rendering, and removed a duplicate refresh after clearing target coordinates.
7. Evaluated background loading and intentionally deferred it because caching/bulk reads already improved load time and thumbnail rendering still depends on Qt GUI objects.
8. Prepared backend reuse by documenting desktop-only dependencies as optional extras and adding tests that prevent `core`/`services` from importing PySide6, Pillow, or GUI modules.

Current verification:
- Full test suite passes with `.venv/bin/python -m unittest discover -s tests`.
- Desktop launch flow remains `.venv/bin/python app.py`.
- Future Docker/API work can reuse the shared backend layer but has not been implemented yet.
