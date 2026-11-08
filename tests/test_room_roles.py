import unittest
from server.session_manager import SessionManager


class FakeClient:
    def __init__(self, username, host_token=None):
        self.username = username
        self.host_token = host_token
        self.requested_color = "#2563EB"


class RoomRoleTests(unittest.TestCase):
    def test_creator_token_restores_host_role_and_roles_are_server_managed(self):
        manager = SessionManager()
        room_id = manager.create_room("Role test")
        room = manager.get_room(room_id)
        host_token = room["host_token"]

        host = FakeClient("Faculty", host_token)
        ok, host_id = manager.join_room(room_id, host)
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, host_id), "host")

        student = FakeClient("Student")
        ok, student_id = manager.join_room(room_id, student)
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, student_id), "student")

        ok, role = manager.set_role(room_id, host_id, student_id, "assistant")
        self.assertTrue(ok)
        self.assertEqual(role, "assistant")
        self.assertEqual(manager.get_role(room_id, student_id), "assistant")

        ok, _ = manager.set_role(room_id, student_id, host_id, "assistant")
        self.assertFalse(ok)

        manager.leave_room(room_id, host_id)
        reconnect = FakeClient("Faculty", host_token)
        ok, new_host_id = manager.join_room(room_id, reconnect)
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, new_host_id), "host")

    def test_duplicate_usernames_are_rejected_case_insensitively(self):
        manager = SessionManager()
        room_id = manager.create_room("Duplicate test")
        first = FakeClient("Alice")
        self.assertTrue(manager.join_room(room_id, first)[0])
        second = FakeClient("aLiCe")
        ok, reason = manager.join_room(room_id, second)
        self.assertFalse(ok)
        self.assertIn("already in use", reason)


if __name__ == "__main__":
    unittest.main()
