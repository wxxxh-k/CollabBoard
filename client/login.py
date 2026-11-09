
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from common.user_colors import DEFAULT_USER_COLOR

# The three roles offered on the login screen (display label -> server role).
ROLE_CHOICES = ("Host", "Assistant", "Student")


class LoginWindow:

    def __init__(self, root, on_join):
        self.root = root
        self.on_join = on_join

        self.root.title("CollabBoard - Login")
        self.root.geometry("450x690")
        self.root.resizable(True, True)
        self.root.minsize(400, 500)
        self.root.configure(bg="#171923")

        self.selected_color = DEFAULT_USER_COLOR
        base_dir = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                    else Path(__file__).resolve().parents[1])
        self.user_history_path = base_dir / "data" / "users.json"
        self.user_history = self._load_user_history()
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

        self.username = self.create_user_selector()
        self.role = self.create_role_selector()
        self.server_ip = self.create_field(
            "Server IP Address", "127.0.0.1"
        )
        self.port = self.create_field("Port Number", "5000")
        self.room = self.create_field("Room ID (for joining)", "")
        self.password = self.create_field(
            "Room Password", show="*"
        )

        actions = tk.Frame(self.root, bg="#171923")
        actions.pack(fill="x", padx=55, pady=24)
        actions.columnconfigure(0, weight=1, uniform="actions")
        actions.columnconfigure(1, weight=1, uniform="actions")
        self.create_button = tk.Button(actions, text="CREATE A ROOM", font=("Arial", 11, "bold"),
            bg="#059669", fg="white", activebackground="#047857", relief="flat",
            cursor="hand2", command=self.create_room)
        self.create_button.grid(row=0, column=0, sticky="ew", ipady=10, padx=(0, 6))
        self.join_button = tk.Button(actions, text="JOIN ROOM", font=("Arial", 11, "bold"),
            bg="#4F46E5", fg="white", activebackground="#4338CA", relief="flat",
            cursor="hand2", command=self.join_room)
        self.join_button.grid(row=0, column=1, sticky="ew", ipady=10, padx=(6, 0))

        self.status = tk.Label(
            self.root,
            text="Enter your details to continue",
            font=("Arial", 9),
            fg="#A0AEC0",
            bg="#171923"
        )
        self.status.pack()

    def _load_user_history(self):
        try:
            with self.user_history_path.open("r", encoding="utf-8") as file:
                users = json.load(file)
            if isinstance(users, list):
                return [name for name in users if isinstance(name, str) and name.strip()][:30]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _save_user_history(self, username):
        self.user_history = [name for name in self.user_history
                             if name.casefold() != username.casefold()]
        self.user_history.insert(0, username)
        self.user_history = self.user_history[:30]
        try:
            self.user_history_path.parent.mkdir(parents=True, exist_ok=True)
            with self.user_history_path.open("w", encoding="utf-8") as file:
                json.dump(self.user_history, file, indent=2)
        except OSError:
            # Login should still work if the local history cannot be written.
            pass
        if hasattr(self, "username"):
            self.username.configure(values=self.user_history)

    def create_user_selector(self):
        tk.Label(
            self.root,
            text="Select User / Username",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#171923",
            anchor="w"
        ).pack(fill="x", padx=55, pady=(8, 3))

        style = ttk.Style(self.root)
        try:
            # The default Windows/macOS ttk themes ignore the field color, which
            # left white text on a white box. "clam" honors it everywhere.
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Collab.TCombobox",
            fieldbackground="#2D3748",
            background="#2D3748",
            foreground="white",
            arrowcolor="white",
            insertcolor="white",
            bordercolor="#2D3748",
            lightcolor="#2D3748",
            darkcolor="#2D3748",
            selectbackground="#4F46E5",
            selectforeground="white"
        )
        style.map(
            "Collab.TCombobox",
            fieldbackground=[("readonly", "#2D3748"), ("!disabled", "#2D3748")],
            foreground=[("readonly", "white"), ("!disabled", "white")],
            selectbackground=[("!disabled", "#4F46E5")],
            selectforeground=[("!disabled", "white")]
        )
        # Dropdown list of the combobox (a plain Tk listbox).
        self.root.option_add("*TCombobox*Listbox.background", "#2D3748")
        self.root.option_add("*TCombobox*Listbox.foreground", "white")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#4F46E5")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        selector = ttk.Combobox(
            self.root,
            values=self.user_history,
            font=("Arial", 11),
            state="normal",
            style="Collab.TCombobox"
        )
        selector.pack(fill="x", padx=55, ipady=5)
        if self.user_history:
            selector.set(self.user_history[0])
        return selector

    def create_role_selector(self):
        tk.Label(
            self.root,
            text="Select Role",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#171923",
            anchor="w"
        ).pack(fill="x", padx=55, pady=(8, 3))
        selector = ttk.Combobox(
            self.root,
            values=ROLE_CHOICES,
            font=("Arial", 11),
            state="readonly",
            style="Collab.TCombobox"
        )
        selector.pack(fill="x", padx=55, ipady=5)
        return selector

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

    def create_room(self):
        self._submit(create=True)

    def join_room(self):
        self._submit(create=False)

    def _submit(self, create=False):
        username = self.username.get().strip()
        server_ip = self.server_ip.get().strip()
        port = self.port.get().strip()
        room = self.room.get().strip()
        password = self.password.get()
        role = self.role.get().strip().lower()

        if not username or not server_ip or not port or (not create and not room):
            messagebox.showerror(
                "Missing details",
                "Please fill in username, server IP, port and room code."
            )
            return

        if role not in [choice.lower() for choice in ROLE_CHOICES]:
            messagebox.showerror("Select a role", "Please select a role before continuing.")
            return

        if create and role != "host":
            messagebox.showerror(
                "Host role required",
                "Only the Host role can create a room. Select Host to create a room, "
                "or use JOIN ROOM to join an existing room as Assistant or Student."
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

        self._save_user_history(username)
        self.on_join(username, server_ip, port, room, password, self.selected_color, create, role=role)
