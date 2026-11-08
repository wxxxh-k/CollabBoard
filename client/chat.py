import tkinter as tk
from datetime import datetime


class ChatPanel(tk.Frame):
    """A clean, messenger-style chat panel for the CollabBoard sidebar."""

    BG = "#F2F5F8"
    WHITE = "#FFFFFF"
    BLUE = "#2798D5"
    TEXT = "#263445"
    MUTED = "#8A98A8"
    PLACEHOLDER = "Type your message..."

    def __init__(self, parent, username, send_callback=None, back_callback=None):
        super().__init__(parent, bg=self.BG, highlightthickness=1,
                         highlightbackground="#E5EAF0")
        self.username = username
        self.send_callback = send_callback
        self.back_callback = back_callback  # returns to the group conversation
        self.user_colors = {}
        self._composer_enabled = True
        self._banner_job = None
        self._banner_visible = False
        self._banner_callback = None
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=self.WHITE, height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Shown only inside a private conversation; returns to the group chat.
        self.back_button = tk.Button(
            header, text="\u2039", command=self._go_back, bg=self.WHITE,
            activebackground="#E8F4FB", fg=self.BLUE, activeforeground=self.BLUE,
            relief="flat", bd=0, font=("Arial", 18, "bold"), cursor="hand2", width=2)

        self.title_area = tk.Frame(header, bg=self.WHITE)
        self.title_area.pack(side="left", fill="both", expand=True, padx=14)
        self.title_label = tk.Label(self.title_area, text="Group Chat", bg=self.WHITE,
                                    fg=self.TEXT, font=("Arial", 12, "bold"))
        self.title_label.pack(anchor="w", pady=(10, 0))
        self.subtitle_label = tk.Label(self.title_area, text="Messages in this room",
                                       bg=self.WHITE, fg=self.MUTED, font=("Arial", 8))
        self.subtitle_label.pack(anchor="w")
        self.status_dot = tk.Label(header, text="●", bg=self.WHITE, fg="#36B982",
                                   font=("Arial", 10))
        self.status_dot.pack(side="right", padx=(0, 14))

        # Thin accent under the header: visible only in private conversations.
        self.private_accent = tk.Frame(self, bg=self.BLUE, height=3)
        # Transient "new private message" notice (click to open the conversation).
        self.banner = tk.Label(self, text="", bg="#E8F4FB", fg=self.BLUE, anchor="w",
                               font=("Arial", 8, "bold"), padx=12, pady=6, cursor="hand2")
        self.banner.bind("<Button-1>", self._banner_clicked)

        # Scrollable conversation area
        self.conversation_frame = tk.Frame(self, bg=self.BG)
        self.conversation_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.conversation_frame, bg=self.BG, highlightthickness=0,
                                bd=0)
        self.scrollbar = tk.Scrollbar(self.conversation_frame, orient="vertical",
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
        if not self._composer_enabled:
            return
        if self.message_entry.get() == "Type your message...":
            self.message_entry.delete(0, tk.END)
            self.message_entry.config(fg=self.TEXT)

    def _restore_placeholder(self, _event=None):
        if not self._composer_enabled:
            return
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
        # The chat and drawing toolbar both use bind_all; only scroll chat
        # when the pointer is actually over the conversation area.
        if not self.winfo_exists():
            return
        try:
            x, y = self.canvas.winfo_pointerx(), self.canvas.winfo_pointery()
            inside = (
                self.canvas.winfo_rootx() <= x <= self.canvas.winfo_rootx() + self.canvas.winfo_width()
                and self.canvas.winfo_rooty() <= y <= self.canvas.winfo_rooty() + self.canvas.winfo_height()
            )
            if inside:
                self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        except tk.TclError:
            pass

    def send_message(self):
        if not self._composer_enabled:
            return
        message = self.message_entry.get().strip()
        if not message or message == "Type your message...":
            return
        if self.send_callback:
            self.send_callback(message)
            self.message_entry.delete(0, tk.END)
            self.message_entry.config(fg=self.TEXT)
            self.message_entry.focus_set()

    # ---- conversation switching (group chat <-> private chats) -------------
    def _go_back(self):
        if self.back_callback:
            self.back_callback()

    @staticmethod
    def _shorten(text, limit):
        text = str(text)
        return text if len(text) <= limit else text[: limit - 1] + "\u2026"

    def set_conversation(self, private=False, name=None, online=True):
        """Switch the header between the group chat and a private chat."""
        self.back_button.pack_forget()
        self.private_accent.pack_forget()
        if private:
            self.title_label.config(text=self._shorten(name, 18))
            self.subtitle_label.config(
                text=f"Private \u00b7 only you and {self._shorten(name, 14)}")
            self.back_button.pack(side="left", before=self.title_area, padx=(8, 0))
            self.private_accent.pack(fill="x", before=self.conversation_frame)
        else:
            self.title_label.config(text="Group Chat")
            self.subtitle_label.config(text="Messages in this room")
        self.status_dot.config(fg="#36B982" if online else "#B8C4CF")

    def clear_messages(self):
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    def focus_input(self):
        if self._composer_enabled:
            self.message_entry.focus_set()

    def get_draft(self):
        if not self._composer_enabled:
            return ""
        text = self.message_entry.get()
        return "" if text == self.PLACEHOLDER else text

    def set_draft(self, text):
        if not self._composer_enabled:
            return
        self.message_entry.delete(0, tk.END)
        if text:
            self.message_entry.insert(0, text)
            self.message_entry.config(fg=self.TEXT)
        else:
            self.message_entry.insert(0, self.PLACEHOLDER)
            self.message_entry.config(fg="#9AA6B2")

    def set_composer_enabled(self, enabled, disabled_text="Unavailable"):
        """Disable typing when a private recipient has left the room."""
        if enabled == self._composer_enabled:
            if not enabled:
                self._show_disabled_text(disabled_text)
            return
        self._composer_enabled = enabled
        if enabled:
            self.message_entry.config(state="normal")
            self.message_entry.delete(0, tk.END)
            self.message_entry.insert(0, self.PLACEHOLDER)
            self.message_entry.config(fg="#9AA6B2")
            self.send_button.config(state="normal", bg=self.BLUE)
        else:
            self._show_disabled_text(disabled_text)
            self.send_button.config(state="disabled", bg="#B8C4CF")

    def _show_disabled_text(self, text):
        self.message_entry.config(state="normal")
        self.message_entry.delete(0, tk.END)
        self.message_entry.insert(0, text)
        self.message_entry.config(fg="#9AA6B2", state="disabled")

    def show_banner(self, text, callback=None, duration_ms=6000):
        """Briefly announce a new private message; clicking opens it."""
        self._banner_callback = callback
        self.banner.config(text=self._shorten(text, 44))
        if not self._banner_visible:
            self.banner.pack(fill="x", before=self.conversation_frame)
            self._banner_visible = True
        if self._banner_job is not None:
            try:
                self.after_cancel(self._banner_job)
            except tk.TclError:
                pass
        self._banner_job = self.after(duration_ms, self.hide_banner)

    def hide_banner(self):
        if self._banner_job is not None:
            try:
                self.after_cancel(self._banner_job)
            except tk.TclError:
                pass
            self._banner_job = None
        if self._banner_visible:
            self.banner.pack_forget()
            self._banner_visible = False

    def _banner_clicked(self, _event=None):
        callback = self._banner_callback
        self.hide_banner()
        if callback:
            callback()

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
