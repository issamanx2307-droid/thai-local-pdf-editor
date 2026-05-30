# React Migration Plan

## Current Checkpoint

Current CustomTkinter build is the stable baseline.

- Windows `.pdf` association points to `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe`.
- Release QA passes with packaged exe smoke test.
- Page list, page move buttons, bottom scrollbar, print fallback, start/stop launchers, and local-only constraints are covered by tests.
- There is no Git repository or remote configured under `D:\PDF editor`, so the current checkpoint cannot be pushed until Git is initialized or a remote is provided.

## Goal

Build a React-based UI that feels like a modern web app while preserving the local desktop workflow and the existing PDF behavior.

The migration must stay local-only:

- No cloud storage.
- No accounts or login.
- No AI features.
- No OCR.
- No plugin system.
- No large batch automation unless explicitly approved.

## Recommended Target Architecture

Use a desktop React shell with local IPC instead of turning the app into a hosted web service.

Recommended stack:

- UI: React + TypeScript + Vite.
- Desktop shell: Tauri or Electron.
- PDF core: keep the existing Python/PyMuPDF core initially.
- Bridge: local IPC commands between React shell and Python worker process.
- Preview rendering: keep Python rendering first, return image/page metadata to React.
- Packaging: ship a single Windows desktop app after parity is reached.

Reasoning:

- The Python core already handles PyMuPDF operations, Thai fonts, redaction, forms, print fallback, and QA.
- A pure browser/PDF.js rewrite would risk behavior regressions in save, redaction, font, and form workflows.
- Keeping Python as the core lets the React migration focus on UI first.

## Migration Phases

### Phase 0 - Freeze Current Desktop Baseline

Acceptance:

- Current CustomTkinter exe remains usable.
- `release_qa.py --include-build` stays green.
- Windows `.pdf` association remains pointed at the stable exe until the React build reaches parity.

Tasks:

- Add Git repository and remote, or provide the existing remote URL.
- Commit the current stable baseline.
- Tag the checkpoint as `tk-stable-before-react`.

### Phase 1 - Extract App Contract

Acceptance:

- React UI can be built from a documented command/event contract without depending on Tk widgets.

Tasks:

- Define document state JSON: file path, total pages, current page, zoom, dirty, selected tool.
- Define commands: open, render page, next/previous page, move page, rotate, duplicate, delete, save as, print, search.
- Define responses and errors in Thai-ready text.
- Add contract tests around existing Python core.

### Phase 2 - Python Worker Prototype

Acceptance:

- A command-line worker can open a PDF, render a page, navigate pages, and return structured JSON.

Tasks:

- Add a thin Python worker entrypoint.
- Keep file paths local and UTF-8 safe.
- Render preview images into a temp/cache directory.
- Expose page operation commands through the worker.
- Add tests that compare worker behavior to current core behavior.

### Phase 3 - React UI Shell

Acceptance:

- React shell shows the real app surface, not a landing page.
- Main layout matches current workflows: toolbar, page list, viewer, tool panel, status bar.

Tasks:

- Scaffold React + TypeScript + Vite.
- Build layout using a professional web-app design system.
- Implement toolbar, page list, viewer, bottom scrollbar, right tool panel, status bar.
- Keep controls dense, clear, and work-focused.
- Add responsive constraints for narrow and wide desktop windows.

### Phase 4 - Viewer And Page Navigation Parity

Acceptance:

- Open a real PDF, render preview, zoom, fit width, fit top-bottom, horizontal/vertical scroll, and page navigation work in React.

Tasks:

- Wire React to Python worker for open/render/navigation.
- Implement current-page sync from state to page list.
- Implement page list selection as action source-of-truth.
- Implement bottom scrollbar and mouse wheel behavior.
- Add Playwright tests for viewer layout and interactions.

### Phase 5 - Page Operations And Editing Parity

Acceptance:

- Core editing workflows match the current desktop app.

Tasks:

- Move up/down, rotate, duplicate, delete, extract.
- Text, image/signature, rectangle, highlight, crop, redact.
- Pending overlay list and edit controls.
- Save As preflight and dirty-state handling.
- Form field editing.
- Metadata editing.

### Phase 6 - Print, Export, And Recent Files

Acceptance:

- Print fallback, JPG export, recent files, drag/drop, and Windows file association work from the React shell.

Tasks:

- Reuse existing print operations where possible.
- Add local recent-file store for the React shell.
- Wire drag/drop to open local PDFs.
- Package Windows association to the React desktop executable only after full parity.

### Phase 7 - Release Cutover

Acceptance:

- React desktop app passes parity QA and replaces the old default exe only after approval.

Tasks:

- Create full React release QA.
- Keep Tkinter app as fallback during one release cycle.
- Build Windows executable.
- Test double-click `.pdf`.
- Update `.pdf` association only after user approval.

## Suggested First Implementation Slice

Start with Phase 1 and Phase 2 only.

Do not touch the current Tkinter UI yet. First create the worker contract and prove:

1. Open a real PDF.
2. Render page 1 to preview image.
3. Navigate to page N.
4. Move selected page up/down.
5. Return state JSON that React can consume.

This keeps the stable app safe while creating the foundation for the React UI.

## Push Requirement

Current status: cannot push from `D:\PDF editor` because it is not a Git repository.

To push this checkpoint, one of these is required:

1. Existing remote URL, then initialize Git and push.
2. Move/copy this project into an existing Git repository.
3. Create a new private repository and set it as `origin`.

After a remote exists, the intended checkpoint command sequence is:

```powershell
git init
git add .
git commit -m "Stable Tkinter PDF editor checkpoint before React migration"
git branch -M main
git remote add origin <REMOTE_URL>
git push -u origin main
```

Before running that sequence, add a `.gitignore` so build output, temp files, logs, and QA artifacts are not accidentally committed.
