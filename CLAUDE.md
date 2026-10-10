# Photo GPS Editor

Python + PySide6 desktop app for viewing and editing GPS metadata in photos
(JPG, CR2, CR3, DNG) through ExifTool. Runs on Linux Mint, Windows 11, and
macOS (Apple Silicon).

Read `PROJECT_CONTEXT.md` before starting work. It is the source of truth for
status, architecture, the current UI, and future ideas.

## Commands

- Run the app: `.venv/bin/python app.py`
- Run the tests: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests`
- Build locally: see `packaging/README.md` (PyInstaller one-folder build)
- CI: `.github/workflows/build.yml` tests and builds Linux, Windows, and macOS on
  every push; a `v*` tag attaches the builds to a draft release

## Layout

- `core/`: models, coordinates, ExifTool wrapper, photo loading, picker places
- `services/`: workflow logic; `services/workflow_facade.py` is the GUI's entry point
- `gui/`: main window, widgets, presenters, window mixins, background loading
- `tests/`: unittest suite, including real mouse/keyboard GUI tests

## Rules

- `core/` and `services/` must not import PySide6, Pillow, or `gui/` (a test
  enforces this). Keep reusable logic there; a web version on a NAS may reuse it.
- Preserve the current architecture unless asked to refactor.
- Prioritize functionality and workflow correctness before visual polish.
- Prefer targeted edits over full-file rewrites; add helpful comments to new
  code, but leave existing comments alone unless they become wrong.
- Every button needs a hover hint (a test enforces this).
- Background results reach the GUI thread through a plain Python queue, not
  queued signals carrying Python objects (that crashed on Windows). Don't open
  dialogs with blocking `exec()`; use `open()` plus a callback.
- When updating `PROJECT_CONTEXT.md`, change only the parts that changed.

## Git

- Solo project using a PR flow: feature branch, push, `gh pr create`, CI, merge
  with GitHub's merge button (merge commit).
- Never commit or push until the user says to; they review changes in VS Code first.
- No AI attribution (Co-Authored-By) lines in commits or PRs.
- Version bumps touch `pyproject.toml`, `APP_VERSION` in `gui/main_window.py`,
  and `README.md`.
