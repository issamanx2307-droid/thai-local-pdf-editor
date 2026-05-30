# -*- coding: utf-8 -*-
"""Scrollable PDF preview canvas."""

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from thai_pdf_editor.app.constants import NO_FILE_MESSAGE
from thai_pdf_editor.app.core.pdf_search import scaled_search_rect
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.ui.fonts import CANVAS_HINT_FONT, CANVAS_TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import (
    BOTTOM_SCROLLBAR_HEIGHT,
    BOTTOM_SCROLLBAR_PAN_MIN_EXTRA,
    BOTTOM_SCROLLBAR_PAN_VIEWPORT_FACTOR,
    BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH,
    HORIZONTAL_SCROLLBAR_THICKNESS,
    SCROLLBAR_WIDTH,
    event_wheel_scroll_units_with_remainder,
)
from thai_pdf_editor.app.ui.theme import COLORS, bind_button_depth, button_style, icon_label


class PdfCanvas(ctk.CTkFrame):
    """Canvas that displays rendered PDF page images."""

    def __init__(self, master: ctk.CTkBaseClass, *, on_open: Callable[[], None] | None = None) -> None:
        super().__init__(
            master,
            corner_radius=8,
            fg_color=COLORS["canvas"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._photo_image: ImageTk.PhotoImage | None = None
        self._zoom = 1.0
        self._drag_start: PdfPoint | None = None
        self._drag_start_canvas: tuple[float, float] | None = None
        self._on_click: Callable[[PdfPoint], None] | None = None
        self._on_rect: Callable[[PdfRect], None] | None = None
        self._on_open = on_open
        self._message_text: str | None = None
        self._empty_open_button: ctk.CTkButton | None = None
        self._wheel_remainder_x = 0.0
        self._wheel_remainder_y = 0.0
        self._x_scroll_first = 0.0
        self._x_scroll_last = 1.0
        self._bottom_scroll_drag_offset = 0.0
        self._page_image_size: tuple[int, int] | None = None
        self._scroll_region_x0 = 0.0
        self._scroll_region_width = 1.0
        self._align_content_left_on_next_region_update = False

        self.canvas = tk.Canvas(self, background=COLORS["canvas"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.y_scroll = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=SCROLLBAR_WIDTH)
        self.y_scroll.grid(row=0, column=1, sticky="ns")
        self.bottom_scrollbar_frame = ctk.CTkFrame(
            self,
            height=BOTTOM_SCROLLBAR_HEIGHT,
            fg_color=COLORS["surface_soft"],
            corner_radius=0,
        )
        self.bottom_scrollbar_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.bottom_scrollbar_frame.grid_propagate(False)
        self.bottom_scrollbar_frame.grid_columnconfigure(0, weight=1)
        self.bottom_scrollbar = tk.Canvas(
            self.bottom_scrollbar_frame,
            height=HORIZONTAL_SCROLLBAR_THICKNESS,
            background=COLORS["surface_soft"],
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="sb_h_double_arrow",
        )
        self.bottom_scrollbar.grid(row=0, column=0, sticky="ew", padx=8, pady=7)
        self.x_scroll = self.bottom_scrollbar

        self.canvas.configure(xscrollcommand=self._set_horizontal_scrollbar, yscrollcommand=self.y_scroll.set)
        self.canvas.bind("<Configure>", self._handle_configure)
        self.bottom_scrollbar.bind("<Configure>", lambda _event: self._draw_bottom_scrollbar())
        self.bottom_scrollbar.bind("<ButtonPress-1>", self._handle_bottom_scroll_press)
        self.bottom_scrollbar.bind("<B1-Motion>", self._handle_bottom_scroll_drag)
        self.bottom_scrollbar.bind("<ButtonRelease-1>", self._handle_bottom_scroll_release)
        self._bind_mouse_wheel()
        self.canvas.bind("<ButtonPress-1>", self._handle_press)
        self.canvas.bind("<B1-Motion>", self._handle_motion)
        self.canvas.bind("<ButtonRelease-1>", self._handle_release)
        self.show_message(NO_FILE_MESSAGE)

    def set_empty_open_handler(self, on_open: Callable[[], None]) -> None:
        """Register the open action used by the no-file empty state."""
        self._on_open = on_open

    def show_message(self, message: str) -> None:
        """Show centered canvas empty-state text."""
        self._photo_image = None
        self._message_text = message
        self._page_image_size = None
        self._scroll_region_x0 = 0.0
        self._scroll_region_width = 1.0
        self._set_horizontal_scrollbar(0.0, 1.0)
        self._draw_empty_state()

    def show_image(self, image: Image.Image, *, zoom: float = 1.0) -> None:
        """Display a rendered page image."""
        self._zoom = max(zoom, 0.01)
        self._message_text = None
        self._page_image_size = (image.width, image.height)
        self._align_content_left_on_next_region_update = True
        self._destroy_empty_button()
        self.canvas.delete("all")
        self._photo_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self._photo_image, anchor="nw")
        self._update_scroll_region()
        self.clamp_scroll_to_content()

    def show_search_highlight(self, rect: tuple[float, float, float, float]) -> None:
        """Draw a temporary search highlight on the current preview."""
        self.clear_search_highlight()
        x0, y0, x1, y1 = scaled_search_rect(rect, self._zoom)
        pad = max(2, int(2 * self._zoom))
        self.canvas.create_rectangle(
            x0 - pad,
            y0 - pad,
            x1 + pad,
            y1 + pad,
            outline="#ffb300",
            width=max(3, int(3 * self._zoom)),
            tags="search_highlight",
        )
        self.canvas.create_rectangle(
            x0 - pad,
            y0 - pad,
            x1 + pad,
            y1 + pad,
            outline="#111111",
            width=1,
            dash=(3, 2),
            tags="search_highlight",
        )
        self._scroll_rect_into_view(x0, y0, x1, y1)

    def clear_search_highlight(self) -> None:
        """Remove temporary search highlighting from the preview."""
        self.canvas.delete("search_highlight")

    def viewport_width(self) -> int:
        """Return current canvas viewport width."""
        width = self.canvas.winfo_width()
        return max(width, 1)

    def viewport_height(self) -> int:
        """Return current canvas viewport height."""
        height = self.canvas.winfo_height()
        return max(height, 1)

    def clamp_scroll_to_content(self) -> None:
        """Keep the viewport aligned to real page content after layout changes."""
        if self._message_text is not None:
            return
        region = self.canvas.bbox("all")
        if region is None:
            return
        x0, y0, x1, y1 = region
        content_width = max(float(x1 - x0), 1.0)
        content_height = max(float(y1 - y0), 1.0)
        view_width = max(float(self.canvas.winfo_width()), 1.0)
        view_height = max(float(self.canvas.winfo_height()), 1.0)
        scroll_width = max(self._scroll_region_width, content_width, 1.0)
        if scroll_width <= view_width:
            self.canvas.xview_moveto(0.0)
        else:
            left, _right = self.canvas.xview()
            max_left = max(0.0, 1.0 - (view_width / scroll_width))
            if left > max_left:
                self.canvas.xview_moveto(max_left)
        if content_height <= view_height:
            self.canvas.yview_moveto(0.0)
        else:
            top, _bottom = self.canvas.yview()
            max_top = max(0.0, 1.0 - (view_height / content_height))
            if top > max_top:
                self.canvas.yview_moveto(max_top)

    def _update_scroll_region(self) -> None:
        if self._page_image_size is None:
            return
        content_width, content_height = self._page_image_size
        view_width = max(self.canvas.winfo_width(), 1)
        x0, x1 = self._horizontal_scroll_bounds(content_width, view_width)
        self._scroll_region_x0 = float(x0)
        self._scroll_region_width = max(float(x1 - x0), 1.0)
        self.canvas.configure(scrollregion=(x0, 0, x1, content_height))
        if self._align_content_left_on_next_region_update and view_width > 20:
            self._align_content_left_on_next_region_update = False
            self._move_xview_to_content_left()
        first, last = self.canvas.xview()
        self._set_horizontal_scrollbar(first, last)

    def _horizontal_scroll_bounds(self, content_width: int, view_width: int) -> tuple[float, float]:
        if content_width > view_width:
            return 0.0, float(content_width)
        pan_extra = max(
            float(BOTTOM_SCROLLBAR_PAN_MIN_EXTRA),
            float(view_width) * BOTTOM_SCROLLBAR_PAN_VIEWPORT_FACTOR,
        )
        return -pan_extra, float(content_width) + pan_extra

    def _move_xview_to_content_left(self) -> None:
        if self._scroll_region_x0 < 0:
            self.canvas.xview_moveto(min(max((0.0 - self._scroll_region_x0) / self._scroll_region_width, 0.0), 1.0))
            return
        self.canvas.xview_moveto(0.0)

    def _set_horizontal_scrollbar(self, first: str | float, last: str | float) -> None:
        self._x_scroll_first = max(0.0, min(1.0, float(first)))
        self._x_scroll_last = max(self._x_scroll_first, min(1.0, float(last)))
        self._draw_bottom_scrollbar()

    def _draw_bottom_scrollbar(self) -> None:
        try:
            width = max(self.bottom_scrollbar.winfo_width(), 1)
            height = max(self.bottom_scrollbar.winfo_height(), HORIZONTAL_SCROLLBAR_THICKNESS)
            self.bottom_scrollbar.delete("all")
        except tk.TclError:
            return

        left, top, right, bottom, thumb_left, thumb_right = self._bottom_scrollbar_geometry(width, height)
        is_scrollable = self._bottom_scrollbar_is_scrollable()
        self.bottom_scrollbar.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill=COLORS["surface_muted"],
            outline=COLORS["border"],
            width=1,
        )
        if not is_scrollable:
            self.bottom_scrollbar.create_line(
                left + 8,
                (top + bottom) / 2,
                right - 8,
                (top + bottom) / 2,
                fill=COLORS["border_strong"],
                width=2,
            )
            return
        self.bottom_scrollbar.create_rectangle(
            thumb_left,
            top,
            thumb_right,
            bottom,
            fill=COLORS["primary"],
            outline=COLORS["primary_hover"],
            width=1,
            tags="thumb",
        )

    def _bottom_scrollbar_geometry(self, width: int, height: int) -> tuple[float, float, float, float, float, float]:
        track_pad = 8.0
        track_left = track_pad
        track_right = max(track_left + BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH, width - track_pad)
        track_top = max(4.0, (height - 16.0) / 2)
        track_bottom = min(height - 4.0, track_top + 16.0)
        track_width = max(track_right - track_left, 1.0)
        view_fraction = max(0.0, min(1.0, self._x_scroll_last - self._x_scroll_first))
        if view_fraction >= 0.995:
            return track_left, track_top, track_right, track_bottom, track_left, track_right
        thumb_width = max(BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH, track_width * view_fraction)
        thumb_left = track_left + (track_width * self._x_scroll_first)
        thumb_left = min(max(track_left, thumb_left), track_right - thumb_width)
        return track_left, track_top, track_right, track_bottom, thumb_left, thumb_left + thumb_width

    def _bottom_scrollbar_is_scrollable(self) -> bool:
        return (self._x_scroll_last - self._x_scroll_first) < 0.995

    def _handle_bottom_scroll_press(self, event: tk.Event) -> str:
        if not self._bottom_scrollbar_is_scrollable():
            return "break"
        width = max(self.bottom_scrollbar.winfo_width(), 1)
        height = max(self.bottom_scrollbar.winfo_height(), HORIZONTAL_SCROLLBAR_THICKNESS)
        left, _top, right, _bottom, thumb_left, thumb_right = self._bottom_scrollbar_geometry(width, height)
        if thumb_left <= event.x <= thumb_right:
            self._bottom_scroll_drag_offset = float(event.x) - thumb_left
            return "break"
        thumb_width = thumb_right - thumb_left
        self._move_bottom_scrollbar_to(float(event.x) - (thumb_width / 2), left, right, thumb_width)
        self._bottom_scroll_drag_offset = thumb_width / 2
        return "break"

    def _handle_bottom_scroll_drag(self, event: tk.Event) -> str:
        if not self._bottom_scrollbar_is_scrollable():
            return "break"
        width = max(self.bottom_scrollbar.winfo_width(), 1)
        height = max(self.bottom_scrollbar.winfo_height(), HORIZONTAL_SCROLLBAR_THICKNESS)
        left, _top, right, _bottom, thumb_left, thumb_right = self._bottom_scrollbar_geometry(width, height)
        self._move_bottom_scrollbar_to(float(event.x) - self._bottom_scroll_drag_offset, left, right, thumb_right - thumb_left)
        return "break"

    def _handle_bottom_scroll_release(self, _event: tk.Event) -> str:
        self._bottom_scroll_drag_offset = 0.0
        return "break"

    def _move_bottom_scrollbar_to(self, thumb_left: float, track_left: float, track_right: float, thumb_width: float) -> None:
        max_left = max(track_left, track_right - thumb_width)
        clamped_left = min(max(track_left, thumb_left), max_left)
        track_width = max(track_right - track_left, 1.0)
        self.canvas.xview_moveto((clamped_left - track_left) / track_width)

    def set_interaction_handlers(
        self,
        *,
        on_click: Callable[[PdfPoint], None],
        on_rect: Callable[[PdfRect], None],
    ) -> None:
        """Register callbacks for click and drag interactions."""
        self._on_click = on_click
        self._on_rect = on_rect

    def _draw_empty_state(self) -> None:
        if self._message_text is None:
            return
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        card_width = min(520, max(360, width - 160))
        card_height = 350
        left = (width - card_width) / 2
        top = max(44, (height - card_height) / 2)
        right = left + card_width
        bottom = top + card_height
        center_x = width / 2

        self.canvas.create_rectangle(left, top, right, bottom, outline="#657182", dash=(3, 3), fill=COLORS["canvas_soft"])
        icon_left = center_x - 44
        icon_top = top + 64
        icon_right = center_x + 44
        icon_bottom = icon_top + 96
        self.canvas.create_rectangle(icon_left, icon_top, icon_right, icon_bottom, outline="#d3d9e4", width=4)
        self.canvas.create_line(icon_right - 34, icon_top, icon_right, icon_top + 34, fill="#d3d9e4", width=4)
        self.canvas.create_line(icon_right - 34, icon_top, icon_right, icon_top + 34, fill="#d3d9e4", width=4)
        self.canvas.create_line(icon_right - 34, icon_top, icon_right - 34, icon_top + 34, fill="#d3d9e4", width=4)
        self.canvas.create_text(center_x, icon_top + 58, text="P", fill="#d3d9e4", font=(CANVAS_TITLE_FONT[0], 28, "bold"))
        self.canvas.create_text(
            center_x,
            top + 194,
            text=self._message_text,
            fill="#ffffff",
            font=CANVAS_TITLE_FONT,
        )
        self.canvas.create_text(
            center_x,
            top + 232,
            text='คลิก "เปิดไฟล์" เพื่อเริ่มต้นใช้งาน',
            fill="#d8dee8",
            font=CANVAS_HINT_FONT,
        )
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self._place_empty_button(center_x, top + 286)

    def _place_empty_button(self, x: float, y: float) -> None:
        if self._on_open is None:
            self._destroy_empty_button()
            return
        if self._empty_open_button is None:
            self._empty_open_button = ctk.CTkButton(
                self,
                text=icon_label("open", "เปิดไฟล์"),
                command=self._on_open,
                width=170,
                **button_style("primary"),
            )
            bind_button_depth(self._empty_open_button, "primary")
        self._empty_open_button.place(x=x, y=y, anchor="center")

    def _destroy_empty_button(self) -> None:
        if self._empty_open_button is not None:
            self._empty_open_button.destroy()
            self._empty_open_button = None

    def _handle_configure(self, _event: tk.Event) -> None:
        if self._message_text is not None:
            self._draw_empty_state()
        else:
            self._update_scroll_region()
            self.after_idle(self.clamp_scroll_to_content)

    def _handle_press(self, event: tk.Event) -> None:
        self._drag_start = self._event_to_pdf_point(event)
        self._drag_start_canvas = self._event_to_canvas_point(event)
        self.canvas.delete("drag_preview")

    def _handle_motion(self, event: tk.Event) -> None:
        if self._drag_start_canvas is None:
            return
        start_x, start_y = self._drag_start_canvas
        end_x, end_y = self._event_to_canvas_point(event)
        self.canvas.delete("drag_preview")
        self.canvas.create_rectangle(
            start_x,
            start_y,
            end_x,
            end_y,
            outline=COLORS["primary"],
            width=2,
            dash=(4, 2),
            tags="drag_preview",
        )

    def _handle_release(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        drag_end = self._event_to_pdf_point(event)
        rect = PdfRect.from_points(self._drag_start, drag_end)
        self.canvas.delete("drag_preview")
        if rect.width >= 4 and rect.height >= 4 and self._on_rect is not None:
            self._on_rect(rect)
        elif self._on_click is not None:
            self._on_click(drag_end)
        self._drag_start = None
        self._drag_start_canvas = None

    def _event_to_pdf_point(self, event: tk.Event) -> PdfPoint:
        canvas_x, canvas_y = self._event_to_canvas_point(event)
        return PdfPoint(x=canvas_x / self._zoom, y=canvas_y / self._zoom)

    def _event_to_canvas_point(self, event: tk.Event) -> tuple[float, float]:
        return (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def _scroll_rect_into_view(self, x0: float, y0: float, x1: float, y1: float) -> None:
        region = self.canvas.bbox("all")
        if region is None:
            return
        _, _, region_x1, region_y1 = region
        view_width = max(self.canvas.winfo_width(), 1)
        view_height = max(self.canvas.winfo_height(), 1)
        target_x = max(0.0, ((x0 + x1) / 2 - view_width / 2) / max(region_x1, 1))
        target_y = max(0.0, ((y0 + y1) / 2 - view_height / 2) / max(region_y1, 1))
        self.canvas.xview_moveto(min(target_x, 1.0))
        self.canvas.yview_moveto(min(target_y, 1.0))

    def _bind_mouse_wheel(self) -> None:
        for widget in (self.canvas, self.y_scroll):
            widget.bind("<Enter>", self._focus_scroll_widget)
            widget.bind("<MouseWheel>", self._handle_mouse_wheel)
            widget.bind("<Shift-MouseWheel>", self._handle_shift_mouse_wheel)
            widget.bind("<Button-4>", self._handle_mouse_wheel)
            widget.bind("<Button-5>", self._handle_mouse_wheel)
        self.bottom_scrollbar.bind("<Enter>", self._focus_scroll_widget)
        self.bottom_scrollbar.bind("<MouseWheel>", self._handle_shift_mouse_wheel)
        self.bottom_scrollbar.bind("<Shift-MouseWheel>", self._handle_shift_mouse_wheel)
        self.bottom_scrollbar.bind("<Button-4>", self._handle_shift_mouse_wheel)
        self.bottom_scrollbar.bind("<Button-5>", self._handle_shift_mouse_wheel)

    def _focus_scroll_widget(self, event: tk.Event) -> None:
        event.widget.focus_set()

    def _handle_mouse_wheel(self, event: tk.Event) -> str:
        units, self._wheel_remainder_y = event_wheel_scroll_units_with_remainder(
            event,
            remainder=self._wheel_remainder_y,
        )
        if units:
            self.canvas.yview_scroll(units, "units")
        return "break"

    def _handle_shift_mouse_wheel(self, event: tk.Event) -> str:
        units, self._wheel_remainder_x = event_wheel_scroll_units_with_remainder(
            event,
            remainder=self._wheel_remainder_x,
        )
        if units:
            self.canvas.xview_scroll(units, "units")
        return "break"
