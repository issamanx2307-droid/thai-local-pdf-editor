# Release Notes

## v1.0.0-local - 2026-05-21

Local-only Thai PDF editor for Windows. This release is intended for personal/local use, with no cloud service, account system, OCR, AI, or plugin runtime.

### ทำได้

- เปิด PDF, แสดงรายการหน้า, ไปหน้าก่อน/ถัดไป, ไปหน้าแรก/สุดท้าย, zoom, fit width, และยืด-ยุบแผงซ้าย/ขวา
- เปิดโปรแกรมใหม่ด้วยหน้าจอเริ่มต้นทุกครั้ง; การยืด-ยุบแผงมีผลเฉพาะรอบที่เปิดใช้งานอยู่
- จัดการหน้า PDF: หมุน, ลบ, ย้าย, ทำซ้ำ, crop, แยกหน้าปัจจุบัน, และรวม PDF
- เพิ่มข้อความภาษาไทย, เลือกฟอนต์, วางรูปภาพ/ลายเซ็นภาพ, วาดกล่อง, highlight, redaction, และแก้ข้อความเดิมแบบ redaction + วางข้อความใหม่
- แก้ metadata และแก้ฟอร์ม PDF ที่มีอยู่แล้วสำหรับ text field และ checkbox
- ค้นหาข้อความจาก text layer, ใช้ recent files, Save As preflight, QA checklist, และบันทึกแบบ temp-safe
- ส่งออก PDF เป็น JPG ทีละไฟล์หรือ Batch JPG แบบ local sequential พร้อม report
- Build เป็น `.exe` ได้ที่ `dist/ThaiLocalPdfEditor/ThaiLocalPdfEditor.exe`

### ยังไม่ทำ / ข้อจำกัด

- ไม่มี OCR, AI, cloud sync/storage, user account/login, plugin system, หรือ PDF to Word
- ลายเซ็นในแอพเป็นรูปภาพลายเซ็น ไม่ใช่ digital signature certificate/PKI
- PDF ที่เป็นภาพสแกนล้วนและไม่มี text layer จะค้นหาข้อความหรือแก้ข้อความเดิมไม่ได้
- PDF ขนาดใหญ่มากอาจใช้เวลาพรีวิวหรือส่งออก เพราะ v1 ใช้ local single-process workflow เป็นหลัก
- ควรตรวจไฟล์ผลลัพธ์หลัง Save As โดยเฉพาะงาน redaction, ฟอร์ม PDF, และข้อความภาษาไทย
