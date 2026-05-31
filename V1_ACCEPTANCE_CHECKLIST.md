# V1 Acceptance Checklist

This checklist defines the remaining local-only acceptance gate for the Thai PDF Editor v1.

## Scope Freeze

- [x] Local-only PDF editing.
- [x] No OCR.
- [x] No cloud sync or cloud storage.
- [x] No account or login system.
- [x] No AI features.
- [x] No plugin system.
- [x] Local sequential Batch JPG is approved and included.
- [ ] Larger batch automation beyond local sequential Batch JPG requires explicit approval.

## Core Function QA

- [ ] Open, render, close, and save a PDF copy without modifying the source file.
- [ ] Page operations: move, rotate, duplicate, delete, extract, merge, and crop.
- [ ] Overlay operations: text, image, visual signature, rectangle, highlight, and redaction.
- [ ] Text search and replace through the local worker.
- [ ] Metadata list/update.
- [ ] Existing PDF form field list/update for text fields and checkboxes.
- [ ] Undo/redo for supported pending overlay operations.
- [ ] Export current/all pages to JPG.
- [ ] Local sequential Batch JPG for multiple PDFs with a JSON report.
- [ ] Dirty guard before open, merge, demo open, close, refresh, or tab close.

## Real PDF Acceptance

- [ ] Thai text PDF path and Thai file name.
- [ ] Multi-page PDF.
- [ ] Image-heavy PDF.
- [ ] PDF with editable form fields.
- [ ] PDF with metadata.
- [ ] Large PDF representative of real use.
- [ ] Corrupt or unsupported PDF reports a clear local error.

## UI Completion

- [ ] Toolbar controls have correct enabled/disabled states.
- [ ] Page panel scrolls and page actions stay reachable.
- [ ] Viewer vertical and horizontal scrollbars move the PDF content.
- [ ] Tool panel tabs keep all tools reachable.
- [ ] Fullscreen/expanded viewer enters and exits cleanly.
- [ ] Status messages explain the latest action and error.
- [ ] Desktop viewport has no overlapping or clipped controls.
- [ ] Narrow viewport has a usable fallback layout.

## Packaging

- [ ] `start.bat` starts the local app from a clean state.
- [ ] `stop.bat` stops the local app cleanly.
- [ ] Local bridge health is available only on loopback.
- [ ] Release QA passes without fatal stderr.
- [ ] Optional `.exe` build runs the smoke test when packaging is requested.

## Final Gate

V1 is ready only when automated acceptance, real PDF acceptance, UI browser QA, and packaging smoke all pass in the same release pass.
