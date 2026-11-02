import json


def encode_message(message):
    """
    Convert a Python dictionary into a JSON message.
    Each message ends with a newline.
    """
    return (json.dumps(message) + "\n").encode("utf-8")


def decode_message(data):
    """
    Convert JSON bytes into a Python dictionary.
    """
    try:
        return json.loads(data.decode("utf-8"))

    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def create_message(message_type, **kwargs):
    """
    Create a standard message format.
    """
    message = {
        "type": message_type
    }

    message.update(kwargs)

    return message