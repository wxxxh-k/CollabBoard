import unittest

from common.user_colors import build_viewer_color_map
from server.session_manager import SessionManager


class FakeClient:
    def __init__(self, username, requested_color):
        self.username = username
        self.requested_color = requested_color


class UserColorAssignmentTests(unittest.TestCase):
    def test_server_preserves_duplicate_preferences(self):
        sessions = SessionManager()
        room = sessions.create_room("colors")
        alice = FakeClient("Alice", "#2563EB")
        bob = FakeClient("Bob", "#2563EB")
        ok, alice_id = sessions.join_room(room, alice)
        self.assertTrue(ok)
        ok, bob_id = sessions.join_room(room, bob)
        self.assertTrue(ok)
        self.assertEqual(alice.user_color, "#2563EB")
        self.assertEqual(bob.user_color, "#2563EB")
        self.assertEqual(alice.requested_color, bob.requested_color)

    def test_each_viewer_gets_their_own_preferred_color(self):
        users = [
            {"client_id": "A", "preferred_color": "#2563EB"},
            {"client_id": "B", "preferred_color": "#2563EB"},
            {"client_id": "C", "preferred_color": "#16A36A"},
        ]
        a_view = build_viewer_color_map("A", "#2563EB", users)
        b_view = build_viewer_color_map("B", "#2563EB", users)
        c_view = build_viewer_color_map("C", "#16A36A", users)

        self.assertEqual(a_view["A"], "#2563EB")
        self.assertEqual(a_view["B"], "#E05252")
        self.assertEqual(a_view["C"], "#16A36A")
        self.assertEqual(b_view["B"], "#2563EB")
        self.assertEqual(b_view["A"], "#E05252")
        self.assertEqual(b_view["C"], "#16A36A")
        self.assertEqual(c_view["C"], "#16A36A")
        self.assertEqual(c_view["A"], "#2563EB")
        self.assertEqual(c_view["B"], "#E05252")

    def test_preference_change_does_not_rewrite_other_users_preferences(self):
        sessions = SessionManager()
        room = sessions.create_room("colors")
        alice = FakeClient("Alice", "#2563EB")
        bob = FakeClient("Bob", "#2563EB")
        _, alice_id = sessions.join_room(room, alice)
        sessions.join_room(room, bob)
        assignment = sessions.update_user_color(room, alice_id, "#16A36A")
        self.assertEqual(assignment["preferred_color"], "#16A36A")
        self.assertEqual(assignment["color"], "#16A36A")
        self.assertEqual(bob.requested_color, "#2563EB")

    def test_palette_handles_many_collisions(self):
        users = [{"client_id": str(i), "preferred_color": "#2563EB"} for i in range(30)]
        for viewer in users:
            mapping = build_viewer_color_map(viewer["client_id"], "#2563EB", users)
            self.assertEqual(mapping[viewer["client_id"]], "#2563EB")
            self.assertEqual(len(mapping), len(users))
            self.assertEqual(len(set(mapping.values())), len(users))


if __name__ == "__main__":
    unittest.main()
