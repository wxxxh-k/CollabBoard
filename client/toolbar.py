import tkinter as tk
from tkinter import colorchooser

class Toolbar:
    """Drawing and shared-board actions for the Whiteboard widget."""
    
    def __init__(self, parent, app):
        self.app = app

        self.frame = tk.Frame(parent, bg="#263750", width=155)
        self.frame.pack(side="left", fill="y", padx=(0, 8))
        self.frame.pack_propagate(False)
        # A scrollable tool rail prevents controls disappearing on short displays.
        self.scroll_canvas = tk.Canvas(self.frame, bg="#263750", highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.scroll_canvas.yview, width=6)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.content = tk.Frame(self.scroll_canvas, bg="#263750")
        self.content_id = self.scroll_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind("<Configure>", lambda e: self.scroll_canvas.itemconfigure(self.content_id, width=e.width))
        self.scroll_canvas.bind_all("<MouseWheel>", self._mousewheel, add="+")

        tk.Label(
            self.content, text="DRAWING TOOLS",
            bg="#263750", fg="#CBD5E1",
            font=("Arial", 10, "bold")
        ).pack(pady=12)

        for name, tool in [
            ("Pen", "pen"), ("Eraser", "eraser"),
            ("Line", "line"), ("Rectangle", "rectangle"),
            ("Circle", "circle"), ("Text", "text")
        ]:
            tk.Button(
                self.content, text=name,
                command=lambda t=tool: app.select_tool(t),
                bg="#334B6B", fg="white",
                relief="flat", pady=5
            ).pack(fill="x", padx=10, pady=2)

        # Color preference
        tk.Label(
            self.content, text="COLOR PREFERENCE",
            bg="#263750", fg="white"
        ).pack(pady=(14, 4))

        self.color_display = tk.Label(
            self.content, bg=app.preferred_color,
            height=2, relief="solid", bd=1
        )
        self.color_display.pack(fill="x", padx=10, pady=5)

        # NEW: Color picker button
        tk.Button(
            self.content,
            text="Choose My Color",
            command=self.choose_color,
            bg="#4F46E5",
            fg="white",
            relief="flat",
            pady=5
        ).pack(fill="x", padx=10, pady=3)

        # Brush size
        tk.Label(
            self.content, text="BRUSH SIZE",
            bg="#263750", fg="white"
        ).pack(pady=(10, 2))

        self.size_scale = tk.Scale(
            self.content, from_=1, to=20,
            orient="horizontal",
            command=app.change_width,
            bg="#263750", fg="white",
            highlightthickness=0,
            troughcolor="#64748B"
        )
        self.size_scale.set(3)
        self.size_scale.pack(fill="x", padx=6)

        # Other controls
        for label, callback in [
            ("Undo", app.on_undo),
            ("Redo", app.on_redo),
            ("Save", app.on_save),
            ("Restore", app.on_load)
        ]:
            tk.Button(
                self.content, text=label,
                command=callback or (lambda: None),
                bg="#334B6B", fg="white",
                relief="flat"
            ).pack(fill="x", padx=10, pady=3)

        tk.Button(
            self.content, text="Clear Canvas",
            command=app.clear_canvas,
            bg="#991B1B", fg="white",
            relief="flat"
        ).pack(fill="x", padx=10, pady=(10, 4))

    def _mousewheel(self, event):
        try:
            if self.winfo_exists() and self.scroll_canvas.winfo_pointerx() >= self.scroll_canvas.winfo_rootx() and self.scroll_canvas.winfo_pointerx() <= self.scroll_canvas.winfo_rootx() + self.scroll_canvas.winfo_width():
                self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
        except tk.TclError:
            pass

    def choose_color(self):
        selected = colorchooser.askcolor(initialcolor=self.app.preferred_color)[1]
        if selected:
            self.app.set_color(selected)
            self.color_display.config(bg=selected)
