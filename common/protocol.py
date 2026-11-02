
import json


# ==========================================
# COLLABBOARD MESSAGE TYPES
# ==========================================

JOIN = "JOIN"
JOIN_ACK = "JOIN_ACK"

DRAW = "DRAW"
DRAW_EVENT = "DRAW_EVENT"

CHAT = "CHAT"

CANVAS_STATE = "CANVAS_STATE"
REQUEST_STATE = "REQUEST_STATE"

UNDO = "UNDO"
UNDO_EVENT = "UNDO_EVENT"

REDO = "REDO"
REDO_EVENT = "REDO_EVENT"

CLEAR = "CLEAR"

SAVE = "SAVE"
SAVE_ACK = "SAVE_ACK"

PING = "PING"
PONG = "PONG"

ERROR = "ERROR"
DISCONNECTED = "DISCONNECTED"


# ==========================================
# MESSAGE ENCODING
# ==========================================

def encode_message(message):
    """
    Convert a Python dictionary into
    newline-delimited JSON bytes.
    """

    json_string = json.dumps(message)

    return (json_string + "\n").encode("utf-8")


# ==========================================
# MESSAGE DECODING
# ==========================================

def decode_message(data):
    """
    Convert a complete JSON byte message
    into a Python dictionary.
    """

    return json.loads(data.decode("utf-8"))
