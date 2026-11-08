import tkinter as tk

from client import theme
from client.conversations import GROUP
from client.widgets import IconButton
from common.user_colors import DEFAULT_USER_COLOR

BADGE_BG = "#2798D5"  # same blue as the chat's send button
ROW_BG = "#1F2937"
ROW_HOVER = "#2A3A52"
ROW_ACTIVE = "#2D3F5F"


class ParticipantsPanel(tk.Frame):
    """Compact conversation + participant list.

    The first row is the room's Group Chat; below it every participant is
    listed with their color swatch. Clicking a participant opens a private chat
    with them. Unread counters and the active conversation are highlighted. The
    list is height-bounded, scrolls when needed and can be collapsed.
    """
    ROW_H = 36

    def __init__(self, parent, username, on_open_private=None, on_open_group=None, on_manage_role=None):
        super().__init__(parent, bg=theme.BG_APP)
        self.username = username
        self.on_open_private = on_open_private
        self.on_open_group = on_open_group
        self.on_manage_role = on_manage_role
        self.users = []            # live participants (as sent by the server)
        self.offline = []          # [(client_id, username)] kept visible while unread/open
        self.viewer_id = None
        self.unread = {}
        self.active = GROUP
        self.collapsed = False
        self.max_list_height = 170
        self._display_users = []
        self._scroll_visible = False

        header = tk.Frame(self, bg=ROW_BG, height=38)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Participants", font=(theme.FONT, 11, "bold"),
                 fg="white", bg=ROW_BG, padx=12).pack(side="left")
        self.toggle_button = IconButton(header, "chevron_up", self.toggle_collapsed,
                                        "Collapse / expand the list", size=28, bg=ROW_BG)
        self.toggle_button.pack(side="right", padx=(0, 6), pady=5)
        self.count_label = tk.Label(header, text="0 online", fg=theme.SUCCESS, bg=ROW_BG,
                                    font=(theme.FONT, 9))
        self.count_label.pack(side="right", padx=(0, 4))

        self.group_host = tk.Frame(self, bg=theme.BG_APP)
        self.group_host.pack(fill="x", padx=6, pady=(5, 0))

        self.list_host = tk.Frame(self, bg=theme.BG_APP)
        self.list_host.pack(fill="x", padx=6, pady=(2, 5))
        self.canvas = tk.Canvas(self.list_host, bg=theme.BG_APP, highlightthickness=0, bd=0,
                                height=self.ROW_H)
        self.scrollbar = tk.Scrollbar(self.list_host, orient="vertical",
                                      command=self.canvas.yview, width=7)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="x", expand=True)
        self.users_frame = tk.Frame(self.canvas, bg=theme.BG_APP)
        self.window_id = self.canvas.create_window((0, 0), window=self.users_frame, anchor="nw")
        self.users_frame.bind("<Configure>", self._update_scroll)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")
        self.refresh()

    # ------------------------------------------------------------------ API
    def update_participants(self, users, offline=None, viewer_id=None, active=None, unread=None):
        self.users = list(users or [])
        self._display_users = list(self.users)
        if offline is not None:
            self.offline = list(offline)
        if viewer_id is not None:
            self.viewer_id = viewer_id
        if active is not None:
            self.active = active
        if unread is not None:
            self.unread = dict(unread)
        self.refresh()

    def set_state(self, viewer_id, active, unread, offline):
        """Update identity, active conversation, unread counters and offline rows at once."""
        self.viewer_id = viewer_id
        self.active = active
        self.unread = dict(unread or {})
        self.offline = list(offline or [])
        self.refresh()

    def set_offline(self, offline):
        self.offline = list(offline or [])
        self.refresh()

    def set_viewer_id(self, viewer_id):
        self.viewer_id = viewer_id
        self.refresh()

    def set_active(self, key):
        self.active = key
        self.refresh()

    def set_unread(self, unread):
        self.unread = dict(unread or {})
        self.refresh()

    def set_max_list_height(self, pixels):
        pixels = max(self.ROW_H, int(pixels))
        if pixels != self.max_list_height:
            self.max_list_height = pixels
            self._apply_list_height()

    def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.toggle_button.icon = "chevron_down" if self.collapsed else "chevron_up"
        self.toggle_button._render()
        if self.collapsed:
            self.list_host.pack_forget()
        else:
            self.list_host.pack(fill="x", padx=6, pady=(2, 5))

    # ------------------------------------------------------------ rendering
    def _signature(self):
        people = tuple((u.get("client_id"), u.get("username"),
                        u.get("display_color", u.get("color")), u.get("role")) if isinstance(u, dict) else (None, u, None)
                       for u in self._display_users)
        return (people, tuple(self.offline), self.viewer_id, self.active,
                tuple(sorted((str(k), v) for k, v in self.unread.items() if v)))

    def refresh(self):
        # Remote strokes trigger frequent color-map rebuilds; only touch the
        # widgets when something visible actually changed.
        signature = self._signature()
        if signature == getattr(self, "_last_signature", None):
            return
        self._last_signature = signature
        previous = self.canvas.yview()[0]
        for widget in self.group_host.winfo_children():
            widget.destroy()
        for widget in self.users_frame.winfo_children():
            widget.destroy()

        self._build_group_row()

        entries = []
        for user in self._display_users:
            if isinstance(user, str):
                entries.append((None, user, DEFAULT_USER_COLOR, True))
                continue
            entries.append((user.get("client_id"), user.get("username", "Unknown"),
                            user.get("display_color", user.get("color", DEFAULT_USER_COLOR)), True))
        for client_id, name in self.offline:
            entries.append((client_id, name, "#64748B", False))
        self._entry_count = len(entries)
        self.count_label.config(text=f"{len(self._display_users)} online")
        for client_id, name, color, online in entries:
            self._build_participant_row(client_id, name, color, online)
        self._apply_list_height()
        self.canvas.yview_moveto(previous)

    def _apply_list_height(self):
        content = max(1, getattr(self, "_entry_count", 0)) * self.ROW_H + 2
        self.canvas.configure(height=min(content, self.max_list_height))
        needs_scroll = content > self.max_list_height
        if needs_scroll and not self._scroll_visible:
            self.scrollbar.pack(side="right", fill="y")
            self._scroll_visible = True
        elif not needs_scroll and self._scroll_visible:
            self.scrollbar.pack_forget()
            self._scroll_visible = False
            self.canvas.yview_moveto(0)

    def _update_scroll(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if not self._scroll_visible or not self.winfo_exists():
            return
        try:
            x, y = self.canvas.winfo_pointerx(), self.canvas.winfo_pointery()
            inside = (self.canvas.winfo_rootx() <= x <= self.canvas.winfo_rootx() + self.canvas.winfo_width()
                      and self.canvas.winfo_rooty() <= y <= self.canvas.winfo_rooty() + self.canvas.winfo_height())
            if inside:
                num = getattr(event, "num", None)
                up = (num == 4) or (num is None and event.delta > 0)
                self.canvas.yview_scroll(-1 if up else 1, "units")
        except tk.TclError:
            pass

    # ----------------------------------------------------------------- rows
    def _manage_context(self, event, row):
        if not self.on_manage_role:
            return
        try:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Make Assistant",
                             command=lambda: self.on_manage_role(row._client_id, "assistant"))
            menu.add_command(label="Make Student",
                             command=lambda: self.on_manage_role(row._client_id, "student"))
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _new_row(self, parent, key, clickable, on_click):
        active = key == self.active
        bg = ROW_ACTIVE if active else ROW_BG
        row = tk.Frame(parent, bg=bg, height=self.ROW_H)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)
        bar = tk.Frame(row, width=3, bg=theme.ACCENT if active else bg)
        bar._keep_bg = True
        bar.pack(side="left", fill="y")
        row._active = active
        row._client_id = key
        row._clickable = clickable
        row._on_click = on_click
        return row

    def _finish_row(self, row):
        """Bind hover + click feedback on the row and all of its children."""
        def bind_all(widget):
            if row._clickable:
                widget.bind("<Enter>", lambda _e: self._paint(row, ROW_HOVER), add="+")
                widget.bind("<Leave>", lambda _e: self._on_row_leave(row), add="+")
                widget.bind("<Button-1>", lambda _e: row._on_click(), add="+")
                try:
                    widget.bind("<Button-3>", lambda e, r=row: self._manage_context(e, r), add="+")
                except tk.TclError:
                    pass
                try:
                    widget.configure(cursor="hand2")
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                bind_all(child)
        bind_all(row)

    def _on_row_leave(self, row):
        try:
            x, y = row.winfo_pointerxy()
            inside = (row.winfo_rootx() <= x < row.winfo_rootx() + row.winfo_width()
                      and row.winfo_rooty() <= y < row.winfo_rooty() + row.winfo_height())
            if not inside:
                self._paint(row, ROW_ACTIVE if row._active else ROW_BG)
        except tk.TclError:
            pass

    def _paint(self, widget, bg):
        try:
            if not getattr(widget, "_keep_bg", False):
                widget.configure(bg=bg)
        except tk.TclError:
            return
        for child in widget.winfo_children():
            self._paint(child, bg)

    def _badge(self, row, key):
        count = self.unread.get(key, 0)
        if count > 0:
            badge = tk.Label(row, text="9+" if count > 9 else str(count), bg=BADGE_BG,
                             fg="white", font=(theme.FONT, 8, "bold"), padx=6)
            badge._keep_bg = True
            badge.pack(side="right", padx=(4, 8))

    def _build_group_row(self):
        row = self._new_row(self.group_host, GROUP, True,
                            lambda: self.on_open_group and self.on_open_group())
        bg = ROW_ACTIVE if row._active else ROW_BG
        icon = tk.Canvas(row, width=26, height=26, bg=bg, highlightthickness=0, bd=0)
        icon.create_oval(1, 1, 25, 25, fill=theme.ACCENT, outline=theme.ACCENT)
        icon.create_oval(7, 7, 12, 12, fill="white", outline="white")
        icon.create_oval(14, 7, 19, 12, fill="white", outline="white")
        icon.create_arc(5, 13, 14, 23, start=0, extent=180, fill="white", outline="white")
        icon.create_arc(12, 13, 21, 23, start=0, extent=180, fill="white", outline="white")
        icon.pack(side="left", padx=(8, 8))
        text = tk.Frame(row, bg=bg)
        text.pack(side="left", fill="y")
        tk.Label(text, text="Group Chat", fg="white", bg=bg, anchor="w",
                 font=(theme.FONT, 9, "bold")).pack(anchor="w", pady=(3, 0))
        tk.Label(text, text="Everyone in this room", fg=theme.TEXT_MUTED, bg=bg, anchor="w",
                 font=(theme.FONT, 7)).pack(anchor="w")
        self._badge(row, GROUP)
        self._finish_row(row)

    def _build_participant_row(self, client_id, name, color, online):
        is_self = client_id is not None and client_id == self.viewer_id
        clickable = client_id is not None and not is_self
        row = self._new_row(
            self.users_frame, client_id, clickable,
            lambda cid=client_id: self.on_open_private and self.on_open_private(cid))
        bg = ROW_ACTIVE if row._active else ROW_BG
        swatch = tk.Canvas(row, width=14, height=14, bg=bg, highlightthickness=0, bd=0)
        swatch.create_oval(2, 2, 12, 12, fill=color, outline=color)
        swatch.pack(side="left", padx=(8, 7))
        tk.Label(row, text=name, fg="white" if online else theme.TEXT_DIM, bg=bg, anchor="w",
                 font=(theme.FONT, 9, "bold")).pack(side="left")
        user_data = next((u for u in self._display_users if isinstance(u, dict) and u.get("client_id") == client_id), {})
        role = user_data.get("role")
        if role:
            tk.Label(row, text=role.upper(), fg="#A5B4FC", bg=bg,
                     font=(theme.FONT, 7, "bold")).pack(side="left", padx=(5, 0))
        if is_self:
            tk.Label(row, text="you", fg=theme.TEXT_MUTED, bg=bg,
                     font=(theme.FONT, 8)).pack(side="left", padx=(5, 0))
        elif not online:
            tk.Label(row, text="left", fg=theme.TEXT_DIM, bg=bg,
                     font=(theme.FONT, 8)).pack(side="left", padx=(5, 0))
        self._badge(row, client_id)
        tk.Label(row, text=color.upper(), fg=color, bg=bg,
                 font=(theme.FONT, 8, "bold")).pack(side="right", padx=(0, 8))
        self._finish_row(row)
