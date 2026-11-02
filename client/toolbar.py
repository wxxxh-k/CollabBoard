import tkinter as tk
from tkinter import colorchooser

class Toolbar:
    """Drawing and shared-board actions for the Whiteboard widget."""
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg="#263750", width=155)
        self.frame.pack(side="left", fill="y", padx=(0, 8))
        self.frame.pack_propagate(False)
        tk.Label(self.frame, text="DRAWING TOOLS", bg="#263750", fg="#CBD5E1",
                 font=("Arial", 10, "bold")).pack(pady=12)
        for name, tool in [("Pen", "pen"), ("Eraser", "eraser"), ("Line", "line"),
                           ("Rectangle", "rectangle"), ("Circle", "circle"), ("Text", "text")]:
            tk.Button(self.frame, text=name, command=lambda t=tool: app.select_tool(t),
                      bg="#334B6B", fg="white", relief="flat", pady=5).pack(fill="x", padx=10, pady=2)
        tk.Label(self.frame, text="COLOR", bg="#263750", fg="white").pack(pady=(14, 4))
        tk.Button(self.frame, text="Choose Color", command=self.choose_color,
                  bg="#334B6B", fg="white", relief="flat").pack(fill="x", padx=10)
        self.color_display = tk.Label(self.frame, bg=app.color, height=1)
        self.color_display.pack(fill="x", padx=10, pady=5)
        tk.Label(self.frame, text="BRUSH SIZE", bg="#263750", fg="white").pack(pady=(10, 2))
        self.size_scale = tk.Scale(self.frame, from_=1, to=20, orient="horizontal",
                                   command=app.change_width, bg="#263750", fg="white",
                                   highlightthickness=0, troughcolor="#64748B")
        self.size_scale.set(3)
        self.size_scale.pack(fill="x", padx=6)
        for label, callback in [
            ("Undo", app.on_undo), ("Redo", app.on_redo),
            ("Save", app.on_save), ("Restore", app.on_load)
        ]:
            tk.Button(self.frame, text=label, command=callback or (lambda: None),
                      bg="#334B6B", fg="white", relief="flat").pack(fill="x", padx=10, pady=3)
        tk.Button(self.frame, text="Clear Canvas", command=app.clear_canvas,
                  bg="#991B1B", fg="white", relief="flat").pack(fill="x", padx=10, pady=(10, 4))

    def choose_color(self):
        selected = colorchooser.askcolor(initialcolor=self.app.color)[1]
        if selected:
            self.app.set_color(selected)
            self.color_display.config(bg=selected)
