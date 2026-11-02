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
        self.event_lock = threading.RLock()

    def join_room(self, host, port, room_id, username, password=None):
        # Drop stale disconnect or event notifications from a previous connection.
        while self.network.get_message() is not None:
            pass
        self.client_id = None
        self.last_sequence = 0
        if not self.network.connect(host, port):
            return False
        self.room_id, self.username = room_id, username
        message = {"type": "join_room", "room_id": room_id, "username": username}
        if password:
            message["password"] = password
        if not self.network.send_message(message):
            return False
        self.running = True
        self.receiver_thread = threading.Thread(target=self.process_messages, daemon=True)
        self.receiver_thread.start()
        return True

    def send_drawing(self, operation):
        if not isinstance(operation, dict):
            return False
        data = operation.get("data", operation)
        return self.network.send_message({"type": "draw", "data": data})

    def send_chat(self, message):
        return self.network.send_message({"type": "chat", "message": message})

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
