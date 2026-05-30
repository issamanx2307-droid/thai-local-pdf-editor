\# PROJECT: Thai Local PDF Editor --- Python Desktop App

คุณคือ Senior Python Desktop Engineer + PDF Processing Engineer

ให้สร้างแอพแก้ไข PDF ภาษาไทยแบบ Local Only สำหรับใช้งานคนเดียวบน Windows
เป็นหลัก

เป้าหมาย:

สร้างแอพ Python สำหรับเปิด ดู แก้ไข จัดหน้า และบันทึกไฟล์ PDF แบบใช้งานง่าย
ภาษาไทยทั้งระบบ ไม่ต้องมี server ไม่ต้องมี login ไม่ต้องเชื่อม cloud ไม่ต้องใช้
internet

\-\--

\## 1) ข้อกำหนดหลัก

\### ระบบต้องเป็น

\- Python desktop app

\- Local only

\- ใช้คนเดียว

\- ใช้งานบน Windows ได้ดี

\- UI ภาษาไทย

\- รองรับชื่อไฟล์/โฟลเดอร์ภาษาไทย

\- รองรับข้อความภาษาไทยใน UI และ PDF เท่าที่ไลบรารีรองรับ

\- โค้ดต้อง clean, stable, maintainable

\- ห้ามสร้างระบบใหญ่เกินจำเป็น

\- ห้ามสร้าง web server

\- ห้ามใช้ database server

\- ห้ามใช้ cloud service

\- ห้ามใช้ API ภายนอก

\- ห้ามส่งข้อมูล PDF ออกนอกเครื่อง

\### Tech stack ที่ให้ใช้

\- Python 3.11+

\- CustomTkinter สำหรับ UI

\- PyMuPDF หรือ fitz สำหรับ render, preview, edit PDF

\- Pillow สำหรับแปลง/จัดการภาพ preview

\- pypdf หรือ pikepdf สำหรับ merge/split/metadata/repair ถ้าจำเป็น

\- pathlib สำหรับ path ทั้งหมด

\- logging สำหรับ log

\- pytest สำหรับ test

หลีกเลี่ยง:

\- ไม่ใช้ PyQt ถ้าไม่จำเป็น

\- ไม่ใช้ Electron

\- ไม่ใช้ Flask/FastAPI/Django

\- ไม่ใช้ multiprocessing ถ้าไม่จำเป็น

\- ไม่ใช้ global state ที่แก้ยาก

\-\--

\## 2) Encoding และภาษาไทย

ต้องรองรับภาษาไทยตั้งแต่ต้น

ข้อกำหนด:

\- ทุกไฟล์ source code ต้องเป็น UTF-8

\- ทุกไฟล์ \`.py\` ต้องใส่ header:

\# -\*- coding: utf-8 -\*-

\- ใช้ pathlib.Path แทน string path

\- ห้าม hardcode path แบบ Windows backslash

\- รองรับชื่อไฟล์ภาษาไทย เช่น:

\- ใบเสนอราคา.pdf

\- เอกสารลูกค้า/สัญญาเช่า.pdf

\- ใน README ต้องแนะนำผู้ใช้ Windows PowerShell:

chcp 65001

ฟอนต์:

\- UI ใช้ font ที่อ่านไทยได้ เช่น Tahoma, Leelawadee UI, Segoe UI

\- สำหรับการเพิ่มข้อความลง PDF ให้รองรับการเลือก font file \`.ttf\`

\- เตรียมโฟลเดอร์:

assets/fonts/

\- ถ้าไม่มี font ให้แจ้งเตือนผู้ใช้แบบสุภาพ ไม่ crash

\- ห้าม assume ว่าเครื่องมี THSarabunNew เสมอ

\- ให้ตั้งค่า default font fallback:

1\. Tahoma

2\. Leelawadee UI

3\. Segoe UI

4\. user-selected .ttf

\-\--

\## 3) ฟีเจอร์ Version 1

ให้สร้าง MVP ที่ stable ก่อน ห้ามใส่ฟีเจอร์ซับซ้อนเกินไป

\### 3.1 เปิดและดู PDF

\- เปิดไฟล์ PDF

\- แสดง preview หน้าปัจจุบัน

\- แสดงจำนวนหน้าทั้งหมด

\- ไปหน้าถัดไป/ก่อนหน้า

\- ช่องกรอกเลขหน้า

\- zoom in / zoom out / fit width

\- แสดง thumbnail ด้านซ้ายแบบเบื้องต้น หรือ list หน้าแทน thumbnail ได้ใน v1

\- รองรับ drag & drop เฉพาะถ้าทำได้ง่ายและไม่ทำให้ระบบไม่เสถียร

\### 3.2 จัดการหน้า PDF

ต้องทำได้:

\- หมุนหน้าซ้าย/ขวา 90 องศา

\- ลบหน้า

\- แยกหน้าออกเป็น PDF ใหม่

\- รวม PDF หลายไฟล์

\- reorder หน้าแบบง่าย:

\- เลือกหน้า

\- ปุ่มย้ายขึ้น

\- ปุ่มย้ายลง

\- duplicate หน้า

\- extract selected pages

\### 3.3 เพิ่มข้อความลง PDF

ต้องทำได้:

\- เลือกตำแหน่งบนหน้า

\- ใส่ข้อความ

\- เลือกขนาดตัวอักษร

\- เลือกสีตัวอักษร

\- เลือก font file ได้

\- รองรับภาษาไทยด้วย font ที่ผู้ใช้เลือก

\- preview ก่อนบันทึก

\- เก็บ text overlay เป็น pending operations ก่อน apply จริง

\### 3.4 เพิ่มรูปภาพ / ลายเซ็น

ต้องทำได้:

\- เลือกรูปภาพ PNG/JPG

\- วางบนหน้า PDF

\- ปรับขนาดแบบง่าย

\- ย้ายตำแหน่ง

\- เหมาะกับใช้เป็นลายเซ็นหรือ stamp

\- รองรับภาพพื้นหลังโปร่งใส PNG

\### 3.5 Highlight / กล่อง / เส้น

ทำแบบพื้นฐาน:

\- วาดสี่เหลี่ยม

\- วาดเส้น

\- highlight แบบ rectangle โปร่งแสง

\- เลือกสีได้

\- กำหนดความหนาเส้นได้

\### 3.6 Redaction แบบปลอดภัย

สำคัญมาก:

\- ถ้าทำ redaction ต้องเป็น redaction จริง ไม่ใช่แค่เอากล่องดำปิดทับ

\- ใช้ PyMuPDF redaction API เช่น add_redact_annot + apply_redactions

\- ตั้งชื่อเมนูเป็น:

"ลบ/ปิดทับข้อมูลถาวร"

\- แสดงคำเตือนก่อน apply:

"การลบข้อมูลถาวรจะไม่สามารถกู้คืนได้ ควรบันทึกเป็นไฟล์ใหม่"

\- ห้ามใช้แค่ rectangle สีดำแล้วเรียกว่า redaction

\### 3.7 Save

ต้องมี:

\- Save As เท่านั้นใน v1

\- ไม่เขียนทับไฟล์ต้นฉบับโดยไม่ถาม

\- ก่อน save ให้สร้างไฟล์ temp ก่อน

\- save สำเร็จแล้วค่อย replace หรือ copy

\- ถ้า save fail ต้องไม่ทำให้ไฟล์ต้นฉบับเสีย

\- หลัง save แสดงข้อความสำเร็จ

\- เก็บ backup optional:

backups/

\- ตั้งชื่อไฟล์ default:

originalname_edited.pdf

\-\--

\## 4) ฟีเจอร์ที่ห้ามทำใน Version 1

ห้ามทำใน v1:

\- OCR

\- แก้ข้อความเดิมใน PDF แบบเหมือน Word

\- PDF form editor ซับซ้อน

\- digital signature certificate จริง

\- password cracking

\- cloud sync

\- user account

\- plugin system

\- AI integration

\- batch automation ใหญ่ ๆ

\- ระบบ permissions หลาย user

หมายเหตุ:

PDF editor v1 นี้เน้น overlay/edit/page operations ไม่ใช่แก้ content เดิมแบบ
Acrobat เต็มรูปแบบ

\-\--

\## 5) UX/UI ภาษาไทย

หน้าจอหลักควรมี layout:

ด้านบน:

\- ปุ่มเปิดไฟล์

\- ปุ่มบันทึกเป็น

\- ปุ่ม undo

\- ปุ่ม redo

\- zoom

\- page navigation

ด้านซ้าย:

\- รายการหน้า PDF

\- ปุ่มย้ายหน้า

\- ปุ่มลบหน้า

\- ปุ่มหมุนหน้า

\- ปุ่มแยกหน้า

ตรงกลาง:

\- PDF preview canvas

\- รองรับ scroll

\- รองรับ zoom

ด้านขวา:

\- เครื่องมือ:

\- เพิ่มข้อความ

\- เพิ่มรูป/ลายเซ็น

\- วาดกล่อง

\- highlight

\- redaction

\- crop

\- metadata

ด้านล่าง:

\- status bar ภาษาไทย เช่น:

\- พร้อมใช้งาน

\- กำลังเปิดไฟล์\...

\- บันทึกสำเร็จ

\- เกิดข้อผิดพลาด: \...

หลักการ UX:

\- ปุ่มต้องชื่อไทยชัดเจน

\- ข้อความ error ต้องอ่านเข้าใจง่าย

\- ห้ามโชว์ traceback ให้ user ทั่วไป

\- traceback ให้ไปอยู่ใน log file

\- ทุก action ที่เสี่ยงต้อง confirm ก่อน

\- มี message box แจ้งเตือน

\- มี dirty state บอกว่าไฟล์มีการเปลี่ยนแปลงยังไม่บันทึก

\-\--

\## 6) Architecture ที่ต้องใช้

ให้แยกโค้ดเป็น module ชัดเจน ห้ามเขียนทุกอย่างในไฟล์เดียว

โครงสร้างโปรเจกต์:

thai_pdf_editor/

├─ app/

│ ├─ \_\_init\_\_.py

│ ├─ main.py

│ ├─ config.py

│ ├─ constants.py

│ ├─ logging_config.py

│ │

│ ├─ ui/

│ │ ├─ \_\_init\_\_.py

│ │ ├─ main_window.py

│ │ ├─ toolbar.py

│ │ ├─ page_panel.py

│ │ ├─ tool_panel.py

│ │ ├─ pdf_canvas.py

│ │ ├─ dialogs.py

│ │ └─ status_bar.py

│ │

│ ├─ core/

│ │ ├─ \_\_init\_\_.py

│ │ ├─ document_state.py

│ │ ├─ pdf_document.py

│ │ ├─ pdf_renderer.py

│ │ ├─ page_operations.py

│ │ ├─ overlay_operations.py

│ │ ├─ save_manager.py

│ │ ├─ undo_redo.py

│ │ └─ errors.py

│ │

│ ├─ models/

│ │ ├─ \_\_init\_\_.py

│ │ ├─ operations.py

│ │ ├─ geometry.py

│ │ └─ app_settings.py

│ │

│ └─ utils/

│ ├─ \_\_init\_\_.py

│ ├─ path_utils.py

│ ├─ font_utils.py

│ ├─ image_utils.py

│ └─ validation.py

│

├─ assets/

│ ├─ fonts/

│ └─ icons/

│

├─ data/

│ ├─ backups/

│ ├─ logs/

│ └─ temp/

│

├─ tests/

│ ├─ test_page_operations.py

│ ├─ test_save_manager.py

│ ├─ test_overlay_operations.py

│ └─ test_path_thai.py

│

├─ README.md

├─ requirements.txt

├─ run_app.py

└─ pyproject.toml

\-\--

\## 7) หลักการ state management

ต้องมี DocumentState กลางตัวเดียว ห้ามกระจาย state มั่ว

DocumentState ต้องเก็บ:

\- current_file_path

\- working_copy_path

\- total_pages

\- current_page_index

\- zoom_level

\- dirty flag

\- pending_operations

\- applied_operations

\- undo_stack

\- redo_stack

\- selected_tool

\- selected_page_indices

\- page_order

\- deleted_pages

\- rotation_map

ห้าม:

\- ห้ามให้ UI แก้ PDF โดยตรง

\- UI ต้องเรียกผ่าน service/core layer

\- ห้ามใช้ global variable สำหรับ document state

\- ห้ามซ่อน state ใน widget โดยไม่มี sync

\- ห้ามให้ canvas เป็น source of truth

หลัก:

UI = แสดงผลและรับ input

Core = จัดการ PDF

Models = เก็บข้อมูล operation

SaveManager = บันทึกไฟล์อย่างปลอดภัย

\-\--

\## 8) Operation model

ให้ทุกการแก้ไขเป็น operation object ก่อน

ตัวอย่าง operation:

\- RotatePageOperation

\- DeletePageOperation

\- MovePageOperation

\- AddTextOperation

\- AddImageOperation

\- DrawRectangleOperation

\- HighlightOperation

\- RedactOperation

\- CropPageOperation

ทุก operation ต้องมี:

\- id

\- type

\- page_index

\- created_at

\- payload

\- apply()

\- undo() ถ้าทำได้

\- validate()

Undo/Redo:

\- ทำ undo/redo ขั้นพื้นฐาน

\- อย่างน้อยต้องรองรับ operation ที่ยังไม่ save

\- ถ้า operation บางชนิด undo ยาก ให้ mark ว่า irreversible และ confirm ก่อน
apply

\-\--

\## 9) Save strategy

ต้องออกแบบ save ให้ปลอดภัย

กติกา:

\- เปิดไฟล์แล้วสร้าง working copy ใน data/temp/

\- ทุกการแก้ไขทำกับ state/working copy

\- Save As สร้างไฟล์ใหม่

\- เขียนไปที่ temp output ก่อน

\- ตรวจว่า output PDF เปิดได้

\- แล้วค่อย copy ไป path ปลายทาง

\- ห้ามทำลายไฟล์ต้นฉบับ

Save flow:

1\. validate document state

2\. create temp output path

3\. apply page operations

4\. apply overlays

5\. apply redactions

6\. save to temp output

7\. reopen temp output to verify

8\. copy to selected output path

9\. clear dirty flag

10\. notify success

Error handling:

\- ถ้า fail ที่ step ไหน ต้อง rollback

\- log exception

\- แจ้ง user ภาษาไทย

\- ไม่ทำให้ไฟล์ต้นฉบับเสีย

\-\--

\## 10) PDF rendering

ใช้ PyMuPDF render หน้า PDF เป็น image preview

ข้อกำหนด:

\- render เฉพาะหน้าปัจจุบันก่อน

\- cache preview เฉพาะหน้าที่เพิ่งเปิด

\- cache key = file_path + page_index + zoom + rotation + dirty_version

\- ถ้า state เปลี่ยน ต้อง invalidate cache

\- ห้าม cache ไม่จำกัด

\- จำกัด cache เช่น 10-20 หน้า

\- เมื่อปิดไฟล์ต้อง clear cache

Cache invalidation:

\- page operation เปลี่ยน → clear affected page cache

\- zoom เปลี่ยน → cache ใหม่ตาม zoom

\- overlay เปลี่ยน → clear page cache

\- save/reload → clear all cache

\-\--

\## 11) ความเสถียรและ error handling

ต้องมี custom error classes:

\- AppError

\- PdfOpenError

\- PdfSaveError

\- PdfRenderError

\- InvalidOperationError

\- FontError

\- ImageInsertError

หลักการ:

\- UI จับ AppError แล้วแสดงข้อความไทย

\- unexpected exception ให้ log เต็ม แต่แสดง user-friendly message

\- ห้าม crash เงียบ

\- ห้าม print debug กระจาย

\- ใช้ logging เท่านั้น

Log:

\- data/logs/app.log

\- rotating log ได้ยิ่งดี

\- log ระดับ INFO, WARNING, ERROR

\- ไม่ log content ของ PDF

\- log เฉพาะ path/action/error

\-\--

\## 12) Clean code rules

ต้องทำตามนี้อย่างเคร่งครัด:

\- 1 ไฟล์ไม่เกิน 1000 บรรทัด

\- 1 function ไม่ควรเกิน 80 บรรทัด

\- 1 class ไม่ควรทำหลายหน้าที่

\- ใช้ type hints

\- ใช้ dataclass สำหรับ model

\- ใช้ pathlib.Path

\- ใช้ enum สำหรับ tool/action type

\- หลีกเลี่ยง circular import

\- หลีกเลี่ยง hidden shared state

\- หลีกเลี่ยง mutable default argument

\- หลีกเลี่ยง broad except โดยไม่ log

\- ห้าม hardcode magic numbers โดยไม่มี constant

\- ทุก public method สำคัญต้องมี docstring สั้น ๆ

\-\--

\## 13) Threading / performance

แอพเป็น local single user จึงไม่ต้องใช้ concurrency ซับซ้อน

แต่ต้องระวัง:

\- เปิดไฟล์ PDF ใหญ่ไม่ควรทำให้ UI ค้างนาน

\- render หน้าใหญ่ควรแยกเป็น background task ได้ถ้าจำเป็น

\- ถ้าใช้ thread:

\- UI update ต้องกลับมาที่ main thread

\- ห้ามแก้ DocumentState จากหลาย thread โดยตรง

\- ใช้ queue หรือ callback ที่ปลอดภัย

\- ถ้าไม่ได้ใช้ concurrency ให้เขียนอธิบายใน README ว่า v1 ใช้ single-threaded
เป็นหลักเพื่อความเสถียร

ก่อนเขียนโค้ด ให้ทำ:

1\. concurrency risk analysis

2\. state flow diagram แบบข้อความ

3\. transaction boundary map สำหรับ save operation

4\. idempotency plan สำหรับ save/retry

5\. retry strategy เฉพาะกรณี file I/O fail

ถ้าบางข้อไม่เกี่ยว ให้เขียนว่า "ไม่ใช้ใน v1 เพราะ\..." ไม่ใช่ข้ามเงียบ ๆ

\-\--

\## 14) Testing

ต้องสร้าง test อย่างน้อย:

\- เปิด PDF sample ได้

\- save as ไม่ทำลายไฟล์ต้นฉบับ

\- rotate page แล้วจำนวนหน้ายังถูกต้อง

\- delete page แล้วจำนวนหน้าลดถูกต้อง

\- merge PDF แล้วจำนวนหน้าถูกต้อง

\- path ภาษาไทยทำงานได้

\- invalid PDF ต้องแจ้ง error ไม่ crash

\- operation validate ทำงาน

\- save manager ใช้ temp file ก่อน output จริง

ให้สร้าง sample PDF สำหรับ test ด้วย Python script ได้:

tests/fixtures/create_sample_pdfs.py

ห้าม commit ไฟล์ PDF ใหญ่

\-\--

\## 15) Packaging

เตรียมให้ package เป็น .exe ภายหลังได้ แต่ v1 ยังไม่ต้อง build exe

ให้มี:

\- requirements.txt

\- README.md

\- run_app.py

\- pyproject.toml แบบพื้นฐาน

README ต้องมี:

\- วิธีติดตั้ง

\- วิธีรัน

\- วิธีแก้ปัญหาภาษาไทยบน PowerShell

\- วิธีเลือก font ภาษาไทย

\- ข้อจำกัดของ v1

\- คำเตือนเรื่อง redaction

\- คำเตือนว่าแอพไม่ส่งไฟล์ออกนอกเครื่อง

คำสั่งตัวอย่าง:

\`\`\`powershell

chcp 65001

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

python run_app.py
