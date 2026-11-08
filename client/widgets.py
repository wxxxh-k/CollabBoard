"""Small reusable Tkinter widgets: vector icon buttons, tooltips, pill buttons."""
import tkinter as tk

from client import theme


def round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# --------------------------------------------------------------------- icons
def _line(c, P, pts, col, w, smooth=False):
    flat = []
    for x, y in pts:
        flat.extend(P(x, y))
    c.create_line(*flat, fill=col, width=w, capstyle="round", joinstyle="round", smooth=smooth)


def _poly(c, P, pts, col, w, fill=""):
    flat = []
    for x, y in pts:
        flat.extend(P(x, y))
    c.create_polygon(*flat, outline=col, fill=fill, width=w, joinstyle="round")


def _icon_pen(c, P, col, w):
    _poly(c, P, [(15.5, 5), (19, 8.5), (8.5, 19), (4.5, 19.5), (5, 15.5)], col, w)
    _line(c, P, [(13, 7.5), (16.5, 11)], col, w)


def _icon_eraser(c, P, col, w):
    _poly(c, P, [(4.5, 13.5), (12, 6), (19, 13), (13.5, 18.5), (9.5, 18.5)], col, w)
    _line(c, P, [(8, 9.5), (15.5, 17)], col, w)
    _line(c, P, [(13, 20), (20, 20)], col, w)


def _icon_line(c, P, col, w):
    _line(c, P, [(5.5, 18.5), (18.5, 5.5)], col, w)


def _icon_rectangle(c, P, col, w):
    _poly(c, P, [(5, 6.5), (19, 6.5), (19, 17.5), (5, 17.5)], col, w)


def _icon_circle(c, P, col, w):
    x1, y1 = P(5, 5)
    x2, y2 = P(19, 19)
    c.create_oval(x1, y1, x2, y2, outline=col, width=w)


def _icon_text(c, P, col, w):
    _line(c, P, [(6, 6.5), (18, 6.5)], col, w)
    _line(c, P, [(12, 6.5), (12, 18.5)], col, w)
    _line(c, P, [(9.5, 18.5), (14.5, 18.5)], col, w)


def _icon_hand(c, P, col, w):
    _line(c, P, [(12, 4), (12, 20)], col, w)
    _line(c, P, [(4, 12), (20, 12)], col, w)
    for tri in ([(12, 2.5), (9.5, 6), (14.5, 6)], [(12, 21.5), (9.5, 18), (14.5, 18)],
                [(2.5, 12), (6, 9.5), (6, 14.5)], [(21.5, 12), (18, 9.5), (18, 14.5)]):
        _poly(c, P, tri, col, 1, fill=col)


def _icon_undo(c, P, col, w, flip=False):
    fx = (lambda x: 24 - x) if flip else (lambda x: x)
    _line(c, P, [(fx(16.5), 18.5), (fx(18), 13), (fx(14.5), 9.5), (fx(10), 9.5)], col, w, smooth=True)
    _poly(c, P, [(fx(10.5), 5), (fx(10.5), 14), (fx(4.5), 9.5)], col, 1, fill=col)


def _icon_redo(c, P, col, w):
    _icon_undo(c, P, col, w, flip=True)


def _icon_save(c, P, col, w):
    _poly(c, P, [(5, 5), (19, 5), (19, 19), (5, 19)], col, w)
    _poly(c, P, [(8, 5), (15, 5), (15, 9.5), (8, 9.5)], col, w)
    _poly(c, P, [(8, 19), (8, 13.5), (16, 13.5), (16, 19)], col, w)


def _icon_load(c, P, col, w):
    _poly(c, P, [(4, 7), (9.5, 7), (11.5, 9.5), (20, 9.5), (20, 18.5), (4, 18.5)], col, w)


def _icon_trash(c, P, col, w):
    _line(c, P, [(5.5, 7.5), (18.5, 7.5)], col, w)
    _line(c, P, [(9.5, 7.5), (9.5, 5), (14.5, 5), (14.5, 7.5)], col, w)
    _poly(c, P, [(7, 7.5), (8, 19.5), (16, 19.5), (17, 7.5)], col, w)
    _line(c, P, [(10.5, 10.5), (10.5, 16.5)], col, 1)
    _line(c, P, [(13.5, 10.5), (13.5, 16.5)], col, 1)


def _icon_zoom_in(c, P, col, w):
    _line(c, P, [(12, 5.5), (12, 18.5)], col, w)
    _line(c, P, [(5.5, 12), (18.5, 12)], col, w)


def _icon_zoom_out(c, P, col, w):
    _line(c, P, [(5.5, 12), (18.5, 12)], col, w)


def _icon_fit(c, P, col, w):
    for pts in ([(5, 10), (5, 5), (10, 5)], [(14, 5), (19, 5), (19, 10)],
                [(19, 14), (19, 19), (14, 19)], [(10, 19), (5, 19), (5, 14)]):
        _line(c, P, pts, col, w)


def _icon_chevron_down(c, P, col, w):
    _line(c, P, [(7, 9.5), (12, 14.5), (17, 9.5)], col, w)


def _icon_chevron_up(c, P, col, w):
    _line(c, P, [(7, 14.5), (12, 9.5), (17, 14.5)], col, w)


ICONS = {
    "pen": _icon_pen, "eraser": _icon_eraser, "line": _icon_line,
    "rectangle": _icon_rectangle, "circle": _icon_circle, "text": _icon_text,
    "hand": _icon_hand, "undo": _icon_undo, "redo": _icon_redo, "save": _icon_save,
    "load": _icon_load, "trash": _icon_trash, "zoom_in": _icon_zoom_in,
    "zoom_out": _icon_zoom_out, "fit": _icon_fit,
    "chevron_down": _icon_chevron_down, "chevron_up": _icon_chevron_up,
}


def draw_icon(canvas, name, size, color):
    """Draw a vector icon centered in a size x size square (24-unit design grid)."""
    drawer = ICONS.get(name)
    if drawer is None:
        return
    scale = (size * 0.58) / 24.0
    offset = (size - 24 * scale) / 2.0

    def P(x, y):
        return offset + x * scale, offset + y * scale

    drawer(canvas, P, color, max(1.5, size / 17.0))


# ------------------------------------------------------------------- tooltip
class Tooltip:
    """Lightweight hover tooltip."""

    def __init__(self, widget, text, delay=450):
        self.widget, self.text, self.delay = widget, text, delay
        self._job = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _show(self):
        self._job = None
        if self._tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 4
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self._tip = tk.Toplevel(self.widget)
            self._tip.wm_overrideredirect(True)
            self._tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self._tip, text=self.text, bg="#0B1220", fg=theme.TEXT,
                     font=(theme.FONT, 9), padx=8, pady=4, bd=0,
                     highlightthickness=1, highlightbackground=theme.BORDER).pack()
        except tk.TclError:
            self._tip = None

    def _hide(self, _event=None):
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


# --------------------------------------------------------------- icon button
class IconButton(tk.Canvas):
    """Flat rounded icon button with hover, pressed and selected feedback."""

    def __init__(self, parent, icon, command=None, tooltip=None, size=36,
                 bg=theme.BG_BAR, selectable=False, danger=False):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.icon, self.command, self.size = icon, command, size
        self.parent_bg = bg
        self.selectable, self.danger = selectable, danger
        self.selected = False
        self._hover = False
        self._pressed = False
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        if tooltip:
            Tooltip(self, tooltip)
        self._render()

    def set_selected(self, value):
        if self.selected != bool(value):
            self.selected = bool(value)
            self._render()

    def _colors(self):
        if self.selected:
            return theme.ACCENT_HOVER if self._hover else theme.ACCENT, "#FFFFFF"
        if self._pressed:
            return (theme.DANGER_BG if self.danger else theme.PRESSED), \
                   (theme.DANGER_FG if self.danger else "#FFFFFF")
        if self._hover:
            return (theme.DANGER_BG if self.danger else theme.HOVER), \
                   (theme.DANGER_FG if self.danger else "#FFFFFF")
        return self.parent_bg, (theme.DANGER_FG if self.danger else "#CBD5E1")

    def _render(self):
        self.delete("all")
        fill, fg = self._colors()
        if fill != self.parent_bg:
            round_rect(self, 1, 1, self.size - 1, self.size - 1, 8, fill=fill, outline=fill)
        draw_icon(self, self.icon, self.size, fg)

    def _on_enter(self, _event=None):
        self._hover = True
        self._render()

    def _on_leave(self, _event=None):
        self._hover = False
        self._pressed = False
        self._render()

    def _on_press(self, _event=None):
        self._pressed = True
        self._render()

    def _on_release(self, event):
        was_pressed = self._pressed
        self._pressed = False
        self._render()
        inside = 0 <= event.x <= self.size and 0 <= event.y <= self.size
        if was_pressed and inside and self.command:
            self.command()


# --------------------------------------------------------------- pill button
class PillButton(tk.Label):
    """Text button with hover feedback, used in the header."""

    def __init__(self, parent, text, command=None, bg="#374151", hover="#4B5563",
                 fg="white", bold=False):
        super().__init__(parent, text=text, bg=bg, fg=fg, padx=12, pady=6,
                         font=(theme.FONT, 9, "bold" if bold else "normal"),
                         cursor="hand2")
        self.command, self._bg, self._hover_bg = command, bg, hover
        self.bind("<Enter>", lambda _e: self.configure(bg=self._hover_bg), add="+")
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg), add="+")
        self.bind("<ButtonRelease-1>", self._click, add="+")

    def _click(self, event):
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            if self.command:
                self.command()

    def set_style(self, bg, hover):
        self._bg, self._hover_bg = bg, hover
        self.configure(bg=bg)
