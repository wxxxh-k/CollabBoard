import threading
import time
from common.protocol import DISCONNECTED

class SyncManager:
    """Connects the TCP message queue to local state and GUI events."""
    def __init__(self, network, state_manager, on_event=None):
        self.network = network
        self.state_manager = state_manager
        self.on_event = on_event
        self.running = False
        self.receiver_thread = None
        self.room_id = None
        self.username = None
        self.client_id = None
        self.last_sequence = 0
        self.role = "student"
        self.last_error = None
        self.host_token = None
        self.host_room_id = None
        self.event_lock = threading.RLock()

    def join_room(self, host, port, room_id, username, password=None, color="#2563EB", create_room=False,
                  role=None):
        # Drop stale disconnect or event notifications from a previous connection.
        while self.network.get_message() is not None:
            pass
        self.client_id = None
        self.last_sequence = 0
        self.last_error = None
        if not self.network.connect(host, port):
            return False
        self.username = username
        if create_room:
            self.host_token = None
            self.host_room_id = None
            create_message = {"type": "create_room", "room_name": f"{username}'s Room",
                              "password": password or None}
            if role:
                create_message["role"] = role
            if not self.network.send_message(create_message):
                return False
            deadline = time.time() + 8
            created = None
            while time.time() < deadline:
                response = self.network.get_message()
                if response and response.get("type") == "room_created":
                    created = response.get("room_id")
                    self.host_token = response.get("host_token")
                    self.host_room_id = created
                    break
                if response and response.get("type") == "error":
                    self.last_error = response.get("message", "Could not create room")
                    self.notify_gui(response)
                    self.network.disconnect()
                    return False
                time.sleep(0.02)
            if not created:
                return False
            room_id = created
        self.room_id = room_id
        message = {"type": "join_room", "room_id": room_id, "username": username,
                   "color": color}
        if role:
            message["role"] = role
        if self.host_token and self.host_room_id == room_id:
            message["host_token"] = self.host_token
        if password:
            message["password"] = password
        if not self.network.send_message(message):
            return False
        # Do not open the workspace until the server has atomically accepted
        # the username and room membership.
        deadline = time.time() + 8
        accepted = None
        while time.time() < deadline:
            response = self.network.get_message()
            if response and response.get("type") in ("joined_room", "error"):
                accepted = response
                break
            time.sleep(0.02)
        if not accepted or accepted.get("type") != "joined_room":
            if accepted:
                self.last_error = accepted.get("message", "Could not join room")
                self.notify_gui(accepted)
            else:
                self.last_error = "The server did not respond in time."
            self.network.disconnect()
            return False
        # Use the server's canonical Room ID (it matches IDs ignoring case).
        self.room_id = accepted.get("room_id") or self.room_id
        # Deliver joined_room right now, before anything that arrived behind it
        # (participants, snapshot...). Re-queueing it would put it *after* them,
        # and the workspace then treats every already-present participant as
        # offline ("has left the room") in private chat.
        self.client_id = accepted.get("client_id")
        self.role = accepted.get("role", "student")
        self.notify_gui(accepted)
        self.running = True
        self.receiver_thread = threading.Thread(target=self.process_messages, daemon=True)
        self.receiver_thread.start()
        return True

    def send_drawing(self, operation):
        if not isinstance(operation, dict):
            return False
        data = operation.get("data", operation)
        return self.network.send_message({"type": "draw", "data": data})

    def send_cursor(self, x, y):
        return self.network.send_message({"type": "cursor_move", "x": x, "y": y})

    def set_role(self, client_id, role):
        return self.network.send_message({"type": "set_role", "client_id": client_id, "role": role})

    def set_user_color(self, color):
        return self.network.send_message({"type": "set_user_color", "color": color})

    def send_chat(self, message):
        """Send a message to the room's group chat."""
        return self.network.send_message({"type": "chat", "message": message})

    def send_private_message(self, to_client_id, message):
        """Send a one-to-one message addressed by the recipient's client id."""
        return self.network.send_message({"type": "private_message",
                                          "to_client_id": to_client_id,
                                          "message": message})

    def undo(self):
        return self.network.send_message({"type": "undo"})

    def redo(self):
        return self.network.send_message({"type": "redo"})

    def clear_canvas(self):
        return self.network.send_message({"type": "clear"})

    def save_board(self):
        return self.network.send_message({"type": "save_board"})

    def load_board(self):
        return self.network.send_message({"type": "load_board"})

    def process_messages(self):
        while self.running:
            message = self.network.get_message()
            if message is None:
                time.sleep(0.01)
                continue
            kind = message.get("type")
            if kind == DISCONNECTED:
                self.running = False
                self.notify_gui(message)
                break
            if kind == "joined_room":
                self.client_id = message.get("client_id")
                self.role = message.get("role", "student")
                self.notify_gui(message)
            elif kind == "board_snapshot":
                self.handle_snapshot(message)
            elif kind == "draw":
                self.handle_drawing_event(message)
            else:
                self.notify_gui(message)

    def handle_drawing_event(self, event):
        sequence = event.get("sequence")
        with self.event_lock:
            if not isinstance(sequence, int) or sequence <= self.last_sequence:
                return
            if sequence != self.last_sequence + 1:
                self.notify_gui({"type": "sync_gap", "expected": self.last_sequence + 1, "received": sequence})
                self.network.send_message({"type": "get_canvas"})
                return
            try:
                accepted = self.state_manager.apply_event(event, sequence)
            except ValueError:
                self.network.send_message({"type": "get_canvas"})
                return
            if accepted:
                self.last_sequence = sequence
                if event.get("user_id") != self.client_id:
                    self.notify_gui({"type": "remote_draw", "event": event})

    def handle_snapshot(self, message):
        board = message.get("board", [])
        sequence = message.get("last_sequence", max((e.get("sequence", 0) for e in board), default=0))
        if not isinstance(board, list) or not isinstance(sequence, int):
            self.notify_gui({"type": "sync_error", "message": "Invalid canvas snapshot"})
            return
        self.state_manager.load_snapshot({"events": board, "last_sequence": sequence})
        with self.event_lock:
            self.last_sequence = sequence
        self.notify_gui({"type": "snapshot_loaded", "board": board})

    def notify_gui(self, event):
        if self.on_event:
            self.on_event(event)

    def disconnect(self):
        if self.network.connected:
            self.network.send_message({"type": "leave_room"})
        self.running = False
        self.network.disconnect()
        current = threading.current_thread()
        if self.receiver_thread and self.receiver_thread is not current:
            self.receiver_thread.join(timeout=1.0)
        receiver = getattr(self.network, "receiver_thread", None)
        if receiver and receiver is not current:
            receiver.join(timeout=1.0)
