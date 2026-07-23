# AGENTS.md — คู่มือสำหรับ AI ที่เข้ามาทำงานในโปรเจกต์นี้

โปรเจกต์: Thai Local PDF Editor (`D:\PDF editor`)
เอกสารนี้บันทึกปัญหาที่เจอจริงและวิธีแก้ เพื่อไม่ให้ AI ตัวถัดไป (Claude, GPT, หรือตัวอื่น) เสียเวลาไล่ซ้ำ

อ่าน `project.md` และ `ROADMAP.md` ก่อนเสมอเพื่อเข้าใจสโคปและกติกาของระบบ เอกสารนี้เป็นเรื่อง **environment/ops** เท่านั้น ไม่ใช่สเปกฟีเจอร์

---

## 1) เครื่องนี้ Python ไม่ได้อยู่ที่ path เดิมเสมอ

- **ห้ามสมมติ** ว่า python อยู่ที่ `C:\Python314\python.exe` — เคยเป็นแบบนั้นตอน build exe ตัวแรก (`python314.dll` ยังอยู่ใน `dist\ThaiLocalPdfEditor\_internal`) แต่เครื่องเปลี่ยน environment ไปแล้ว
- ให้เช็คก่อนเสมอ: `where python`
- ปัจจุบัน (2026-07-23) python ที่ใช้งานได้จริงคือ
  `C:\Users\WINDOWS\AppData\Local\Programs\Python\Python312\python.exe`
- โปรเจกต์ **ไม่มี `.venv`** — ใช้ global python ตรงๆ (ไม่ตรงกับที่ `project.md`/`README.md` แนะนำให้สร้าง venv จริงๆ ถ้ามีเวลาควรสร้าง `.venv` แล้ว pin เวอร์ชันให้ตรงกับที่ build exe เพื่อกันปัญหานี้ซ้ำ)
- `start.bat` เลือก python ตามลำดับ: `.venv\Scripts\python.exe` → fixed path (`C:\Users\WINDOWS\...\Python312\python.exe`) → python จาก PATH — ถ้าย้ายเครื่องอีก ต้องแก้ fixed path ใน `start.bat` ด้วย

## 2) ก่อนรันแอปครั้งแรกในเครื่องใหม่ ให้ลง dependency ก่อน

```
python -m pip install -r requirements.txt
```

ถ้าจะ build exe ด้วย ให้ลงเพิ่ม:

```
python -m pip install -r requirements-build.txt
```

อาการถ้าลืม: `ModuleNotFoundError: No module named 'customtkinter'` ตอนรัน `run_app.py`

## 3) Build exe

รันผ่าน `cmd /c scripts\build_exe.bat` เท่านั้น (ไม่ใช้ `.spec` ตรงๆ เพราะ script นี้ generate spec ใหม่ทุกครั้งจาก CLI flags ใน `packaging\ThaiLocalPdfEditor.spec`)

- ไอคอนแอป/ไฟล์ pdf ใช้ `assets\icons\pdf_editor.ico` — ผูกไว้ใน `build_exe.bat` ด้วยแฟล็ก `--icon`
- ถ้าจะเปลี่ยนไอคอน ให้รัน `python scripts\make_icon.py` (แก้สคริปต์เพื่อปรับดีไซน์) แล้ว rebuild exe ใหม่
- ปิดโปรแกรมที่กำลังรันอยู่ก่อน build (สคริปต์พยายามปิดให้อัตโนมัติแล้ว แต่ถ้า exe ถูกล็อกอยู่ build จะพัง)

## 4) การตั้งเป็นโปรแกรมเปิดไฟล์ .pdf เริ่มต้น (default app)

Windows ตั้งแต่ Win8 ขึ้นมา **ไม่ยอมให้สคริปต์ตั้ง default app แทนผู้ใช้โดยอัตโนมัติ** (ป้องกัน malware hijack file association) ดังนั้น:

- ทำได้แค่ "register" แอปเข้าระบบผ่าน registry (ProgID `ThaiPDFEditor.pdf` ใต้ `HKCU\Software\Classes`, capabilities ใต้ `HKCU\Software\ThaiPDFEditor`, entry ใน `HKCU\Software\RegisteredApplications`)
- การตั้งเป็น default จริงต้องให้ **ผู้ใช้กดเอง** ผ่านทางใดทางหนึ่ง:
  - `Start-Process 'ms-settings:defaultapps'` แล้วค้นหา `.pdf`
  - หรือ `rundll32.exe shell32.dll,OpenAs_RunDLL "<real .pdf file>"` แล้วติ๊ก "Always use this app"
- เช็คว่าตอนนี้ default เป็นอะไรอยู่ด้วย:
  ```powershell
  Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice' | Select-Object ProgId
  ```
- ไอคอนไฟล์ .pdf ที่ Explorer แสดง มาจาก `DefaultIcon` ของ ProgID ที่เป็น default อยู่จริง — ถ้าไม่ใช่ `ThaiPDFEditor.pdf` ไอคอนจะไม่เปลี่ยนแม้ตั้ง registry ของเราไว้แล้ว (ต้องเช็คข้อ UserChoice ก่อนเสมอถ้าไอคอนไม่ขึ้น)
- หลังแก้ registry ไอคอน ให้ล้าง icon cache: `ie4uinit.exe -ClearIconCache` แล้ว restart explorer (`Stop-Process -Name explorer -Force; Start-Process explorer.exe`)

## 5) Desktop Commander เครื่องนี้ (สำคัญมากสำหรับ AI ที่ใช้เครื่องมือ)

- คำสั่ง `reg` (reg.exe) **ถูกบล็อก** — ห้ามใช้ `reg add`/`reg query` ตรงๆ ให้ใช้ PowerShell registry provider แทน เช่น `New-Item -Path 'HKCU:\...'`, `Set-Item`, `New-ItemProperty`, `Get-ItemProperty`
- Default shell คือ `powershell.exe` — การห่อคำสั่งด้วย `cmd /c "..."` ที่มี quote ซ้อนหลายชั้น (เช่น reg add ที่มีค่าเป็นข้อความไทยที่มีวงเล็บ) จะพังเพราะ powershell parse ก่อนส่งต่อให้ cmd ให้เลี่ยงการซ้อน quote หลายชั้น เขียนเป็น PowerShell คำสั่งเดียวไปเลยจะชัวร์กว่า
- ไฟล์ที่สร้าง/แก้บนเครื่อง user (`D:\...`) ต้องใช้ Desktop Commander (`write_file`, `edit_block`, `start_process` เป็นต้น) **ห้ามใช้** `create_file`/`str_replace`/`view`/`bash_tool` ของ container เพราะเป็นคนละ filesystem กับเครื่อง user

## 5.5) Git ติดตั้งแล้วผ่าน winget (2026-07-23) แต่ PATH ในเซสชันเก่ายังไม่เห็น

- ลง git ด้วย `winget install --id Git.Git -e` สำเร็จแล้ว (v2.55)
- แต่ process ที่ Desktop Commander สร้างใหม่ยังใช้ PATH เก่า (inherit จาก process แม่ตอนตอน MCP server เริ่มทำงาน ก่อน git ติดตั้ง) ทำให้เรียก `git` แล้วขึ้น "not recognized"
- workaround: เติมบรรทัดนี้นำหน้าก่อนเรียก git ทุกครั้งในเซสชันนี้:
  ```powershell
  $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); git ...
  ```
- วิธีแก้ถาวร: ปิด/เปิด Desktop Commander (หรือรีสตาร์ทเครื่อง) ครั้งเดียว แล้ว process ใหม่จะเห็น PATH ที่อัปเดตแล้วโดยไม่ต้องเติมบรรทัดนี้อีก

## 6) บั๊กที่รู้อยู่แล้ว (ดูสถานะก่อนแก้ซ้ำ)

- `thai_pdf_editor/app/core/pdf_document.py` เมธอด `open()`: error path เรียก `working_copy_path.unlink(missing_ok=True)` ตรงๆ แทนที่จะใช้ helper `_remove_working_copy()` ที่ retry/chmod รองรับ Windows file lock — ทำให้ `test_invalid_pdf_returns_thai_error_without_crashing` ล้มเหลวเป็น `PermissionError` บน Windows (พบ 2026-07-23 กับ pymupdf เวอร์ชันใหม่)

## 7) เช็คสุขภาพระบบก่อนเริ่มงานใหญ่

```
python -m pytest -q
python scripts/release_qa.py
```

ถ้า pytest แดง ให้ดูว่าเป็นบั๊กเดิมที่รู้อยู่แล้ว (ข้อ 6) หรือของใหม่ ก่อนจะเดินหน้าฟีเจอร์ต่อ

## 8) React migration

มีแผนอยู่ที่ `REACT_MIGRATION_PLAN.md` แต่ยังไม่เริ่ม (ค้างที่ Phase 0 — freeze baseline + git tag) ห้ามเริ่มแก้ UI เป็น React โดยไม่ยืนยันกับผู้ใช้ก่อน เพราะเป็นงานใหญ่นอกสโคป v1

---

_อัปเดตล่าสุด: 2026-07-23 หลังแก้ปัญหา environment drift (python path, missing deps, missing icon, git ไม่อยู่ใน PATH)_
