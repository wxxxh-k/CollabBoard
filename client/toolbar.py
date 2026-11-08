import tkinter as tk
from tkinter import colorchooser

from client import theme
from client.widgets import IconButton, round_rect
from common.user_colors import USER_COLORS

TOOLS = [
    ("pen", "Pen"), ("eraser", "Eraser"), ("line", "Line"),
    ("rectangle", "Rectangle"), ("circle", "Circle"), ("text", "Text"),
    ("hand", "Pan (hand)  -  or hold Space / middle mouse"),
]


class Toolbar:
    """Compact tool rail: drawing tools, color preference and brush size.

    Board actions (undo, redo, save, restore, clear) and zoom live in the
    whiteboard's top bar. The rail scrolls (and shows a scrollbar) only when the
    window is too short to show everything, so no control is ever unreachable.
    """

    WIDTH = 104
    BG = theme.BG_RAIL

    def __init__(self, parent, app):
        self.app = app
        self._scroll_visible = False
        self.frame = tk.Frame(parent, bg=self.BG, width=self.WIDTH,
                              highlightthickness=1, highlightbackground=theme.BORDER)
        self.frame.pack(side="left", fill="y", padx=(0, 8))
        self.frame.pack_propagate(False)

        self.scroll_canvas = tk.Canvas(self.frame, bg=self.BG, highlightthickness=0,
                                       bd=0, yscrollincrement=24)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical",
                                      command=self.scroll_canvas.yview, width=8,
                                      relief="flat", bg=theme.HOVER,
                                      troughcolor=theme.BG_APP)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.scroll_canvas, bg=self.BG)
        self.content_id = self.scroll_canvas.create_window((0, 0), window=self.content,
                                                           anchor="nw")
        self.content.bind("<Configure>", self._refresh_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", self._mousewheel, add="+")
        self.scroll_canvas.bind_all("<Button-4>", self._mousewheel_linux, add="+")
        self.scroll_canvas.bind_all("<Button-5>", self._mousewheel_linux, add="+")

        self._build_tools()
        self._divider()
        self._build_color()
        self._divider()
        self._build_brush()
        tk.Frame(self.content, height=10, bg=self.BG).pack(fill="x")
        self.highlight_tool("pen")

    # ---------------------------------------------------------------- build
    def _section_title(self, text, pady=(10, 6)):
        tk.Label(self.content, text=text, bg=self.BG, fg=theme.TEXT_DIM,
                 font=(theme.FONT, 8, "bold"), anchor="w").pack(fill="x", padx=12, pady=pady)

    def _divider(self):
        tk.Frame(self.content, height=1, bg=theme.BORDER).pack(fill="x", padx=10, pady=(10, 0))

    def _build_tools(self):
        self._section_title("TOOLS", pady=(12, 6))
        grid = tk.Frame(self.content, bg=self.BG)
        grid.pack(padx=8)
        self.tool_buttons = {}
        for index, (tool, tip) in enumerate(TOOLS):
            button = IconButton(
                grid, tool, tooltip=tip, size=40, bg=self.BG, selectable=True,
                command=lambda selected=tool: self._select_tool(selected))
            button.grid(row=index // 2, column=index % 2, padx=2, pady=2)
            self.tool_buttons[tool] = button

    def _build_color(self):
        self._section_title("MY COLOR")
        self.color_display = tk.Canvas(self.content, width=84, height=30, bg=self.BG,
                                       highlightthickness=0, bd=0, cursor="hand2")
        self.color_display.pack(padx=10)
        self._swatch_item = round_rect(self.color_display, 1, 1, 83, 29, 8,
                                       fill=self.app.preferred_color,
                                       outline="#FFFFFF", width=1)
        self.color_display.bind("<Button-1>", lambda _e: self.choose_color())
        self.color_display.bind("<Enter>", lambda _e: self.color_display.itemconfigure(
            self._swatch_item, width=2))
        self.color_display.bind("<Leave>", lambda _e: self.color_display.itemconfigure(
            self._swatch_item, width=1))
        self.color_hex = tk.Label(self.content, text=self.app.preferred_color.upper(),
                                  bg=self.BG, fg=theme.TEXT_MUTED, font=(theme.FONT, 8))
        self.color_hex.pack(pady=(3, 4))

        palette = tk.Frame(self.content, bg=self.BG)
        palette.pack(padx=8)
        self.palette_items = {}
        for index, color in enumerate(USER_COLORS[:8]):
            dot = tk.Canvas(palette, width=20, height=20, bg=self.BG,
                            highlightthickness=0, bd=0, cursor="hand2")
            item = dot.create_oval(3, 3, 17, 17, fill=color, outline=self.BG, width=2)
            dot.grid(row=index // 4, column=index % 4, padx=1, pady=1)
            dot.bind("<Button-1>", lambda _e, c=color: self._pick_palette(c))
            dot.bind("<Enter>", lambda _e, d=dot, i=item: d.itemconfigure(i, outline="#FFFFFF"))
            dot.bind("<Leave>", lambda _e, d=dot, i=item, c=color: d.itemconfigure(
                i, outline="#FFFFFF" if self._same(c, self.app.preferred_color) else self.BG))
            self.palette_items[color] = (dot, item)
        self._sync_palette(self.app.preferred_color)

    def _build_brush(self):
        self._section_title("BRUSH SIZE")
        self.size_value = tk.Label(self.content, text="3 px", bg=self.BG, fg=theme.TEXT,
                                   font=(theme.FONT, 9, "bold"))
        self.size_value.pack(anchor="e", padx=14)
        self.size_scale = tk.Scale(
            self.content, from_=1, to=20, orient="horizontal",
            command=self._change_width, bg=self.BG, fg="white",
            highlightthickness=0, troughcolor="#0F172A", bd=0, relief="flat",
            activebackground=theme.ACCENT_HOVER, showvalue=False,
            sliderlength=16, width=10, length=84)
        self.size_scale.set(3)
        self.size_scale.pack(padx=10, pady=(0, 4))
        self.brush_preview = tk.Canvas(self.content, width=84, height=34, bg="#0F172A",
                                       highlightthickness=0, bd=0)
        self.brush_preview.pack(padx=10, pady=(0, 6))
        self._draw_preview()

    # --------------------------------------------------------------- scroll
    def _on_canvas_configure(self, event):
        self.scroll_canvas.itemconfigure(self.content_id, width=event.width)
        self._refresh_scroll_region()

    def _refresh_scroll_region(self, _event=None):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        needs_scroll = self.content.winfo_reqheight() > self.scroll_canvas.winfo_height() + 1
        if needs_scroll and not self._scroll_visible:
            self.scrollbar.pack(side="right", fill="y")
            self._scroll_visible = True
        elif not needs_scroll and self._scroll_visible:
            self.scrollbar.pack_forget()
            self._scroll_visible = False
            self.scroll_canvas.yview_moveto(0)

    def _pointer_over_toolbar(self):
        if not self.frame.winfo_exists():
            return False
        x = self.scroll_canvas.winfo_pointerx()
        y = self.scroll_canvas.winfo_pointery()
        return (
            self.scroll_canvas.winfo_rootx() <= x <= self.scroll_canvas.winfo_rootx() + self.scroll_canvas.winfo_width()
            and self.scroll_canvas.winfo_rooty() <= y <= self.scroll_canvas.winfo_rooty() + self.scroll_canvas.winfo_height()
        )

    def _mousewheel(self, event):
        try:
            if self._scroll_visible and self._pointer_over_toolbar():
                self.scroll_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        except tk.TclError:
            pass

    def _mousewheel_linux(self, event):
        try:
            if self._scroll_visible and self._pointer_over_toolbar():
                self.scroll_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        except tk.TclError:
            pass

    # -------------------------------------------------------------- actions
    def _select_tool(self, tool):
        self.app.select_tool(tool)

    def highlight_tool(self, selected):
        for tool, button in self.tool_buttons.items():
            button.set_selected(tool == selected)
        self._draw_preview()

    def _change_width(self, value):
        size = int(float(value))
        self.size_value.configure(text=f"{size} px")
        self.app.change_width(value)
        self._draw_preview()

    @staticmethod
    def _same(a, b):
        return str(a).upper() == str(b).upper()

    def _sync_palette(self, color):
        for swatch, (dot, item) in self.palette_items.items():
            dot.itemconfigure(item, outline="#FFFFFF" if self._same(swatch, color) else self.BG)

    def _draw_preview(self):
        if not hasattr(self, "brush_preview"):
            return
        self.brush_preview.delete("all")
        size = int(self.size_scale.get())
        eraser = getattr(self.app, "tool", "pen") == "eraser"
        diameter = min(30, size * (4 if eraser else 1) + 2)
        cx, cy = 42, 17
        r = diameter / 2
        if eraser:
            self.brush_preview.create_oval(cx - r, cy - r, cx + r, cy + r,
                                           outline="#CBD5E1", fill="#FFFFFF", width=1)
        else:
            color = self.app.preferred_color
            self.brush_preview.create_oval(cx - r, cy - r, cx + r, cy + r,
                                           fill=color, outline=color)

    def set_preferred(self, color):
        """Reflect the user's preferred color in the swatch, hex label and palette."""
        self.color_display.itemconfigure(self._swatch_item, fill=color)
        self.color_hex.configure(text=color.upper())
        self._sync_palette(color)
        self._draw_preview()

    def _pick_palette(self, color):
        self.app.set_color(color)

    def choose_color(self):
        selected = colorchooser.askcolor(initialcolor=self.app.preferred_color)[1]
        if selected:
            self.app.set_color(selected)
