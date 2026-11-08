import queue
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from client import theme
from client.chat import ChatPanel
from client.conversations import ConversationStore, GROUP
from client.participants import ParticipantsPanel
from client.whiteboard import Whiteboard
from client.widgets import PillButton, draw_icon, round_rect
from common.user_colors import DEFAULT_USER_COLOR, build_viewer_color_map, normalize_color

MIN_WIDTH, MIN_HEIGHT = 760, 500
SIDEBAR_MIN, SIDEBAR_MAX = 270, 340
AUTO_HIDE_SIDEBAR_BELOW = 900  # narrower windows give the whole width to the whiteboard


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
        self.live_users = []            # participants currently in the room (from the server)
        self.store = ConversationStore()  # group + private conversation histories
        self.store.set_viewer(self.viewer_id)
        self.drafts = {}                # unsent text per conversation
        self.sidebar_visible = True
        self.sidebar_pref = None        # None = automatic, True/False = chosen by the user
        self._sidebar_applied = None
        self.root.title(f"CollabBoard - {room}")
        # The login window disables resizing; the workspace must be freely resizable.
        self.root.resizable(True, True)
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_w = min(1440, max(MIN_WIDTH, screen_w - 60))
        start_h = min(900, max(MIN_HEIGHT, screen_h - 90))
        pos_x = max(0, (screen_w - start_w) // 2)
        pos_y = max(0, (screen_h - start_h) // 2 - 20)
        self.root.geometry(f"{start_w}x{start_h}+{pos_x}+{pos_y}")
        self.root.minsize(min(MIN_WIDTH, screen_w), min(MIN_HEIGHT, screen_h))
        self.root.configure(bg=theme.BG_APP)
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(50, self.process_events)

    # ------------------------------------------------------------------ UI
    def _build(self):
        # Header stays fixed; the workspace below it expands to every available pixel.
        header = tk.Frame(self.root, bg=theme.BG_PANEL, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Right side first so these controls are the last to be clipped.
        self.sidebar_button = PillButton(header, "Hide chat", self.toggle_sidebar,
                                         bg="#374151", hover="#4B5563")
        self.sidebar_button.pack(side="right", padx=(6, 12), pady=10)
        if self.on_reconnect:
            PillButton(header, "Reconnect", self.reconnect, bg="#374151",
                       hover="#4B5563").pack(side="right", padx=4, pady=10)
        tk.Label(header, text=f"Signed in as {self.username}", fg=theme.SUCCESS,
                 bg=theme.BG_PANEL, font=(theme.FONT, 9)).pack(side="right", padx=10)

        logo = tk.Canvas(header, width=30, height=30, bg=theme.BG_PANEL,
                         highlightthickness=0, bd=0)
        round_rect(logo, 1, 1, 29, 29, 8, fill=theme.ACCENT, outline=theme.ACCENT)
        draw_icon(logo, "pen", 30, "#FFFFFF")
        logo.pack(side="left", padx=(14, 8), pady=12)
        tk.Label(header, text="CollabBoard", font=(theme.FONT, 15, "bold"),
                 fg="white", bg=theme.BG_PANEL).pack(side="left")
        tk.Label(header, text=f"Room: {self.room}", fg="#A5B4FC", bg=theme.BG_APP,
                 font=(theme.FONT, 9), padx=10, pady=4).pack(side="left", padx=14)

        # Grid layout: the whiteboard column takes all spare space, the sidebar has a
        # bounded width and can be hidden entirely on small windows.
        workspace = tk.Frame(self.root, bg=theme.BG_APP)
        workspace.pack(fill="both", expand=True, padx=7, pady=7)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, weight=0)
        self.workspace = workspace

        self.board_host = tk.Frame(workspace, bg=theme.BG_BOARD)
        self.board_host.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.sidebar = tk.Frame(workspace, bg=theme.BG_APP, width=300)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.pack_propagate(False)  # keep the width we set; children are packed

        self.participants = ParticipantsPanel(
            self.sidebar, self.username,
            on_open_private=self.open_private, on_open_group=self.open_group)
        self.participants.pack(fill="x", expand=False)
        self.chat = ChatPanel(self.sidebar, self.username,
                              send_callback=self.send_from_chat,
                              back_callback=self.open_group)
        self.chat.pack(fill="both", expand=True, pady=(7, 0))

        self.whiteboard = Whiteboard(
            self.board_host,
            on_operation=self.sync.send_drawing,
            on_clear=self.sync.clear_canvas,
            on_undo=self.sync.undo,
            on_redo=self.sync.redo,
            on_save=self.sync.save_board,
            on_load=self.sync.load_board
        )
        self.whiteboard.on_color_change = self.sync.set_user_color
        self.whiteboard.update_status("Connected to server")
        self._refresh_conversation_ui()
        self.root.bind("<Configure>", self._adapt_layout, add="+")
        self._adapt_layout()

    def _adapt_layout(self, event=None):
        # Ignore Configure events bubbling up from child widgets.
        if event is not None and event.widget is not self.root:
            return
        try:
            width = max(1, self.root.winfo_width())
            height = max(1, self.root.winfo_height())
            sidebar_width = max(SIDEBAR_MIN, min(SIDEBAR_MAX, int(width * 0.27)))
            self.sidebar.configure(width=sidebar_width)
            # The participant list is height-bounded and scrolls; chat keeps the rest.
            usable = max(1, height - 54 - 14)
            self.participants.set_max_list_height(
                max(self.participants.ROW_H * 2, min(190, int(usable * 0.24))))
            if self.sidebar_pref is None:
                self._set_sidebar_visible(width >= AUTO_HIDE_SIDEBAR_BELOW)
            else:
                self._set_sidebar_visible(self.sidebar_pref)
        except tk.TclError:
            pass

    def _set_sidebar_visible(self, visible):
        if visible == self._sidebar_applied:
            self.sidebar_visible = visible
            self._update_sidebar_button()
            return
        self._sidebar_applied = visible
        self.sidebar_visible = visible
        if visible:
            self.sidebar.grid()
            self.board_host.grid_configure(padx=(0, 7))
        else:
            self.sidebar.grid_remove()
            self.board_host.grid_configure(padx=0)
        self._update_sidebar_button()

    def toggle_sidebar(self):
        self.sidebar_pref = not self.sidebar_visible
        self._set_sidebar_visible(self.sidebar_pref)

    def _update_sidebar_button(self):
        unread = sum(self.store.unread.values())
        if self.sidebar_visible:
            self.sidebar_button.configure(text="Hide chat")
            self.sidebar_button.set_style("#374151", "#4B5563")
        elif unread:
            self.sidebar_button.configure(text=f"Show chat \u00b7 {unread} new")
            self.sidebar_button.set_style(theme.ACCENT, theme.ACCENT_HOVER)
        else:
            self.sidebar_button.configure(text="Show chat")
            self.sidebar_button.set_style("#374151", "#4B5563")

    def enqueue_event(self, event):
        self.events.put(event)

    # --------------------------------------------------------- color views
    def _rebuild_color_views(self, redraw_board=False):
        users = [dict(u) for u in self.live_users]
        # Include historical authors so saved drawings remain consistently
        # colored even if their author has left the room. They only take part in
        # the color mapping; the participant list shows people who are online.
        try:
            history = self.sync.state_manager.get_events()
        except Exception:
            history = []
        known = {u.get("client_id") for u in users if isinstance(u, dict)}
        color_users = list(users)
        for event in history:
            uid = event.get("user_id")
            if uid is not None and uid not in known:
                color_users.append({"client_id": uid,
                                    "username": event.get("username", "Former participant"),
                                    "preferred_color": event.get("preferred_color",
                                        event.get("data", {}).get("color", DEFAULT_USER_COLOR))})
                known.add(uid)
        self.color_map = build_viewer_color_map(
            self.viewer_id, self.viewer_preferred_color, color_users
        )

        def with_display_color(user):
            item = dict(user)
            item["display_color"] = self.color_map.get(
                item.get("client_id"),
                normalize_color(item.get("preferred_color", item.get("color", DEFAULT_USER_COLOR))))
            return item

        live_display = [with_display_color(u) for u in users]
        all_display = [with_display_color(u) for u in color_users]
        self.participants.update_participants(
            live_display, offline=self.store.offline_entries(), viewer_id=self.viewer_id,
            active=self.store.active, unread=self.store.unread)
        self.chat.set_user_colors([
            {"username": u.get("username"), "color": u.get("display_color", u.get("color", DEFAULT_USER_COLOR))}
            for u in all_display
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

    # -------------------------------------------------------- conversations
    def _entry_color(self, entry):
        uid = entry.get("uid")
        fallback = self.viewer_preferred_color if uid == self.viewer_id else entry.get("color")
        return self.color_map.get(uid, fallback)

    def _display_entry(self, entry):
        if entry["kind"] == "notice":
            self.chat.display_message("CollabBoard", entry["text"])
            return
        ts = entry.get("ts")
        stamp = datetime.fromtimestamp(ts).strftime("%H:%M") if isinstance(ts, (int, float)) else None
        self.chat.display_message(entry.get("username", "User"), entry["text"],
                                  timestamp=stamp, is_own=entry["own"],
                                  color=self._entry_color(entry))

    def _notice(self, key, text):
        """Record a system notice in a conversation and show it if it is open."""
        entry = self.store.add_notice(key, text)
        if key == self.store.active:
            self._display_entry(entry)

    def _refresh_conversation_ui(self):
        """Refresh everything that reflects unread counts and the active conversation."""
        self.participants.set_state(self.viewer_id, self.store.active, self.store.unread,
                                    self.store.offline_entries())
        self._update_sidebar_button()

    def _refresh_header_and_composer(self):
        key = self.store.active
        if key == GROUP:
            self.chat.set_conversation(private=False)
            self.chat.set_composer_enabled(True)
        else:
            name = self.store.peer_name(key)
            online = self.store.peer_online(key)
            self.chat.set_conversation(private=True, name=name, online=online)
            self.chat.set_composer_enabled(online, f"{name} has left the room")

    def open_group(self):
        self._open_conversation(GROUP)

    def open_private(self, client_id):
        if client_id is None or client_id == self.viewer_id:
            return
        if client_id not in self.store.peers:
            # Clicked before the server's participant list reached the store.
            match = next((u for u in self.live_users if u.get("client_id") == client_id), None)
            if match is None:
                return
            self.store.peers[client_id] = {"username": match.get("username", "User"), "online": True}
        self._open_conversation(client_id)

    def _open_conversation(self, key):
        if key == self.store.active:
            if not self.sidebar_visible:
                self.sidebar_pref = True
                self._set_sidebar_visible(True)
            self.chat.hide_banner()
            self.chat.focus_input()
            return
        self.drafts[self.store.active] = self.chat.get_draft()
        self.store.open(key)
        self.chat.hide_banner()
        self.chat.clear_messages()
        self._refresh_header_and_composer()
        self.chat.set_draft(self.drafts.get(key, ""))
        entries = self.store.messages(key)
        for entry in entries:
            self._display_entry(entry)
        if key != GROUP and not entries:
            self.chat.display_message(
                "CollabBoard", f"Private chat with {self.store.peer_name(key)}. "
                               "Only the two of you can see these messages.")
        self._refresh_conversation_ui()
        self.chat.focus_input()

    def send_from_chat(self, text):
        """Route the composer text to the group chat or the open private chat."""
        key = self.store.active
        if key == GROUP:
            sent = self.sync.send_chat(text)
        elif not self.store.peer_online(key):
            self._notice(key, f"{self.store.peer_name(key)} has left the room.")
            return
        else:
            sent = self.sync.send_private_message(key, text)
        if not sent:
            self._notice(key, "Not connected to the server. Message not sent.")

    def _peer_left(self, client_id, name=None):
        """A participant disconnected: update presence and the open conversation."""
        known_before = client_id in self.store.peers
        changed = self.store.mark_offline(client_id)
        if client_id == self.store.active and changed:
            self._notice(client_id, f"{name or self.store.peer_name(client_id)} left the room.")
            self._refresh_header_and_composer()
        elif known_before and changed and client_id in self.store.history:
            self.store.add_notice(client_id, f"{name or self.store.peer_name(client_id)} left the room.")

    def _handle_group_chat(self, event):
        entry = self.store.add_group_message(
            event.get("client_id"), event.get("username", "User"),
            event.get("message", ""), event.get("ts"))
        entry["color"] = event.get("preferred_color", event.get("color"))
        if self.store.active == GROUP:
            self._display_entry(entry)
        else:
            self._refresh_conversation_ui()

    def _handle_private_message(self, event):
        peer_id, entry = self.store.add_private_message(
            event.get("from_client_id"), event.get("from_username", "User"),
            event.get("to_client_id"), event.get("to_username", "User"),
            event.get("message", ""), event.get("ts"))
        entry["color"] = event.get("preferred_color", event.get("color"))
        if peer_id == self.store.active:
            self._display_entry(entry)
        elif not entry["own"]:
            name = self.store.peer_name(peer_id)
            self.chat.show_banner(f"New message from {name}: {entry['text']}",
                                  callback=lambda cid=peer_id: self.open_private(cid))
        self._refresh_conversation_ui()

    def _handle_private_failed(self, event):
        client_id = event.get("to_client_id")
        reason = event.get("reason", "Message not delivered")
        key = client_id if client_id in self.store.peers or client_id in self.store.history \
            else self.store.active
        if client_id in self.store.peers and ("left" in reason.lower() or "offline" in reason.lower()):
            self._peer_left(client_id)
        self._notice(key, f"Not delivered: {reason}.")
        if key != self.store.active:
            self.chat.show_banner(f"Message to {self.store.peer_name(key)} was not delivered",
                                  callback=lambda cid=key: self.open_private(cid))
        self._refresh_conversation_ui()

    # --------------------------------------------------------- event loop
    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event.get("type")
                if kind == "joined_room":
                    self.viewer_id = event.get("client_id", self.viewer_id)
                    self.store.set_viewer(self.viewer_id)
                    self.viewer_preferred_color = normalize_color(
                        event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR))
                    )
                    self.whiteboard.set_user_color(self.viewer_preferred_color)
                    self.whiteboard.set_preferred_color(self.viewer_preferred_color)
                    self._rebuild_color_views()
                    self._refresh_header_and_composer()
                elif kind == "snapshot_loaded":
                    self._rebuild_color_views()
                    board = [self._event_with_viewer_color(item) for item in event.get("board", [])]
                    self.whiteboard.load_board(board)
                    self.whiteboard.update_status("Canvas synchronized")
                elif kind == "remote_draw":
                    self._rebuild_color_views()
                    self.whiteboard.apply_operation(self._event_with_viewer_color(event["event"]))
                elif kind == "chat":
                    self._handle_group_chat(event)
                elif kind == "private_message":
                    self._handle_private_message(event)
                elif kind == "private_message_failed":
                    self._handle_private_failed(event)
                elif kind == "user_color_changed":
                    uid = event.get("client_id")
                    preferred = normalize_color(event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR)))
                    if uid == self.viewer_id or event.get("username") == self.username:
                        self.viewer_preferred_color = preferred
                        self.whiteboard.set_user_color(preferred)
                        self.whiteboard.set_preferred_color(preferred)
                    users = [dict(u) for u in self.live_users]
                    found = False
                    for user in users:
                        if user.get("client_id") == uid or user.get("username") == event.get("username"):
                            user["preferred_color"] = preferred
                            user["color"] = preferred
                            found = True
                    if not found:
                        users.append({"client_id": uid, "username": event.get("username", "User"),
                                      "preferred_color": preferred, "color": preferred})
                    self.live_users = users
                    self._rebuild_color_views(redraw_board=True)
                    self._notice(GROUP, f"{event.get('username', 'A participant')} changed their preferred color")
                elif kind == "participants":
                    self.live_users = [dict(u) for u in event.get("participants", [])]
                    for cid in self.store.update_participants(self.live_users):
                        if cid == self.store.active:
                            self._notice(cid, f"{self.store.peer_name(cid)} left the room.")
                    self._refresh_header_and_composer()
                    self._rebuild_color_views(redraw_board=True)
                elif kind == "participant_joined":
                    users = [dict(u) for u in self.live_users]
                    uid = event.get("client_id")
                    if not any(u.get("client_id") == uid for u in users):
                        users.append({"client_id": uid, "username": event.get("username", "User"),
                                      "preferred_color": event.get("preferred_color", event.get("color", DEFAULT_USER_COLOR))})
                    self.live_users = users
                    self.store.update_participants(self.live_users)
                    self._rebuild_color_views(redraw_board=True)
                    self._notice(GROUP, f'{event.get("username", "A user")} joined the room')
                elif kind == "participant_left":
                    uid = event.get("client_id")
                    name = event.get("username") or next(
                        (u.get("username") for u in self.live_users if u.get("client_id") == uid), None)
                    self.live_users = [u for u in self.live_users if u.get("client_id") != uid]
                    self._peer_left(uid, name)
                    self._notice(GROUP, f"{name} left the room" if name else "A participant left the room")
                    self._rebuild_color_views()
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
