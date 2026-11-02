import unittest
from server.session_manager import SessionManager
from server.canvas_manager import CanvasManager

class FakeClient:
    username = "tester"

class CanvasManagerTests(unittest.TestCase):
    def setUp(self):
        self.sessions = SessionManager()
        self.room = self.sessions.create_room("test")
        ok, self.user = self.sessions.join_room(self.room, FakeClient())
        self.assertTrue(ok)
        self.canvas = CanvasManager(self.sessions)

    def test_draw_undo_redo_and_clear_sequence(self):
        event = self.canvas.add_drawing(self.room, self.user, {"tool": "pen", "points": [[1, 2]]})
        self.assertEqual(event["sequence"], 1)
        snapshot = self.canvas.undo(self.room, self.user)
        self.assertEqual(snapshot["board"], [])
        self.assertEqual(snapshot["last_sequence"], 2)
        snapshot = self.canvas.redo(self.room, self.user)
        self.assertEqual(len(snapshot["board"]), 1)
        self.assertEqual(snapshot["last_sequence"], 3)
        snapshot = self.canvas.clear_board(self.room)
        self.assertEqual(snapshot["board"], [])
        self.assertEqual(snapshot["last_sequence"], 4)

if __name__ == "__main__":
    unittest.main()
