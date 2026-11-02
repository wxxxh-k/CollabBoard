
import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, PROJECT_ROOT)

from client.state_manager import StateManager


state = StateManager()

# Apply two drawing events
state.apply_event(
    {"type": "DRAW", "x": 10, "y": 20},
    sequence=1
)

state.apply_event(
    {"type": "DRAW", "x": 30, "y": 40},
    sequence=2
)

print("Canvas events:", state.get_events())

# Test snapshot
snapshot = state.get_snapshot()
print("Snapshot:", snapshot)

# Test snapshot restoration
new_state = StateManager()
new_state.load_snapshot(snapshot)

print("Restored events:", new_state.get_events())

# Test undo and redo tracking
state.record_undo({"type": "DRAW", "x": 50, "y": 60})

print("Undo result:", state.undo())
print("Redo result:", state.redo())

print("StateManager test completed!")
