"""Newline-delimited JSON protocol shared by CollabBoard clients and server."""
import json

MAX_MESSAGE_SIZE = 1024 * 1024
DISCONNECTED = "disconnected"

MESSAGE_TYPES = {
    "create_room", "room_created", "join_room", "joined_room",
    "leave_room", "left_room", "draw", "chat", "participants",
    "participant_joined", "participant_left", "board_snapshot",
    "clear", "undo", "redo", "save_board", "load_board", "set_user_color",
    "user_color_changed", "cursor_move", "cursor", "role_update", "role_changed",
    # Messaging: "chat" is the room-wide group chat (kept for backward
    # compatibility). "private_message" is a one-to-one message addressed by
    # client id; "private_message_failed" tells only the sender why it was
    # not delivered.
    "private_message", "private_message_failed",
    "save_result", "error", "ping", "pong"
}

# Limits shared by the client and the server.
MAX_CHAT_LENGTH = 2000

def encode_message(message):
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ValueError("A message must be a dictionary with a string 'type'.")
    payload = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("Message exceeds the maximum allowed size.")
    return payload

def decode_message(payload):
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    message = json.loads(payload)
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ValueError("Invalid message structure.")
    return message
