# -*- coding: utf-8 -*-
"""Save, export, merge, and checklist window actions."""

from __future__ import annotations

import threading
from pathlib import Path

from thai_pdf_editor.app.core.export_operations import (
    batch_export_pdfs_as_jpg,
    export_pdf_as_jpg,
    resolve_jpg_page_indices,
)
from thai_pdf_editor.app.core.print_operations import print_pdf
from thai_pdf_editor.app.core.page_operations import merge_pdfs
from thai_pdf_editor.app.core.recent_files import add_recent_file
from thai_pdf_editor.app.core.save_preflight import (
    build_save_preflight_details,
    build_save_preflight_message,
    has_save_preflight_items,
)
from thai_pdf_editor.app.ui.dialogs import (
    ask_batch_jpg_export_options,
    ask_batch_jpg_pdf_paths,
    ask_export_jpg_directory,
    ask_jpg_export_options,
    ask_merge_pdf_paths,
    ask_save_pdf_path,
    show_info,
)
from thai_pdf_editor.app.ui.print_dialog import ask_print_options
from thai_pdf_editor.app.ui.qa_checklist_dialog import checklist_items_for_document, show_qa_checklist_dialog
from thai_pdf_editor.app.ui.save_preflight_dialog import ask_save_preflight_confirmation
from thai_pdf_editor.app.utils.path_utils import default_edited_path
from thai_pdf_editor.app.constants import APP_TITLE, APP_VERSION

import customtkinter as ctk
from thai_pdf_editor.app.ui.theme import COLORS
from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT


class SaveExportActionsMixin:
    """Actions for Save As, JPG export, PDF merge, and manual QA checklist."""

    def save_as(self) -> None:
        """Save the working document as a new PDF."""
        if not self.doc_state.has_document or self.doc_state.current_file_path is None:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        default_path = default_edited_path(self.doc_state.current_file_path)
        self.lift()
        self.focus_force()
        self.update()
        path_text = ask_save_pdf_path(default_path, parent=self)
        if not path_text:
            return
        destination = Path(path_text)
        if has_save_preflight_items(self.doc_state):
            confirmed = ask_save_preflight_confirmation(
                self,
                summary=build_save_preflight_message(self.doc_state),
                details=build_save_preflight_details(self.doc_state),
            )
            if not confirmed:
                self.status_bar.set_status("ยกเลิกการบันทึก")
                return

        def action() -> None:
            self.status_bar.set_status("กำลังบันทึกไฟล์...")
            previous_page_index = self.doc_state.current_page_index
            saved_path = self.save_manager.save_as(self.document.raw, self.doc_state, destination)
            self.document.open(saved_path)
            self.title(f"{saved_path.name} - {APP_TITLE} {APP_VERSION}")
            add_recent_file(saved_path)
            self.search_results.clear()
            self.search_current_index = -1
            self.doc_state.set_current_page(min(previous_page_index, self.doc_state.total_pages - 1))
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status(f"บันทึกสำเร็จ: {saved_path.name}")
            show_info("บันทึกไฟล์ PDF สำเร็จ")

        self._run_user_action(action)

    def export_jpg_files(self) -> None:
        """Export the current PDF as JPG files."""
        if not self.doc_state.has_document or self.doc_state.current_file_path is None:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        options = ask_jpg_export_options(
            self,
            current_page=self.doc_state.display_page_number,
            total_pages=self.doc_state.total_pages,
        )
        if options is None:
            return
        default_dir = self.doc_state.current_file_path.with_name(f"{self.doc_state.current_file_path.stem}_jpg")
        self.lift()
        self.focus_force()
        self.update()
        directory_text = ask_export_jpg_directory(default_dir, parent=self)
        if not directory_text:
            return
        destination_dir = Path(directory_text)
        page_scope = str(options["page_scope"])
        dpi = int(options["dpi"])
        quality = int(options["quality"])

        def action() -> None:
            self.status_bar.set_status("กำลังส่งออก JPG...")
            page_indices = resolve_jpg_page_indices(
                page_scope,
                self.doc_state.current_page_index,
                self.doc_state.total_pages,
            )
            output_paths = export_pdf_as_jpg(
                self.document.raw,
                self.doc_state,
                destination_dir,
                page_indices=page_indices,
                dpi=dpi,
                quality=quality,
            )
            self.status_bar.set_status(f"ส่งออก JPG สำเร็จ {len(output_paths)} ไฟล์")
            show_info(f"ส่งออก JPG สำเร็จ {len(output_paths)} ไฟล์\nโฟลเดอร์: {destination_dir}")

        self._run_user_action(action)

    def batch_export_jpg_files(self) -> None:
        """Export selected PDFs to JPG files with a live progress window."""
        self.lift()
        self.focus_force()
        self.update()
        path_texts = ask_batch_jpg_pdf_paths(parent=self)
        if not path_texts:
            return
        options = ask_batch_jpg_export_options(self)
        if options is None:
            return
        source_paths = [Path(pt) for pt in path_texts]
        default_dir = source_paths[0].parent / "batch_jpg"
        directory_text = ask_export_jpg_directory(default_dir, parent=self)
        if not directory_text:
            return
        destination_dir = Path(directory_text)
        dpi = int(options["dpi"])
        quality = int(options["quality"])
        total = len(source_paths)

        # ── progress window ──────────────────────────────────────────────
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("Batch Export JPG")
        progress_win.resizable(False, False)
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.protocol("WM_DELETE_WINDOW", lambda: None)   # block manual close
        progress_win.configure(fg_color=COLORS["app_bg"])

        card = ctk.CTkFrame(progress_win, fg_color=COLORS["surface"],
                            corner_radius=12, border_width=1, border_color=COLORS["border"])
        card.pack(padx=20, pady=20)

        status_var = ctk.StringVar(value=f"กำลังส่งออก 0 / {total} ไฟล์ ...")
        ctk.CTkLabel(card, textvariable=status_var, font=LABEL_FONT,
                     text_color=COLORS["text"]).pack(padx=24, pady=(20, 10))
        progress_bar = ctk.CTkProgressBar(card, width=360,
                                          progress_color=COLORS["primary"])
        progress_bar.set(0)
        progress_bar.pack(padx=24, pady=(0, 20))

        progress_win.update_idletasks()
        pw, ph = self.winfo_width(), self.winfo_height()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        dw, dh = progress_win.winfo_width(), progress_win.winfo_height()
        progress_win.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        # ── worker ───────────────────────────────────────────────────────
        report_holder: list[dict] = []
        error_holder: list[Exception] = []

        def on_progress(done: int, total: int) -> None:
            try:
                self.after(0, lambda d=done, t=total: _update(d, t))
            except Exception:  # noqa: BLE001
                pass

        def _update(done: int, total: int) -> None:
            try:
                status_var.set(f"กำลังส่งออก {done} / {total} ไฟล์ ...")
                progress_bar.set(done / total)
            except Exception:  # noqa: BLE001
                pass

        def worker() -> None:
            try:
                report = batch_export_pdfs_as_jpg(
                    source_paths, destination_dir,
                    dpi=dpi, quality=quality,
                    progress_callback=on_progress,
                )
                report_holder.append(report)
            except Exception as exc:  # noqa: BLE001
                error_holder.append(exc)
            finally:
                try:
                    self.after(0, on_done)
                except Exception:  # noqa: BLE001
                    pass

        def on_done() -> None:
            try:
                progress_win.destroy()
            except Exception:  # noqa: BLE001
                pass
            if error_holder:
                exc = error_holder[0]
                msg = getattr(exc, "user_message", str(exc))
                self.status_bar.set_status(f"เกิดข้อผิดพลาด: {msg}")
                show_error(msg)
            elif report_holder:
                report = report_holder[0]
                succeeded = int(report["succeeded"])
                failed = int(report["failed"])
                report_path = str(report["report_path"])
                self.status_bar.set_status(
                    f"Batch JPG สำเร็จ {succeeded} ไฟล์ ล้มเหลว {failed} ไฟล์")
                show_info(
                    f"Batch JPG เสร็จแล้ว\nสำเร็จ: {succeeded}\nล้มเหลว: {failed}\nรายงาน: {report_path}")

        threading.Thread(target=worker, daemon=True).start()
        progress_win.wait_window()

    def merge_pdf_files(self) -> None:
        """Merge selected PDF files into a new PDF."""
        self.lift()
        self.focus_force()
        self.update()
        path_texts = ask_merge_pdf_paths(parent=self)
        if not path_texts:
            return
        source_paths = [Path(path_text) for path_text in path_texts]
        default_path = source_paths[0].with_name(f"{source_paths[0].stem}_merged.pdf")
        destination_text = ask_save_pdf_path(default_path, parent=self)
        if not destination_text:
            return

        def action() -> None:
            merged_path = merge_pdfs(source_paths, Path(destination_text))
            self.status_bar.set_status(f"รวม PDF สำเร็จ: {merged_path.name}")
            show_info("รวมไฟล์ PDF สำเร็จ")

        self._run_user_action(action)

    def open_qa_checklist(self) -> None:
        """Open the local manual QA checklist."""
        items = checklist_items_for_document(has_document=self.doc_state.has_document, dirty=self.doc_state.dirty)
        show_qa_checklist_dialog(self, items)

    def print_current_pdf(self) -> None:
        """Send the current PDF to a printer selected by the user."""
        if not self.doc_state.has_document or self.doc_state.current_file_path is None:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        options = ask_print_options(
            self,
            total_pages=self.doc_state.total_pages,
            current_page=self.doc_state.display_page_number,
        )
        if options is None:
            return
        printer = str(options["printer"])
        copies = int(options["copies"])  # type: ignore[arg-type]
        pages = options.get("pages")  # type: ignore[assignment]
        pages_text = str(pages) if pages else None

        def action() -> None:
            self.status_bar.set_status(f"กำลังส่งพิมพ์ → {printer} …")
            print_pdf(self.doc_state.current_file_path, printer, copies=copies, pages=pages_text)
            self.status_bar.set_status(f"ส่งคำสั่งพิมพ์แล้ว → {printer}")

        self._run_user_action(action)
