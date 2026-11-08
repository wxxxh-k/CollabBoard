import threading
import uuid
import hashlib
import secrets
import re
from common.user_colors import DEFAULT_USER_COLOR, normalize_color

# Roles a user can select at login.
ROLES = ("host", "assistant", "student")


class SessionManager:

    def __init__(self):

        # Stores all active rooms
        self.rooms = {}

        # Prevents simultaneous modifications
        self.lock = threading.RLock()

    # --------------------------------
    # CREATE ROOM
    # --------------------------------

    def create_room(self, room_name, password=None, room_id=None, owner_handler=None):

        with self.lock:

            if room_id is None:
                room_id = str(uuid.uuid4())[:8]
                while room_id in self.rooms:
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

                "sequence": 0,
                "host_connection": id(owner_handler) if owner_handler is not None else None,
                "host_token": secrets.token_urlsafe(32),
                "host_client_id": None,
                "roles": {},
                # username (casefolded) -> {"username", "role"}. Survives
                # disconnects so a returning user is recognised as the same
                # identity (and the Host can always get back in).
                "members": {}
            }

            print(f"[ROOM CREATED] {room_name} ({room_id})")

            return room_id

    # --------------------------------
    # JOIN ROOM
    # --------------------------------

    def resolve_room_id(self, room_id):
        """Return the stored room ID matching room_id (ignoring case), else None.

        Lookup only; it never creates a room.
        """
        if not isinstance(room_id, str):
            return None
        with self.lock:
            if room_id in self.rooms:
                return room_id
            wanted = room_id.casefold()
            for existing in self.rooms:
                if existing.casefold() == wanted:
                    return existing
            return None

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

            username = getattr(client, "username", "")
            if username and any(
                getattr(existing, "username", "").casefold() == username.casefold()
                for existing in room["clients"].values()
            ):
                return False, "That username is already in use in this room"

            client_id = str(uuid.uuid4())
            requested_role = getattr(client, "requested_role", None)
            if requested_role is not None:
                ok, role_or_reason = self._resolve_requested_role(room, client, requested_role)
                if not ok:
                    return False, role_or_reason
                role = role_or_reason
                if role == "host":
                    room["host_client_id"] = client_id
                    # The creator's connection marker is no longer needed and
                    # object ids can be reused, so never let it match again.
                    room["host_connection"] = None
                    for member in room["members"].values():
                        if member["role"] == "host":
                            member["role"] = "student"
                room["members"][username.casefold()] = {"username": username, "role": role}
            elif room.get("host_client_id") is None and room.get("host_connection") is None:
                room["host_client_id"] = client_id
                role = "host"
            elif (room.get("host_connection") == id(client) or
                  (getattr(client, "host_token", None) and
                   secrets.compare_digest(getattr(client, "host_token"), room.get("host_token", "")))):
                room["host_client_id"] = client_id
                room["host_connection"] = id(client)
                role = "host"
            else:
                role = "student"
            if requested_role is None and username:
                room["members"][username.casefold()] = {"username": username, "role": role}
            room["roles"][client_id] = role
            client.role = role
            requested_color = normalize_color(
                getattr(client, "requested_color", DEFAULT_USER_COLOR)
            )
            client.requested_color = requested_color
            # Store the user's preference only. Each client resolves collisions
            # independently from its own point of view.
            client.user_color = requested_color
            room["clients"][client_id] = client

            print(
                f"[ROOM JOINED] Client {client_id} joined {room_id}"
            )

            return True, client_id

    def _resolve_requested_role(self, room, client, requested_role):
        """Decide the role for a join that names one (host/assistant/student).

        Assistant and Student are granted as selected. Host is granted only to
        the room's own Host identity: the creator (private host token), the
        username already registered as Host (rejoin), or the first claimant of
        a room that has no Host yet. Callers hold self.lock.
        """
        if requested_role not in ROLES:
            return False, "Invalid role"
        username = getattr(client, "username", "") or ""
        member = room["members"].get(username.casefold())
        token = getattr(client, "host_token", None)
        has_token = bool(token) and secrets.compare_digest(token, room.get("host_token", ""))
        registered_host = member is not None and member["role"] == "host"
        host_exists = any(m["role"] == "host" for m in room["members"].values())
        room_has_host = (host_exists or room.get("host_client_id") is not None)
        # A room created by a client is awaiting its creator even before they join.
        awaiting_creator = room.get("host_connection") is not None and not host_exists

        if requested_role == "host":
            if has_token or registered_host:
                return True, "host"
            if not room_has_host and not awaiting_creator:
                return True, "host"
            return False, "This room already has a Host. Join as Assistant or Student."
        if registered_host or has_token:
            return False, "You are the Host of this room. Select the Host role to join it."
        return True, requested_role

    # --------------------------------
    # LEAVE ROOM
    # --------------------------------

    def update_user_color(self, room_id, client_id, preferred_color):
        """Update and return the participant's preferred color (not a global allocation)."""
        with self.lock:
            room = self.rooms.get(room_id)
            if not room or client_id not in room["clients"]:
                return None
            client = room["clients"][client_id]
            preferred = normalize_color(preferred_color)
            client.requested_color = preferred
            client.user_color = preferred
            return {"preferred_color": preferred, "color": preferred}

    def get_role(self, room_id, client_id):
        with self.lock:
            room = self.rooms.get(room_id)
            return room.get("roles", {}).get(client_id) if room else None

    def set_role(self, room_id, actor_id, target_id, role):
        if role not in ("assistant", "student"):
            return False, "Only assistant or student roles can be assigned"
        with self.lock:
            room = self.rooms.get(room_id)
            if not room or room.get("host_client_id") != actor_id:
                return False, "Only the host can manage roles"
            if target_id not in room["clients"]:
                return False, "Participant is no longer in this room"
            room["roles"][target_id] = role
            room["clients"][target_id].role = role
            target_name = getattr(room["clients"][target_id], "username", "")
            if target_name:
                room["members"][target_name.casefold()] = {"username": target_name, "role": role}
            return True, role

    def leave_room(self, room_id, client_id):

        with self.lock:

            room = self.rooms.get(room_id)

            if room and client_id in room["clients"]:

                del room["clients"][client_id]
                room.get("roles", {}).pop(client_id, None)

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

    def get_client(self, room_id, client_id):
        """Return the handler for client_id, but only if it is in room_id.

        Looking the recipient up inside the sender's own room is what keeps
        private messages from ever crossing room boundaries.
        """
        with self.lock:
            room = self.rooms.get(room_id)
            if room is None:
                return None
            return room["clients"].get(client_id)

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