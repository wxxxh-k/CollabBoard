import copy
import threading

class StateManager:
    """Local mirror of the authoritative server canvas."""
    def __init__(self):
        self.events = []
        self.last_sequence = 0
        self.lock = threading.RLock()

    def apply_event(self, event, sequence=None):
        with self.lock:
            sequence = event.get("sequence") if sequence is None else sequence
            if not isinstance(sequence, int) or sequence <= self.last_sequence:
                return False
            if sequence != self.last_sequence + 1:
                raise ValueError(f"Sequence gap: expected {self.last_sequence + 1}, got {sequence}")
            self.events.append(copy.deepcopy(event))
            self.last_sequence = sequence
            return True

    def get_events(self):
        with self.lock:
            return copy.deepcopy(self.events)

    def get_snapshot(self):
        with self.lock:
            return {"events": copy.deepcopy(self.events), "last_sequence": self.last_sequence}

    def load_snapshot(self, snapshot):
        with self.lock:
            self.events = copy.deepcopy(snapshot.get("events", []))
            self.last_sequence = int(snapshot.get("last_sequence", 0))
