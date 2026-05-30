# Thai Local PDF Editor React Shell

This folder is the first React + Vite shell for migrating the current Tkinter PDF editor into a web-app-style UI.

It is not wired as the default Windows `.pdf` handler yet. The packaged Tkinter executable in `dist/ThaiLocalPdfEditor/ThaiLocalPdfEditor.exe` remains the active default app until the React migration is complete and explicitly promoted.

## Commands

```powershell
npm install
npm run bridge
npm run dev
npm run lint
npm run build
```

## Current Scope

- App shell layout with compact toolbar, page list, PDF viewer area, tool inspector, and status bar.
- Local Python bridge at `127.0.0.1:5178` for migration testing.
- Worker-backed preview rendering for a local demo PDF.
- Interactive state for page selection, page move up/down, previous/next page, and zoom controls.
- Visual parity target is the existing local Thai PDF editor, not a cloud editor.
- Backend bridge target is the Python worker contract under `thai_pdf_editor/app/worker.py`.

## Migration Guardrail

Keep this shell local-only. Do not add OCR, cloud storage, account login, plugin systems, or AI features unless the project scope is explicitly reopened.
