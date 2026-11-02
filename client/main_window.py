import queue
import tkinter as tk
from tkinter import messagebox
from client.whiteboard import Whiteboard
from client.chat import ChatPanel
from client.participants import ParticipantsPanel
from common.user_colors import DEFAULT_USER_COLOR, build_viewer_color_map, normalize_color

class MainWindow:
    def __init__(self, root, username, room, sync_manager, on_close=None, on_reconnect=None):
        self.root, self.username, self.room = root, username, room
        self.sync = sync_manager
        self.on_close = on_close
        self.on_reconnect = on_reconnect
        self.events = queue.Queue()
        self.viewer_id = getattr(sync_manager, "client_id", None)
        self.viewer_preferred_color = DEFAULT_USER_COLOR
        self.color_map = {}
        self.root.title(f"CollabBoard - {room}")
        # Start at a useful size without exceeding the available desktop area.
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_w = min(1440, max(900, screen_w - 60))
        start_h = min(900, max(560, screen_h - 90))
        self.root.geometry(f"{start_w}x{start_h}")
        self.root.minsize(900, 560)
        self.root.configure(bg="#111827")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(50, self.process_events)

    def _build(self):
        # Header stays fixed; the workspace below it expands to every available pixel.
        header = tk.Frame(self.root, bg="#1F2937", height=54)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🎨 CollabBoard", font=("Arial", 17, "bold"),
                 fg="white", bg="#1F2937").pack(side="left", padx=14)
        tk.Label(header, text=f"Room: {self.room}", fg="#A5B4FC",
                 bg="#1F2937").pack(side="left", padx=12)
        tk.Label(header, text=f"Signed in as {self.username}", fg="#34D399",
                 bg="#1F2937").pack(side="right", padx=10)
        if self.on_reconnect:
            tk.Button(header, text="Reconnect", command=self.reconnect,
                      bg="#374151", fg="white", relief="flat").pack(side="right", padx=7)

        # Use grid instead of nested PanedWindows. The previous sash positioning
        # could leave the sidebar outside the visible workspace on Windows DPI setups.
        workspace = tk.Frame(self.root, bg="#111827")
        workspace.pack(fill="both", expand=True, padx=7, pady=7)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, weight=0)

        board_host = tk.Frame(workspace, bg="#17243B")
        board_host.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.sidebar = tk.Frame(workspace, bg="#111827", width=310)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.participants = ParticipantsPanel(self.sidebar, self.username)
        self.participants.pack(fill="x", expand=False)
        self.chat = ChatPanel(self.sidebar, self.username, send_callback=self.sync.send_chat)
        self.chat.pack(fill="both", expand=True, pady=(7, 0))

        self.whiteboard = Whiteboard(
            board_host,
            on_operation=self.sync.send_drawing,
            on_clear=self.sync.clear_canvas,
            on_undo=self.sync.undo,
            on_redo=self.sync.redo,
            on_save=self.sync.save_board,
            on_load=self.sync.load_board
        )
        self.whiteboard.on_color_change = self.sync.set_user_color
        self.whiteboard.update_status("Connected to server")
        self.root.bind("<Configure>", self._adapt_layout, add="+")
        self._adapt_layout()

    def _adapt_layout(self, event=None):
        # Ignore Configure events bubbling up from child widgets.
        if event is not None and event.widget is not self.root:
            return
        try:
            width = max(1, self.root.winfo_width())
            height = max(1, self.root.winfo_height())
            # Sidebar remains wide enough for chat, but yields space to the board
            # on compact displays. The participants list itself is scrollable.
            sidebar_width = 285 if width < 1100 else 310
            self.sidebar.configure(width=sidebar_width)
            participant_height = min(205, max(125, int(height * 0.22)))
            self.participants.configure(height=participant_height)
            self.participants.pack_propagate(False)
        except tk.TclError:
            pass

    def enqueue_event(self, event):
        self.events.put(event)

    def _rebuild_color_views(self, redraw_board=False):
        users = list(self.participants.users)
        # Include historical authors so saved drawings remain consistently
        # colored even if their author has left the room.
        try:
            history = self.sync.state_manager.get_events()
        except Exception:
            history = []
        known = {u.get("client_id") for u in users if isinstance(u, dict)}
        for event in history:
            uid = event.get("user_id")
            if uid is not None and uid not in known:
                users.append({"client_id": uid,
                              "username": event.get("username", "Former participant"),
                              "preferred_color": event.get("preferred_color",
                                  event.get("data", {}).get("color", DEFAULT_USER_COLOR))})
                known.add(uid)
        self.color_map = build_viewer_color_map(
            self.viewer_id, self.viewer_preferred_color, users
        )
        display_users = []
        for user in users:
            item = dict(user)
            uid = item.get("client_id")
            item["display_color"] = self.color_map.get(
                uid, normalize_color(item.get("preferred_color", item.get("color", DEFAULT_USER_COLOR)))
            )
            display_users.append(item)
        # Keep the canonical participant list (with preferences) separate from
        # the per-viewer display colors.
        self.participants.users = [dict(u) for u in users]
        self.participants.update_participants(display_users)
        self.chat.set_user_colors([
            {"username": u.get("username"), "color": u.get("display_color", u.get("color", DEFAULT_USER_COLOR))}
            for u in display_users
        ])
        if redraw_board and history:
            self.whiteboard.load_board([
                self._event_with_viewer_color(event) for event in history
            ])

    def _event_with_viewer_color(self, event):
        rendered = dict(event)
        data = dict(event.get("data", {}))
        uid = event.get("user_id")
        if data.get("tool") != "eraser":
            preferred = event.get("preferred_color", data.get("color", DEFAULT_USER_COLOR))
            data["color"] = self.color_map.get(uid, normalize_color(preferred))
        rendered["data"] = data
        return rendered

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event.get("type")
                if kind == "joined_room":
                    self.viewer_id = event.get("client_id", self.viewer_id)
                    self.viewer_preferred_color = normalize_color(
                        event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR))
                    )
                    self.whiteboard.set_user_color(self.viewer_preferred_color)
                    self.whiteboard.set_preferred_color(self.viewer_preferred_color)
                    self._rebuild_color_views()
                elif kind == "snapshot_loaded":
                    self._rebuild_color_views()
                    board = [self._event_with_viewer_color(item) for item in event.get("board", [])]
                    self.whiteboard.load_board(board)
                    self.whiteboard.update_status("Canvas synchronized")
                elif kind == "remote_draw":
                    self._rebuild_color_views()
                    self.whiteboard.apply_operation(self._event_with_viewer_color(event["event"]))
                elif kind == "chat":
                    uid = event.get("client_id")
                    color = self.color_map.get(uid, self.viewer_preferred_color if uid == self.viewer_id else event.get("preferred_color", event.get("color")))
                    self.chat.display_message(event.get("username", "User"),
                                               event.get("message", ""), color=color)
                elif kind == "user_color_changed":
                    uid = event.get("client_id")
                    preferred = normalize_color(event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR)))
                    if uid == self.viewer_id or event.get("username") == self.username:
                        self.viewer_preferred_color = preferred
                        self.whiteboard.set_user_color(preferred)
                        self.whiteboard.set_preferred_color(preferred)
                    users = [dict(u) for u in self.participants.users]
                    found = False
                    for user in users:
                        if user.get("client_id") == uid or user.get("username") == event.get("username"):
                            user["preferred_color"] = preferred
                            user["color"] = preferred
                            found = True
                    if not found:
                        users.append({"client_id": uid, "username": event.get("username", "User"),
                                      "preferred_color": preferred, "color": preferred})
                    self.participants.users = users
                    self._rebuild_color_views(redraw_board=True)
                    self.chat.display_message("CollabBoard",
                                               f"{event.get('username', 'A participant')} changed their preferred color")
                elif kind == "participants":
                    self.participants.users = [dict(u) for u in event.get("participants", [])]
                    self._rebuild_color_views(redraw_board=True)
                elif kind == "participant_joined":
                    users = [dict(u) for u in self.participants.users]
                    uid = event.get("client_id")
                    if not any(u.get("client_id") == uid for u in users):
                        users.append({"client_id": uid, "username": event.get("username", "User"),
                                      "preferred_color": event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR))})
                    self.participants.users = users
                    self._rebuild_color_views(redraw_board=True)
                    self.chat.display_message("CollabBoard", f'{event.get("username", "A user")} joined the room')
                elif kind == "participant_left":
                    self.chat.display_message("CollabBoard", "A participant left the room")
                elif kind == "save_result":
                    messagebox.showinfo("Save board", "Board saved on the server." if event.get("success")
                                        else "Could not save the board.")
                elif kind == "error":
                    messagebox.showerror("CollabBoard", event.get("message", "Server error"))
                elif kind == "sync_gap":
                    self.whiteboard.update_status("Resynchronizing canvas...")
                elif kind == "sync_error":
                    self.whiteboard.update_status("Synchronization error")
                    messagebox.showerror("Synchronization", event.get("message", "Unknown error"))
                elif kind == "disconnected":
                    self.whiteboard.update_status("Disconnected from server")
                    messagebox.showwarning("Connection lost", "The connection to the server was lost. Close and reconnect.")
                elif kind == "left_room":
                    self.whiteboard.update_status("Left room")
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(50, self.process_events)

    def reconnect(self):
        if self.on_reconnect:
            self.on_reconnect()

    def close(self):
        if self.on_close:
            self.on_close()
        else:
            self.sync.disconnect()
            self.root.destroy()
