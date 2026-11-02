import threading
import uuid
import hashlib
import secrets


class SessionManager:

    def __init__(self):

        # Stores all active rooms
        self.rooms = {}

        # Prevents simultaneous modifications
        self.lock = threading.RLock()

    # --------------------------------
    # CREATE ROOM
    # --------------------------------

    def create_room(self, room_name, password=None):

        with self.lock:

            room_id = str(uuid.uuid4())[:8]

            salt = secrets.token_bytes(16)

            password_hash = None

            if password:
                password_hash = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    200000
                ).hex()

            self.rooms[room_id] = {

                "room_name": room_name,

                "password_salt": salt.hex(),

                "password_hash": password_hash,

                "clients": {},

                "board": [],

                "sequence": 0
            }

            print(f"[ROOM CREATED] {room_name} ({room_id})")

            return room_id

    # --------------------------------
    # JOIN ROOM
    # --------------------------------

    def join_room(self, room_id, client, password=None):

        with self.lock:

            room = self.rooms.get(room_id)

            if room is None:

                return False, "Room does not exist"

            stored_hash = room["password_hash"]

            if stored_hash:

                if password is None:

                    return False, "Password required"

                salt = bytes.fromhex(
                    room["password_salt"]
                )

                supplied_hash = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    200000
                ).hex()

                if not secrets.compare_digest(
                    supplied_hash,
                    stored_hash
                ):

                    return False, "Incorrect password"

            client_id = str(uuid.uuid4())

            room["clients"][client_id] = client

            print(
                f"[ROOM JOINED] Client {client_id} joined {room_id}"
            )

            return True, client_id

    # --------------------------------
    # LEAVE ROOM
    # --------------------------------

    def leave_room(self, room_id, client_id):

        with self.lock:

            room = self.rooms.get(room_id)

            if room and client_id in room["clients"]:

                del room["clients"][client_id]

                print(
                    f"[ROOM LEFT] Client {client_id} left {room_id}"
                )

            # IMPORTANT:
            # Do not delete the room when it becomes empty.
            # This preserves its board data for reconnection.

    # --------------------------------
    # GET ROOM CLIENTS
    # --------------------------------

    def get_clients(self, room_id):

        with self.lock:

            room = self.rooms.get(room_id)

            if room:

                return list(room["clients"].items())

            return []

    # --------------------------------
    # GET ROOM INFORMATION
    # --------------------------------

    def get_room(self, room_id):

        with self.lock:

            return self.rooms.get(room_id)

    # --------------------------------
    # GET ALL ROOMS
    # --------------------------------

    def get_all_rooms(self):

        with self.lock:

            return {
                room_id: {
                    "room_name": room["room_name"],
                    "participant_count": len(room["clients"])
                }

                for room_id, room in self.rooms.items()
            }