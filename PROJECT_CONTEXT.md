# Photo GPS Editor - Project Context

## Snapshot

Last updated: 2026-10-09
Version: 1.4 released (Linux, Windows, macOS): the app's own Add Photos picker, the map (Pick from a Map, street map and satellite imagery), Edit > Settings, and the same pinned ExifTool on every system
Status: Two-pane layout (Photo List and Photos to Change, with Location and Date & Time tabs), the app's own photo picker (folder tree, only photos), a pop-out map for picking a location (OpenStreetMap, USGS, or Esri with the user's key), fast thumbnails (shared Linux thumbnail cache, embedded JPEG thumbnails), background loading, failure-tolerant writes, undo/redo that restores the photo list, optional backups, an error log, and CI builds for Linux, Windows, and macOS.

Repository: https://github.com/Petruchio96/photo-gps-editor

## Goal

Desktop application for viewing and editing GPS metadata in photo files.

Key objectives:
- Select one or many photos with the app's own picker (folder tree on the left, only photos on the right)
- Display thumbnails in a grid, including real thumbnails for RAW files
- View and copy GPS metadata
- Apply GPS metadata to the photos selected in the grid, from typed, pasted, photo-sourced, or map-picked coordinates
- Clear GPS metadata from selected photos
- Support JPG and selected RAW formats: CR2, CR3, DNG
- Run on Linux Mint, Windows 11, and macOS (Apple Silicon)

## Architecture

### Core

- `core/models.py`: shared data models such as `PhotoInfo` and `GpsCoordinates`
- `core/coordinates.py`: latitude/longitude validation
- `core/file_types.py`: supported extension checks
- `core/map_tiles.py`: map tile math (Web Mercator, visible tiles, zoom to fit) and the tile sources (OpenStreetMap street map, USGS satellite imagery); no Qt
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
- `gui/widgets/`: browser panel (Photo List pane: header, Show filter, selection bar, grid with click-to-add selection), editor panel (Photos to Change pane with tabs), `photo_picker.py` (the Add Photos picker), `map_view.py` (the map widget: tiles drawn with QPainter, downloaded by QNetworkAccessManager on the GUI thread into a disk cache; pin and photo dots), `map_window.py` (the pop-out map window and photo preview), `settings_dialog.py` (Edit > Settings: backups and the ArcGIS key), loading indicator, thumbnail delegate (shimmer placeholders, SOURCE marker, "No GPS" dimming, faded deselected photos), `icons.py` (line icons drawn in code)
- `gui/presenters/`: UI-facing view-state builders; `inspector_state.py` holds the inspector logic with no Qt code
- `gui/window_mixins/`: focused behavior for the photo list, inspector, New Location / pick mode, the map (`map_picker.py`), and apply/remove workflows

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
- `Pick from a Map` opens the map window (below)
- The location source shows on a blue card and as a blue `SOURCE` outline in the grid; editing the fields by hand drops it
- `Apply Location to N Photos` (orange); a note warns when existing GPS will be replaced; the confirmation offers `Skip Photos with GPS`, `Replace`, or `Cancel`
- `Remove GPS from Selected N Photos` (red outline, counts the selected photos that have GPS), with confirmation
- `Date & Time` tab: placeholder until date/time editing is designed
- Pop-ups for a browsed photo with no GPS and for an unreadable photo

### Map window

- Opened with `Pick from a Map` in New Location; a separate window that blocks the main window while open (application-modal, shown with `show()` like the picker, not a blocking `exec()`); `Done` (orange) or Esc closes it, then Apply in the main window writes the location
- The map is another source for New Location, not a separate workflow: a quick click on the map (released within 0.30 s, moving under 2 px; a longer hold or any wiggle pans instead, so a sloppy click-and-hold doesn't move the pin; the click that brings the map window back from another program only activates it: Linux window managers activate the window just before delivering the click, so a click within 0.3 s of the window getting focus, from Qt's app-wide focus-window signal, is ignored) moves the blue pin there and fills the latitude/longitude fields (as typing would, so a location source photo is dropped); dragging the pin fills them when it is dropped. Apply writes them as usual
- The pin follows New Location (typed, pasted, copied from a photo); the map moves to it only when it changed and is out of view; empty fields remove the pin
- Photos in the Photo List with GPS show as neon purple dots with a white outline (green blended into the map), orange when selected. Hovering a dot shows the file name(s); clicking one shows a small preview (thumbnail, name, `Use This Location`, and `< 1 of 2 >` arrows beside the count when several photos' dots land on the same spot, within 2 px, so they look like one dot; nearby but separate dots each open their own preview; `Use This Location` uses the photo shown) and does not move the pin
- While another program is active, the map shows the normal arrow and no photo-name hints (a click there only brings the window back); otherwise the pointer is a crosshair (drawn in code at the screen's scale, dark with a white halo; its hot spot is its center), a pointing hand over a photo dot, an open hand over the pin, and a closed hand as soon as the button is pressed (except on a dot); a readout under the map shows the coordinates under the mouse as it moves
- Drag to pan, wheel or `+`/`-` to zoom (whole levels; opening may use an in-between level, drawn from the nearest level's tiles scaled); toolbar: `Street` and one satellite button (`Satellite` = Esri when a key is set in Edit > Settings, `US Satellite` = USGS when not), `Show All Photo Locations`, `Go to Selected Location`, zoom buttons. If Esri's imagery doesn't load (key refused, offline), an amber banner says to check the key in Edit > Settings and offers `Use US Satellite Instead` (the button then reads `US Satellite` until the map is opened again)
- Street map: OpenStreetMap's tile server (identifying User-Agent, cache headers honored, no bulk downloads, credit shown). US Satellite: USGS The National Map orthoimagery (no key; no use constraints; United States only, detailed to zoom 16 and enlarged beyond; a note says so elsewhere). Esri Satellite: Esri World Imagery from the image tile service for API keys (`ibasemaps-api.arcgis.com`; worldwide, street-level detail to zoom 19 and beyond, 256-pixel tiles). The Static Basemap Tiles service has no imagery style (only imagery labels), and this service accepts the key only as `?token=` in the address, not in a header, so the key also appears in the tile cache's records. It needs the user's own API key from a free ArcGIS Location Platform account (an open-source app can't keep its own key secret; a Public application key with only the Static basemap tiles privilege works): the key is entered in Edit > Settings and saved in plain text in the app's settings. Without a key Esri answers 200 with a JSON "Token Required" error and the map shows a note; as of 2026-10-09 it serves imagery for any non-empty token, so a wrong key is not detected (usage shows in the ArcGIS dashboard a day later)
- Tiles are kept in a 200 MB disk cache in the app's cache folder, so places viewed before show offline; a note appears when tiles can't be downloaded, and failed tiles are retried after 15 seconds
- Each time it opens it shows the street map, centered on the photos in the Photo List with GPS, zoomed to fit them with a 12% margin on every side (zoom 15 at most, for one photo); with none, it shows the lower 48 states with the same margin. It does not jump to New Location when opening (`Go to Selected Location` does). The window size and position are remembered
- Off while picking from the Photo List
- QtWebEngine + Leaflet was rejected (about 200 MB more per build) and QtLocation/QML too (a second UI language, untested offscreen); dragging photos onto the map was considered and rejected

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
- `Settings...` (Ctrl+, / Cmd+,; Qt's standard Preferences key is the "Settings" media key on Linux; on macOS in the app menu): a modal window (shown with `show()`) with Backups (`Keep Backup Copies of Originals`, saved between sessions) and the Esri Satellite key (instructions and links, Paste, Remove Key); Save applies, Cancel changes nothing

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
- Explore a future API/web/container layer (Docker on a Synology NAS) on top of the reusable `services/` backend

## Development Notes

- Use the project virtual environment when running the app or tests
- Run the app with `.venv/bin/python app.py`
- Run tests with `.venv/bin/python -m unittest discover -s tests` (add `QT_QPA_PLATFORM=offscreen` to run without a display)
- GitHub Actions (`.github/workflows/build.yml`) runs the tests and builds Linux, Windows, and macOS apps on every push; pushing a `v*` tag attaches the builds to that release
- On Linux, `app.py` sets `XCURSOR_SIZE`/`XCURSOR_THEME` from the desktop's gsettings (Cinnamon, then GNOME) before Qt starts, unless already set: otherwise Qt sizes the pointer from the font DPI and it looks a little smaller inside the app
- All three builds bundle the same pinned ExifTool (`packaging/fetch_exiftool.py`, currently 13.59); Linux and macOS use ExifTool's Perl distribution with the system Perl
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
