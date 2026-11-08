import tkinter as tk
from tkinter import messagebox, simpledialog

from client import theme
from client.toolbar import Toolbar
from client.viewport import Viewport, PAGE_WIDTH, PAGE_HEIGHT
from client.widgets import IconButton

TOOL_LABELS = {"pen": "Pen", "eraser": "Eraser", "line": "Line", "rectangle": "Rectangle",
               "circle": "Circle", "text": "Text", "hand": "Pan"}
TOOL_CURSORS = {"pen": "crosshair", "eraser": "crosshair", "line": "crosshair",
                "rectangle": "crosshair", "circle": "crosshair", "text": "xterm",
                "hand": "fleur"}


class Whiteboard:
    """Tkinter drawing surface. All shared actions are delegated to SyncManager.

    Drawing data is stored and sent in *world* coordinates on a fixed
    PAGE_WIDTH x PAGE_HEIGHT page; the Viewport maps them to canvas pixels, so
    drawings stay correct (and identical for every participant) at any zoom,
    pan offset or window size.
    """
    ZOOM_STEP = 1.25
    WHEEL_STEP = 1.12

    def __init__(self, parent, on_operation=None, on_clear=None,
                 on_undo=None, on_redo=None, on_save=None, on_load=None):
        self.parent = parent
        self.on_operation = on_operation
        self.on_clear = on_clear
        self.on_undo = on_undo
        self.on_redo = on_redo
        self.on_save = on_save
        self.on_load = on_load
        self.on_color_change = None
        self.on_cursor_move = None
        self.remote_cursors = {}
        self.remote_cursor_positions = {}
        self.tool, self.color, self.width = "pen", "#2563EB", 3
        self.user_color = "#2563EB"       # actual server-assigned drawing color
        self.preferred_color = "#2563EB"  # user's requested preference
        self.points, self.preview = [], None
        self.operations = []
        self.view = Viewport()
        self.auto_fit = True              # keep the whole page fitted until the user zooms/pans
        self._redraw_job = None
        self._live_items = []
        self._shape_end = None
        self._ring = None
        self._panning = False
        self._pan_last = (0, 0)
        self._space_down = False
        self._title_visible = True
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.frame = tk.Frame(self.parent, bg=theme.BG_BOARD)
        self.frame.pack(side="left", fill="both", expand=True)

        # ---- top bar: history / file actions on the left, zoom on the right
        self.topbar = tk.Frame(self.frame, bg=theme.BG_BAR, height=50,
                               highlightthickness=1, highlightbackground=theme.BORDER)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)
        self.topbar.bind("<Configure>", self._on_topbar_configure)

        zoom_group = tk.Frame(self.topbar, bg=theme.BG_BAR)
        zoom_group.pack(side="right", padx=(0, 8))
        IconButton(zoom_group, "fit", self.fit_to_window, "Fit board to window  (0)",
                   size=34).pack(side="right", padx=1, pady=8)
        IconButton(zoom_group, "zoom_in", self.zoom_in, "Zoom in  (+ or mouse wheel)",
                   size=34).pack(side="right", padx=1, pady=8)
        self.zoom_label = tk.Label(zoom_group, text="100%", width=5, bg=theme.BG_BAR,
                                   fg=theme.TEXT, font=(theme.FONT, 9, "bold"), cursor="hand2")
        self.zoom_label.pack(side="right", pady=8)
        self.zoom_label.bind("<Button-1>", lambda _e: self.reset_zoom())
        IconButton(zoom_group, "zoom_out", self.zoom_out, "Zoom out  (-)",
                   size=34).pack(side="right", padx=1, pady=8)

        self.title_label = tk.Label(self.topbar, text="Whiteboard", bg=theme.BG_BAR,
                                    fg=theme.TEXT, font=(theme.FONT, 11, "bold"))
        self.title_label.pack(side="left", padx=(14, 8))

        self.history_group = tk.Frame(self.topbar, bg=theme.BG_BAR)
        self.history_group.pack(side="left", padx=(4, 0))
        IconButton(self.history_group, "undo", lambda: self._call(self.on_undo),
                   "Undo  (Ctrl+Z)", size=34).pack(side="left", padx=1, pady=8)
        IconButton(self.history_group, "redo", lambda: self._call(self.on_redo),
                   "Redo  (Ctrl+Y)", size=34).pack(side="left", padx=1, pady=8)
        tk.Frame(self.history_group, width=1, bg=theme.BORDER).pack(
            side="left", fill="y", padx=6, pady=12)
        IconButton(self.history_group, "save", lambda: self._call(self.on_save),
                   "Save board on the server", size=34).pack(side="left", padx=1, pady=8)
        IconButton(self.history_group, "load", lambda: self._call(self.on_load),
                   "Restore the saved board", size=34).pack(side="left", padx=1, pady=8)
        tk.Frame(self.history_group, width=1, bg=theme.BORDER).pack(
            side="left", fill="y", padx=6, pady=12)
        self.clear_button = IconButton(self.history_group, "trash", self.request_clear,
                   "Clear the board for everyone", size=34, danger=True)
        self.clear_button.pack(side="left", padx=1, pady=8)
        self.read_only = False
        self.can_clear = True

        # ---- body: tool rail + canvas
        body = tk.Frame(self.frame, bg=theme.BG_BOARD)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        self.toolbar = Toolbar(body, self)

        holder = tk.Frame(body, bg=theme.BG_WORKSPACE, highlightthickness=1,
                          highlightbackground=theme.BORDER)
        self.canvas_holder = holder
        holder.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(holder, bg=theme.BG_WORKSPACE, cursor="crosshair",
                                highlightthickness=0, bd=0, takefocus=1)
        self.canvas.pack(fill="both", expand=True)

        c = self.canvas
        c.bind("<Button-1>", self.start_drawing)
        c.bind("<B1-Motion>", self.draw)
        c.bind("<ButtonRelease-1>", self.stop_drawing)
        for button in (2, 3):  # middle / right mouse button pan (macOS uses 2 for right)
            c.bind(f"<ButtonPress-{button}>", self._begin_pan)
            c.bind(f"<B{button}-Motion>", self._pan_motion)
            c.bind(f"<ButtonRelease-{button}>", self._end_pan)
        c.bind("<Motion>", self._on_motion)
        c.bind("<Leave>", self._on_leave)
        c.bind("<Configure>", self._on_canvas_configure)
        c.bind("<MouseWheel>", self._on_wheel)
        c.bind("<Button-4>", self._on_wheel)
        c.bind("<Button-5>", self._on_wheel)
        c.bind("<KeyPress-space>", self._space_press)
        c.bind("<KeyRelease-space>", self._space_release)
        c.bind("<Control-z>", lambda _e: self._call(self.on_undo))
        c.bind("<Control-y>", lambda _e: self._call(self.on_redo))
        c.bind("<Control-Z>", lambda _e: self._call(self.on_redo))
        for key in ("<plus>", "<equal>", "<KP_Add>", "<Control-plus>", "<Control-equal>"):
            c.bind(key, lambda _e: self.zoom_in())
        for key in ("<minus>", "<KP_Subtract>", "<Control-minus>"):
            c.bind(key, lambda _e: self.zoom_out())
        for key in ("<Key-0>", "<Control-Key-0>"):
            c.bind(key, lambda _e: self.fit_to_window())

        # ---- status bar
        statusbar = tk.Frame(self.frame, bg=theme.BG_BAR, height=26)
        statusbar.pack(fill="x")
        statusbar.pack_propagate(False)
        self.coords = tk.Label(statusbar, text="", bg=theme.BG_BAR, fg=theme.TEXT_DIM,
                               font=(theme.FONT, 8), anchor="e", padx=12)
        self.coords.pack(side="right")
        self.status = tk.Label(statusbar, text="Connected", bg=theme.BG_BAR,
                               fg=theme.TEXT_MUTED, font=(theme.FONT, 9), anchor="w", padx=12)
        self.status.pack(side="left", fill="x", expand=True)

    def _on_topbar_configure(self, event):
        narrow = event.width < 560
        if narrow and self._title_visible:
            self.title_label.pack_forget()
            self._title_visible = False
        elif not narrow and not self._title_visible:
            self.title_label.pack(side="left", padx=(14, 8), before=self.history_group)
            self._title_visible = True

    def _call(self, callback):
        if callback:
            callback()

    # ------------------------------------------------------------ settings
    def set_read_only(self, read_only, can_clear=False):
        self.read_only = bool(read_only)
        self.can_clear = bool(can_clear)
        if self.read_only:
            self.select_tool("hand")
            self.toolbar.frame.pack_forget()
            self.history_group.pack_forget()
        else:
            self.toolbar.frame.pack(side="left", fill="y", padx=(0, 8),
                                    before=self.canvas_holder)
            self.history_group.pack(side="left", padx=(4, 0))
        self.clear_button.pack_forget()
        if self.can_clear:
            self.clear_button.pack(side="left", padx=1, pady=8)

    def select_tool(self, tool):
        self.tool = tool
        self._remove_ring()
        self._apply_cursor()
        if hasattr(self, "toolbar"):
            self.toolbar.highlight_tool(tool)
        self.status.config(text=f"Tool: {TOOL_LABELS.get(tool, tool.title())}")

    def _apply_cursor(self):
        cursor = "fleur" if (self._space_down or self._panning) else TOOL_CURSORS.get(self.tool, "crosshair")
        self.canvas.configure(cursor=cursor)

    def set_user_color(self, color):
        """Apply the actual, unique color assigned by the server."""
        if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
            return
        self.user_color = color.upper()
        self.color = self.user_color
        self.status.config(text=f"Your assigned drawing color: {self.user_color}")

    def set_preferred_color(self, color):
        """Update the local preference preview (not the actual drawing color)."""
        if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
            return
        self.preferred_color = color.upper()
        if hasattr(self, "toolbar"):
            self.toolbar.set_preferred(self.preferred_color)

    def set_color(self, color):
        # A toolbar selection is a preference; the server decides the actual color.
        self.set_preferred_color(color)
        # The viewer always uses their own selected preference immediately.
        self.user_color = self.preferred_color
        self.color = self.user_color
        if self.on_color_change:
            self.on_color_change(color)

    def change_width(self, value):
        self.width = int(float(value))

    # ------------------------------------------------------ coordinates
    def _canvas_size(self):
        return max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())

    def _world(self, event, clamp=True):
        wx, wy = self.view.to_world(event.x, event.y)
        return self.view.clamp_world(wx, wy) if clamp else (wx, wy)

    @staticmethod
    def _round_point(wx, wy):
        return [round(wx, 1), round(wy, 1)]

    # ------------------------------------------------------ zoom & pan
    def _after_view_change(self, redraw=True):
        self.auto_fit = False
        self._update_zoom_label()
        if redraw:
            self.schedule_redraw()

    def _update_zoom_label(self):
        self.zoom_label.config(text=f"{round(self.view.zoom * 100)}%")

    def zoom_in(self):
        w, h = self._canvas_size()
        self.zoom_at(self.ZOOM_STEP, w / 2, h / 2)

    def zoom_out(self):
        w, h = self._canvas_size()
        self.zoom_at(1 / self.ZOOM_STEP, w / 2, h / 2)

    def zoom_at(self, factor, sx, sy):
        if self.view.zoom_at(factor, sx, sy):
            self.view.clamp(*self._canvas_size())
            self._after_view_change()

    def reset_zoom(self):
        w, h = self._canvas_size()
        self.view.set_zoom_centered(1.0, w, h)
        self.view.clamp(w, h)
        self._after_view_change()

    def fit_to_window(self):
        w, h = self._canvas_size()
        self.view.fit(w, h)
        self.auto_fit = True
        self._update_zoom_label()
        self.schedule_redraw()

    def pan_by(self, dx, dy):
        w, h = self._canvas_size()
        applied_x, applied_y = self.view.pan(dx, dy, w, h)
        if applied_x or applied_y:
            self._remove_ring()
            self.canvas.move("all", applied_x, applied_y)
            self.auto_fit = False

    def _begin_pan(self, event):
        self._panning = True
        self._pan_last = (event.x, event.y)
        self._remove_ring()
        self._apply_cursor()

    def _pan_motion(self, event):
        if not self._panning:
            return
        self.pan_by(event.x - self._pan_last[0], event.y - self._pan_last[1])
        self._pan_last = (event.x, event.y)

    def _end_pan(self, _event=None):
        self._panning = False
        self._apply_cursor()

    def _space_press(self, _event=None):
        if not self._space_down:
            self._space_down = True
            self._apply_cursor()

    def _space_release(self, _event=None):
        self._space_down = False
        self._apply_cursor()

    def _on_wheel(self, event):
        num = getattr(event, "num", None)
        if num == 4:
            direction = 1
        elif num == 5:
            direction = -1
        else:
            direction = 1 if getattr(event, "delta", 0) > 0 else -1
        if getattr(event, "state", 0) & 0x1:  # Shift + wheel pans horizontally
            self.pan_by(60 * direction, 0)
            return
        factor = self.WHEEL_STEP if direction > 0 else 1 / self.WHEEL_STEP
        self.zoom_at(factor, event.x, event.y)

    def _on_canvas_configure(self, _event=None):
        w, h = self._canvas_size()
        if self.auto_fit:
            self.view.fit(w, h)
            self._update_zoom_label()
            self.schedule_redraw()
        else:
            before = (self.view.ox, self.view.oy)
            self.view.clamp(w, h)
            if (self.view.ox, self.view.oy) != before:
                self.schedule_redraw()

    # ------------------------------------------------------------ rendering
    def schedule_redraw(self):
        """Coalesce bursts of zoom/resize events into one redraw."""
        if self._redraw_job is None:
            self._redraw_job = self.canvas.after(16, self.redraw)

    def redraw(self):
        self._redraw_job = None
        try:
            self.canvas.delete("all")
            self._ring = None
            self._live_items = []
            self.preview = None
            self._draw_page()
            for operation in self.operations:
                self._render_operation(operation)
            self.remote_cursors.clear()
            for client_id, (username, color, x, y) in self.remote_cursor_positions.items():
                self.update_remote_cursor(client_id, username, color, x, y)
        except tk.TclError:
            pass  # window is closing

    def _draw_page(self):
        x1, y1 = self.view.to_screen(0, 0)
        x2, y2 = self.view.to_screen(PAGE_WIDTH, PAGE_HEIGHT)
        self.canvas.create_rectangle(x1 + 4, y1 + 5, x2 + 4, y2 + 5,
                                     fill=theme.PAPER_SHADOW, outline="")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=theme.PAPER, outline="")

    def _render_operation(self, operation, display_color=None):
        """Draw one stored operation (world coordinates) at the current view."""
        data = operation.get("data", {}) if isinstance(operation, dict) else {}
        try:
            self._render_data(data, display_color)
        except (TypeError, ValueError, IndexError, KeyError):
            pass  # ignore a malformed remote event instead of breaking the UI

    def _render_data(self, data, display_color):
        tool = data.get("tool")
        z = self.view.zoom
        color = theme.PAPER if tool == "eraser" else (display_color or data.get("color", "#000000"))
        base_width = int(data.get("width", 3)) * (4 if tool == "eraser" else 1)
        width = max(1.0, base_width * z)
        S = self.view.to_screen
        if tool in ("pen", "eraser"):
            points = data.get("points", [])
            if len(points) == 1:
                x, y = S(*points[0])
                r = width / 2
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)
            elif len(points) > 1:
                flat = [v for p in points for v in S(p[0], p[1])]
                self.canvas.create_line(*flat, fill=color, width=width,
                                        capstyle=tk.ROUND, joinstyle=tk.ROUND)
        elif tool in ("line", "rectangle", "circle"):
            points = data.get("points", [])
            if len(points) >= 2:
                x1, y1 = S(*points[0])
                x2, y2 = S(*points[-1])
                if tool == "line":
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width,
                                            capstyle=tk.ROUND)
                elif tool == "rectangle":
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
                else:
                    self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=width)
        elif tool == "text":
            x, y = S(data.get("x", 0), data.get("y", 0))
            size = max(1, round(max(10, int(data.get("width", 3)) * 4) * z))
            self.canvas.create_text(x, y, text=data.get("text", ""), fill=color,
                                    font=(theme.FONT, size))

    # -------------------------------------------------------------- drawing
    def start_drawing(self, event):
        self.canvas.focus_set()
        if self.tool == "hand" or self._space_down:
            self._begin_pan(event)
            return
        wx, wy = self._world(event, clamp=False)
        if not self.view.inside_page(wx, wy):
            self.status.config(text="Start drawing inside the white page")
            self.points = []
            return
        if self.tool == "text":
            text = simpledialog.askstring("Add Text", "Enter your text:")
            if text:
                x, y = self._round_point(wx, wy)
                self.publish({"tool": "text", "x": x, "y": y,
                              "text": text, "color": self.color, "width": self.width})
            return
        self.points = [self._round_point(wx, wy)]
        self.start_world = (wx, wy)
        self.last_x, self.last_y = event.x, event.y
        self.preview = None
        self._shape_end = None
        self._live_items = []

    def draw(self, event):
        if self._panning:
            self._pan_motion(event)
            return
        if not self.points:
            return
        wx, wy = self._world(event)
        x, y = self.view.to_screen(wx, wy)  # clamped, so live strokes stay on the page
        z = self.view.zoom
        if self.tool in ("pen", "eraser"):
            color = theme.PAPER if self.tool == "eraser" else self.color
            width = max(1.0, self.width * (4 if self.tool == "eraser" else 1) * z)
            self._live_items.append(self.canvas.create_line(
                self.last_x, self.last_y, x, y, fill=color, width=width,
                capstyle=tk.ROUND))
            self.points.append(self._round_point(wx, wy))
        else:
            if self.preview:
                self.canvas.delete(self.preview)
            sx, sy = self.view.to_screen(*self.start_world)
            width = max(1.0, self.width * z)
            if self.tool == "line":
                self.preview = self.canvas.create_line(sx, sy, x, y, fill=self.color, width=width)
            elif self.tool == "rectangle":
                self.preview = self.canvas.create_rectangle(sx, sy, x, y, outline=self.color,
                                                             width=width)
            elif self.tool == "circle":
                self.preview = self.canvas.create_oval(sx, sy, x, y, outline=self.color,
                                                       width=width)
            self._shape_end = self._round_point(wx, wy)
        self.last_x, self.last_y = x, y
        self._update_ring(event)

    def stop_drawing(self, event):
        if self._panning:
            self._end_pan(event)
            return
        if not self.points:
            return
        if self.preview:
            self.canvas.delete(self.preview)
            self.preview = None
        for item in self._live_items:
            self.canvas.delete(item)
        self._live_items = []
        if self.tool in ("pen", "eraser"):
            points = self.points[:]
        elif self._shape_end is not None:
            points = [self.points[0], self._shape_end]
        else:
            points = []  # a click without dragging creates no shape
        self.points = []
        if points:
            self.publish({"tool": self.tool, "color": self.color, "width": self.width,
                          "points": points})

    def publish(self, data):
        data = dict(data)
        if data.get("tool") != "eraser":
            data["color"] = self.user_color
        operation = {"type": "draw", "data": data}
        # Render local event immediately; server echo is deduplicated by sequence in SyncManager.
        self.apply_operation(operation)
        if self.on_operation:
            self.on_operation(operation)

    def apply_operation(self, operation, display_color=None):
        self._render_operation(operation, display_color)
        self.operations.append(operation)

    def load_board(self, board):
        self.operations = list(board)
        self.redraw()

    def clear_local(self):
        self.operations.clear()
        self.redraw()

    def clear_canvas(self):
        if self.on_clear:
            self.on_clear()
        else:
            self.clear_local()

    def request_clear(self):
        """Ask first: clearing affects every participant in the room."""
        if messagebox.askyesno("Clear board", "Clear the whole board for everyone in this room?"):
            self.clear_canvas()

    # ----------------------------------------------------- pointer feedback
    def _on_motion(self, event):
        wx, wy = self.view.to_world(event.x, event.y)
        if self.on_cursor_move and self.view.inside_page(wx, wy):
            self.on_cursor_move(wx, wy)
        self.coords.config(text=f"x {int(wx)}   y {int(wy)}" if self.view.inside_page(wx, wy) else "")
        if not self.points and not self._panning:
            self._update_ring(event)

    def update_remote_cursor(self, client_id, username, color, x, y):
        """Render another participant's pointer in shared page/world coordinates."""
        self.remote_cursor_positions[client_id] = (username, color, float(x), float(y))
        try:
            sx, sy = self.view.to_screen(float(x), float(y))
            if client_id not in self.remote_cursors:
                dot = self.canvas.create_oval(sx-5, sy-5, sx+5, sy+5,
                                              fill=color, outline="#FFFFFF", width=1,
                                              tags=("remote_cursor",))
                label = self.canvas.create_text(sx+9, sy-10, text=username,
                                                anchor="sw", fill=color,
                                                font=("Arial", 9, "bold"),
                                                tags=("remote_cursor",))
                self.remote_cursors[client_id] = (dot, label)
            else:
                dot, label = self.remote_cursors[client_id]
                self.canvas.coords(dot, sx-5, sy-5, sx+5, sy+5)
                self.canvas.coords(label, sx+9, sy-10)
                self.canvas.itemconfigure(dot, fill=color)
                self.canvas.itemconfigure(label, text=username, fill=color)
            self.canvas.tag_raise("remote_cursor")
        except (tk.TclError, TypeError, ValueError):
            pass

    def remove_remote_cursor(self, client_id):
        self.remote_cursor_positions.pop(client_id, None)
        items = self.remote_cursors.pop(client_id, ())
        for item in items:
            try:
                self.canvas.delete(item)
            except tk.TclError:
                pass

    def clear_remote_cursors(self):
        for client_id in list(self.remote_cursors):
            self.remove_remote_cursor(client_id)

    def _on_leave(self, _event=None):
        self._remove_ring()
        self.coords.config(text="")

    def _update_ring(self, event):
        """Show the real brush size under the pointer for pen and eraser."""
        if self.tool not in ("pen", "eraser") or self._space_down:
            self._remove_ring()
            return
        eraser = self.tool == "eraser"
        radius = max(1.0, self.width * (4 if eraser else 1) * self.view.zoom / 2)
        if not eraser and radius < 4:
            self._remove_ring()
            return
        box = (event.x - radius, event.y - radius, event.x + radius, event.y + radius)
        if self._ring is None:
            self._ring = self.canvas.create_oval(*box, outline="#475569" if eraser else self.color,
                                                 width=1)
        else:
            self.canvas.coords(self._ring, *box)
        self.canvas.tag_raise(self._ring)

    def _remove_ring(self):
        if self._ring is not None:
            self.canvas.delete(self._ring)
            self._ring = None

    def update_status(self, message):
        self.status.config(text=message)
