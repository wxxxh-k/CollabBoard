
import threading
import time

from common.protocol import DISCONNECTED


class SyncManager:
    """
    Coordinates synchronization between NetworkClient,
    StateManager and the server.
    """

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
        self.sync_gap_detected = False

        self.event_lock = threading.Lock()

    # ----------------------------------
    # JOIN ROOM
    # ----------------------------------

    def join_room(self, host, port, room_id, username, password=None):

        if not self.network.connect(host, port):
            return False

        self.room_id = room_id
        self.username = username

        message = {
            "type": "join_room",
            "room_id": room_id,
            "username": username
        }

        if password:
            message["password"] = password

        if not self.network.send_message(message):
            return False

        self.running = True

        self.receiver_thread = threading.Thread(
            target=self.process_messages,
            daemon=True
        )

        self.receiver_thread.start()

        return True

    # ----------------------------------
    # SEND DRAWING
    # ----------------------------------

    def send_drawing(self, operation):

        if not self.network.connected:
            return False

        if not isinstance(operation, dict):
            return False

        return self.network.send_message({
            "type": "draw",
            "data": operation.get("data", {})
        })

    # ----------------------------------
    # UNDO
    # ----------------------------------

    def undo(self):

        return self.network.send_message({
            "type": "undo"
        })

    # ----------------------------------
    # CLEAR CANVAS
    # ----------------------------------

    def clear_canvas(self):

        return self.network.send_message({
            "type": "clear"
        })

    # ----------------------------------
    # SAVE BOARD
    # ----------------------------------

    def save_board(self):

        return self.network.send_message({
            "type": "save_board"
        })

    # ----------------------------------
    # LOAD BOARD
    # ----------------------------------

    def load_board(self):

        return self.network.send_message({
            "type": "load_board"
        })

    # ----------------------------------
    # PROCESS INCOMING MESSAGES
    # ----------------------------------

    def process_messages(self):

        while self.running:

            message = self.network.get_message()

            if message is None:
                time.sleep(0.01)
                continue

            message_type = message.get("type")

            if message_type == DISCONNECTED:

                self.running = False
                self.notify_gui(message)
                break

            elif message_type == "joined_room":

                self.client_id = message.get("client_id")
                self.notify_gui(message)

            elif message_type == "board_snapshot":

                self.handle_snapshot(message)

            elif message_type == "draw":

                self.handle_drawing_event(message)

            elif message_type in (
                "participant_joined",
                "participant_left",
                "participants",
                "chat",
                "save_result",
                "error",
                "pong",
                "left_room"
            ):

                self.notify_gui(message)

            else:

                self.notify_gui(message)

    # ----------------------------------
    # HANDLE DRAWING EVENT
    # ----------------------------------

    def handle_drawing_event(self, event):

        sequence = event.get("sequence")

        if not isinstance(sequence, int):
            self.notify_gui({
                "type": "sync_error",
                "message": "Drawing event has no valid sequence number"
            })
            return

        with self.event_lock:

            if sequence <= self.last_sequence:
                return

            if sequence != self.last_sequence + 1:

                self.sync_gap_detected = True

                self.notify_gui({
                    "type": "sync_gap",
                    "expected": self.last_sequence + 1,
                    "received": sequence
                })

                return

            accepted = self.state_manager.apply_event(
                event,
                sequence=sequence
            )

            if accepted:

                self.last_sequence = sequence

                self.notify_gui({
                    "type": "remote_draw",
                    "event": event
                })

    # ----------------------------------
    # HANDLE CANVAS SNAPSHOT
    # ----------------------------------

    def handle_snapshot(self, message):

        board = message.get("board", [])

        if not isinstance(board, list):
            self.notify_gui({
                "type": "sync_error",
                "message": "Invalid canvas snapshot"
            })
            return

        server_sequence = message.get("last_sequence")

        if server_sequence is None:

            # Temporary fallback.
            # Not reliable after undo or clear.
            server_sequence = max(
                (
                    event.get("sequence", 0)
                    for event in board
                ),
                default=0
            )

            self.notify_gui({
                "type": "sync_warning",
                "message": (
                    "Snapshot has no last_sequence. "
                    "Sequence recovery may be inaccurate."
                )
            })

        if not isinstance(server_sequence, int):
            self.notify_gui({
                "type": "sync_error",
                "message": "Invalid snapshot sequence"
            })
            return

        snapshot = {
            "events": board,
            "last_sequence": server_sequence
        }

        self.state_manager.load_snapshot(snapshot)

        with self.event_lock:
            self.last_sequence = server_sequence
            self.sync_gap_detected = False

        self.notify_gui({
            "type": "snapshot_loaded",
            "board": board
        })

    # ----------------------------------
    # GUI CALLBACK
    # ----------------------------------

    def notify_gui(self, event):

        if self.on_event:
            self.on_event(event)

    # ----------------------------------
    # DISCONNECT
    # ----------------------------------

    def disconnect(self):

        self.running = False
        self.network.disconnect()
