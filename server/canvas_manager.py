import threading
import copy


class CanvasManager:

    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.lock = threading.RLock()

    def add_drawing(self, room_id, user_id, drawing_data):

        with self.lock:

            room = self.session_manager.get_room(room_id)

            if room is None:
                return None

            sequence = room["sequence"] + 1

            drawing_event = {
                "type": "draw",
                "sequence": sequence,
                "user_id": user_id,
                "data": drawing_data
            }

            room["sequence"] = sequence
            room["board"].append(drawing_event)

            return copy.deepcopy(drawing_event)

    def undo(self, room_id, user_id):

        with self.lock:

            room = self.session_manager.get_room(room_id)

            if room is None:
                return None

            # Remove the latest drawing belonging to this user.
            for index in range(len(room["board"]) - 1, -1, -1):

                if room["board"][index]["user_id"] == user_id:

                    del room["board"][index]

                    return copy.deepcopy(room["board"])

            return None

    def clear_board(self, room_id):

        with self.lock:

            room = self.session_manager.get_room(room_id)

            if room is None:
                return False

            room["board"].clear()

            return True

    def get_board(self, room_id):

        with self.lock:

            room = self.session_manager.get_room(room_id)

            if room is None:
                return None

            return copy.deepcopy(room["board"])

    def replace_board(self, room_id, board):

        with self.lock:

            room = self.session_manager.get_room(room_id)

            if room is None:
                return False

            room["board"] = copy.deepcopy(board)

            room["sequence"] = max(
                (
                    event.get("sequence", 0)
                    for event in board
                ),
                default=0
            )

            return True