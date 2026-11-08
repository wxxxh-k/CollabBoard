"""Create / join / rejoin flows with the role chosen on the login screen.

These use a real CollabBoardServer and the real client SyncManager over TCP,
i.e. the same code path the Create Room and Join Room buttons trigger.
"""
import threading
import time
import unittest

from client.network import NetworkClient
from client.state_manager import StateManager
from client.sync_manager import SyncManager
from server.server import CollabBoardServer
from server.session_manager import SessionManager
from common.user_colors import StrokeColorResolver, build_viewer_color_map


class FakeClient:
    def __init__(self, username, role=None, host_token=None):
        self.username = username
        self.requested_role = role
        self.host_token = host_token
        self.requested_color = "#2563EB"


class SessionRoleTests(unittest.TestCase):
    def test_selected_role_is_granted_and_host_cannot_be_claimed_by_others(self):
        manager = SessionManager()
        room_id = manager.create_room("R", "pw", owner_handler=object())
        token = manager.get_room(room_id)["host_token"]

        ok, host_id = manager.join_room(room_id, FakeClient("Hana", "host", token), "pw")
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, host_id), "host")

        ok, aid = manager.join_room(room_id, FakeClient("Asha", "assistant"), "pw")
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, aid), "assistant")
        ok, sid = manager.join_room(room_id, FakeClient("Sam", "student"), "pw")
        self.assertEqual(manager.get_role(room_id, sid), "student")

        ok, reason = manager.join_room(room_id, FakeClient("Mallory", "host"), "pw")
        self.assertFalse(ok)
        self.assertIn("already has a Host", reason)

    def test_host_rejoins_by_username_but_cannot_downgrade_by_accident(self):
        manager = SessionManager()
        room_id = manager.create_room("R", None, owner_handler=object())
        token = manager.get_room(room_id)["host_token"]
        _, hid = manager.join_room(room_id, FakeClient("Hana", "host", token))
        manager.leave_room(room_id, hid)

        ok, reason = manager.join_room(room_id, FakeClient("Hana", "student"))
        self.assertFalse(ok)
        self.assertIn("Host of this room", reason)
        ok, hid2 = manager.join_room(room_id, FakeClient("hana", "host"))  # token lost, same user
        self.assertTrue(ok)
        self.assertEqual(manager.get_role(room_id, hid2), "host")

    def test_host_assigned_role_is_not_mixed_up_with_other_users(self):
        manager = SessionManager()
        room_id = manager.create_room("R", None, owner_handler=object())
        token = manager.get_room(room_id)["host_token"]
        _, hid = manager.join_room(room_id, FakeClient("Hana", "host", token))
        _, sid = manager.join_room(room_id, FakeClient("Sam", "student"))
        _, oid = manager.join_room(room_id, FakeClient("Other", "student"))
        manager.set_role(room_id, hid, sid, "assistant")
        self.assertEqual(manager.get_role(room_id, sid), "assistant")
        self.assertEqual(manager.get_role(room_id, oid), "student")
        self.assertEqual(manager.get_role(room_id, hid), "host")

    def test_resolve_room_id_ignores_case_and_never_creates(self):
        manager = SessionManager()
        room_id = manager.create_room("R", None, room_id="AbC123")
        before = set(manager.rooms)
        self.assertEqual(manager.resolve_room_id("abc123"), room_id)
        self.assertIsNone(manager.resolve_room_id("nope"))
        self.assertEqual(set(manager.rooms), before)


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.server = CollabBoardServer(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        while (self.server.server_socket is None or
               self.server.server_socket.getsockname()[1] == 0) and time.time() < deadline:
            time.sleep(0.01)
        self.port = self.server.server_socket.getsockname()[1]
        self.clients = []

    def tearDown(self):
        for sync in self.clients:
            sync.disconnect()
        self.server.stop()
        self.thread.join(timeout=2)

    def new(self):
        sync = SyncManager(NetworkClient(), StateManager())
        self.clients.append(sync)
        return sync

    def create(self, username, password, role="host"):
        sync = self.new()
        ok = sync.join_room("127.0.0.1", self.port, "", username, password, "#2563EB", True, role=role)
        return sync, ok

    def join(self, username, room, password, role):
        sync = self.new()
        ok = sync.join_room("127.0.0.1", self.port, room, username, password, "#2563EB", False, role=role)
        return sync, ok

    def room_count(self):
        return len(self.server.session_manager.rooms)

    def test_create_room_generates_unique_ids_and_host_role(self):
        a, ok_a = self.create("Alice", "secret")
        b, ok_b = self.create("Bob", "")
        self.assertTrue(ok_a and ok_b)
        self.assertEqual(a.role, "host")
        self.assertNotEqual(a.room_id, b.room_id)
        self.assertTrue(a.room_id in self.server.session_manager.rooms)

    def test_create_requires_host_role(self):
        for role in ("assistant", "student"):
            sync, ok = self.create("Carol", "pw", role=role)
            self.assertFalse(ok)
            self.assertIn("Only the Host role", sync.last_error)
        self.assertEqual(self.room_count(), 1)  # only the built-in default room

    def test_join_with_correct_and_incorrect_credentials(self):
        host, _ = self.create("Alice", "secret")
        rooms = self.room_count()

        sync, ok = self.join("Bob", host.room_id, "secret", "student")
        self.assertTrue(ok)
        self.assertEqual(sync.role, "student")
        self.assertEqual(sync.room_id, host.room_id)

        sync, ok = self.join("Cat", host.room_id, "wrong", "student")
        self.assertFalse(ok)
        self.assertEqual(sync.last_error, "Incorrect password")

        sync, ok = self.join("Dan", host.room_id, "", "student")
        self.assertFalse(ok)
        self.assertEqual(sync.last_error, "Password required")

        sync, ok = self.join("Eve", "nosuchroom", "secret", "student")
        self.assertFalse(ok)
        self.assertEqual(sync.last_error, "Room does not exist")

        self.assertEqual(self.room_count(), rooms)  # join never creates a room

    def test_room_id_is_matched_ignoring_case_and_whitespace(self):
        host, _ = self.create("Alice", "secret")
        sync, ok = self.join("Bob", "  " + host.room_id.upper() + " ", "secret", "assistant")
        self.assertTrue(ok, sync.last_error)
        self.assertEqual(sync.room_id, host.room_id)
        self.assertEqual(sync.role, "assistant")

    def test_selected_role_is_kept_for_each_user(self):
        host, _ = self.create("Alice", "pw")
        asst, ok1 = self.join("Asha", host.room_id, "pw", "assistant")
        stud, ok2 = self.join("Sam", host.room_id, "pw", "student")
        self.assertTrue(ok1 and ok2)
        manager = self.server.session_manager
        self.assertEqual(manager.get_role(host.room_id, host.client_id), "host")
        self.assertEqual(manager.get_role(host.room_id, asst.client_id), "assistant")
        self.assertEqual(manager.get_role(host.room_id, stud.client_id), "student")

    def test_second_host_is_rejected(self):
        host, _ = self.create("Alice", "pw")
        sync, ok = self.join("Mallory", host.room_id, "pw", "host")
        self.assertFalse(ok)
        self.assertIn("already has a Host", sync.last_error)

    def test_rejoin_keeps_identity_without_creating_a_room(self):
        host, _ = self.create("Alice", "pw")
        student, _ = self.join("Sam", host.room_id, "pw", "student")
        room_id = host.room_id
        rooms = self.room_count()

        host.disconnect()
        student.disconnect()
        time.sleep(0.3)

        new_student, ok = self.join("Sam", room_id, "pw", "student")
        self.assertTrue(ok, new_student.last_error)
        self.assertEqual(new_student.role, "student")
        # A fresh app run: the private host token is gone, but it is still Alice.
        new_host, ok = self.join("Alice", room_id, "pw", "host")
        self.assertTrue(ok, new_host.last_error)
        self.assertEqual(new_host.role, "host")
        self.assertEqual(self.room_count(), rooms)

        # Host cannot silently turn into a different role.
        other, ok = self.join("Alice", room_id, "pw", "student")
        self.assertFalse(ok)

    def test_failed_join_can_be_retried_immediately(self):
        host, _ = self.create("Alice", "pw")
        sync = self.new()
        self.assertFalse(sync.join_room("127.0.0.1", self.port, host.room_id, "Bob", "bad",
                                        "#2563EB", False, role="student"))
        self.assertTrue(sync.join_room("127.0.0.1", self.port, host.room_id, "Bob", "pw",
                                       "#2563EB", False, role="student"))

    def test_default_room_first_host_then_others(self):
        first, ok = self.join("Alice", "default", "", "host")
        self.assertTrue(ok)
        self.assertEqual(first.role, "host")
        second, ok = self.join("Bob", "default", "", "student")
        self.assertTrue(ok)
        self.assertEqual(second.role, "student")

    def test_invalid_role_is_rejected(self):
        sync, ok = self.join("Bob", "default", "", "superuser")
        self.assertFalse(ok)
        self.assertEqual(sync.last_error, "Invalid role")

    def test_joined_room_is_delivered_before_the_participant_list(self):
        """A student joining a room with a host must see the host as online.

        joined_room used to be re-queued behind the snapshot/participant events,
        so the client processed the participant list first and then marked every
        peer offline ("host left the room", composer disabled).
        """
        host, _ = self.create("Alice", "pw")

        class SlowPoll(NetworkClient):
            def get_message(self):
                time.sleep(0.15)  # let the server's whole burst arrive first
                return super().get_message()

        events = []
        sync = SyncManager(SlowPoll(), StateManager(), on_event=events.append)
        self.clients.append(sync)
        self.assertTrue(sync.join_room("127.0.0.1", self.port, host.room_id, "Sam", "pw",
                                       "#2563EB", False, role="student"))
        deadline = time.time() + 3
        while not any(e["type"] == "participants" for e in events) and time.time() < deadline:
            time.sleep(0.05)
        kinds = [e["type"] for e in events]
        self.assertEqual(kinds[0], "joined_room")
        self.assertIn("participants", kinds)
        self.assertEqual(sync.client_id, events[0]["client_id"])


class StrokeColorTests(unittest.TestCase):
    def test_departed_author_keeps_each_strokes_own_color(self):
        old_author, viewer = "old-session", "me"
        history = [
            {"sequence": 1, "user_id": old_author, "data": {"tool": "pen", "color": "#2563EB"}},
            {"sequence": 2, "user_id": old_author, "data": {"tool": "pen", "color": "#DC2626"}},
        ]
        # Same inputs main_window builds: the viewer is live, the author is not,
        # and their first stroke color is their mapped preference.
        color_map = build_viewer_color_map(viewer, "#16A36A", [
            {"client_id": viewer, "preferred_color": "#16A36A"},
            {"client_id": old_author, "preferred_color": "#2563EB"}])
        prefs = {viewer: "#16A36A", old_author: "#2563EB"}
        resolver = StrokeColorResolver()
        self.assertEqual([resolver.resolve(e, color_map, prefs) for e in history],
                         ["#2563EB", "#DC2626"])


if __name__ == "__main__":
    unittest.main()
