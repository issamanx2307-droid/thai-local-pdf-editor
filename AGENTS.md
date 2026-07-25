# AGENTS.md — คู่มือสำหรับ AI ที่เข้ามาทำงานในโปรเจกต์นี้

โปรเจกต์: Thai Local PDF Editor (`D:\PDF editor`)
เอกสารนี้บันทึกปัญหาที่เจอจริงและวิธีแก้ เพื่อไม่ให้ AI ตัวถัดไป (Claude, GPT, หรือตัวอื่น) เสียเวลาไล่ซ้ำ

อ่าน `project.md` และ `ROADMAP.md` ก่อนเสมอเพื่อเข้าใจสโคปและกติกาของระบบ เอกสารนี้เป็นเรื่อง **environment/ops** เท่านั้น ไม่ใช่สเปกฟีเจอร์

---

## 1) เครื่องนี้ Python ไม่ได้อยู่ที่ path เดิมเสมอ (แก้แล้วด้วย `.venv`)

- โปรเจกต์นี้มี **`.venv` แล้ว** (สร้าง 2026-07-23) ให้ใช้ `.venv\Scripts\python.exe` เป็นหลักเสมอ ไม่ต้องพึ่ง python จาก PATH ของเครื่องอีก
- `requirements.txt` และ `requirements-build.txt` **pin เวอร์ชันตายตัวแล้ว** (ไม่ใช่ `>=`) ตามที่ทดสอบผ่านจริงบนเครื่องนี้ ถ้าจะอัปเดตเวอร์ชัน ให้แก้ไฟล์นี้แล้วรัน `python -m pytest -q` ผ่าน venv ยืนยันก่อนทุกครั้ง
- ถ้า `.venv` หายไป (ย้ายเครื่อง/ลบทิ้ง) สร้างใหม่ด้วย:
  ```
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
  ```
- `start.bat` เลือก python ตามลำดับ: `.venv\Scripts\python.exe` (ใช้อันนี้เกือบตลอด) → fixed path เก่า (`C:\Users\WINDOWS\...\Python312\python.exe`, เผื่อ `.venv` หาย) → python จาก PATH (fallback สุดท้าย)
- **ห้ามสมมติ** ว่า python อยู่ที่ `C:\Python314\python.exe` — เคยเป็นแบบนั้นตอน build exe ตัวแรก แต่เครื่องเปลี่ยน environment ไปแล้ว ตอนนี้ใช้ `.venv` แทนเพื่อกันปัญหานี้ซ้ำถาวร

## 2) ก่อนรันแอปครั้งแรกในเครื่องใหม่ ให้ลง dependency ก่อน (ผ่าน `.venv`)

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

ถ้าจะ build exe ด้วย ให้ลงเพิ่ม:

```
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

อาการถ้าลืม: `ModuleNotFoundError: No module named 'customtkinter'` ตอนรัน `run_app.py`

## 3) Build exe (Tkinter app — **เลิกใช้แล้ว 2026-07-25**, เก็บโค้ดไว้เป็น fallback เท่านั้น)

**Tauri app (ข้อ 9) เป็นตัวหลักที่ผู้ใช้ใช้งานจริงแล้ว** ไฟล์ build เดิมที่ `dist\ThaiLocalPdfEditor\` ถูกลบไปแล้ว (source ที่ `thai_pdf_editor/` ยังอยู่ครบ, bridge เดียวกันถูกใช้เป็น backend ของ Tauri app ด้วย) ห้ามลบ source หรือเทสต์ของ `thai_pdf_editor/` เพราะ Tauri sidecar (`run_react_bridge.py` → `react_shell/local_bridge.py`) import โค้ดชุดนี้ตรงๆ

ถ้าจำเป็นต้อง build .exe แบบ Tkinter เดิมอีกครั้ง (เช่น debug เทียบ behavior):

รันผ่าน `cmd /c scripts\build_exe.bat` เท่านั้น (ไม่ใช้ `.spec` ตรงๆ เพราะ script นี้ generate spec ใหม่ทุกครั้งจาก CLI flags ใน `packaging\ThaiLocalPdfEditor.spec`)

- ไอคอนแอป/ไฟล์ pdf ใช้ `assets\icons\pdf_editor.ico` — ผูกไว้ใน `build_exe.bat` ด้วยแฟล็ก `--icon`
- ถ้าจะเปลี่ยนไอคอน ให้รัน `python scripts\make_icon.py` (แก้สคริปต์เพื่อปรับดีไซน์) แล้ว rebuild exe ใหม่
- ปิดโปรแกรมที่กำลังรันอยู่ก่อน build (สคริปต์พยายามปิดให้อัตโนมัติแล้ว แต่ถ้า exe ถูกล็อกอยู่ build จะพัง)

## 4) การตั้งเป็นโปรแกรมเปิดไฟล์ .pdf เริ่มต้น (default app)

Windows ตั้งแต่ Win8 ขึ้นมา **ไม่ยอมให้สคริปต์ตั้ง default app แทนผู้ใช้โดยอัตโนมัติ** (ป้องกัน malware hijack file association) ดังนั้น:

- **ตอนนี้ ProgID ที่ถูกต้องคือ `Thai Local PDF`** (Tauri สร้างให้อัตโนมัติตอนติดตั้ง จาก `fileAssociations` ใน `tauri.conf.json`) ProgID เก่า `ThaiPDFEditor.pdf` (ของ Tkinter exe) ถูกลบออกจาก registry แล้ว (2026-07-25) — ถ้าเจอ ProgID นี้โผล่มาอีกแปลว่ามีอะไรสร้างมันขึ้นมาใหม่ ให้เช็คว่าทำไม
- การตั้งเป็น default จริงต้องให้ **ผู้ใช้กดเอง** ผ่านทางใดทางหนึ่ง:
  - `Start-Process 'ms-settings:defaultapps'` แล้วค้นหา `.pdf`
  - หรือ `rundll32.exe shell32.dll,OpenAs_RunDLL "<real .pdf file>"` แล้วติ๊ก "Always use this app"
- เช็คว่าตอนนี้ default เป็นอะไรอยู่ด้วย:
  ```powershell
  Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice' | Select-Object ProgId
  ```
- ไอคอนไฟล์ .pdf ที่ Explorer แสดง มาจาก `DefaultIcon` ของ ProgID ที่เป็น default อยู่จริง — ถ้าไม่ตรงกับที่ตั้งไว้ ไอคอนจะไม่เปลี่ยน (ต้องเช็คข้อ UserChoice ก่อนเสมอถ้าไอคอนไม่ขึ้น)
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

## 6) บั๊กที่แก้ไปแล้ว (2026-07-23)

- `thai_pdf_editor/app/core/pdf_document.py` เมธอด `open()`: error path เดิมเรียก `working_copy_path.unlink(missing_ok=True)` ตรงๆ ไม่ใช้ helper `_remove_working_copy()` — แก้แล้วให้ใช้ helper เสมอ, ย้าย cleanup ออกมานอก `except` block, เปลี่ยน `LOGGER.exception()` เป็น log ข้อความ traceback ที่ format เป็น string แล้ว (กัน reference ค้าง), และเพิ่ม `gc.collect()` ใน retry loop ของ `_remove_working_copy()`
- **ข้อควรระวังตอน debug ปัญหานี้**: ถ้าเทสต์ `test_invalid_pdf_returns_thai_error_without_crashing` ยัง fail แบบไฟล์ `_working.pdf` ค้างอยู่ ให้เช็คก่อนว่าเป็นไฟล์ **ขยะเก่าจากการรันเทสต์ครั้งก่อนๆ** ที่ค้างใน `data/temp/` หรือไม่ (glob pattern ของเทสต์นี้ match ได้กับไฟล์เก่าจากรันก่อนหน้าด้วย ไม่ใช่แค่ไฟล์ของรันปัจจุบัน) ลบไฟล์ `*acceptance_unique*_working.pdf` ใน `data/temp/` ทิ้งก่อนสรุปว่าโค้ดยังพัง

## 7) เช็คสุขภาพระบบก่อนเริ่มงานใหญ่

```
python -m pytest -q
python scripts/release_qa.py
```

ถ้า pytest แดง ให้ดูว่าเป็นบั๊กเดิมที่รู้อยู่แล้ว (ข้อ 6) หรือของใหม่ ก่อนจะเดินหน้าฟีเจอร์ต่อ

## 8) React migration → **Tauri app คือของจริงแล้ว ไม่ใช่แค่แผนอีกต่อไป**

`REACT_MIGRATION_PLAN.md` เดิมวางแผนไว้เฉยๆ แต่ตอนนี้ (2026-07-25) build จริงแล้วและ **ผู้ใช้เปลี่ยนมาใช้ Tauri app เป็นหลักแทน Tkinter exe แล้ว** ดูข้อ 9

## 9) Tauri app (ตัวหลักที่ใช้งานจริงตอนนี้)

**สถาปัตยกรรม**: `react_shell/src/` (React/Vite UI) + `react_shell/src-tauri/` (Rust shell) เรียก sidecar process `pdf-bridge.exe` (PyInstaller build ของ `run_react_bridge.py` → `react_shell/local_bridge.py`, import โค้ด `thai_pdf_editor/` ตรงๆ) bridge ฟัง HTTP ที่ `127.0.0.1:5178`

**ติดตั้งอยู่ที่**: `%LOCALAPPDATA%\Programs\Thai Local PDF Editor\` (per-user install, ไม่ต้อง admin) — **ห้าม** ปล่อยให้ installer ติดตั้งที่ path default ที่มันจำมาจาก registry เดิม (เจอปัญหานี้มาแล้ว — NSIS จำ `InstallLocation` เก่าจาก registry แม้ uninstall ไปแล้วก็ยังจำอยู่ถ้า registry key ไม่ถูกลบสมบูรณ์) ระบุ path เองเสมอตอน install แบบ silent:
```powershell
Start-Process -FilePath "<installer.exe>" -ArgumentList "/S", "/D=$env:LOCALAPPDATA\Programs\Thai Local PDF Editor" -Wait
```

**Build ลำดับที่ถูกต้อง** (ต้อง build sidecar ก่อนเสมอ ไม่งั้น Tauri จะห่อ sidecar เก่าที่ค้างอยู่):
```
scripts\build_react_bridge.bat        REM 1. build sidecar (PyInstaller) ก่อน
cd react_shell
set NODE_ENV=development
npm run tauri:build                    REM 2. ถึงจะ build ตัว Tauri app (ห่อ sidecar เข้าไปด้วย)
```
**เคยพลาดมาแล้ว**: แก้ `local_bridge.py` แล้วลืม rebuild sidecar exe ก่อน build tauri:build → ได้ app ใหม่ที่ยังมีบั๊กเดิมฝังอยู่ใน sidecar เพราะ Tauri แค่ก็อปปี้ `binaries/pdf-bridge-x86_64-pc-windows-msvc.exe` ที่มีอยู่แล้วเข้าไปห่อ ไม่ได้ build ให้ใหม่

**NODE_ENV=production ตั้งไว้ระดับระบบ** — ทำให้ `npm install` ข้าม devDependencies เงียบๆ (eslint/vite/typescript หายจาก `node_modules`) ต้อง `set NODE_ENV=development` นำหน้า `npm install`/`npm run tauri:build` เสมอในเซสชันนี้

**Sidecar เป็น PyInstaller `--onefile` → มี process ซ้อน 2 ชั้น**: bootloader process spawn child process จริงอีกที การฆ่าแค่ `CommandChild.kill()` (จาก tauri-plugin-shell) ฆ่าได้แค่ bootloader ตัวลูกไม่ตาย ต้องเสริม `taskkill /F /IM pdf-bridge.exe /T` ใน `src-tauri/src/lib.rs` ด้วย (ดู `kill_pdf_bridge_tree()`) ถึงจะฆ่าครบทั้ง process tree ตอนปิดแอป — ทดสอบต้องปิดแอปแบบ **graceful** (`$proc.CloseMainWindow()` หรือกด X จริง) เท่านั้น `Stop-Process -Force` จะข้าม cleanup code ทุกแอปอยู่แล้ว ไม่ใช่การทดสอบที่ถูกต้อง

**ความปลอดภัย CORS**: `local_bridge.py` `_allowed_origin()` ต้องคืนค่า origin ที่รู้จักเท่านั้น (`ALLOWED_DEV_ORIGINS`/`DEFAULT_DEV_ORIGIN`) **ห้ามคืน `"*"` แม้จะบอกว่า bind 127.0.0.1 แล้วปลอดภัย** — เว็บอันตรายที่เปิดในเบราว์เซอร์เครื่องเดียวกันยิง fetch เข้า localhost ได้ปกติ ถ้า CORS เป็น `*` เว็บนั้นอ่าน response กลับไปได้ด้วย มีเทสต์ (`tests/test_react_bridge.py`) จับเรื่องนี้อยู่แล้ว ถ้าแก้แล้ว pytest แดงตรงนี้คือของจริง

**`react_shell/src-tauri/binaries/` gitignore ไว้** (exe compiled ~34MB, machine-specific) build ใหม่ทุกครั้งด้วย `scripts\build_react_bridge.bat` แทนการ commit

---

_อัปเดตล่าสุด: 2026-07-25 — Tauri app กลายเป็นตัวหลักที่ใช้งานจริง, Tkinter exe เลิกใช้แล้ว, ProgID เก่าถูกลบออกจาก registry
