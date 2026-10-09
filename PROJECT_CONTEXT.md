# Photo GPS Editor - Project Context

## Snapshot

Last updated: 2026-10-09
Version: 1.3 released (Linux, Windows, macOS); the app's own Add Photos picker merged to `main` for the next release
Status: Two-pane layout (Photo List and Photos to Change, with Location and Date & Time tabs), the app's own photo picker (folder tree, only photos), fast thumbnails (shared Linux thumbnail cache, embedded JPEG thumbnails), background loading, failure-tolerant writes, undo/redo that restores the photo list, optional backups, an error log, and CI builds for Linux, Windows, and macOS.

Repository: https://github.com/Petruchio96/photo-gps-editor

## Goal

Desktop application for viewing and editing GPS metadata in photo files.

Key objectives:
- Select one or many photos with the app's own picker (folder tree on the left, only photos on the right)
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
- `core/places.py`: the picker's places and folder listings (bookmarks from the Linux file manager, network share names, system mounts to skip, hidden files per system); no Qt
- `core/exiftool_wrapper.py`: ExifTool read/write/clear integration through one long-running `-stay_open` process; reads embedded RAW previews (small thumbnails are captured during the bulk GPS read to avoid reopening files); optional `keep_backups`
- `core/process_guard.py`: starts helper processes (ExifTool) so they cannot outlive the app after a crash (shell watchdog on Linux/macOS, job object on Windows)
- `core/photo_loader.py`: converts paths into `PhotoInfo` using single-file and bulk metadata reads

### Services

- Reusable workflow logic outside the PySide frontend
- Handles source resolution, target-file rules, session refresh, overwrite detection, coordinate parsing, and GPS apply orchestration
- `services/workflow_facade.py`: single backend workflow entry point used by the desktop frontend
- `services/photo_metadata_cache.py`: backend-owned in-memory metadata cache for unchanged selected photos
- `services/gps_edit_history.py`: single-step undo/redo memory, including a snapshot of the photo list and selection
- Apply, clear, and undo/redo attempt every file and report failures instead of stopping at the first one
- Intended to remain reusable for possible future desktop, API, web, or container workflows

### Desktop GUI

- `gui/main_window.py`: shell window, menus, status row messages, selection bar state, undo/redo actions
- `gui/background.py`: one background thread for loading GPS data and thumbnails; results go back to the GUI thread through a plain Python queue (a data-free signal only wakes the GUI thread; passing Python objects through queued signals crashed on Windows); waits for the running job before the app exits
- `gui/thumbnail_loader.py`: thumbnail generation, cheapest source first: the shared Linux thumbnail cache, embedded previews (RAW previews; the small EXIF thumbnail near the start of JPEGs), then the whole JPEG; cropped and rotated upright; fallback icons, GPS badge overlay, and icon caching
- `gui/system_thumbnails.py`: reads and writes the freedesktop.org thumbnail cache (`~/.cache/thumbnails`) shared with Nemo/Nautilus; PNG labels are read directly because Qt can't read `Thumb::MTime`
- `gui/error_log.py`: `error-log.txt` in the app's data folder (Windows: `%LOCALAPPDATA%\Photo GPS Editor\Photo GPS Editor`); unexpected errors (with a pop-up), Qt warnings/fatals, hard-crash call stacks (faulthandler), and low-level stderr in windowed builds
- `gui/gc_guard.py`: automatic garbage collection is off; a timer collects on the GUI thread between events
- `gui/widgets/`: browser panel (Photo List pane: header, Show filter, selection bar, grid with click-to-add selection), editor panel (Photos to Change pane with tabs), `photo_picker.py` (the Add Photos picker), loading indicator, thumbnail delegate (shimmer placeholders, SOURCE marker, "No GPS" dimming, faded deselected photos), `icons.py` (line icons drawn in code)
- `gui/presenters/`: UI-facing view-state builders; `inspector_state.py` holds the inspector logic with no Qt code
- `gui/window_mixins/`: focused behavior for the photo list, inspector, New Location / pick mode, and apply/remove workflows

## Current UI

The photos selected in the Photo List are the photos being edited. Color has
one meaning each: navy = Photo List, orange/brown = selection and the Apply
action, blue = location source, green/amber = has/needs GPS. The window title
is the OS title bar (no in-app title bar). Every button has a hover hint (a
test enforces this).

### Left: Photo List

- Navy `PHOTO LIST` header with `+ Add Photos` (opens the picker, below; adds to the list, skipping photos already in it; GPS data and thumbnails load in the background) and `Clear List` (files are never deleted)
- A list that was empty opens on `Needs GPS` (or `All` if none need GPS); adding to a list keeps the current view
- `Show` filter: `All`, `Needs GPS`, `Has GPS`, with counts; then, after a gap, the `Only Show Selected Photos` toggle (enabled with a selection; shows the selection, fades photos deselected there in place, and turns off when a view button is clicked)
- The selection is the same in every view; photos hidden by the view stay selected and are still acted on
- Selection bar inside the grid: `N selected | Select All | Deselect All | Remove from List`; white with nothing selected, orange with a selection
- Groups photos without GPS first, then photos with GPS, with colored headings; the divider shows only between two groups shown
- Shows GPS badges on thumbnails that already have GPS
- Selection: click or Ctrl+click adds/removes a photo; Shift+click adds a range; empty clicks and drags do nothing; Ctrl+A and `Select All` add the photos shown; arrow keys move focus without changing the selection; Space toggles; Delete removes the selected photos from the list
- Right-click: `Copy GPS Coordinates`, `Use This Location`, `Remove from List` (does not change the selection)
- Status row under the grid appears only for action results (with an `Undo` link), errors, and loading progress

### Right: Photos to Change

- Brown `PHOTOS TO CHANGE` header, then `N Photos Selected` and `X without GPS · Y with GPS` (one photo: its name and GPS), `Copy` for a single photo with GPS
- `Location` tab:
- `New Location`: `Copy location` with `From a Photo in the Photo List` and `From a Photo on Your Computer`; latitude/longitude fields (decimal, DMS, DDM; a pasted pair auto-splits); `Paste`, `Clear`
- `From a Photo in the Photo List` enters pick mode: the button becomes `Cancel`, a blue banner explains the mode, the grid switches to `Has GPS` (view buttons locked), and everything except `Add Photos`, `Clear List`, and `Cancel` is disabled; afterwards the previous view (and Only Show Selected Photos) returns, and the selection is kept. Disabled, with a hover hint, when no photo in the list has GPS
- The location source shows on a blue card and as a blue `SOURCE` outline in the grid; editing the fields by hand drops it
- `Apply Location to N Photos` (orange); a note warns when existing GPS will be replaced; the confirmation offers `Skip Photos with GPS`, `Replace`, or `Cancel`
- `Remove GPS from Selected N Photos` (red outline, counts the selected photos that have GPS), with confirmation
- `Date & Time` tab: placeholder until date/time editing is designed
- Pop-ups for a browsed photo with no GPS and for an unreadable photo

### Menus

- File:
- `Add Photos...` (Ctrl+O)
- `Clear List`
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
- `Apply Location to N Photos`
- `Remove GPS from Selected N Photos`
- Stores prior GPS state for each successfully changed photo
- Restores prior coordinates or blank/no-GPS state on undo
- Also puts the photo list and selection back as they were at the edit (photos added since disappear, removed ones come back; files that no longer exist are left out)
- Redo reapplies the undone GPS action
- Undo/redo memory is replaced by the next apply/clear action; adding, removing, or clearing photos does not clear it
- Memory is not written to disk and is cleared on program exit

### Add Photos picker

- The app's own picker replaces the system file dialogs (they mix folders and photos; on Linux choosing both silently does nothing). Used by `+ Add Photos` and, in one-photo mode, by `From a Photo on Your Computer`
- Opened modal but non-blocking (`open()` plus a callback): a blocking `exec()` ran a nested event loop that crashed the Windows build when background results arrived
- Left: folder tree with My Computer (user folders), Bookmarks (Linux file manager bookmarks, without repeats of user folders), Devices/Drives (mounted drives), Network (mounted shares, named like `photo on nas.local`). Folders expand on demand; an arrow shows only for folders with subfolders; hidden folders are left out like each system's file manager. The current folder is highlighted (navy) and the tree opens down to it. Folder icons come from Qt's style, not the system shell
- Top: Back, Forward, Up, and a path box (type or paste a folder; UNC paths like `\\server\share` work on Windows)
- Right: only photos, as thumbnails with GPS badges; same click/Shift-click/Select All rules and selection bar as the Photo List; photos already in the Photo List are marked "In Photo List" and can't be selected. Tiles appear at once as placeholders; thumbnails fill in batch by batch, then GPS badges in a second pass
- One-photo mode: a click selects one photo, double-click chooses it, button `Use This Photo's Location`
- Opens in the last folder used (also after cancelling)
- Windows: unmapped network shares don't appear in the tree (File Explorer's Network lists discovered computers); mapped drives appear under Drives. macOS: no Bookmarks section. Neither has a shared thumbnail cache, so only embedded previews speed things up there

## Known Issue

- Qt icon mode loses track of photo positions when a hidden photo's thumbnail changes; the grid is re-laid out after that (see `_relayout_after_hidden_icon_change`).

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
