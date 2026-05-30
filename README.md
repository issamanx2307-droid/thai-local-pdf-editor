# Thai Local PDF Editor

แอพแก้ไข PDF ภาษาไทยแบบ local-first สำหรับ Windows ใช้ Python, CustomTkinter และ PyMuPDF ไม่มี server, login, cloud storage หรือการเปิดพอร์ตใด ๆ รวมถึงพอร์ต 8000 ยกเว้นการดาวน์โหลดฟอนต์ฟรีจาก Google Fonts เมื่อผู้ใช้กดสั่งนำเข้าฟอนต์เอง

## ติดตั้ง

```powershell
chcp 65001
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

สำหรับ build เป็น `.exe`:

```powershell
pip install -r requirements-build.txt
cmd /c scripts\build_exe.bat
```

`requirements.txt` เก็บเฉพาะ runtime dependency ของแอพ ส่วน `requirements-build.txt` ใช้สำหรับ test/build เท่านั้น

## รัน

```powershell
python run_app.py
```

หรือใช้ launcher ที่ root:

```bat
start.bat
stop.bat
```

สำหรับตรวจ smoke แบบไม่ค้างหน้าต่าง:

```powershell
python run_app.py --smoke-test
cmd /c start.bat --smoke-test
cmd /c stop.bat
```

## ฟีเจอร์ที่ทำเสร็จ

- เปิด PDF และแสดง preview หน้าปัจจุบัน
- ลากไฟล์ PDF มาวางเพื่อเปิดไฟล์
- เปลี่ยนหน้า previous/next และเลือกหน้าจากรายการหน้า
- zoom in, zoom out, fit width
- ค้นหาข้อความใน PDF จาก text layer, เปิดรายการผลลัพธ์, ไปผลลัพธ์ก่อนหน้า/ถัดไป, เลือกผลลัพธ์เพื่อไปหน้านั้น และแสดงกรอบ highlight ชั่วคราวบน preview
- ปุ่มลัดคีย์บอร์ด: `PageUp`/`PageDown` เปลี่ยนหน้าก่อนหน้า/ถัดไป และ `Home`/`End` ไปหน้าแรก/หน้าสุดท้ายเมื่อไม่ได้โฟกัสช่องกรอกข้อความ
- undo/redo สำหรับ overlay ที่ยังไม่ได้ Save As
- หมุนหน้า, ลบหน้า, ย้ายหน้าขึ้น/ลง, ทำซ้ำหน้า
- crop หน้าปัจจุบันด้วยการลากพื้นที่ที่ต้องการเก็บไว้
- Save As แบบปลอดภัย เขียน temp file และตรวจเปิดได้ก่อนคัดลอกไปปลายทาง
- Save As preflight: ก่อนบันทึกจะแสดงสรุปรายการที่กำลังจะเขียนลงไฟล์ใหม่, รายละเอียดตามหน้า และเตือนชัดเมื่อมี redaction/แก้ข้อความเดิม
- แก้ฟอร์ม PDF ที่มีอยู่แล้ว เฉพาะ text field และ checkbox
- แก้ข้อความเดิมแบบปลอดภัย: ค้นหาข้อความที่ฝังอยู่ใน PDF แล้ว redaction สีขาวก่อนวางข้อความใหม่ทับตำแหน่งเดิมผ่าน Save As
- หา/โหลดฟอนต์จาก PDF: อ่านชื่อฟอนต์จาก text layer/font resource, นำเข้าฟอนต์ที่ตรงหรือใกล้เคียงเข้า `assets/fonts/imported`, และดาวน์โหลดฟอนต์ฟรีจาก Google Fonts เมื่อไม่มีฟอนต์ในเครื่อง
- เพิ่มข้อความลง PDF พร้อมเลือกฟอนต์ `.ttf` สำหรับภาษาไทย
- เพิ่มรูปภาพหรือลายเซ็นภาพ PNG/JPG
- สร้างลายเซ็นภาพแบบง่ายจากข้อความในเครื่อง แล้ววางลง PDF เป็น image overlay ผ่าน Save As
- วาดกล่องและ highlight
- redaction จริงด้วย PyMuPDF `add_redact_annot` และ `apply_redactions`
- แยกหน้าปัจจุบันเป็น PDF ใหม่
- ส่งออก PDF เป็น JPG โดยเลือกหน้าปัจจุบันหรือทุกหน้า, DPI, คุณภาพ JPG และโฟลเดอร์ปลายทางได้
- Batch JPG แบบ local sequential: เลือก PDF หลายไฟล์แล้วส่งออกทุกหน้าเป็น JPG พร้อม `batch_jpg_report.json`
- รวม PDF หลายไฟล์
- แก้ metadata ของ PDF เช่น ชื่อเรื่อง ผู้เขียน หัวข้อ และคำค้น ผ่าน Save As
- เตือนก่อนเปิดไฟล์ใหม่หรือปิดโปรแกรมเมื่อมีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก
- จัดการรายการที่วางแล้วก่อน Save As: ดู pending overlays, ลบรายการที่เลือก, ย้ายซ้าย/ขวา/ขึ้น/ลง, และย่อ/ขยาย
- Recent files: เก็บรายชื่อ PDF ที่เปิดล่าสุดใน `data/settings/recent_files.json` แบบ local-only, รองรับ path ภาษาไทย, แสดง path เต็ม, ลบรายการเดียว และล้างทั้งหมดได้
- หน้าต่างตรวจงานก่อนส่งพร้อม checklist สำหรับตรวจไฟล์ผลลัพธ์, ไฟล์ต้นฉบับ, redaction, ฟอนต์ไทย, รูป/ลายเซ็นภาพ และ path ภาษาไทย
- log ที่ `data/logs/app.log`

## สิ่งที่ตั้งใจไม่ใส่ในระบบ

- OCR: ไม่ใส่เข้ามาในระบบตามข้อกำหนดล่าสุด เพื่อลด dependency, runtime ภายนอก และความซับซ้อนของการติดตั้ง
- Plugin system: ตัดออกจาก scope ไม่ต้องเพิ่มระบบปลั๊กอิน
- Cloud sync / cloud storage: ตัดออกจาก scope แอพต้องทำงาน local-only
- User account / login: ตัดออกจาก scope ไม่ต้องมีบัญชีผู้ใช้หรือระบบสิทธิ์
- AI integration: ตัดออกจาก scope ไม่ต้องเพิ่มระบบ AI
- PDF to Word แบบ OCR/layout reconstruction: ไม่ใส่ใน PDF editor นี้ ให้ใช้แอพ `D:\pdf_doc` แยกต่างหาก
- Digital signature certificate/PKI: ยังไม่ใส่ในระบบ ปุ่มลายเซ็นในแอพเป็นการวางหรือสร้างรูปลายเซ็นเท่านั้น ไม่ใช่การเซ็นเอกสารด้วย certificate

## งานที่ต้องถามก่อนลงมือ

- Batch automation ใหญ่ที่เกินกว่า Batch JPG แบบ local sequential: ต้องถามและได้รับคำยืนยันก่อนลงมือทุกครั้ง

## ฟีเจอร์ที่ยังไม่ทำใน v1

- แก้ข้อความเดิมแบบ reflow เต็มรูปแบบเหมือน Word/Acrobat เช่น ตัดบรรทัดใหม่ทั้งย่อหน้า เลื่อน layout อัตโนมัติ หรือรักษา font run ซับซ้อนทุกกรณี
- สร้าง PDF form ใหม่หรือแก้ฟอร์มซับซ้อน เช่น dropdown, radio group, validation script
- digital signature certificate จริง ต้องออกแบบ PKI/certificate workflow แยกต่างหากก่อนทำ

## วิธีทดสอบ

```powershell
python -m pytest
python -m compileall thai_pdf_editor scripts run_app.py tests
python run_app.py --smoke-test
cmd /c start.bat --smoke-test
cmd /c stop.bat
python scripts/phase7_qa.py --include-gui
python scripts/font_import_qa.py
python scripts/overlay_edit_qa.py
python scripts/phase43_ui_qa.py
python scripts/release_qa.py
python scripts/final_acceptance.py
cmd /c scripts\build_exe.bat
dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe --smoke-test
```

## สถาปัตยกรรมและความเสี่ยง

- State flow: UI รับ input แล้วเรียก core service, core อัปเดต `DocumentState`, renderer อ่าน state เพื่อแสดง preview; canvas ไม่เป็น source of truth
- Dirty guard: ถ้า `DocumentState.dirty` เป็นจริง แอพจะถามยืนยันก่อนเปิด PDF ใหม่หรือปิดหน้าต่าง เพื่อกันการทิ้งงานที่ยังไม่ได้ Save As โดยไม่ตั้งใจ
- Undo/redo scope: รุ่นนี้ย้อนกลับ/ทำซ้ำได้เฉพาะ pending overlay ที่ยังไม่ได้ Save As เช่น ข้อความ รูป กล่อง highlight และ redaction mark; page operation ที่แก้ working PDF แล้วจะไม่ถูกย้อนกลับแบบเดา
- PDF form scope: แก้ได้เฉพาะฟอร์มที่มีอยู่แล้วชนิด text field และ checkbox จากนั้นต้อง Save As เป็นไฟล์ใหม่ ยังไม่สร้าง field ใหม่หรือรองรับสคริปต์/ฟอร์มซับซ้อน
- Signature scope: ฟีเจอร์ลายเซ็นปัจจุบันเป็น image overlay สำหรับรูปหรือลายเซ็นภาพเท่านั้น สร้าง PNG โปร่งใสไว้ที่ `data/signatures` ได้ แต่ยังไม่มี cryptographic signing, certificate validation, timestamping หรือ PKI chain
- Existing text replacement scope: การแก้ข้อความเดิมใช้การค้นหา text layer ของ PDF, redaction สีขาว, แล้ววางข้อความใหม่ทับตำแหน่งเดิม จึงเหมาะกับการแก้คำ/วลีสั้น ๆ ที่ค้นหาเจอ ไม่ใช่ reflow เอกสารทั้งย่อหน้าแบบ Word/Acrobat
- Text search: ค้นหาจาก text layer ของ PDF เท่านั้น ถ้า PDF เป็นภาพสแกนล้วนจะไม่เจอข้อความ เพราะไม่มี OCR ตาม scope ของโปรเจกต์ กรอบ highlight เป็น preview ชั่วคราวและไม่ถูกเขียนลง PDF
- Recent files: เก็บเฉพาะ path ในเครื่องและกรองไฟล์ที่ไม่มีอยู่แล้วออกเมื่อโหลดรายการ
- Manual QA checklist: เป็นรายการตรวจในเครื่องเท่านั้น ไม่รับรองผลแทนการเปิดไฟล์ปลายทางตรวจจริง โดยเฉพาะงาน redaction และข้อความไทย
- Main window structure: `main_window.py` เป็นไฟล์ประกอบ UI เป็นหลัก ส่วน action ถูกแยกไว้ใต้ `thai_pdf_editor/app/ui/actions` เพื่อคุมขนาดไฟล์และลดความเสี่ยงเวลาแก้ต่อ
- JPG export: ส่งออกจากสำเนาในหน่วยความจำและ temp JPG ก่อนคัดลอกไปปลายทาง เลือกได้ระหว่างหน้าปัจจุบัน/ทุกหน้า, DPI 96/150/300 และคุณภาพ 1-100 จึงไม่แก้ไฟล์ PDF ต้นฉบับ และไม่ overwrite JPG เดิมในโฟลเดอร์ปลายทาง
- Batch JPG: ทำงานทีละไฟล์แบบ sequential ในเครื่อง เขียน report ว่าไฟล์ไหนสำเร็จ/ล้มเหลว และไปไฟล์ถัดไปได้ถ้าบางไฟล์เสีย
- QA workflow: `python scripts/phase7_qa.py --include-gui` ตรวจ path ภาษาไทย, edit/save, form fill, redaction, export JPG, extract, merge และ hash ไฟล์ต้นฉบับ
- Font import QA: `python scripts/font_import_qa.py` สร้าง PDF ภาษาไทยที่ฝังฟอนต์จริง, ตรวจการอ่านชื่อฟอนต์, นำเข้าฟอนต์เข้า `assets/fonts/imported`, และบันทึกผลที่ `data/logs/font_import_qa_report.json`
- Overlay edit QA: `python scripts/overlay_edit_qa.py` ตรวจการลบ/ย้าย/ย่อ/ขยายรายการที่วางแล้ว, ลายเซ็นภาพ, Save As และ hash ไฟล์ต้นฉบับ
- Phase 43 UI QA: `python scripts/phase43_ui_qa.py` ตรวจ search highlight geometry, recent files, Save As preflight details และ checklist helpers พร้อม report
- Final acceptance: `python scripts/final_acceptance.py` ตรวจเปิด/render PDF, navigation, zoom, page operations, hash ไฟล์ต้นฉบับ, app log, README/ROADMAP และ source hygiene
- Concurrency: v1 ใช้ single-threaded เป็นหลักเพื่อลด race condition ระหว่าง UI, `DocumentState` และ PyMuPDF document
- Save transaction boundary: เขียนไฟล์ฐานไป `data/temp`, apply redaction แล้วจึง apply overlay บน temp document, save temp output, reopen ตรวจสอบ, แล้วค่อย copy ไปปลายทาง
- Idempotency: ถ้า save fail ที่ขั้นใด ไฟล์ต้นฉบับไม่ถูกเขียนทับ และ temp output จะถูกลบใน `finally`
- Retry strategy: ถ้า file I/O fail ให้ผู้ใช้เลือก path ใหม่หรือปิดโปรแกรมที่ล็อกไฟล์ แล้ว Save As ซ้ำ; แอพไม่ retry เขียนทับ path เดิมแบบเงียบ ๆ

## ภาษาไทยและฟอนต์

- เปิด PowerShell ด้วย `chcp 65001` ก่อนติดตั้งหรือรันถ้าเห็นข้อความไทยเพี้ยน
- UI ใช้ฟอนต์ Windows ที่อ่านไทยได้ เช่น Tahoma, Leelawadee UI หรือ Segoe UI
- ปุ่ม `หา/โหลดฟอนต์` จะอ่านชื่อฟอนต์จาก PDF ก่อน ถ้าพบฟอนต์ในเครื่องจะ copy เข้า `assets/fonts/imported`; ถ้าไม่มีและมี mapping ฟอนต์ฟรีที่ใกล้เคียง จะดาวน์โหลดจาก Google Fonts แล้วตั้งเป็นฟอนต์สำหรับแก้ข้อความ
- หลังหา/โหลดฟอนต์ แอพจะแสดงรายงานว่าเจอชื่อฟอนต์อะไรใน PDF, ใช้ข้อมูลจากหน้าใด, สถานะเป็นฟอนต์ตรง/ฟอนต์ใกล้เคียง/ดาวน์โหลด/ยังหาไม่ได้, และไฟล์ฟอนต์ใดถูกตั้งเป็นฟอนต์แก้ข้อความ
- ปุ่มหลักและ panel ตั้งค่าขนาดขั้นต่ำไว้ให้รองรับข้อความไทยยาว เช่น `ลายเซ็นภาพ` และ `ลบ/ปิดทับข้อมูลถาวร`
- Scrollbar ของ preview และรายการหน้าถูกขยายให้จับง่ายขึ้น และเลื่อนด้วยลูกกลิ้งเมาส์ได้เมื่อเมาส์อยู่เหนือพื้นที่นั้น
- ปุ่มลัด `PageUp`, `PageDown`, `Home`, และ `End` ใช้กับการนำทางเอกสาร แต่จะปล่อยให้ช่องกรอกข้อความใช้ปุ่มเหล่านี้ตามปกติ
- ค่าเริ่มต้นสำหรับเพิ่มข้อความไทยลง PDF คือ `D:\ฟอนท์ไทย\THSarabunNew.ttf`
- ถ้าไม่พบไฟล์นี้ แอพจะ fallback ไปที่ฟอนต์ Windows เช่น `C:\Windows\Fonts\tahoma.ttf`
- ถ้า PDF เป็นภาพสแกนล้วนหรือไม่มีข้อมูลฟอนต์ที่เทียบได้ แอพจะแจ้งว่า `ไม่สามารถหาข้อมูลได้` โดยไม่ใช้ OCR หรือ AI
- ใช้ `pathlib.Path` และมี test path ภาษาไทย เช่น `เอกสารลูกค้า/ใบเสนอราคา.pdf`

## ข้อควรระวังเรื่อง redaction

redaction ในแอพนี้เป็นการลบข้อมูลถาวรจริงจาก temp document ก่อน Save As ไม่ใช่แค่วาดกล่องดำทับ ข้อมูลที่ถูก redact แล้วในไฟล์ปลายทางจะกู้คืนไม่ได้ ควรบันทึกเป็นชื่อไฟล์ใหม่เสมอและตรวจไฟล์ผลลัพธ์ก่อนส่งต่อ

การแก้ข้อความเดิมก็ใช้ redaction สีขาวเพื่อลบข้อความเดิมจริงก่อนวางข้อความใหม่ ดังนั้นไฟล์ปลายทางจะกู้ข้อความเดิมคืนไม่ได้ และควรตรวจ layout หลัง Save As ทุกครั้ง โดยเฉพาะถ้าข้อความใหม่ยาวกว่าพื้นที่เดิมหรือ PDF ใช้ font/encoding ฝังแบบพิเศษ

## ข้อจำกัด

v1 ใช้ single-threaded เป็นหลักเพื่อความเสถียร หากเปิด PDF ใหญ่มาก preview อาจใช้เวลาสักครู่ แอพนี้ทำงาน local-only และไม่ส่งไฟล์ PDF ออกนอกเครื่อง
