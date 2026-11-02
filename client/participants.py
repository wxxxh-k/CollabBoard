import tkinter as tk
from common.user_colors import DEFAULT_USER_COLOR


class ParticipantsPanel(tk.Frame):
    """Compact, scrollable participant list for rooms of any size."""
    def __init__(self, parent, username):
        super().__init__(parent, bg="#111827")
        self.username = username
        self.users = []
        tk.Label(self, text="👥  Participants & Colors", font=("Arial", 11, "bold"),
                 fg="white", bg="#1F2937", padx=10, pady=9).pack(fill="x")
        self.count_label = tk.Label(self, text="0 members online · color key", fg="#34D399",
                                    bg="#111827", anchor="w", padx=10)
        self.count_label.pack(fill="x", pady=(5, 1))

        list_host = tk.Frame(self, bg="#111827")
        list_host.pack(fill="both", expand=True, padx=6, pady=(2, 5))
        self.canvas = tk.Canvas(list_host, bg="#111827", highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_host, orient="vertical", command=self.canvas.yview, width=7)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.users_frame = tk.Frame(self.canvas, bg="#111827")
        self.window_id = self.canvas.create_window((0, 0), window=self.users_frame, anchor="nw")
        self.users_frame.bind("<Configure>", self._update_scroll)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))

    def _update_scroll(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def update_participants(self, users):
        self.users = list(users or [])
        for widget in self.users_frame.winfo_children():
            widget.destroy()
        self.count_label.config(text=f"{len(self.users)} members online · color key")
        for user in self.users:
            if isinstance(user, str):
                name, color = user, DEFAULT_USER_COLOR
            else:
                name = user.get("username", "Unknown")
                color = user.get("display_color", user.get("color", DEFAULT_USER_COLOR))
            row = tk.Frame(self.users_frame, bg="#1F2937", padx=7, pady=4)
            row.pack(fill="x", pady=1)
            swatch = tk.Canvas(row, width=14, height=14, bg="#1F2937", highlightthickness=0, bd=0)
            swatch.create_oval(2, 2, 12, 12, fill=color, outline=color)
            swatch.pack(side="left", padx=(0, 7))
            tk.Label(row, text=name, fg="white", bg="#1F2937", anchor="w",
                     font=("Arial", 9, "bold")).pack(side="left", fill="x", expand=True)
            tk.Label(row, text=color.upper(), fg=color, bg="#1F2937",
                     font=("Arial", 8, "bold")).pack(side="right")
        self.canvas.yview_moveto(0)
