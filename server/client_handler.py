import json
import re
import socket
import threading
import time
import uuid
from common.protocol import MAX_MESSAGE_SIZE, MAX_CHAT_LENGTH
from server.session_manager import ROLES

class ClientHandler(threading.Thread):
    def __init__(self, client_socket, address, session_manager, canvas_manager, persistence_manager):
        super().__init__(daemon=True)
        self.client_socket = client_socket
        self.address = address
        self.session_manager = session_manager
        self.canvas_manager = canvas_manager
        self.persistence_manager = persistence_manager
        self.client_id = None
        self.room_id = None
        self.username = f"User-{address[1]}"
        self.running = True
        self.send_lock = threading.Lock()

    def send_message(self, message):
        try:
            encoded = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            if len(encoded) > MAX_MESSAGE_SIZE:
                return False
            with self.send_lock:
                self.client_socket.sendall(encoded)
            return True
        except (OSError, TypeError, ValueError):
            self.running = False
            return False

    def broadcast(self, message, room_id=None):
        target_room = room_id or self.room_id
        if not target_room:
            return
        for _, handler in self.session_manager.get_clients(target_room):
            handler.send_message(message)

    def send_snapshot(self):
        snapshot = self.canvas_manager.snapshot(self.room_id)
        if snapshot is not None:
            self.send_message({"type": "board_snapshot", **snapshot})

    def handle_message(self, message):
        if not isinstance(message, dict) or not isinstance(message.get("type"), str):
            self.send_message({"type": "error", "message": "Invalid message structure"})
            return
        kind = message["type"]

        if kind == "create_room":
            room_name = message.get("room_name", "Untitled Room")
            password = message.get("password")
            if not isinstance(room_name, str) or not room_name.strip():
                self.send_message({"type": "error", "message": "Invalid room name"})
                return
            if password is not None and not isinstance(password, str):
                self.send_message({"type": "error", "message": "Invalid password"})
                return
            # Whoever creates a room becomes its Host, so a different selected
            # role cannot be honoured for creation.
            create_role = message.get("role")
            if create_role is not None and create_role != "host":
                self.send_message({"type": "error",
                                   "message": "Only the Host role can create a room. Select Host to create one."})
                return
            room_id = self.session_manager.create_room(room_name.strip(), password, owner_handler=self)
            room = self.session_manager.get_room(room_id)
            self.send_message({"type": "room_created", "room_id": room_id,
                               "room_name": room_name.strip(),
                               "host_token": room.get("host_token")})
            return

        if kind == "join_room":
            if self.room_id is not None:
                self.send_message({"type": "error", "message": "Leave your current room first"})
                return
            room_id = message.get("room_id")
            username = message.get("username")
            password = message.get("password")
            if not isinstance(room_id, str) or not room_id.strip() or len(room_id) > 64:
                self.send_message({"type": "error", "message": "Invalid room code"})
                return
            if not isinstance(username, str) or not username.strip() or len(username.strip()) > 40:
                self.send_message({"type": "error", "message": "Username must contain 1-40 characters"})
                return
            if password is not None and not isinstance(password, str):
                self.send_message({"type": "error", "message": "Invalid password"})
                return
            requested_role = message.get("role")
            if requested_role is not None:
                requested_role = requested_role.strip().lower() if isinstance(requested_role, str) else None
                if requested_role not in ROLES:
                    self.send_message({"type": "error", "message": "Invalid role"})
                    return
            # Match the Room ID ignoring case; this only looks rooms up and never creates one.
            resolved_room = self.session_manager.resolve_room_id(room_id.strip())
            if resolved_room is None:
                self.send_message({"type": "error", "message": "Room does not exist"})
                return
            room_id = resolved_room
            self.username = username.strip()
            self.requested_role = requested_role
            token = message.get("host_token")
            self.host_token = token if isinstance(token, str) and len(token) <= 256 else None
            requested_color = message.get("color", "#2563EB")
            if not isinstance(requested_color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", requested_color):
                requested_color = "#2563EB"
            self.requested_color = requested_color.upper()
            success, result = self.session_manager.join_room(room_id.strip(), self, password)
            if not success:
                self.send_message({"type": "error", "message": result})
                return
            self.client_id, self.room_id = result, room_id.strip()
            self.send_message({"type": "joined_room", "room_id": self.room_id,
                               "client_id": self.client_id, "username": self.username,
                               "preferred_color": self.requested_color,
                               "color": self.user_color, "role": self.role})
            self.send_snapshot()
            self.broadcast({"type": "participant_joined", "client_id": self.client_id,
                            "username": self.username, "color": self.requested_color,
                            "preferred_color": self.requested_color, "role": self.role})
            self.broadcast_participants()
            return

        if kind == "ping":
            self.send_message({"type": "pong"})
            return

        if kind == "leave_room":
            self.leave_current_room()
            return

        if not self.room_id:
            self.send_message({"type": "error", "message": "Join a room first"})
            return

        role = self.session_manager.get_role(self.room_id, self.client_id)
        if kind == "cursor_move":
            x, y = message.get("x"), message.get("y")
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                return
            if not (-100000 <= x <= 100000 and -100000 <= y <= 100000):
                return
            self.broadcast({"type": "cursor", "client_id": self.client_id,
                            "username": self.username, "color": self.requested_color,
                            "x": float(x), "y": float(y)}, self.room_id)
        elif kind == "set_role":
            target_id, new_role = message.get("client_id"), message.get("role")
            ok, result = self.session_manager.set_role(self.room_id, self.client_id, target_id, new_role)
            if not ok:
                self.send_message({"type": "error", "message": result})
                return
            target = self.session_manager.get_client(self.room_id, target_id)
            if target:
                target.send_message({"type": "role_changed", "client_id": target_id, "role": result})
            self.broadcast_participants()
        elif kind == "draw":
            if role not in ("host", "assistant"):
                self.send_message({"type": "error", "message": "Students have read-only access"})
                return
            data = message.get("data")
            if not isinstance(data, dict) or len(json.dumps(data)) > 50000:
                self.send_message({"type": "error", "message": "Invalid or oversized drawing event"})
                return
            data = dict(data)
            # The server controls the user's identity color so clients cannot spoof it.
            if data.get("tool") != "eraser":
                data["color"] = self.requested_color
            event = self.canvas_manager.add_drawing(self.room_id, self.client_id, data)
            if event:
                event["username"] = self.username
                event["preferred_color"] = self.requested_color
                self.broadcast(event)
        elif kind == "set_user_color":
            color = message.get("color")
            if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                self.send_message({"type": "error", "message": "Invalid user color"})
                return
            assignment = self.session_manager.update_user_color(
                self.room_id, self.client_id, color
            )
            if assignment is None:
                self.send_message({"type": "error", "message": "Could not update user color"})
                return
            self.requested_color = assignment["preferred_color"]
            self.user_color = assignment["color"]
            self.broadcast({"type": "user_color_changed", "client_id": self.client_id,
                            "username": self.username,
                            "preferred_color": self.requested_color,
                            "color": self.requested_color})
            self.broadcast_participants()
        elif kind == "chat":
            text = message.get("message")
            if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHAT_LENGTH:
                self.send_message({"type": "error", "message": "Chat messages must contain 1-2000 characters"})
                return
            # Group chat: room-wide broadcast to every participant (including
            # the sender, whose client renders the echoed message).
            self.broadcast({"type": "chat", "scope": "group", "client_id": self.client_id,
                            "username": self.username, "preferred_color": self.requested_color,
                            "color": self.requested_color, "message": text.strip(),
                            "ts": int(time.time())})
        elif kind == "private_message":
            self.handle_private_message(message)
        elif kind == "undo":
            if role not in ("host", "assistant"):
                self.send_message({"type": "error", "message": "Students have read-only access"})
                return
            snapshot = self.canvas_manager.undo(self.room_id, self.client_id)
            if snapshot is not None:
                self.broadcast({"type": "board_snapshot", **snapshot})
        elif kind == "redo":
            if role not in ("host", "assistant"):
                self.send_message({"type": "error", "message": "Students have read-only access"})
                return
            snapshot = self.canvas_manager.redo(self.room_id, self.client_id)
            if snapshot is not None:
                self.broadcast({"type": "board_snapshot", **snapshot})
        elif kind == "clear":
            if role != "host":
                self.send_message({"type": "error", "message": "Only the host can clear the board"})
                return
            snapshot = self.canvas_manager.clear_board(self.room_id)
            if snapshot is not None:
                self.broadcast({"type": "board_snapshot", **snapshot})
        elif kind in ("get_canvas", "get_participants"):
            if kind == "get_canvas":
                self.send_snapshot()
            else:
                self.send_participants()
        elif kind == "save_board":
            board = self.canvas_manager.get_board(self.room_id)
            success = self.persistence_manager.save_board(self.room_id, board or [])
            self.send_message({"type": "save_result", "success": success})
        elif kind == "load_board":
            if role not in ("host", "assistant"):
                self.send_message({"type": "error", "message": "Students have read-only access"})
                return
            board = self.persistence_manager.load_board(self.room_id)
            if board is None:
                self.send_message({"type": "error", "message": "No saved board found"})
                return
            self.canvas_manager.replace_board(self.room_id, board)
            self.send_snapshot_to_room()
        else:
            self.send_message({"type": "error", "message": f"Unknown message type: {kind}"})

    def handle_private_message(self, message):
        """Route a one-to-one message to its recipient and echo it to the sender.

        The sender is always the authenticated connection (self.client_id), never
        a value supplied by the client, and the recipient is resolved by client id
        strictly inside the sender's own room. Nothing is broadcast.
        """
        recipient_id = message.get("to_client_id")
        text = message.get("message")
        safe_id = recipient_id if isinstance(recipient_id, str) and len(recipient_id) <= 64 else None
        safe_text = text if isinstance(text, str) and len(text) <= MAX_CHAT_LENGTH else None

        def fail(reason):
            self.send_message({"type": "private_message_failed", "to_client_id": safe_id,
                               "text": safe_text, "reason": reason})

        if safe_id is None or not safe_id.strip():
            fail("Invalid recipient")
            return
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHAT_LENGTH:
            fail("Private messages must contain 1-2000 characters")
            return
        if safe_id == self.client_id:
            fail("You cannot send a private message to yourself")
            return
        recipient = self.session_manager.get_client(self.room_id, safe_id)
        if recipient is None:
            fail("That participant is not in this room (they may have left)")
            return
        payload = {"type": "private_message", "message_id": uuid.uuid4().hex,
                   "from_client_id": self.client_id, "from_username": self.username,
                   "to_client_id": safe_id, "to_username": recipient.username,
                   "preferred_color": self.requested_color, "color": self.requested_color,
                   "message": text.strip(), "ts": int(time.time())}
        if not recipient.send_message(payload):
            fail(f"{recipient.username} is offline")
            return
        # Echo to the sender so both sides render the same server-confirmed message.
        self.send_message(payload)

    def send_snapshot_to_room(self):
        snapshot = self.canvas_manager.snapshot(self.room_id)
        if snapshot is not None:
            self.broadcast({"type": "board_snapshot", **snapshot})

    def send_participants(self):
        if not self.room_id:
            return
        participants = [{"client_id": cid, "username": handler.username,
                  "color": getattr(handler, "requested_color", "#475569"),
                  "preferred_color": getattr(handler, "requested_color", "#475569"),
                  "role": self.session_manager.get_role(self.room_id, cid)}
                 for cid, handler in self.session_manager.get_clients(self.room_id)]
        self.send_message({"type": "participants", "participants": participants})

    def broadcast_participants(self):
        if not self.room_id:
            return
        participants = [{"client_id": cid, "username": handler.username,
                  "color": getattr(handler, "requested_color", "#475569"),
                  "preferred_color": getattr(handler, "requested_color", "#475569"),
                  "role": self.session_manager.get_role(self.room_id, cid)}
                 for cid, handler in self.session_manager.get_clients(self.room_id)]
        self.broadcast({"type": "participants", "participants": participants})

    def leave_current_room(self):
        if not self.room_id:
            return
        old_room, old_client = self.room_id, self.client_id
        self.session_manager.leave_room(old_room, old_client)
        self.room_id = self.client_id = None
        self.broadcast({"type": "participant_left", "client_id": old_client,
                        "username": self.username}, old_room)
        self.send_message({"type": "left_room"})
        remaining = [{"client_id": cid, "username": handler.username,
                      "color": getattr(handler, "requested_color", "#475569"),
                  "preferred_color": getattr(handler, "requested_color", "#475569"),
                  "role": self.session_manager.get_role(old_room, cid)}
                     for cid, handler in self.session_manager.get_clients(old_room)]
        self.broadcast({"type": "participants", "participants": remaining}, old_room)

    def run(self):
        print(f"[CONNECTED] {self.address}")
        buffer = bytearray()
        try:
            while self.running:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                if len(buffer) > MAX_MESSAGE_SIZE and b"\n" not in buffer:
                    break
                while b"\n" in buffer:
                    line, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    if not line.strip():
                        continue
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        self.send_message({"type": "error", "message": "Invalid JSON"})
                        continue
                    try:
                        self.handle_message(message)
                    except Exception as error:
                        print("[CLIENT HANDLER ERROR]", error)
                        self.send_message({"type": "error", "message": "Server could not process the request"})
        except OSError as error:
            if self.running:
                print("[NETWORK ERROR]", error)
        finally:
            self.running = False
            self.leave_current_room()
            try:
                self.client_socket.close()
            except OSError:
                pass
            print(f"[DISCONNECTED] {self.address}")
