
import threading
import copy


class StateManager:
    """
    Maintains the local canvas state and drawing event history.

    The server remains authoritative for shared event ordering.
    """

    def __init__(self):
        self.events = []
        self.last_sequence = 0

        # Undo and redo history
        self.undo_stack = []
        self.redo_stack = []

        # Protect state when multiple threads access it
        self.lock = threading.Lock()

    def apply_event(self, event, sequence=None):
        """
        Apply a drawing event to the local canvas history.

        Returns True if the event was accepted.
        Returns False if it was already processed.
        """

        with self.lock:

            if sequence is not None:
                if sequence <= self.last_sequence:
                    return False

                if sequence != self.last_sequence + 1:
                    raise ValueError(
                        f"Sequence gap: expected "
                        f"{self.last_sequence + 1}, got {sequence}"
                    )

                self.last_sequence = sequence

            self.events.append(copy.deepcopy(event))

            return True

    def get_events(self):
        """Return a safe copy of all canvas events."""

        with self.lock:
            return copy.deepcopy(self.events)

    def get_snapshot(self):
        """Create a snapshot of the current canvas state."""

        with self.lock:
            return {
                "events": copy.deepcopy(self.events),
                "last_sequence": self.last_sequence
            }

    def load_snapshot(self, snapshot):
        """Replace local state with a server-provided snapshot."""

        with self.lock:

            self.events = copy.deepcopy(
                snapshot.get("events", [])
            )

            self.last_sequence = snapshot.get(
                "last_sequence", 0
            )

            self.undo_stack.clear()
            self.redo_stack.clear()

    def record_undo(self, event):
        """Record an event for undo tracking."""

        with self.lock:
            self.undo_stack.append(copy.deepcopy(event))
            self.redo_stack.clear()

    def undo(self):
        """Move the latest locally tracked operation to redo history."""

        with self.lock:

            if not self.undo_stack:
                return None

            event = self.undo_stack.pop()
            self.redo_stack.append(event)

            return copy.deepcopy(event)

    def redo(self):
        """Restore the latest locally undone operation."""

        with self.lock:

            if not self.redo_stack:
                return None

            event = self.redo_stack.pop()
            self.undo_stack.append(event)

            return copy.deepcopy(event)

    def clear(self):
        """Clear local canvas history."""

        with self.lock:
            self.events.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
