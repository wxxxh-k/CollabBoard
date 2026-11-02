import tkinter as tk
from datetime import datetime


class ChatPanel(tk.Frame):
    """A clean, messenger-style chat panel for the CollabBoard sidebar."""

    BG = "#F2F5F8"
    WHITE = "#FFFFFF"
    BLUE = "#2798D5"
    TEXT = "#263445"
    MUTED = "#8A98A8"

    def __init__(self, parent, username, send_callback=None):
        super().__init__(parent, bg=self.BG, highlightthickness=1,
                         highlightbackground="#E5EAF0")
        self.username = username
        self.send_callback = send_callback
        self.user_colors = {}
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=self.WHITE, height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_area = tk.Frame(header, bg=self.WHITE)
        title_area.pack(side="left", fill="both", expand=True, padx=14)
        tk.Label(title_area, text="Group Chat", bg=self.WHITE, fg=self.TEXT,
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(title_area, text="Messages in this room", bg=self.WHITE,
                 fg=self.MUTED, font=("Arial", 8)).pack(anchor="w")
        tk.Label(header, text="●", bg=self.WHITE, fg="#36B982",
                 font=("Arial", 10)).pack(side="right", padx=(0, 14))

        # Scrollable conversation area
        conversation = tk.Frame(self, bg=self.BG)
        conversation.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(conversation, bg=self.BG, highlightthickness=0,
                                bd=0)
        self.scrollbar = tk.Scrollbar(conversation, orient="vertical",
                                      command=self.canvas.yview, width=7)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self.BG)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner,
                                                   anchor="nw")
        self.inner.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        # Composer
        composer = tk.Frame(self, bg=self.WHITE, padx=10, pady=10,
                            highlightthickness=1, highlightbackground="#E8EDF2")
        composer.pack(fill="x", side="bottom")
        entry_shell = tk.Frame(composer, bg="#F2F5F8",
                               highlightthickness=1,
                               highlightbackground="#E7ECF1")
        entry_shell.pack(fill="x")
        self.message_entry = tk.Entry(
            entry_shell, font=("Arial", 9), bg="#F2F5F8", fg=self.TEXT,
            insertbackground=self.TEXT, relief="flat", bd=0
        )
        self.message_entry.pack(side="left", fill="x", expand=True,
                                padx=(10, 4), pady=9)
        self.message_entry.insert(0, "Type your message...")
        self.message_entry.config(fg="#9AA6B2")
        self.message_entry.bind("<FocusIn>", self._clear_placeholder)
        self.message_entry.bind("<FocusOut>", self._restore_placeholder)
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        self.send_button = tk.Button(
            entry_shell, text="➤", command=self.send_message,
            bg=self.BLUE, activebackground="#1687C4", fg=self.WHITE,
            activeforeground=self.WHITE, relief="flat", bd=0,
            font=("Arial", 12, "bold"), cursor="hand2", width=3
        )
        self.send_button.pack(side="right", padx=4, pady=3, ipady=2)

    def _clear_placeholder(self, _event=None):
        if self.message_entry.get() == "Type your message...":
            self.message_entry.delete(0, tk.END)
            self.message_entry.config(fg=self.TEXT)

    def _restore_placeholder(self, _event=None):
        if not self.message_entry.get().strip():
            self.message_entry.delete(0, tk.END)
            self.message_entry.insert(0, "Type your message...")
            self.message_entry.config(fg="#9AA6B2")

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.after_idle(lambda: self.canvas.yview_moveto(1.0))

    def _resize_inner(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)
        # Keep message bubbles inside the available sidebar width.
        self.message_wrap = max(110, min(260, event.width - 85))

    def _on_mousewheel(self, event):
        if self.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def send_message(self):
        message = self.message_entry.get().strip()
        if not message or message == "Type your message...":
            return
        if self.send_callback:
            self.send_callback(message)
            self.message_entry.delete(0, tk.END)
            self.message_entry.config(fg=self.TEXT)
            self.message_entry.focus_set()

    def set_user_colors(self, users):
        self.user_colors = {
            item.get("username"): item.get("color", "#64748B")
            for item in (users or []) if isinstance(item, dict)
        }

    def display_message(self, username, message, timestamp=None, is_own=None, color=None):
        timestamp = timestamp or datetime.now().strftime("%H:%M")
        color = color or self.user_colors.get(username, "#64748B")
        own = (username == self.username) if is_own is None else is_own
        system = username == "CollabBoard"

        if system:
            notice = tk.Label(self.inner, text=str(message), bg="#E5EDF4",
                              fg="#738397", font=("Arial", 8),
                              padx=10, pady=5, wraplength=220)
            notice.pack(anchor="center", pady=8)
        else:
            row = tk.Frame(self.inner, bg=self.BG)
            row.pack(fill="x", padx=8, pady=(7, 2))

            bubble_column = tk.Frame(row, bg=self.BG)
            bubble_column.pack(side="right" if own else "left",
                               anchor="e" if own else "w",
                               padx=(24, 0) if own else (0, 24))

            if not own:
                initials = "".join(part[0] for part in str(username).split()[:2]).upper()
                avatar = tk.Label(row, text=initials or "U", bg=color,
                                  fg="#FFFFFF", font=("Arial", 7, "bold"),
                                  width=3, height=1, padx=2, pady=4)
                avatar.pack(side="left", anchor="s", padx=(0, 5), pady=(0, 15))

            if not own:
                tk.Label(bubble_column, text=str(username), bg=self.BG,
                         fg=color, font=("Arial", 7, "bold")).pack(anchor="w", pady=(0, 2))

            bubble_bg = color if own else self.WHITE
            bubble_fg = self.WHITE if own else self.TEXT
            bubble = tk.Label(
                bubble_column, text=str(message), bg=bubble_bg, fg=bubble_fg,
                font=("Arial", 9), justify="left", anchor="w",
                wraplength=max(110, min(260, self.canvas.winfo_width() - 85)), padx=10, pady=7, relief="flat",
                highlightthickness=0
            )
            bubble.pack(anchor="e" if own else "w")
            tk.Label(bubble_column, text=timestamp, bg=self.BG,
                     fg=self.MUTED, font=("Arial", 7)).pack(
                         anchor="e" if own else "w", pady=(2, 0))

        self.canvas.after_idle(lambda: self.canvas.yview_moveto(1.0))
