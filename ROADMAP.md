# Thai Local PDF Editor Roadmap

## Status

- Phase 1-4 core milestones: completed
- Phase 5 automated hardening: completed
- Phase 6 UX readiness: completed
- Phase 7 manual GUI QA: completed with repeatable QA workflow
- Phase 8 packaging: completed
- Phase 9 page utility: completed
- Phase 10 metadata editor: completed
- Phase 11 crop page: completed
- Phase 12 unsaved-changes guard: completed
- Phase 13 pending overlay undo/redo: completed
- Phase 14 drag-and-drop open: completed
- Phase 15 JPG export: completed
- Phase 16 JPG export QA hardening: completed
- Phase 17 JPG export options: completed
- Phase 18 local sequential Batch JPG: completed
- Phase 19 existing PDF form fill: completed
- Phase 20 form fill QA and Thai text hygiene: completed
- Phase 21 signature terminology hardening: completed
- Phase 22 UI readability and release QA: completed
- Phase 23 packaging footprint cleanup: completed
- Phase 24 scroll usability: completed
- Phase 25 keyboard navigation: completed
- Phase 26 safe existing-text replacement: completed
- Phase 27 PDF font inspect/import/download: completed
- Phase 28 real PDF font/edit QA: completed
- Phase 29 font import report UX: completed
- Phase 30 simple visual signature: completed
- Phase 31 pending overlay manager: completed
- Phase 32 pending overlay move/resize: completed
- Phase 33 overlay edit QA: completed
- Phase 34 text-layer PDF search: completed
- Phase 35 Save As preflight summary: completed
- Phase 36 recent files: completed
- Phase 37 search result highlight: completed
- Phase 38 recent files UX: completed
- Phase 39 Save As detail preview: completed
- Phase 40 manual QA checklist: completed
- Phase 41 main window action refactor: completed
- Phase 42 dialog UX polish: completed
- Phase 43 UI helper QA report: completed
- Phase 44 final acceptance pass: completed
- OCR: intentionally excluded from this system by user requirement
- Plugin, cloud, and user account features: intentionally excluded by user requirement
- AI integration: intentionally excluded by user requirement
- PDF to Word OCR/layout reconstruction: intentionally kept in `D:\pdf_doc`, not this editor
- Large batch automation beyond local sequential Batch JPG: ask before implementation

## Phase 6: UX Readiness

Goal: make the existing v1 safer and clearer without adding new PDF features.

- Disable document-only controls until a PDF is open
- Disable navigation controls at page boundaries
- Show the active overlay tool in the tool panel
- Show a drag preview rectangle before committing rectangle/highlight/redaction areas
- Keep merge available because it works without an already opened document

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`

## Phase 7: Manual GUI QA

Goal: prove the app works with real user flows, not only automated smoke checks.

- Open a PDF stored under a Thai path
- Verify preview, next/previous page, page list, zoom, rotate, delete, move
- Add Thai text with a selected Thai `.ttf` font
- Add PNG/JPG image or signature
- Draw rectangle and highlight
- Apply real redaction and verify text is removed in the saved PDF
- Extract a page and merge PDFs
- Confirm original PDF hash is not changed after Save As

Repeatable command:

- `python scripts/phase7_qa.py --include-gui`

Output:

- Record any blocker as a bug and fix only that blocker
- If no blockers are found, mark v1 ready for packaging

## Phase 8: Packaging

Goal: prepare a Windows `.exe` only after manual QA passes.

- Choose packaging tool, default PyInstaller
- Build from the current local-only desktop entrypoint
- Verify packaged app writes logs to `data/logs/app.log`
- Verify no server, no port, and no port 8000

Build command:

- `cmd /c scripts\build_exe.bat`

Smoke command:

- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

Output:

- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe`

## Phase 9: Page Utility

Goal: add one low-risk page operation from the v1 backlog without changing the save model.

- Duplicate the current page after itself
- Keep the duplicated page selected
- Mark the document dirty so Save As writes the duplicated page to a new file
- Keep the original PDF untouched until Save As

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 10: Metadata Editor

Goal: add a safe document-level operation from the v1 backlog while preserving the Save As boundary.

- Edit PDF title, author, subject, and keywords
- Apply metadata changes only to the working copy
- Mark the document dirty after metadata changes
- Persist metadata only through Save As
- Keep the original PDF untouched

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 11: Crop Page

Goal: add a page crop workflow using the existing drag rectangle interaction.

- Add a Crop page tool to the right panel
- Crop only the current working-copy page
- Mark the document dirty after crop
- Persist the cropped page only through Save As
- Keep the original PDF untouched

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 12: Unsaved-Changes Guard

Goal: protect dirty working-copy changes before opening another PDF or closing the app.

- Confirm before opening a new PDF when the current document is dirty
- Confirm before closing the window when the current document is dirty
- Continue without a dialog when the document is clean
- Keep direct Save As behavior unchanged

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 13: Pending Overlay Undo/Redo

Goal: add basic undo/redo without pretending every PDF mutation can be reversed safely.

- Add Thai Undo and Redo buttons to the toolbar
- Undo the latest pending overlay operation before Save As
- Redo the latest pending overlay operation after undo
- Disable undo when the latest operation is a committed page/document mutation
- Keep Save As and original-file protection unchanged

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 14: Drag-and-Drop Open

Goal: support opening PDFs by dropping files onto the app without adding OCR or server behavior.

- Add Windows file drag-and-drop support with `tkinterdnd2`
- Open the first dropped `.pdf` file
- Reject non-PDF drops with a Thai error message
- Respect the unsaved-changes guard before replacing the current document
- Keep OCR intentionally excluded from dependencies and runtime

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 15: JPG Export

Goal: export the opened PDF to page-by-page JPG files without adding OCR, AI, server behavior, or PDF-to-Word scope.

- Add a page-panel command to export the current PDF as JPG
- Export every page to `*_page_0001.jpg`, `*_page_0002.jpg`, and so on
- Use PyMuPDF rendering only, with no OCR dependency
- Apply pending overlay/redaction operations to the exported image copy
- Preserve existing JPG files by writing unique filenames instead of overwriting
- Keep the source PDF untouched

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 16: JPG Export QA Hardening

Goal: make the repeatable QA workflow prove the JPG export feature, not only unit tests.

- Export the saved QA PDF to JPG files in a Thai path
- Verify the JPG count matches the saved PDF page count
- Verify exported JPG files are valid image files with non-zero dimensions
- Verify JPG export does not modify the saved PDF hash
- Keep OCR, AI, server behavior, plugin, cloud, and user account scope excluded

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `python scripts/phase7_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 17: JPG Export Options

Goal: make JPG export usable without expanding into batch automation.

- Let the user export either the current page or every page
- Let the user choose DPI from 96, 150, or 300
- Let the user choose JPG quality from 1 to 100
- Keep output folder selection explicit
- Keep filenames unique and preserve existing JPG files
- Keep source PDFs untouched
- Keep batch automation out of this phase

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 18: Local Sequential Batch JPG

Goal: add a small, explicit batch workflow for JPG export without adding background workers, cloud, AI, OCR, plugin behavior, or account features.

- Let the user select multiple PDF files
- Export every page of each selected PDF to JPG
- Reuse DPI and JPG quality controls
- Process files sequentially in the desktop app
- Continue to the next file if one PDF fails
- Write `batch_jpg_report.json` with succeeded/failed item details
- Keep all source PDFs untouched
- Keep larger batch automation out of scope unless explicitly approved later

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 19: Existing PDF Form Fill

Goal: start the PDF form editor scope safely by filling existing fields only.

- Detect existing supported PDF form widgets
- Support text fields and checkboxes only
- Let the user edit values through a simple Thai dialog
- Mark the working document dirty after form edits
- Persist form edits only through Save As
- Keep the original PDF untouched
- Do not create new form fields
- Do not implement dropdown/radio/script validation in this phase
- Do not implement certificate/PKI digital signatures

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 20: Form Fill QA and Thai Text Hygiene

Goal: make the repeatable QA workflow prove the existing PDF form fill feature and prevent unreadable Thai text from returning.

- Add an existing PDF form sample under a Thai path to `scripts/phase7_qa.py`
- Fill a text field and checkbox through the same core form operation used by the UI
- Save As to a new PDF and verify the form values persist
- Verify the form source PDF hash is unchanged
- Add a production text hygiene test for common double-decoding/mojibake markers
- Keep OCR, AI, plugin, cloud, user account, and large batch automation out of scope
- Keep certificate/PKI digital signatures out of scope until designed separately

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `python scripts/phase7_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 21: Signature Terminology Hardening

Goal: prevent the image-signature overlay feature from being mistaken for real certificate-based digital signing.

- Rename visible image-signature UI copy to `ลายเซ็นภาพ`
- Document that current signature support is an image overlay only
- Document that certificate/PKI digital signatures require a separate design before implementation
- Add tests that prevent accidental certificate-signature dependency drift
- Keep OCR, AI, plugin, cloud, user account, and large batch automation out of scope

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 22: UI Readability and Release QA

Goal: lock the Thai UI readability baseline and make the final release checks repeatable.

- Increase the main window minimum size so the toolbar and side panels have enough room
- Increase primary button and entry heights for Thai text
- Increase left and right panel widths for longer Thai labels
- Add a reusable button-width helper for Thai toolbar labels
- Add tests for readable UI dimensions and long Thai button labels
- Add `scripts/release_qa.py` to run the repeated release QA gate and write `data/logs/release_qa_report.json`
- Keep OCR, AI, plugin, cloud, user account, PDF-to-Word, PKI signatures, and large batch automation out of scope

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python run_app.py --smoke-test`
- `cmd /c start.bat --smoke-test`
- `cmd /c stop.bat`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 23: Packaging Footprint Cleanup

Goal: keep the runtime install and packaged app focused on the desktop PDF editor instead of dragging test/build or unused optional libraries into the release.

- Remove the unused `pypdf` runtime dependency because production PDF work uses PyMuPDF
- Keep `requirements.txt` for runtime dependencies only
- Keep test/build tools in `requirements-build.txt`
- Exclude dev and unused optional modules from PyInstaller analysis, including pytest, pandas, matplotlib, openpyxl, lxml, numpy, cryptography, OpenSSL, and twisted
- Add regression tests for minimal runtime requirements and packaging excludes
- Keep OCR, AI, plugin, cloud, user account, PDF-to-Word, PKI signatures, and large batch automation out of scope

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 24: Scroll Usability

Goal: make long PDFs easier to navigate with larger scrollbars and mouse-wheel support.

- Enlarge the PDF preview vertical and horizontal scrollbars
- Add mouse-wheel scrolling to the PDF preview when the pointer is over the preview or its scrollbars
- Add Shift + mouse-wheel horizontal scrolling for the PDF preview
- Add a visible larger scrollbar to the page list
- Add mouse-wheel scrolling to the page list when the pointer is over the page list or its scrollbar
- Add tests for scrollbar width and wheel-scroll step behavior

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 25: Keyboard Navigation

Goal: make long PDFs quicker to navigate from the keyboard without breaking text-entry behavior.

- Add `PageUp` for previous page
- Add `PageDown` for next page
- Add `Home` for first page
- Add `End` for last page
- Keep normal `Home`/`End`/page-key behavior inside text input widgets
- Add tests for shortcut mapping and text-input guard behavior

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 26: Safe Existing-Text Replacement

Goal: support practical existing-text edits without pretending PDF can be reflowed like Word.

- Add a page-panel command to find and replace existing PDF text
- Support current-page or all-page replacement scope
- Use real redaction with white fill to remove the original text in Save As output
- Place replacement text with the selected Thai-capable font after redaction
- Keep the original PDF untouched until Save As
- Document that full Word/Acrobat-style paragraph reflow and complex font-run editing remain out of scope
- Add tests for replacement operation creation, Save As output, scope resolution, and no-match errors

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 27: PDF Font Inspect, Import, and Download

Goal: help text replacement use a font that matches the opened PDF as closely as the PDF data allows.

- Scan font names from PDF text spans and page font resources
- Normalize subset font names such as `ABCDEE+THSarabunNew`
- Import exact local matches from `assets/fonts`, `D:\ฟอนท์ไทย`, or `C:\Windows\Fonts`
- Import known similar local fonts when the exact font is missing
- Download known free similar fonts from Google Fonts when no local match exists and the user requested internet download
- Store imported/downloaded fonts in `assets/fonts/imported`
- Set the imported font as the active text-editing font
- Report `ไม่สามารถหาข้อมูลได้` when the PDF has no usable font data or no match
- Keep OCR, AI, plugin systems, cloud storage, and user accounts out of scope

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 28: Real PDF Font/Edit QA

Goal: make font scan and text-edit readiness repeatable before adding more PDF editing surface.

- Add `scripts/font_import_qa.py` to create a controlled Thai PDF under a Thai path with a real embedded font
- Verify the app can scan PDF font usage from the controlled text layer
- Verify the detected font can be resolved/imported into `assets/fonts/imported`
- Verify blank/image-like PDFs without font data report `ไม่สามารถหาข้อมูลได้`
- Inspect existing Phase 7 QA PDFs on a best-effort basis and write a report without failing just because one real PDF lacks a text layer
- Write `data/logs/font_import_qa_report.json`
- Add the font import QA gate to `scripts/release_qa.py`

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/font_import_qa.py`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 29: Font Import Report UX

Goal: make font detection transparent to the user before they edit text.

- Add a reusable formatter for font import results
- Show each detected PDF font name without subset prefixes such as `ABCDEE+`
- Show whether the app used an exact local font, a similar local font, a downloaded font, or no match
- Show the selected imported font file used for text editing
- Show where the PDF font data came from, including pages, span count, character count, and text-layer/resource source
- Keep OCR and AI out of the font detection path

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 30: Simple Visual Signature

Goal: let the user create a simple no-certificate signature for practical local PDF workflows.

- Add a local visual-signature generator that creates transparent PNG files under `data/signatures`
- Use the selected Thai font when available, otherwise fall back to the configured Thai font
- Add a right-panel command `สร้างลายเซ็นภาพ`
- After creating the PNG, set it as the selected image overlay and set the placement width
- If a PDF is open, activate the image placement tool so the user can click the target position
- Keep this explicitly as an image overlay, not certificate/PKI signing
- Add tests for PNG creation, blank text validation, and readable Thai UI label sizing

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 31: Pending Overlay Manager

Goal: let the user correct pending overlay mistakes before Save As.

- Add a `รายการที่วางแล้ว` command for the currently opened PDF
- Show pending text, image/signature, rectangle, highlight, redaction, and replacement-text operations
- Show readable labels with page numbers and short operation details
- Delete the selected pending item without touching saved PDF content
- Remove deleted items from undo/redo stacks so stale undo references do not remain
- Keep the source PDF untouched until Save As

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 32: Pending Overlay Move and Resize

Goal: adjust pending overlays such as signatures without recreating them.

- Move selected pending overlays left, right, up, or down in PDF points
- Resize selected text, images/signatures, shapes, highlights, redaction marks, and replacement-text boxes
- Re-render the preview after every pending edit
- Keep edits pending until Save As and keep original PDF files untouched

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 33: Overlay Edit QA

Goal: prove the pending-overlay manager works with real PDF output.

- Add `scripts/overlay_edit_qa.py`
- Create a PDF under a Thai path
- Create a local visual signature image
- Add text, signature image, rectangle, and highlight overlays
- Delete one pending overlay before Save As
- Move and resize selected pending overlays before Save As
- Save as a new PDF and verify the original hash is unchanged
- Verify saved output opens, contains expected Thai text, excludes the deleted text, and contains an image
- Write `data/logs/overlay_edit_qa_report.json`
- Add this QA step to `scripts/release_qa.py`

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/overlay_edit_qa.py`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 34: Text-Layer PDF Search

Goal: let the user find existing selectable PDF text without adding OCR or AI.

- Add a top-toolbar `ค้นหา` command that is enabled only after a PDF is open
- Search through PyMuPDF `page.search_for()` text-layer matches only
- Show all matches with page labels in a dialog
- Let the user move to previous/next result with wraparound
- Let the user select a result and jump to that page
- Show Thai validation errors for blank queries and no-match cases
- Keep scanned-image OCR explicitly out of scope

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 35: Save As Preflight Summary

Goal: make destructive or pending Save As output visible before writing a new PDF.

- Build a reusable Thai summary from pending and applied operations
- Show counts for text, image/signature, rectangle, highlight, redaction, form, metadata, and page operations
- Warn when Save As includes redaction or existing-text replacement
- Allow the user to cancel before writing any destination output
- Keep the existing safe temp-file Save As transaction unchanged

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 36: Recent Files

Goal: make local reopening faster without adding accounts, cloud sync, or a plugin system.

- Add a top-toolbar `ล่าสุด` command
- Store recent PDF paths as UTF-8 JSON at `data/settings/recent_files.json`
- Keep the list local-only, newest first, deduplicated, and limited to 10 files
- Filter missing files and non-PDF paths when loading
- Add opened and newly saved PDF files to the recent list
- Preserve Thai paths in storage and tests

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 37: Search Result Highlight

Goal: make text-layer search results visible on the preview without writing anything to the PDF.

- Scale PDF search rectangles into preview-canvas coordinates
- Draw a temporary yellow outline around the selected match
- Scroll the preview toward the selected match
- Clear the temporary highlight when the search dialog closes
- Keep this as preview-only UI state, not a saved PDF operation

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 38: Recent Files UX

Goal: let the user maintain the local recent-file list without editing JSON manually.

- Show full local paths in the recent-file dialog
- Show the selected path in a readable status area
- Remove one selected recent item
- Clear all recent items
- Keep storage local-only at `data/settings/recent_files.json`

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 39: Save As Detail Preview

Goal: let the user inspect exactly what Save As is about to write.

- Replace the short messagebox confirmation with a preflight dialog
- Keep the existing summary counts and destructive-operation warning
- Add page-level detail lines for pending and applied operations
- Preserve the ability to cancel before writing destination output
- Keep the safe temp-file transaction unchanged

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 40: Manual QA Checklist

Goal: add a local checklist that helps catch PDF-specific mistakes before sharing output files.

- Add a `ตรวจงาน` command in the page panel
- Show checklist items for saved output, original-file protection, redaction, Thai fonts, images/signatures, forms, metadata, and Thai paths
- Include current state context when the document still has unsaved work or no PDF is open
- Keep the checklist local-only and informational; it does not replace opening the saved PDF for inspection

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 41: Main Window Action Refactor

Goal: keep the main UI file comfortably below the 1000-line acceptance limit before adding any future work.

- Move document/navigation actions to `thai_pdf_editor/app/ui/actions/document_actions.py`
- Move search actions to `thai_pdf_editor/app/ui/actions/search_actions.py`
- Move Save As/export/checklist actions to `thai_pdf_editor/app/ui/actions/save_export_actions.py`
- Move metadata/form/font/undo actions to `thai_pdf_editor/app/ui/actions/document_edit_actions.py`
- Move page/overlay placement actions to `thai_pdf_editor/app/ui/actions/page_overlay_actions.py`
- Keep `main_window.py` focused on UI composition and callback wiring

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 42: Dialog UX Polish

Goal: improve existing dialogs without adding new product scope.

- Add minimum dialog sizes for search, recent files, Save As preflight, and checklist dialogs
- Add Escape-to-close behavior for modal dialogs
- Add Enter-to-open and Delete-to-remove behavior in the recent-file dialog
- Make close/cancel button labels clearer in Thai
- Keep all changes local-only and limited to existing dialogs

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 43: UI Helper QA Report

Goal: make the latest non-GUI helper behavior repeatable.

- Add `scripts/phase43_ui_qa.py`
- Create a PDF under a Thai path and verify text-layer search finds the expected result
- Verify search highlight rectangle scaling
- Verify recent-file add/remove/clear with UTF-8 local JSON
- Verify Save As preflight summary and page-level detail lines
- Verify checklist content includes redaction and Thai-font review items
- Write `data/logs/phase43_ui_qa_report.json`
- Add the QA script to `scripts/release_qa.py`

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/phase43_ui_qa.py`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`

## Phase 44: Final Acceptance Pass

Goal: run a final local acceptance check against the project criteria before adding any new feature.

- Add `scripts/final_acceptance.py`
- Create and open a PDF under a Thai path
- Render preview at normal and zoomed scales
- Check page navigation and page operations on the working copy
- Verify the source PDF hash stays unchanged
- Verify app log, README/ROADMAP, and source hygiene checks
- Write `data/logs/final_acceptance_report.json`
- Add the final acceptance script to `scripts/release_qa.py`

Acceptance gate:

- `python -m pytest`
- `python -m compileall thai_pdf_editor scripts run_app.py tests`
- `python scripts/final_acceptance.py`
- `python scripts/release_qa.py`
- `cmd /c scripts\build_exe.bat`
- `dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test`
