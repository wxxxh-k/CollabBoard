"""End-to-end tests for group chat and private (one-to-one) messaging.

Every test talks to a real CollabBoardServer over real TCP sockets using the
same newline-delimited JSON framing as the application.
"""
import json
import queue
import socket
import threading
import time
import unittest

from server.server import CollabBoardServer


class TestClient:
    """Minimal protocol client with a background reader (like the real client)."""

    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.inbox = queue.Queue()
        self.seen = []
        self.client_id = None
        self.username = None
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        buffer = bytearray()
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    return
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if line.strip():
                        self.inbox.put(json.loads(line.decode("utf-8")))
        except OSError:
            return

    def send(self, message):
        self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

    def join(self, username, room="default"):
        self.username = username
        self.send({"type": "join_room", "room_id": room, "username": username})
        joined = self.wait_for("joined_room")
        self.client_id = joined["client_id"]
        return joined

    def wait_for(self, kind, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                message = self.inbox.get(timeout=max(0.01, deadline - time.time()))
            except queue.Empty:
                break
            self.seen.append(message)
            if message["type"] == kind:
                return message
        raise AssertionError(f"{self.username}: no '{kind}' message received")

    def expect_none(self, kind, timeout=0.5):
        """Assert that no message of this kind arrives within the timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                message = self.inbox.get(timeout=max(0.01, deadline - time.time()))
            except queue.Empty:
                break
            self.seen.append(message)
            if message["type"] == kind:
                raise AssertionError(f"{self.username} unexpectedly received {message}")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class MessagingTests(unittest.TestCase):
    def setUp(self):
        self.server = CollabBoardServer(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        while (self.server.server_socket is None
               or self.server.server_socket.getsockname()[1] == 0) and time.time() < deadline:
            time.sleep(0.01)
        self.port = self.server.server_socket.getsockname()[1]
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.server.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=2)

    def client(self, username, room="default"):
        c = TestClient(self.port)
        self.clients.append(c)
        c.join(username, room)
        return c

    def three(self):
        return self.client("Alice"), self.client("Bob"), self.client("Carol")

    # ---------------------------------------------------------------- group
    def test_group_message_reaches_everyone_in_room(self):
        alice, bob, carol = self.three()
        bob.send({"type": "chat", "message": "hello team"})
        for c in (alice, bob, carol):
            message = c.wait_for("chat")
            self.assertEqual(message["message"], "hello team")
            self.assertEqual(message["username"], "Bob")
            self.assertEqual(message["client_id"], bob.client_id)
            self.assertEqual(message["scope"], "group")
            self.assertIsInstance(message["ts"], int)

    def test_group_message_does_not_leave_room(self):
        alice = self.client("Alice")
        other_room = self._create_room(alice)
        dave = self.client("Dave", other_room)
        alice.send({"type": "chat", "message": "default room only"})
        alice.wait_for("chat")
        dave.expect_none("chat")

    # -------------------------------------------------------------- private
    def test_private_message_only_reaches_sender_and_recipient(self):
        alice, bob, carol = self.three()
        alice.send({"type": "private_message", "to_client_id": bob.client_id,
                    "message": "psst, secret"})
        to_bob = bob.wait_for("private_message")
        echo = alice.wait_for("private_message")
        for message in (to_bob, echo):
            self.assertEqual(message["message"], "psst, secret")
            self.assertEqual(message["from_client_id"], alice.client_id)
            self.assertEqual(message["to_client_id"], bob.client_id)
            self.assertEqual(message["from_username"], "Alice")
            self.assertEqual(message["to_username"], "Bob")
        self.assertEqual(to_bob["message_id"], echo["message_id"])
        # Carol must see nothing private, and her connection must still work.
        carol.expect_none("private_message")
        carol.expect_none("private_message_failed", timeout=0.1)
        alice.send({"type": "chat", "message": "group still works"})
        self.assertEqual(carol.wait_for("chat")["message"], "group still works")
        for c in (alice, bob, carol):
            for seen in c.seen:
                if c is carol:
                    self.assertNotEqual(seen["type"], "private_message")
                    self.assertNotIn("psst, secret", json.dumps(seen))

    def test_private_conversation_is_two_way_and_group_unaffected(self):
        alice, bob, carol = self.three()
        alice.send({"type": "private_message", "to_client_id": bob.client_id, "message": "hi Bob"})
        bob.wait_for("private_message")
        bob.send({"type": "private_message", "to_client_id": alice.client_id, "message": "hi Alice"})
        reply = alice.wait_for("private_message")  # first one is Alice's own echo
        if reply["message"] != "hi Alice":
            reply = alice.wait_for("private_message")
        self.assertEqual(reply["from_client_id"], bob.client_id)
        carol.expect_none("private_message")

    def test_sender_identity_cannot_be_spoofed(self):
        alice, bob, carol = self.three()
        alice.send({"type": "private_message", "to_client_id": bob.client_id,
                    "message": "spoof", "from_client_id": carol.client_id,
                    "from_username": "Carol"})
        message = bob.wait_for("private_message")
        self.assertEqual(message["from_client_id"], alice.client_id)
        self.assertEqual(message["from_username"], "Alice")

    def test_invalid_recipients_are_rejected_to_sender_only(self):
        alice, bob, _ = self.three()
        cases = [
            ({"to_client_id": "does-not-exist", "message": "x"}, "not in this room"),
            ({"to_client_id": alice.client_id, "message": "x"}, "yourself"),
            ({"message": "x"}, "Invalid recipient"),
            ({"to_client_id": 123, "message": "x"}, "Invalid recipient"),
            ({"to_client_id": bob.client_id, "message": "   "}, "1-2000"),
            ({"to_client_id": bob.client_id, "message": "a" * 2001}, "1-2000"),
            ({"to_client_id": bob.client_id, "message": 42}, "1-2000"),
        ]
        for payload, expected in cases:
            alice.send({"type": "private_message", **payload})
            failure = alice.wait_for("private_message_failed")
            self.assertIn(expected, failure["reason"])
        bob.expect_none("private_message")
        bob.expect_none("private_message_failed", timeout=0.1)

    def test_cannot_message_user_in_another_room(self):
        alice = self.client("Alice")
        other_room = self._create_room(alice)
        dave = self.client("Dave", other_room)
        alice.send({"type": "private_message", "to_client_id": dave.client_id,
                    "message": "cross-room"})
        failure = alice.wait_for("private_message_failed")
        self.assertIn("not in this room", failure["reason"])
        dave.expect_none("private_message")

    def test_message_to_disconnected_user_fails_gracefully(self):
        alice, bob, carol = self.three()
        bob_id = bob.client_id
        bob.close()
        left = alice.wait_for("participant_left")
        self.assertEqual(left["client_id"], bob_id)
        self.assertEqual(left["username"], "Bob")
        alice.send({"type": "private_message", "to_client_id": bob_id, "message": "you there?"})
        failure = alice.wait_for("private_message_failed")
        self.assertEqual(failure["to_client_id"], bob_id)
        self.assertEqual(failure["text"], "you there?")
        # Server and remaining clients are unaffected.
        alice.send({"type": "chat", "message": "still alive"})
        self.assertEqual(carol.wait_for("chat")["message"], "still alive")

    def test_private_message_requires_a_room(self):
        sock = TestClient(self.port)
        self.clients.append(sock)
        sock.send({"type": "private_message", "to_client_id": "x", "message": "hi"})
        self.assertIn("Join a room", sock.wait_for("error")["message"])

    # -------------------------------------------------------------- helpers
    def _create_room(self, client):
        client.send({"type": "create_room", "room_name": "Second room"})
        return client.wait_for("room_created")["room_id"]


if __name__ == "__main__":
    unittest.main()
