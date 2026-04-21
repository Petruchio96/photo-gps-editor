# Release Checklist

Use this checklist against the packaged application, not the source checkout.

## Build Verification

- [ ] Automated tests pass from source.
- [ ] Linux PyInstaller bundle builds successfully.
- [ ] Windows PyInstaller bundle builds successfully on Windows.
- [ ] Packaged app launches on a machine without the project virtual environment.
- [ ] Packaged app can find bundled ExifTool.

## Launch

- [ ] App opens from the packaged executable.
- [ ] App icon appears in the window/task switcher where supported.
- [ ] About dialog opens and shows the project link.
- [ ] No dependency error dialog appears at startup.

## Loading

- [ ] Choose Photos opens the OS file picker.
- [ ] JPG files load.
- [ ] CR2, CR3, or DNG files load if sample files are available.
- [ ] Unsupported files are ignored or handled gracefully.
- [ ] Portrait thumbnails render correctly in the main app.

## GPS Read

- [ ] Photos with GPS show GPS badges.
- [ ] Photos without GPS appear before the GPS group.
- [ ] Right-click copy GPS works from a tagged thumbnail.

## GPS Write

- [ ] Manual decimal coordinates validate.
- [ ] Manual coordinates apply to selected photos.
- [ ] Source photo coordinates apply to selected photos.
- [ ] Overwrite warning appears before replacing existing GPS coordinates.
- [ ] Clear GPS removes coordinates from tagged photos.

## Undo And Persistence

- [ ] Undo restores the previous GPS state.
- [ ] Redo reapplies the GPS state.
- [ ] After closing and reopening the app, metadata changes are still present.
- [ ] Edited files still open normally in a standard photo viewer.
