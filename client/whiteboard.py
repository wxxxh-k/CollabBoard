import tkinter as tk
from tkinter import simpledialog
from client.toolbar import Toolbar

class Whiteboard:
    """Tkinter drawing surface. All shared actions are delegated to SyncManager."""
    def __init__(self, parent, on_operation=None, on_clear=None,
                 on_undo=None, on_redo=None, on_save=None, on_load=None):
        self.parent = parent
        self.on_operation = on_operation
        self.on_clear = on_clear
        self.on_undo = on_undo
        self.on_redo = on_redo
        self.on_save = on_save
        self.on_load = on_load
        self.tool, self.color, self.width = "pen", "#2563EB", 3
        self.points, self.preview = [], None
        self.operations = []
        self._build()

    def _build(self):
        self.frame = tk.Frame(self.parent, bg="#17243B")
        self.frame.pack(side="left", fill="both", expand=True)
        header = tk.Frame(self.frame, bg="#17243B", height=42)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="COLLABORATIVE WHITEBOARD", fg="white",
                 bg="#17243B", font=("Arial", 10, "bold")).pack(side="left", padx=12, pady=10)

        body = tk.Frame(self.frame, bg="#17243B")
        body.pack(fill="both", expand=True, padx=5, pady=5)
        self.toolbar = Toolbar(body, self)

        canvas_frame = tk.Frame(body, bg="#DCE3EC")
        canvas_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="white", cursor="cross",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=3, pady=3)
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        self.status = tk.Label(self.frame, text="Connected", bg="#17243B",
                               fg="#CBD5E1", anchor="w", padx=10)
        self.status.pack(fill="x", pady=3)

    def select_tool(self, tool):
        self.tool = tool
        self.status.config(text=f"Tool: {tool.title()}")

    def set_color(self, color):
        self.color = color

    def change_width(self, value):
        self.width = int(float(value))

    def start_drawing(self, event):
        if self.tool == "text":
            text = simpledialog.askstring("Add Text", "Enter your text:")
            if text:
                self.publish({"tool": "text", "x": event.x, "y": event.y,
                              "text": text, "color": self.color, "width": self.width})
            return
        self.points = [[event.x, event.y]]
        self.start_x, self.start_y = event.x, event.y
        self.last_x, self.last_y = event.x, event.y
        self.preview = None

    def draw(self, event):
        if not self.points:
            return
        x, y = event.x, event.y
        if self.tool in ("pen", "eraser"):
            color = "white" if self.tool == "eraser" else self.color
            width = self.width * 4 if self.tool == "eraser" else self.width
            self.canvas.create_line(self.last_x, self.last_y, x, y, fill=color,
                                    width=width, capstyle=tk.ROUND, smooth=True)
            self.points.append([x, y])
        else:
            if self.preview:
                self.canvas.delete(self.preview)
            if self.tool == "line":
                self.preview = self.canvas.create_line(self.start_x, self.start_y, x, y,
                                                        fill=self.color, width=self.width)
            elif self.tool == "rectangle":
                self.preview = self.canvas.create_rectangle(self.start_x, self.start_y, x, y,
                                                             outline=self.color, width=self.width)
            elif self.tool == "circle":
                self.preview = self.canvas.create_oval(self.start_x, self.start_y, x, y,
                                                       outline=self.color, width=self.width)
        if self.tool not in ("pen", "eraser"):
            self.points.append([x, y])
        self.last_x, self.last_y = x, y

    def stop_drawing(self, event):
        if not self.points:
            return
        if self.preview:
            self.canvas.delete(self.preview)
            self.preview = None
        data = {"tool": self.tool, "color": self.color, "width": self.width,
                "points": self.points[:]}
        self.publish(data)
        self.points = []

    def publish(self, data):
        operation = {"type": "draw", "data": data}
        # Render local event immediately; server echo is deduplicated by sequence in SyncManager.
        self.apply_operation(operation)
        if self.on_operation:
            self.on_operation(operation)

    def apply_operation(self, operation):
        data = operation.get("data", {})
        tool = data.get("tool")
        color = "white" if tool == "eraser" else data.get("color", "#000000")
        width = int(data.get("width", 3)) * (4 if tool == "eraser" else 1)
        if tool in ("pen", "eraser"):
            points = data.get("points", [])
            if len(points) == 1:
                x, y = points[0]
                r = width / 2
                self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline=color)
            else:
                for a, b in zip(points, points[1:]):
                    self.canvas.create_line(*a, *b, fill=color, width=width,
                                            capstyle=tk.ROUND, smooth=True)
        elif tool in ("line", "rectangle", "circle"):
            points = data.get("points", [])
            if len(points) >= 2:
                x1, y1 = points[0]
                x2, y2 = points[-1]
                if tool == "line":
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
                elif tool == "rectangle":
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
                else:
                    self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=width)
        elif tool == "text":
            self.canvas.create_text(data.get("x", 0), data.get("y", 0),
                                    text=data.get("text", ""), fill=color,
                                    font=("Arial", max(10, width * 4)))
        self.operations.append(operation)

    def load_board(self, board):
        self.canvas.delete("all")
        self.operations = []
        for event in board:
            self.apply_operation(event)

    def clear_local(self):
        self.canvas.delete("all")
        self.operations.clear()

    def clear_canvas(self):
        if self.on_clear:
            self.on_clear()
        else:
            self.clear_local()

    def update_status(self, message):
        self.status.config(text=message)
