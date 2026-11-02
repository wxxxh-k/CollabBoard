import copy
import threading

class CanvasManager:
    """Stores ordered drawing operations and per-user undo/redo history."""
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.lock = threading.RLock()
        self.redo_stacks = {}

    def _room(self, room_id):
        return self.session_manager.get_room(room_id)

    def add_drawing(self, room_id, user_id, drawing_data):
        with self.lock:
            room = self._room(room_id)
            if room is None:
                return None
            room["sequence"] += 1
            event = {"type": "draw", "sequence": room["sequence"],
                     "user_id": user_id, "data": copy.deepcopy(drawing_data)}
            room["board"].append(event)
            self.redo_stacks.setdefault((room_id, user_id), []).clear()
            return copy.deepcopy(event)

    def undo(self, room_id, user_id):
        with self.lock:
            room = self._room(room_id)
            if room is None:
                return None
            for index in range(len(room["board"]) - 1, -1, -1):
                if room["board"][index].get("user_id") == user_id:
                    removed = room["board"].pop(index)
                    self.redo_stacks.setdefault((room_id, user_id), []).append(removed)
                    room["sequence"] += 1
                    return self.snapshot(room_id)
            return None

    def redo(self, room_id, user_id):
        with self.lock:
            room = self._room(room_id)
            stack = self.redo_stacks.setdefault((room_id, user_id), [])
            if room is None or not stack:
                return None
            old = stack.pop()
            room["sequence"] += 1
            event = {"type": "draw", "sequence": room["sequence"],
                     "user_id": user_id, "data": copy.deepcopy(old["data"])}
            room["board"].append(event)
            return self.snapshot(room_id)

    def clear_board(self, room_id):
        with self.lock:
            room = self._room(room_id)
            if room is None:
                return None
            room["board"].clear()
            room["sequence"] += 1
            for key in list(self.redo_stacks):
                if key[0] == room_id:
                    self.redo_stacks[key].clear()
            return self.snapshot(room_id)

    def get_board(self, room_id):
        with self.lock:
            room = self._room(room_id)
            return copy.deepcopy(room["board"]) if room else None

    def snapshot(self, room_id):
        with self.lock:
            room = self._room(room_id)
            if room is None:
                return None
            return {"board": copy.deepcopy(room["board"]), "last_sequence": room["sequence"]}

    def replace_board(self, room_id, board):
        with self.lock:
            room = self._room(room_id)
            if room is None or not isinstance(board, list):
                return False
            room["board"] = copy.deepcopy(board)
            room["sequence"] += 1
            for key in list(self.redo_stacks):
                if key[0] == room_id:
                    self.redo_stacks[key].clear()
            return True
