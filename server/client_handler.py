import json
import socket
import threading


MAX_MESSAGE_SIZE = 1024 * 1024


class ClientHandler(threading.Thread):

    def __init__(
        self,
        client_socket,
        address,
        session_manager,
        canvas_manager,
        persistence_manager
    ):

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

    # ---------------- SEND MESSAGE ----------------

    def send_message(self, message):

        try:

            encoded = (
                json.dumps(message) + "\n"
            ).encode("utf-8")

            with self.send_lock:

                self.client_socket.sendall(encoded)

            return True

        except (OSError, TypeError, ValueError):

            self.running = False

            return False

    # ---------------- BROADCAST ----------------

    def broadcast(self, message):

        clients = self.session_manager.get_clients(
            self.room_id
        )

        for client_id, handler in clients:

            handler.send_message(message)

    # ---------------- HANDLE MESSAGES ----------------

    def handle_message(self, message):

        if not isinstance(message, dict):
            return

        message_type = message.get("type")

        if not isinstance(message_type, str):
            self.send_message({
                "type": "error",
                "message": "Invalid message type"
            })
            return

        # CREATE ROOM

        if message_type == "create_room":

            room_name = message.get("room_name", "Untitled Room")
            password = message.get("password")

            if not isinstance(room_name, str) or not room_name.strip():
                self.send_message({
                    "type": "error",
                    "message": "Invalid room name"
                })
                return

            if password is not None and not isinstance(password, str):
                self.send_message({
                    "type": "error",
                    "message": "Invalid password"
                })
                return

            room_id = self.session_manager.create_room(
                room_name,
                password
            )

            self.send_message({
                "type": "room_created",
                "room_id": room_id,
                "room_name": room_name
            })

        # JOIN ROOM

        elif message_type == "join_room":

            if self.room_id is not None:

                self.send_message({
                    "type": "error",
                    "message": "Leave your current room first"
                })

                return

            room_id = message.get("room_id")
            password = message.get("password")

            username = message.get("username", self.username)

            if not isinstance(room_id, str):
                self.send_message({
                    "type": "error",
                    "message": "Invalid room ID"
                })
                return

            if not isinstance(username, str) or not username.strip():
                self.send_message({
                    "type": "error",
                    "message": "Invalid username"
                })
                return

            if password is not None and not isinstance(password, str):
                self.send_message({
                    "type": "error",
                    "message": "Invalid password"
                })
                return

            success, result = self.session_manager.join_room(
                room_id,
                self,
                password
            )

            if success:

                self.client_id = result
                self.room_id = room_id
                self.username = username[:40]

                self.send_message({
                    "type": "joined_room",
                    "room_id": room_id,
                    "client_id": self.client_id,
                    "username": self.username
                })

                board = self.canvas_manager.get_board(room_id)

                self.send_message({
                    "type": "board_snapshot",
                    "board": board
                })

                self.broadcast({
                    "type": "participant_joined",
                    "client_id": self.client_id,
                    "username": self.username
                })

                self.send_participants()

            else:

                self.send_message({
                    "type": "error",
                    "message": result
                })

        # LEAVE ROOM

        elif message_type == "leave_room":

            self.leave_current_room()

        # DRAW

        elif message_type == "draw":

            if not self.room_id:
                return

            drawing_data = message.get("data")

            if not isinstance(drawing_data, dict):
                self.send_message({
                    "type": "error",
                    "message": "Invalid drawing data"
                })
                return

            if len(json.dumps(drawing_data)) > 50000:
                self.send_message({
                    "type": "error",
                    "message": "Drawing event too large"
                })
                return

            event = self.canvas_manager.add_drawing(
                self.room_id,
                self.client_id,
                drawing_data
            )

            if event:

                self.broadcast(event)

        # CHAT

        elif message_type == "chat":

            if not self.room_id:
                return

            text = message.get("message")

            if not isinstance(text, str) or not text.strip():
                return

            if len(text) > 2000:
                return

            self.broadcast({
                "type": "chat",
                "client_id": self.client_id,
                "username": self.username,
                "message": text,
            })

        # UNDO

        elif message_type == "undo":

            if not self.room_id:
                return

            board = self.canvas_manager.undo(
                self.room_id,
                self.client_id
            )

            if board is not None:

                self.broadcast({
                    "type": "board_snapshot",
                    "board": board
                })

        # CLEAR BOARD

        elif message_type == "clear":

            if not self.room_id:
                return

            self.canvas_manager.clear_board(
                self.room_id
            )

            self.broadcast({
                "type": "board_snapshot",
                "board": []
            })

        # GET PARTICIPANTS

        elif message_type == "get_participants":

            self.send_participants()

        # SAVE BOARD

        elif message_type == "save_board":

            if not self.room_id:
                return

            board = self.canvas_manager.get_board(
                self.room_id
            )

            success = self.persistence_manager.save_board(
                self.room_id,
                board
            )

            self.send_message({
                "type": "save_result",
                "success": success
            })

        # LOAD BOARD

        elif message_type == "load_board":

            if not self.room_id:
                return

            board = self.persistence_manager.load_board(
                self.room_id
            )

            if board is None:

                self.send_message({
                    "type": "error",
                    "message": "No saved board found"
                })

                return

            self.canvas_manager.replace_board(
                self.room_id,
                board
            )

            self.broadcast({
                "type": "board_snapshot",
                "board": board
            })

        # PING

        elif message_type == "ping":

            self.send_message({
                "type": "pong"
            })

        else:

            self.send_message({
                "type": "error",
                "message": "Unknown message type"
            })

    # ---------------- PARTICIPANTS ----------------

    def send_participants(self):

        if not self.room_id:
            return

        clients = self.session_manager.get_clients(
            self.room_id
        )

        participants = []

        for client_id, handler in clients:

            participants.append({
                "client_id": client_id,
                "username": handler.username
            })

        self.send_message({
            "type": "participants",
            "participants": participants
        })

    # ---------------- LEAVE ROOM ----------------

    def leave_current_room(self):

        if self.room_id is None:
            return

        old_room_id = self.room_id
        old_client_id = self.client_id

        self.session_manager.leave_room(
            old_room_id,
            old_client_id
        )

        self.room_id = None
        self.client_id = None

        clients = self.session_manager.get_clients(
            old_room_id
        )

        message = {
            "type": "participant_left",
            "client_id": old_client_id
        }

        for client_id, handler in clients:
            handler.send_message(message)

        self.send_message({
            "type": "left_room"
        })

        for client_id, handler in clients:
            handler.send_participants()

    # ---------------- RUN THREAD ----------------

    def run(self):

        print(f"[CONNECTED] {self.address}")

        buffer = bytearray()

        try:

            while self.running:

                data = self.client_socket.recv(4096)

                if not data:
                    break

                buffer.extend(data)

                if len(buffer) > MAX_MESSAGE_SIZE:
                    break

                while b"\n" in buffer:

                    raw_message, _, remaining = buffer.partition(b"\n")

                    buffer = bytearray(remaining)

                    if not raw_message.strip():
                        continue

                    try:

                        message = json.loads(
                            raw_message.decode("utf-8")
                        )

                    except (json.JSONDecodeError, UnicodeDecodeError):

                        self.send_message({
                            "type": "error",
                            "message": "Invalid JSON"
                        })

                        continue

                    self.handle_message(message)

        except OSError as error:

            print("[NETWORK ERROR]", error)

        finally:

            self.running = False

            if self.room_id and self.client_id:
                self.leave_current_room()

            try:
                self.client_socket.close()
            except OSError:
                pass

            print(f"[DISCONNECTED] {self.address}")