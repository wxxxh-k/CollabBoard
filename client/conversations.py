"""Conversation state for the chat sidebar (no Tkinter, fully unit-testable).

A conversation is either the room's group chat (key ``GROUP``) or a private
chat with one participant (key = that participant's unique client id). Each
conversation keeps its own history and unread counter for the active session.
"""

GROUP = "group"


class ConversationStore:
    MAX_HISTORY = 1000

    def __init__(self):
        self.viewer_id = None
        self.active = GROUP
        self.history = {GROUP: []}
        self.unread = {}
        self.peers = {}  # client_id -> {"username": str, "online": bool}

    # ------------------------------------------------------------ identity
    def set_viewer(self, viewer_id):
        """Called on (re)join. The server issues a new client id per session,
        so every known peer is offline until the next participant list."""
        self.viewer_id = viewer_id
        for peer in self.peers.values():
            peer["online"] = False

    def update_participants(self, participants):
        """Refresh peer presence from the server's participant list.

        Returns the client ids of peers that just went offline."""
        live = {}
        for item in participants or []:
            if not isinstance(item, dict):
                continue
            cid = item.get("client_id")
            if cid is None or cid == self.viewer_id:
                continue
            live[cid] = item.get("username", "User")
        went_offline = []
        for cid, peer in self.peers.items():
            if cid not in live and peer["online"]:
                peer["online"] = False
                went_offline.append(cid)
        for cid, name in live.items():
            self.peers[cid] = {"username": name, "online": True}
        return went_offline

    def mark_offline(self, client_id):
        peer = self.peers.get(client_id)
        if peer and peer["online"]:
            peer["online"] = False
            return True
        return False

    def remember_peer(self, client_id, username):
        """Record a peer seen only through a message (keeps its name)."""
        if client_id is None or client_id == self.viewer_id:
            return
        peer = self.peers.setdefault(client_id, {"username": username, "online": False})
        if username:
            peer["username"] = username

    def peer_name(self, client_id):
        return self.peers.get(client_id, {}).get("username", "User")

    def peer_online(self, client_id):
        return bool(self.peers.get(client_id, {}).get("online"))

    # ------------------------------------------------------------ messages
    def _append(self, key, entry):
        entries = self.history.setdefault(key, [])
        entries.append(entry)
        if len(entries) > self.MAX_HISTORY:
            del entries[: len(entries) - self.MAX_HISTORY]
        if key != self.active and entry["kind"] == "msg" and not entry["own"]:
            self.unread[key] = self.unread.get(key, 0) + 1
        return entry

    def add_group_message(self, uid, username, text, ts=None):
        own = uid is not None and uid == self.viewer_id
        return self._append(GROUP, {"kind": "msg", "uid": uid, "username": username,
                                    "text": text, "ts": ts, "own": own})

    def add_private_message(self, from_id, from_name, to_id, to_name, text, ts=None):
        """Store a private message under the *other* participant's id."""
        own = from_id == self.viewer_id
        peer_id, peer_name = (to_id, to_name) if own else (from_id, from_name)
        self.remember_peer(peer_id, peer_name)
        entry = self._append(peer_id, {"kind": "msg", "uid": from_id,
                                       "username": from_name, "text": text,
                                       "ts": ts, "own": own})
        return peer_id, entry

    def add_notice(self, key, text):
        return self._append(key, {"kind": "notice", "text": text})

    def messages(self, key):
        return list(self.history.get(key, []))

    # ------------------------------------------------------------- state
    def open(self, key):
        self.active = key
        self.unread[key] = 0

    def unread_count(self, key):
        return self.unread.get(key, 0)

    def private_unread_total(self):
        return sum(n for key, n in self.unread.items() if key != GROUP)

    def is_private(self, key=None):
        return (self.active if key is None else key) != GROUP

    def offline_entries(self):
        """Offline peers worth keeping visible: unread messages or currently open."""
        return [(cid, peer["username"]) for cid, peer in self.peers.items()
                if not peer["online"] and (self.unread.get(cid, 0) > 0 or cid == self.active)]
