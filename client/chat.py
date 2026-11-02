import tkinter as tk
from datetime import datetime

class ChatPanel(tk.Frame):
    def __init__(self, parent, username, send_callback=None):
        super().__init__(parent, bg="#111827")
        self.username = username
        self.send_callback = send_callback
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#1F2937", height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="💬  Group Chat", font=("Arial", 13, "bold"),
                 fg="white", bg="#1F2937").pack(anchor="w", padx=14, pady=15)

        self.messages = tk.Text(self, bg="#111827", fg="white", wrap="word",
                                state="disabled", font=("Arial", 10),
                                relief="flat", padx=10, pady=8)
        self.messages.pack(fill="both", expand=True)
        input_row = tk.Frame(self, bg="#1F2937", padx=8, pady=8)
        input_row.pack(fill="x")
        self.message_entry = tk.Entry(input_row, font=("Arial", 10))
        self.message_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.message_entry.bind("<Return>", lambda event: self.send_message())
        tk.Button(input_row, text="Send", command=self.send_message,
                  bg="#4F46E5", fg="white", relief="flat").pack(side="right", padx=(6, 0), ipady=5)

    def send_message(self):
        message = self.message_entry.get().strip()
        if not message:
            return
        if self.send_callback:
            self.send_callback(message)
            self.message_entry.delete(0, tk.END)

    def display_message(self, username, message, timestamp=None, is_own=None):
        timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.messages.config(state="normal")
        self.messages.insert(tk.END, f"[{timestamp}] {username}: {message}\n")
        self.messages.config(state="disabled")
        self.messages.see(tk.END)
