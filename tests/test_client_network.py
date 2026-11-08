"""Exercise the real NetworkClient + SyncManager against a real server (no Tkinter)."""
import threading
import time
import unittest

from client.network import NetworkClient
from client.state_manager import StateManager
from client.sync_manager import SyncManager
from server.server import CollabBoardServer


class Peer:
    def __init__(self, port, username):
        self.events = []
        self.lock = threading.Lock()
        self.network = NetworkClient()
        self.sync = SyncManager(self.network, StateManager(), self._on_event)
        assert self.sync.join_room("127.0.0.1", port, "default", username)
        self.wait(lambda: self.sync.client_id is not None)
        self.username = username

    def _on_event(self, event):
        with self.lock:
            self.events.append(event)

    def of_type(self, kind):
        with self.lock:
            return [e for e in self.events if e.get("type") == kind]

    def wait(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        raise AssertionError("condition not met in time")


class ClientNetworkTests(unittest.TestCase):
    def setUp(self):
        self.server = CollabBoardServer(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        while (self.server.server_socket is None
               or self.server.server_socket.getsockname()[1] == 0) and time.time() < deadline:
            time.sleep(0.01)
        self.port = self.server.server_socket.getsockname()[1]
        self.peers = []

    def tearDown(self):
        for peer in self.peers:
            peer.sync.disconnect()
        self.server.stop()

    def peer(self, name):
        p = Peer(self.port, name)
        self.peers.append(p)
        return p

    def test_group_and_private_through_client_stack(self):
        a, b, c = self.peer("Ann"), self.peer("Ben"), self.peer("Cat")
        a.sync.send_chat("hello all")
        for p in (a, b, c):
            p.wait(lambda p=p: len(p.of_type("chat")) == 1)
        self.assertTrue(a.sync.send_private_message(b.sync.client_id, "just for Ben"))
        b.wait(lambda: len(b.of_type("private_message")) == 1)
        a.wait(lambda: len(a.of_type("private_message")) == 1)  # echo to sender
        time.sleep(0.3)
        self.assertEqual(c.of_type("private_message"), [])
        self.assertEqual(b.of_type("private_message")[0]["message"], "just for Ben")

    def test_sends_are_queued_in_order_and_do_not_block(self):
        a, b = self.peer("Ann"), self.peer("Ben")
        start = time.time()
        for index in range(300):
            self.assertTrue(a.sync.send_chat(f"m{index}"))
        self.assertLess(time.time() - start, 1.0)  # queueing only, no socket I/O inline
        b.wait(lambda: len(b.of_type("chat")) == 300, timeout=5)
        self.assertEqual([e["message"] for e in b.of_type("chat")], [f"m{i}" for i in range(300)])

    def test_send_after_disconnect_returns_false_and_leave_is_flushed(self):
        a, b = self.peer("Ann"), self.peer("Ben")
        a.sync.disconnect()  # queues leave_room, flushes it, then closes
        b.wait(lambda: len(b.of_type("participant_left")) == 1)
        self.assertFalse(a.sync.send_private_message("x", "nope"))
        self.assertFalse(a.sync.send_chat("nope"))

    def test_invalid_recipient_reports_failure_event_without_crashing(self):
        a = self.peer("Ann")
        a.sync.send_private_message("not-a-client", "hi")
        a.wait(lambda: len(a.of_type("private_message_failed")) == 1)


if __name__ == "__main__":
    unittest.main()
