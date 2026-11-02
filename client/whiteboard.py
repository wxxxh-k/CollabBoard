
import tkinter as tk
from tkinter import colorchooser, simpledialog


class Whiteboard:

    def __init__(self, root, on_operation=None, on_clear=None):

        self.root = root
        self.on_operation = on_operation
        self.on_clear = on_clear

        self.root.title("CollabBoard - Collaborative Whiteboard")
        self.root.geometry("1200x750")
        self.root.minsize(850, 550)
        self.root.configure(bg="#17243B")

        self.tool = "pen"
        self.color = "#2563EB"
        self.width = 3

        self.start_x = 0
        self.start_y = 0
        self.last_x = 0
        self.last_y = 0

        self.points = []
        self.preview = None
        self.operations = []

        # Header
        header = tk.Frame(root, bg="#17243B", height=55)
        header.pack(fill="x")

        tk.Label(
            header,
            text="  CollabBoard",
            font=("Arial", 19, "bold"),
            fg="white",
            bg="#17243B"
        ).pack(side="left", padx=15, pady=10)

        tk.Label(
            header,
            text="LAN COLLABORATIVE WHITEBOARD",
            font=("Arial", 9),
            fg="#94A3B8",
            bg="#17243B"
        ).pack(side="left", padx=10)

        # Main area
        main = tk.Frame(root, bg="#17243B")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # Toolbar
        toolbar = tk.Frame(main, bg="#263750", width=155)
        toolbar.pack(side="left", fill="y", padx=(0, 10))
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text="DRAWING TOOLS",
            bg="#263750",
            fg="#CBD5E1",
            font=("Arial", 10, "bold")
        ).pack(pady=15)

        self.add_tool(toolbar, "Pen", "pen")
        self.add_tool(toolbar, "Eraser", "eraser")
        self.add_tool(toolbar, "Line", "line")
        self.add_tool(toolbar, "Rectangle", "rectangle")
        self.add_tool(toolbar, "Circle", "circle")
        self.add_tool(toolbar, "Text", "text")

        tk.Label(
            toolbar,
            text="COLOR",
            bg="#263750",
            fg="white"
        ).pack(pady=(20, 5))

        tk.Button(
            toolbar,
            text="Choose Color",
            command=self.choose_color,
            bg="#334B6B",
            fg="white",
            relief="flat"
        ).pack(fill="x", padx=12)

        self.color_display = tk.Label(
            toolbar,
            bg=self.color,
            height=1
        )
        self.color_display.pack(fill="x", padx=12, pady=5)

        tk.Label(
            toolbar,
            text="BRUSH SIZE",
            bg="#263750",
            fg="white"
        ).pack(pady=(15, 5))

        self.size_slider = tk.Scale(
            toolbar,
            from_=1,
            to=20,
            orient="horizontal",
            command=self.change_width,
            bg="#263750",
            fg="white",
            highlightthickness=0,
            troughcolor="#64748B"
        )
        self.size_slider.set(3)
        self.size_slider.pack(fill="x", padx=8)

        tk.Button(
            toolbar,
            text="Clear Canvas",
            command=self.clear_canvas,
            bg="#991B1B",
            fg="white",
            relief="flat"
        ).pack(fill="x", padx=12, pady=20)

        # Drawing canvas
        canvas_frame = tk.Frame(main, bg="#DCE3EC")
        canvas_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            cursor="cross",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=3, pady=3)

        # Mouse events
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)

        # Status bar
        self.status = tk.Label(
            root,
            text="Ready | Tool: Pen | Local Mode",
            bg="#17243B",
            fg="#CBD5E1",
            anchor="w",
            padx=15
        )
        self.status.pack(fill="x", pady=5)

    # ----------------------------------
    # TOOL SELECTION
    # ----------------------------------

    def add_tool(self, parent, name, tool):

        tk.Button(
            parent,
            text=name,
            command=lambda: self.select_tool(tool),
            bg="#334B6B",
            fg="white",
            activebackground="#2563EB",
            relief="flat",
            font=("Arial", 10),
            pady=7
        ).pack(fill="x", padx=12, pady=3)

    def select_tool(self, tool):

        self.tool = tool

        self.status.config(
            text=f"Ready | Tool: {tool.title()}"
        )

    # ----------------------------------
    # COLOR AND WIDTH
    # ----------------------------------

    def choose_color(self):

        selected = colorchooser.askcolor(
            initialcolor=self.color
        )[1]

        if selected:
            self.color = selected
            self.color_display.config(bg=selected)

    def change_width(self, value):

        self.width = int(float(value))

    # ----------------------------------
    # START DRAWING
    # ----------------------------------

    def start_drawing(self, event):

        self.start_x = event.x
        self.start_y = event.y

        self.last_x = event.x
        self.last_y = event.y

        if self.tool == "text":
            self.add_text(event.x, event.y)
            return

        self.points = [[event.x, event.y]]
        self.preview = None

    # ----------------------------------
    # DRAW PREVIEW
    # ----------------------------------

    def draw(self, event):

        if self.tool == "text" or not self.points:
            return

        x = event.x
        y = event.y

        if self.tool in ("pen", "eraser"):

            current_color = (
                "white" if self.tool == "eraser"
                else self.color
            )

            self.canvas.create_line(
                self.last_x,
                self.last_y,
                x,
                y,
                fill=current_color,
                width=self.width * (
                    4 if self.tool == "eraser" else 1
                ),
                capstyle=tk.ROUND,
                smooth=True
            )

            self.points.append([x, y])

        else:

            if self.preview:
                self.canvas.delete(self.preview)

            if self.tool == "line":

                self.preview = self.canvas.create_line(
                    self.start_x,
                    self.start_y,
                    x,
                    y,
                    fill=self.color,
                    width=self.width
                )

            elif self.tool == "rectangle":

                self.preview = self.canvas.create_rectangle(
                    self.start_x,
                    self.start_y,
                    x,
                    y,
                    outline=self.color,
                    width=self.width
                )

            elif self.tool == "circle":

                self.preview = self.canvas.create_oval(
                    self.start_x,
                    self.start_y,
                    x,
                    y,
                    outline=self.color,
                    width=self.width
                )

        self.last_x = x
        self.last_y = y

    # ----------------------------------
    # STOP DRAWING
    # ----------------------------------

    def stop_drawing(self, event):

        if self.tool == "text" or not self.points:
            return

        self.points.append([event.x, event.y])

        operation = {
            "type": "DRAW",
            "data": {
                "tool": self.tool,
                "color": self.color,
                "width": self.width,
                "points": list(self.points)
            }
        }

        if self.preview:
            self.canvas.delete(self.preview)
            self.preview = None

        # Render final operation locally
        self.apply_operation(operation)

        # Send operation to synchronization manager
        if self.on_operation:
            self.on_operation(operation)

        self.points = []

    # ----------------------------------
    # TEXT ANNOTATION
    # ----------------------------------

    def add_text(self, x, y):

        text = simpledialog.askstring(
            "Add Text",
            "Enter your text:"
        )

        if text:

            operation = {
                "type": "DRAW",
                "data": {
                    "tool": "text",
                    "x": x,
                    "y": y,
                    "text": text,
                    "color": self.color,
                    "width": self.width
                }
            }

            self.apply_operation(operation)

            if self.on_operation:
                self.on_operation(operation)

    # ----------------------------------
    # APPLY DRAWING OPERATION
    # ----------------------------------

    def apply_operation(self, operation):

        data = operation.get("data", {})
        tool = data.get("tool")

        if tool in ("pen", "eraser"):

            points = data.get("points", [])

            color = (
                "white" if tool == "eraser"
                else data.get("color", "#000000")
            )

            width = data.get("width", 3) * (
                4 if tool == "eraser" else 1
            )

            for i in range(1, len(points)):

                self.canvas.create_line(
                    *points[i - 1],
                    *points[i],
                    fill=color,
                    width=width,
                    capstyle=tk.ROUND,
                    smooth=True
                )

        elif tool in ("line", "rectangle", "circle"):

            points = data.get("points", [])

            if not points:
                return

            x1, y1 = points[0]
            x2, y2 = points[-1]

            if tool == "line":

                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=data["color"],
                    width=data["width"]
                )

            elif tool == "rectangle":

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=data["color"],
                    width=data["width"]
                )

            elif tool == "circle":

                self.canvas.create_oval(
                    x1, y1, x2, y2,
                    outline=data["color"],
                    width=data["width"]
                )

        elif tool == "text":

            self.canvas.create_text(
                data["x"],
                data["y"],
                text=data["text"],
                fill=data["color"],
                font=("Arial", 14)
            )

        self.operations.append(operation)

    # ----------------------------------
    # APPLY REMOTE DRAWING
    # ----------------------------------

    def apply_remote_operation(self, event):

        operation = {
            "type": "DRAW",
            "data": event.get("data", {})
        }

        self.apply_operation(operation)

    # ----------------------------------
    # LOAD CANVAS SNAPSHOT
    # ----------------------------------

    def load_canvas(self, board):

        self.canvas.delete("all")
        self.operations.clear()

        for event in board:

            self.apply_remote_operation(event)

    # ----------------------------------
    # CLEAR CANVAS
    # ----------------------------------

    def clear_canvas(self):

        if self.on_clear:
            self.on_clear()
        else:
            self.canvas.delete("all")
            self.operations.clear()

    # ----------------------------------
    # UPDATE STATUS
    # ----------------------------------

    def update_status(self, message):

        self.status.config(text=message)


if __name__ == "__main__":

    root = tk.Tk()
    app = Whiteboard(root)
    root.mainloop()
