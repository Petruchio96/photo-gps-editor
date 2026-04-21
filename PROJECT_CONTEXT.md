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
- `core/photo_loader.py`: converts paths into `PhotoInfo` using single-file and bulk metadata reads

### Services

- Reusable workflow logic outside the PySide frontend
- Handles source resolution, target-file rules, session refresh, overwrite detection, coordinate parsing, and GPS apply orchestration
- `services/workflow_facade.py`: single backend workflow entry point used by the desktop frontend
- `services/photo_metadata_cache.py`: backend-owned in-memory metadata cache for unchanged selected photos
- Intended to remain reusable for possible future desktop, API, web, or container workflows

### Desktop GUI

- `gui/main_window.py`: shell window, menus, shared UI state, undo/redo memory
- `gui/thumbnail_loader.py`: desktop thumbnail generation, fallback icons, GPS badge overlay, and icon caching
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

## Refactor Plan (Revised)

### Purpose

This refactor has two primary objectives:

1. Clean separation of frontend (desktop) and backend (shared logic)
2. Faster photo selection performance, especially in the left browser pane

“Small and fast” means:
- simpler ownership per module
- reduced runtime overhead
- less duplicated orchestration
- faster metadata loading

It does NOT mean minimizing file count or lines of code.

---

## Global Rules

Codex must follow these rules for every phase:

1. Make targeted edits only
2. Do not rewrite large files unless necessary
3. Preserve user-visible behavior unless explicitly required
4. Keep the desktop app working after each phase
5. Work phase-by-phase only (no skipping ahead)
6. Transitional states are allowed between phases
7. Avoid introducing new frameworks
8. Achieving the refactor goals is the priority, but Codex should look for safe opportunities to simplify, remove duplication, and keep the codebase as condensed as practical without weakening boundaries or changing behavior

After each phase:

1. List changed files
2. Explain what was accomplished
3. Note anything deferred
4. Suggest a commit message
5. Update the **Refactor Progress** section (append only)
6. Run `.venv/bin/python -m unittest discover -s tests` and report the result
7. Perform a quick desktop smoke test when possible

---

## Refactor Progress

Append progress here after each phase:

- Phase 1 complete: moved `ThumbnailLoader` from `core/thumbnail_loader.py` to `gui/thumbnail_loader.py`, updated desktop/test imports, and removed desktop thumbnail rendering ownership from shared backend code.
- Phase 2 complete: introduced `PhotoWorkflowFacade`, routed desktop load/refresh/source/apply orchestration through `self.workflow`, and added facade coverage while leaving undo/redo restore migration for Phase 5.
- Phase 3 complete: added backend-owned `PhotoMetadataCache`, routed selected-photo refresh/apply reloads through cached metadata, and covered unchanged-file reuse, changed-file invalidation, multi-file cache access, and facade cache coordination.
- Phase 4 complete: added ExifTool bulk GPS reads, routed uncached selected-photo loads through bulk `PhotoLoader.load_photo_infos`, preserved unsupported-file handling and single-file fallback paths, and covered bulk result mapping, missing-record fallback, cache-miss batching, and bulk failure fallback.
- Phase 5 complete: moved undo/redo GPS restore execution behind `PhotoWorkflowFacade.restore_gps_states_workflow`, kept GUI action wiring/status behavior in the desktop layer, and added backend/facade tests for write, clear, and refresh behavior.

---

## Target Architecture

The project should evolve toward:

### Backend (shared, reusable)

- No PySide6 dependencies
- Usable by both desktop and future API

Layers:

1. Domain
   - models
   - coordinate validation
   - file type rules

2. Application
   - workflow orchestration
   - apply logic
   - source resolution
   - undo/redo logic
   - caching coordination

3. Infrastructure
   - ExifTool integration
   - metadata read/write
   - bulk read support

---

### Desktop (frontend)

- MainWindow
- mixins
- widgets
- thumbnail rendering
- icon/badge drawing
- clipboard and UI behavior

All PySide6 usage must stay here.

---

## Known Problems to Fix

1. GUI directly constructs and uses backend infrastructure
2. Thumbnail logic lives in backend-oriented code
3. Photo selection loads metadata inefficiently
4. Metadata reads may call ExifTool once per file
5. Undo/redo logic is partially in GUI

---

## Phase 1: Move Thumbnail Code to Desktop Layer

### Goal
Remove all PySide6/image rendering from shared backend.

### Required

1. Move `ThumbnailLoader` out of `core` into desktop layer
2. Keep all Qt/Pillow usage in desktop code only
3. Update imports accordingly
4. Preserve:
   - JPEG thumbnails
   - fallback icons
   - GPS badge overlay
   - cache behavior

### Rules

- No behavior changes
- No performance optimization yet
- Backend must not import thumbnail code after this phase

---

## Phase 2: Introduce Backend Workflow Facade (Controlled Scope)

### Goal
Give GUI a single backend entry point without over-refactoring.

### Required

1. Introduce a facade (e.g. `PhotoWorkflowFacade`)
2. Move only **clear orchestration** behind it:
   - load selected photos
   - load source photo
   - prepare apply
   - execute apply
   - refresh session

3. Update MainWindow to use the facade for these operations

### Important Constraints

- Do NOT migrate everything in one pass
- Some direct backend calls may remain temporarily
- Transitional adapters are acceptable

---

## Phase 3: Add Metadata Cache

### Goal
Avoid reloading unchanged files.

### Required

1. Add backend cache keyed by:
   - path
   - modified time
   - optionally file size

2. Cache must support:
   - single file get/set
   - multi-file get/set (prepare for Phase 4)

3. Use cache during photo selection and refresh

### Rules

- Cache must live in backend, not GUI
- Preserve correctness if files change

---

## Phase 4: Add Bulk Metadata Reading (High Priority)

### Goal
Reduce cost of loading many photos.

### Required

1. Add bulk metadata read support in infrastructure layer
2. Allow reading GPS for multiple files in one call
3. Integrate into photo loading workflow

### Critical Safety Requirements

Must preserve:

1. Per-file error handling
2. Per-file success handling
3. Unsupported file handling
4. Missing GPS vs read failure distinction
5. Correct mapping of results to file paths
6. Existing data model compatibility

Must include:

- fallback to single-file reads if bulk parsing fails

### Notes

- This is the highest risk phase
- Prefer safe correctness over aggressive optimization

---

## Phase 5: Move Undo/Redo into Backend

### Goal
Remove restore logic from GUI.

### Required

1. Move GPS restore logic into application layer
2. GUI calls backend for undo/redo operations
3. Preserve current behavior

### Notes

- Introduce backend concepts only if needed
- Keep implementation simple

---

## Phase 6: Reduce Full List Rebuild Cost

### Goal
Improve responsiveness of left pane.

### Required

1. Reduce unnecessary full list rebuilds
2. Separate:
   - session refresh
   - thumbnail generation
   - UI rendering

3. Preserve:
   - grouping
   - selection
   - GPS badges

### Constraints

- Do NOT implement full async system here
- Keep changes small and safe

---

## Phase 7: Optional Background Loading

### Goal
Improve UI responsiveness further.

### Optional

1. Move metadata and thumbnail work off main thread
2. Keep UI responsive during large loads

### Constraints

- Keep implementation simple
- Avoid complex threading systems

---

## Phase 8: Packaging for Backend Reuse

### Goal
Prepare for future Docker/API use.

### Required

1. Ensure backend has no PySide6 dependency
2. Make backend importable independently
3. Keep desktop entry point working

### Notes

- Do not build API yet
- Do not over-engineer packaging

---

## Testing Guidance

Prioritize backend tests:

1. coordinate parsing
2. source resolution
3. target path logic
4. apply workflow
5. cache behavior
6. bulk read behavior

UI testing is secondary.

---

## How to Use This Plan

Commands to Codex:

- "Do refactor phase 1"
- "Do refactor phase 2"
- etc.

For each phase Codex must:

1. Inspect current repo
2. Implement only that phase
3. Keep app working
4. Report changes
5. Update Refactor Progress
6. Suggest commit message

---

## Success Criteria

Refactor is successful when:

1. Backend is fully reusable without PySide6
2. Desktop code owns all UI and rendering
3. GUI uses a backend workflow facade
4. Metadata loading is cached and more efficient
5. Bulk metadata reads reduce selection latency
6. Project is ready for future API reuse
