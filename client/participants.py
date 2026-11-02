import tkinter as tk

class ParticipantsPanel(tk.Frame):
    def __init__(self, parent, username):
        super().__init__(parent, bg="#111827")
        self.username = username
        self.users = []
        tk.Label(self, text="👥  Participants", font=("Arial", 12, "bold"),
                 fg="white", bg="#1F2937", padx=12, pady=12).pack(fill="x")
        self.count_label = tk.Label(self, text="0 members online", fg="#34D399",
                                    bg="#111827", anchor="w", padx=12)
        self.count_label.pack(fill="x", pady=6)
        self.users_frame = tk.Frame(self, bg="#111827")
        self.users_frame.pack(fill="both", expand=True, padx=8, pady=5)

    def update_participants(self, users):
        self.users = list(users or [])
        for widget in self.users_frame.winfo_children():
            widget.destroy()
        self.count_label.config(text=f"{len(self.users)} members online")
        for user in self.users:
            name = user if isinstance(user, str) else user.get("username", "Unknown")
            row = tk.Frame(self.users_frame, bg="#1F2937", padx=8, pady=8)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=name, fg="white", bg="#1F2937",
                     anchor="w").pack(fill="x")
