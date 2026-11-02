
import tkinter as tk
from tkinter import messagebox
from common.user_colors import DEFAULT_USER_COLOR


class LoginWindow:

    def __init__(self, root, on_join):
        self.root = root
        self.on_join = on_join

        self.root.title("CollabBoard - Login")
        self.root.geometry("450x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#171923")

        self.selected_color = DEFAULT_USER_COLOR
        self.create_widgets()

    def create_widgets(self):

        title = tk.Label(
            self.root,
            text="CollabBoard",
            font=("Arial", 28, "bold"),
            fg="white",
            bg="#171923"
        )
        title.pack(pady=(35, 5))

        subtitle = tk.Label(
            self.root,
            text="Collaborate. Draw. Create together.",
            font=("Arial", 11),
            fg="#A0AEC0",
            bg="#171923"
        )
        subtitle.pack(pady=(0, 30))

        self.username = self.create_field("Username")
        self.server_ip = self.create_field(
            "Server IP Address", "127.0.0.1"
        )
        self.port = self.create_field("Port Number", "5000")
        self.room = self.create_field("Room Code", "default")
        self.password = self.create_field(
            "Room Password", show="*"
        )

        join_button = tk.Button(
            self.root,
            text="JOIN WHITEBOARD",
            font=("Arial", 12, "bold"),
            bg="#4F46E5",
            fg="white",
            activebackground="#4338CA",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.join_room
        )
        join_button.pack(fill="x", padx=55, pady=30, ipady=10)

        self.status = tk.Label(
            self.root,
            text="Enter your details to continue",
            font=("Arial", 9),
            fg="#A0AEC0",
            bg="#171923"
        )
        self.status.pack()

    def create_field(self, label, default="", show=None):

        tk.Label(
            self.root,
            text=label,
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#171923",
            anchor="w"
        ).pack(fill="x", padx=55, pady=(8, 3))

        entry = tk.Entry(
            self.root,
            font=("Arial", 11),
            bg="#2D3748",
            fg="white",
            insertbackground="white",
            relief="flat",
            show=show
        )
        entry.pack(fill="x", padx=55, ipady=9)
        entry.insert(0, default)

        return entry

    def join_room(self):

        username = self.username.get().strip()
        server_ip = self.server_ip.get().strip()
        port = self.port.get().strip()
        room = self.room.get().strip()
        password = self.password.get()

        if not username or not server_ip or not port or not room:
            messagebox.showerror(
                "Missing details",
                "Please fill in username, server IP, port and room code."
            )
            return

        try:
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid port",
                "Enter a valid port between 1 and 65535."
            )
            return

        self.on_join(username, server_ip, port, room, password, self.selected_color)
