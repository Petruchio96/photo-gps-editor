
# Project working instructions

Use `PROJECT_CONTEXT.md` as the source of truth for project status, architecture, and current priorities.

Coding style for this repo:
1. Use targeted edits only
2. Do not rewrite full files unless explicitly asked but suggest full function rewrites for changes longer than 4 lines
3. Give instructions in this format:
   - Find this block:
   - Replace it with:
   - Add this below:
4. Assume edits are being made directly in VS Code
5. Keep explanations short and practical
6. Add helpful comments to new code, but do not modify existing comments unless necessary
7. Prefer step by step changes over large rewrites
8. When updating the PROJECT_CONTEXT.md file only update the parts that changed and keep the rest as is

Project notes:
1. This is a Python + PySide6 desktop app
2. Prioritize functionality and workflow correctness before visual polish
3. Preserve current architecture unless explicitly asked to refactor
